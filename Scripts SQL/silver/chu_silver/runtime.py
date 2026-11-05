# -*- coding: utf-8 -*-
"""Execution Spark 1.6 : traceabilite, controles, sorties immuables par tentative."""
import hashlib
import json
import time
from . import __version__
from . import contracts as C
from . import rules
from .readers import read_records

META = [('_record_id', 'STRING'), ('_status', 'STRING'), ('_motif', 'STRING'),
        ('_warnings', 'STRING'), ('_payload', 'STRING')]


class Run(object):
    def __init__(self, sc, sql, config, lot, attempt, key, key_version, excluded):
        from pyspark import StorageLevel
        self.sc, self.sql, self.config = sc, sql, config
        self.lot, self.attempt, self.key = lot, attempt, key
        self.key_version, self.excluded = key_version, excluded
        self.level = StorageLevel.DISK_ONLY
        self.root = config['runs_root'].rstrip('/') + '/' + lot + '/' + attempt
        self.audit = self.root + '/audit'
        self.metrics, self.outputs, self.fingerprints = {}, {}, {}
        self.pending_cache = []
        self.started = time.time()
        self.Path = sc._jvm.org.apache.hadoop.fs.Path
        self.fs = self.Path(self.root).getFileSystem(sc._jsc.hadoopConfiguration())
        if self.fs.exists(self.Path(self.root)):
            raise ValueError('Tentative deja presente : utiliser un nouvel attempt-id')
        self.fs.mkdirs(self.Path(self.audit))
        for name, spec in sorted(config['sources'].items()):
            self.fingerprints[name] = self.fingerprint(self.path(spec))
        # Identite de registre : fichiers immuables + regles. Jamais un hash de nom.
        manifest = json.dumps(self.fingerprints, sort_keys=True).encode('utf-8')
        self.input_id = hashlib.sha256(manifest).hexdigest()
        self.write_json('manifest_entrees.json', self.fingerprints)

    def path(self, spec):
        return self.config['bronze_root'].rstrip('/') + '/' + spec['path']

    def fingerprint(self, path):
        obj = self.Path(path)
        stat = self.fs.getFileStatus(obj)
        if not stat.isFile():
            raise ValueError('Un fichier est attendu')
        checksum = self.fs.getFileChecksum(obj)
        if checksum is None:
            raise ValueError('Empreinte HDFS indisponible')
        return {'path': path, 'length': stat.getLen(), 'modified': stat.getModificationTime(),
                'checksum': checksum.toString()}

    def write_text(self, path, text):
        target = self.Path(path)
        self.fs.mkdirs(target.getParent())
        stream = self.fs.create(target, False)
        try:
            # Texte JSON/SQL exclusivement : aucune donnee individuelle.
            stream.write(bytearray(text.encode('utf-8')))
        finally:
            stream.close()

    def write_json(self, name, value):
        self.write_text(self.audit + '/' + name,
                        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True))

    def records(self, source):
        spec = self.config['sources'][source]
        return read_records(self.sc, self.path(spec), source, spec,
                            self.config.get('small_file_limit_bytes', 8388608))

    def normalized(self, source, kind, spec, options=None, records=None):
        """Une passe Python par partition ; pas de relecture par attribut/UDF."""
        key = self.key
        opts = dict(options or {})
        opts['excluded'] = self.excluded
        names = [name for name, unused in spec]
        records = records if records is not None else self.records(source)

        def batch(iterator):
            for record_id, row in iterator:
                values, status, motif, warnings = rules.transform(kind, row, key, opts)
                business = [values.get(name) for name in names]
                yield tuple(business + [record_id, status, motif, warnings,
                                        rules.payload_hash(business)])
        return self.sql.createDataFrame(records.mapPartitions(batch), C.schema(spec + META))

    def annotate(self, df, condition, motif, category='REJECT'):
        from pyspark.sql import functions as F
        # Une seule categorie terminale : ne pas recompter les erreurs anterieures.
        condition = (F.col('_status') == 'VALID') & condition
        return (df.withColumn('_motif', F.when(condition, F.lit(motif)).otherwise(F.col('_motif')))
                .withColumn('_status', F.when(condition, F.lit(category)).otherwise(F.col('_status'))))

    def reference(self, df, key, reference, motif):
        from pyspark.sql import functions as F
        right = reference.select(F.col(key).alias('_reference_key')).withColumn('_found', F.lit(1))
        joined = df.join(right, df[key] == right['_reference_key'], 'left_outer')
        joined = self.annotate(joined, F.col('_found').isNull(), motif)
        return joined.drop('_reference_key').drop('_found')

    def unique(self, df, keys):
        """Pas de premiere ligne Spark : conflits rejetes, repetition stable."""
        from pyspark.sql import functions as F
        # Les deux agregations reutilisent la meme lecture/normalisation.
        df.persist(self.level)
        self.pending_cache.append(df)
        active = df.filter(F.col('_status') == 'VALID')
        variants = active.groupBy(*keys).agg(F.countDistinct('_payload').alias('_variants'))
        df = df.join(variants, keys, 'left_outer')
        df = self.annotate(df, F.col('_variants') > 1, 'CONFLIT_CLE')
        first = active.groupBy(*(keys + ['_payload'])).agg(F.min('_record_id').alias('_first'))
        df = df.join(first, keys + ['_payload'], 'left_outer')
        df = self.annotate(df, F.col('_record_id') != F.col('_first'),
                           'REPETITION_IDENTIQUE', 'DUPLICATE')
        return df.drop('_first').drop('_variants')

    def finish(self, label, df, table=None, keys=None):
        """Materialise une seule fois ; bilan exclusif et rejets minimises."""
        from pyspark.sql import functions as F
        df.persist(self.level)
        grouped = df.groupBy('_status', '_motif', '_warnings').count().collect()
        metrics = {'read': 0, 'VALID': 0, 'REJECT': 0, 'DUPLICATE': 0,
                   'ALTERNATIVE': 0, 'EXCLUDE': 0, 'details': []}
        for row in grouped:
            count = row['count']
            metrics['read'] += count
            metrics[row['_status']] += count
            metrics['details'].append({'status': row['_status'], 'motif': row['_motif'],
                                       'warnings': row['_warnings'], 'count': count})
        self.metrics[label] = metrics
        # Pas de valeurs brutes ni de pseudonyme dans les rejets techniques.
        rejected = df.filter(F.col('_status') != 'VALID').select('_record_id', '_status', '_motif', '_warnings')
        rejected.write.mode('error').orc(self.root + '/rejets/' + label)
        accepted = df.filter(F.col('_status') == 'VALID')
        if table:
            self.save(table, accepted.select(*C.names(table)), metrics['VALID'])
            accepted = self.load(table)
            df.unpersist()
        self.write_json('qualite_' + label + '.json', metrics)
        for previous in self.pending_cache:
            previous.unpersist()
        self.pending_cache = []
        # Sans table, l'appelant libere df apres avoir materialise ses derives.
        return accepted, df

    def save(self, table, df, expected=None):
        from pyspark.sql import functions as F
        started = time.time()
        df = df.select(*C.names(table))
        path = self.root + '/tables/' + table
        partitions = self.config.get('output_partitions', {}).get(table, 4)
        if partitions < 1:
            raise ValueError('Nombre de partitions invalide')
        # Spark 1.6 : pas de repartitionByRange ni de coalesce(1) massif.
        df.repartition(partitions).write.mode('error').orc(path)
        readback = self.sql.read.orc(path)
        actual = readback.count()
        if expected is not None and actual != expected:
            raise ValueError('Cardinalite modifiee pour ' + table)
        if readback.schema != C.schema(C.TABLES[table]):
            # ORC peut rendre nullable une colonne non nullable ; notre
            # contrat utilise nullable=True, seuls noms/types sont imposes.
            actual_schema = [(f.name, f.dataType.simpleString()) for f in readback.schema.fields]
            expected_schema = [(f.name, f.dataType.simpleString()) for f in C.schema(C.TABLES[table]).fields]
            if actual_schema != expected_schema:
                raise ValueError('Schema relu incompatible : ' + table)
        completeness = readback.agg(*[
            F.sum(F.when(F.col(name).isNull(), 1).otherwise(0)).alias(name)
            for name in C.names(table)]).collect()[0].asDict()
        nulls = dict((name, int(value or 0)) for name, value in completeness.items())
        self.outputs[table] = {'path': path, 'rows': actual, 'nulls': nulls,
            'completeness': dict((name, (float(actual - n) / actual if actual else None))
                                 for name, n in nulls.items()),
            'seconds': round(time.time() - started, 3), 'partitions_requested': partitions,
            'schema': C.TABLES[table]}

    def load(self, table):
        if table not in self.outputs:
            raise ValueError('Dependance non produite : ' + table)
        return self.sql.read.orc(self.outputs[table]['path'])

    def check_unique(self, table):
        df = self.load(table)
        keys = C.KEYS[table]
        if df.groupBy(*keys).count().filter('count > 1').limit(1).count():
            raise ValueError('Cle dupliquee dans ' + table)
        from pyspark.sql import functions as F
        condition = F.lit(False)
        for key in keys:
            condition = condition | F.col(key).isNull()
        if df.filter(condition).limit(1).count():
            raise ValueError('Cle NULL dans ' + table)

    def complete(self, prepare_publication=True):
        """Controle global puis DDL de publication versionnee (sans bascule)."""
        if set(self.outputs) != set(C.TABLES):
            raise ValueError('Tables Silver incompletes')
        for name in sorted(self.outputs):
            self.check_unique(name)
        from pyspark.sql import functions as F
        for child, key, parent in [
                ('consultation', 'id_patient', 'patient'),
                ('consultation', 'code_diag', 'diagnostic'),
                ('consultation', 'id_prof_sante', 'professionnel'),
                ('hospitalisation', 'id_patient', 'patient'),
                ('hospitalisation', 'code_diag', 'diagnostic'),
                ('hospitalisation', 'identifiant_organisation', 'etablissement'),
                ('activite', 'id_prof_sante', 'professionnel'),
                ('activite', 'identifiant_organisation', 'etablissement'),
                ('deces', 'defunt_key', 'defunt'),
                ('satisfaction', 'region', 'region')]:
            left = self.load(child)
            right = self.load(parent).select(F.col(key).alias('_reference_key'))
            joined = left.join(right, left[key] == right['_reference_key'], 'left_outer')
            if joined.filter(F.col('_reference_key').isNull()).limit(1).count():
                raise ValueError('Reference orpheline : ' + child + ' -> ' + parent)
        if self.outputs['deces']['rows'] != self.outputs['defunt']['rows']:
            raise ValueError('Nombre de deces et de defunts different')
        for table in ('patient', 'consultation', 'hospitalisation'):
            if self.load(table).filter(~F.col('id_patient').rlike('^[0-9a-f]{64}$')).limit(1).count():
                raise ValueError('Pseudonyme invalide dans ' + table)
        for label, metric in self.metrics.items():
            if 'derived_unknown' in metric:
                continue
            counted = sum(metric.get(status, 0) for status in
                          ('VALID', 'REJECT', 'DUPLICATE', 'ALTERNATIVE', 'EXCLUDE'))
            if counted != metric['read']:
                raise ValueError('Reconciliation invalide : ' + label)
        for name, spec in sorted(self.config['sources'].items()):
            if self.fingerprint(self.path(spec)) != self.fingerprints[name]:
                raise ValueError('Source modifiee pendant le traitement : ' + name)
        if not prepare_publication:
            self.write_json('rapport_controles.json', {'status': 'CHECKS_OK_NOT_READY',
                'reason': 'Lot historique : pseudonymisation professionnelle a mettre en coherence.',
                'lot_id': self.lot, 'attempt_id': self.attempt,
                'outputs': self.outputs, 'metrics': self.metrics})
            print('SILVER_CHECKS_OK_NOT_READY : ' + self.audit)
            return
        locations = dict((name, value['path']) for name, value in self.outputs.items())
        db = 'silver_' + self.lot.lower() + '_' + self.attempt.lower()
        # Les noms lot/tentative sont valides par le lanceur.
        self.write_text(self.audit + '/publication.hql', C.publication_sql(db, locations))
        # La bascule commune est volontaire et distincte ; Gold doit etre arrete.
        stable = ['CREATE DATABASE IF NOT EXISTS silver;']
        for name in sorted(C.TABLES):
            stable.append('CREATE OR REPLACE VIEW silver.`%s` AS SELECT * FROM `%s`.`%s`;' %
                          (name, db, name))
        for alias, name in sorted(C.ALIASES.items()):
            stable.append('CREATE OR REPLACE VIEW silver.`%s` AS SELECT * FROM `%s`.`%s`;' %
                          (alias, db, name))
        self.write_text(self.audit + '/activation.hql', '\n'.join(stable) + '\n')
        self.write_json('rapport_final.json', {'status': 'READY_NOT_PUBLISHED',
            'lot_id': self.lot, 'attempt_id': self.attempt, 'version': __version__,
            'spark_version': self.sc.version, 'key_version': self.key_version,
            'inputs_id': self.input_id, 'outputs': self.outputs, 'metrics': self.metrics,
            'hive_database': db, 'seconds': round(time.time() - self.started, 3)})
        print('SILVER_READY : ' + self.audit)
