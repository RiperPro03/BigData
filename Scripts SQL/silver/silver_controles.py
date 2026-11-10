# -*- coding: utf-8 -*-
"""Prerequis et controles qualite Silver."""
import subprocess
import sys
import time

def verifier_avant(config):
    """Arrete la chaine si HDFS, les entrees ou Hive ne sont pas disponibles."""
    def command(args):
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        if proc.returncode:
            raise RuntimeError('Prerequis indisponible : ' + args[0])
        return out
    state = command(['hdfs', 'dfsadmin', '-safemode', 'get']).decode('utf-8', 'replace')
    if 'OFF' not in state.upper():
        raise RuntimeError('HDFS est en mode sans ecriture ou son etat est inconnu')
    for name, spec in sorted(config['sources'].items()):
        path = config['bronze_root'].rstrip('/') + '/' + spec['path']
        try:
            command(['hdfs', 'dfs', '-test', '-f', path])
        except RuntimeError:
            raise RuntimeError('Fichier Bronze absent ou inaccessible : ' + name + ' (' + path + ')')
    command(['beeline', '-u', 'jdbc:hive2://localhost:10000/default', '-n', 'cloudera',
             '--force=false', '--silent=true', '-e', 'SELECT 1'])
    print('SILVER_PREFLIGHT_OK')
    sys.stdout.flush()

def verifier_hmac(sc, key):
    import silver_hors_deces as rules
    expected = rules.pseudonym('42', key)
    if sc.parallelize(['42'], 1).map(lambda x: rules.pseudonym(x, key)).collect() != [expected]:
        raise ValueError('Test HMAC driver/worker non concordant')

def verifier_professionnels(run):
    from pyspark.sql import functions as F
    for table in ('professionnel', 'consultation', 'activite'):
        invalid = F.col('id_prof_sante').isNull() | ~F.col('id_prof_sante').rlike('^[0-9a-f]{64}$')
        if run.load(table).filter(invalid).limit(1).count():
            raise ValueError('Pseudonyme professionnel invalide : ' + table)

def bilan_finess(run):
    """Compte les lignes de satisfaction associees a un etablissement Silver.

    Le resultat est informatif : une difference de perimetre ne rejette pas
    automatiquement un site. La cle d'organisation derivee du FINESS est utilisee.
    """
    from pyspark.sql import functions as F
    sites = run.load('etablissement').select(
        F.col('identifiant_organisation').alias('_site_reference'))
    satisfaction = run.load('satisfaction')
    joined = satisfaction.join(sites,
        satisfaction['identifiant_organisation'] == sites['_site_reference'], 'left_outer')
    row = joined.agg(F.count(F.lit(1)).alias('total'),
        F.sum(F.when(F.col('_site_reference').isNotNull(), 1).otherwise(0)).alias('matches')).collect()[0]
    total, matched = int(row['total']), int(row['matches'] or 0)
    return {'lignes_satisfaction': total, 'lignes_avec_etablissement': matched,
            'lignes_sans_etablissement': total - matched,
            'taux_correspondance': float(matched) / total if total else None,
            'regle': 'identifiant_organisation', 'statut': 'INFORMATIF'}

class Checks(object):
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

    def check_unique(self, table):
        import silver_pipeline as pipeline
        df = self.load(table)
        keys = pipeline.KEYS[table]
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
        import silver_pipeline as pipeline
        if set(self.outputs) != set(pipeline.TABLES):
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
        self.indicateurs = {'finess_correspondance': bilan_finess(self)}
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
        self.write_text(self.audit + '/publication.hql', pipeline.publication_sql(db, locations))
        # La bascule commune est volontaire et distincte ; Gold doit etre arrete.
        stable = ['CREATE DATABASE IF NOT EXISTS silver;']
        for name in sorted(pipeline.TABLES):
            stable.append('CREATE OR REPLACE VIEW silver.`%s` AS SELECT * FROM `%s`.`%s`;' %
                          (name, db, name))
        for alias, name in sorted(pipeline.ALIASES.items()):
            stable.append('CREATE OR REPLACE VIEW silver.`%s` AS SELECT * FROM `%s`.`%s`;' %
                          (alias, db, name))
        self.write_text(self.audit + '/activation.hql', '\n'.join(stable) + '\n')
        self.write_json('rapport_final.json', {'status': 'READY_NOT_PUBLISHED',
            'lot_id': self.lot, 'attempt_id': self.attempt, 'version': pipeline.__version__,
            'spark_version': self.sc.version, 'key_version': self.key_version,
            'inputs_id': self.input_id, 'outputs': self.outputs, 'metrics': self.metrics,
            'indicateurs': self.indicateurs,
            'hive_database': db, 'seconds': round(time.time() - self.started, 3)})
        print('SILVER_READY : ' + self.audit)



if __name__ == '__main__':
    import silver_pipeline
    silver_pipeline.phase_main('03')
