# -*- coding: utf-8 -*-
"""Orchestration Silver, contrats et services communs Spark 1.6."""
import sys
import os
import re
import json
import hashlib
import hmac
import subprocess
import silver_controles
C = sys.modules[__name__]
__version__ = '2.0.0'

# -*- coding: utf-8 -*-
"""Contrats explicites derives des DDL/DML main (7ed0f68) et des sources.

Un tuple (nom, type Hive) sert aussi a construire le StructType Spark.
Les colonnes de provenance ne font pas partie des tables metier publiees.
"""
PG = {
    "diagnostic": "Code_diag Diagnostic".split(),
    "specialite": "Code_specialite Fonction Specialite".split(),
    "professionnel": "Identifiant Civilite Categorie_professionnelle Nom Prenom Profession Type_identifiant Code_specialite".split(),
    "patient": "Id_patient Nom Prenom Sexe Adresse Ville Code_postal Pays EMail Tel Date Age Num_Secu Groupe_sanguin Poid Taille".split(),
    "consultation": "Num_consultation Id_mut Id_patient Id_prof_sante Code_diag Motif Date Heure_debut Heure_fin".split()
}
ETABLISSEMENT = "adresse cedex code_commune code_postal commune complement_destinataire complement_point_geographique email enseigne_commerciale_site finess_etablissement_juridique finess_site identifiant_organisation indice_repetition_voie mention_distribution numero_voie pays raison_sociale_site siren_site siret_site telecopie telephone telephone_2 type_voie voie".split()
HOSPITALISATION = "Num_Hospitalisation Id_patient identifiant_organisation Code_diagnostic Suite_diagnostic_consultation Date_Entree Jour_Hospitalisation".split()
DECES = "nom prenom sexe date_naissance code_lieu_naissance lieu_naissance pays_naissance date_deces code_lieu_deces numero_acte_deces".split()
SATISFACTION = "finess_geo region score_all_rea_ajust nb_rep_score_all_rea_ajust".split()


def fields(text):
    return [tuple(item.split(':')) for item in text.split()]


TABLES = {
    "diagnostic": fields("code_diag:STRING libelle:STRING"),
    "specialite": fields("code_specialite:STRING fonction:STRING specialite:STRING"),
    "patient": fields("id_patient:STRING sexe:STRING age:INT"),
    # Colonnes auxiliaires retirees apres enrichissement par specialite.
    "professionnel": fields("id_prof_sante:STRING categorie:STRING profession:STRING specialite:STRING"),
    "etablissement": [(name, "STRING") for name in ETABLISSEMENT],
    "activite": fields("id_prof_sante:STRING identifiant_organisation:STRING mode_exercice:STRING"),
    "consultation": fields("num_consultation:INT date_consultation:DATE id_patient:STRING code_diag:STRING id_prof_sante:STRING"),
    "hospitalisation": fields("num_hospitalisation:INT date_entree:DATE id_patient:STRING code_diag:STRING identifiant_organisation:STRING"),
    "satisfaction": fields("finess_geo:STRING identifiant_organisation:STRING annee:SMALLINT region:STRING code_region:STRING score_all_rea_ajust:DOUBLE nb_rep_score_all_rea_ajust:INT"),
    "deces": fields("deces_key:INT date_deces:DATE code_commune_deces:STRING defunt_key:INT code_departement:STRING code_region:STRING libelle_region:STRING statut_rattachement:STRING"),
    "defunt": fields("defunt_key:INT sexe:STRING"),
    "codes_postaux": fields("code_commune_insee:STRING nom_de_la_commune:STRING code_postal:STRING libelle_d_acheminement:STRING"),
    "commune": fields("code_commune_insee:STRING type_commune:STRING code_commune_parent:STRING libelle_commune:STRING code_departement:STRING code_region:STRING libelle_region:STRING statut_rattachement:STRING"),
    "region": fields("code_region:STRING region:STRING")
}
KEYS = {
    "diagnostic": ["code_diag"], "specialite": ["code_specialite"],
    "patient": ["id_patient"], "professionnel": ["id_prof_sante"],
    "etablissement": ["identifiant_organisation"],
    "activite": ["id_prof_sante", "identifiant_organisation"],
    "consultation": ["num_consultation"], "hospitalisation": ["num_hospitalisation"],
    "satisfaction": ["finess_geo", "annee"], "deces": ["deces_key"],
    "defunt": ["defunt_key"], "codes_postaux": ["code_commune_insee"],
    "commune": ["code_commune_insee"], "region": ["region"]
}
ALIASES = {
    "s1_consultation": "consultation", "s2_hospitalisation": "hospitalisation",
    "s2_etablissement": "etablissement", "s2_activite": "activite",
    "s3_satisfaction": "satisfaction", "s4_deces": "deces"
}
STEPS = {
    "01": ["diagnostic", "specialite", "codes_postaux", "commune", "region"],
    "02": ["patient"], "03": ["professionnel", "etablissement", "activite"],
    "04": ["consultation"], "05": ["hospitalisation"],
    "06": ["satisfaction"], "07": ["deces", "defunt"]
}


def names(table):
    return [name for name, unused in TABLES[table]]


def schema(spec):
    from pyspark.sql import types as T
    types = {"STRING": T.StringType, "INT": T.IntegerType,
             "SMALLINT": T.ShortType, "DOUBLE": T.DoubleType,
             "DATE": T.DateType, "BIGINT": T.LongType}
    return T.StructType([T.StructField(name, types[kind](), True)
                         for name, kind in spec])


def publication_sql(database, locations):
    """Publication isolee par execution ; aucune commande DROP/INSERT Gold."""
    import re
    if not re.match(r'^[a-z][a-z0-9_]*$', database):
        raise ValueError("Nom de base invalide")
    lines = ["CREATE DATABASE IF NOT EXISTS `%s`;" % database]
    for table in sorted(TABLES):
        path = locations[table]
        if "'" in path or ";" in path or "\n" in path:
            raise ValueError("Chemin non autorise")
        columns = ', '.join('`%s` %s' % item for item in TABLES[table])
        lines.append("CREATE EXTERNAL TABLE `%s`.`%s` (%s) STORED AS ORC LOCATION '%s';" %
                     (database, table, columns, path))
    for alias, table in sorted(ALIASES.items()):
        lines.append("CREATE VIEW `%s`.`%s` AS SELECT * FROM `%s`.`%s`;" %
                     (database, alias, database, table))
    return '\n'.join(lines) + '\n'



# -*- coding: utf-8 -*-
"""CSV distribue UTF-8 ; petits cp1252/XLSX bornes en memoire sur le driver.

Le lecteur distribue conserve l'offset HDFS. Il echoue sur un enregistrement
multiligne : aucune continuation CSV n'est acceptee comme une autre personne.
Une source multiligne demande un lecteur specifique avant publication.
"""
import csv
import io
import subprocess
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

PY2 = sys.version_info[0] == 2


def clean(value):
    """Normalise les en-tetes comme les regles Silver historiques."""
    if value is None:
        return None
    try:
        text_type = unicode
    except NameError:
        text_type = str
    if not isinstance(value, text_type):
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        else:
            value = text_type(value)
    return value.strip().lstrip(u'\ufeff') or None


def csv_records(text, delimiter):
    # json.loads renvoie unicode en Python 2.6, mais _csv exige un byte str.
    if PY2:
        delimiter = delimiter.encode('ascii')
    if len(delimiter) != 1:
        raise ValueError('Separateur CSV invalide')
    if PY2:
        stream = io.BytesIO(text.encode('utf-8'))
    else:
        stream = io.StringIO(text)
    for row in csv.reader(stream, delimiter=delimiter, strict=True):
        yield [cell.decode('utf-8') if PY2 else cell for cell in row]


def parse_line(line, delimiter, width):
    try:
        rows = list(csv_records(line, delimiter))
    except csv.Error:
        raise ValueError('STRUCTURE_CSV_INVALIDE : champ cite non termine')
    if len(rows) != 1 or len(rows[0]) != width:
        raise ValueError('STRUCTURE_CSV_INVALIDE : nombre de champs ou ligne multiligne')
    return rows[0]


def bounded_hdfs_read(path, limit):
    proc = subprocess.Popen(['hdfs', 'dfs', '-cat', path], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    try:
        data = proc.stdout.read(limit + 1)
        if len(data) > limit:
            proc.kill()
            raise ValueError('Source trop volumineuse pour le lecteur borne')
        # stderr ne contient normalement que des messages de client HDFS.
        # Ne pas l'afficher : le chemin d'un fichier peut etre prive.
        proc.stderr.read()
        if proc.wait() != 0:
            raise IOError('Lecture HDFS impossible')
        return data
    finally:
        proc.stdout.close()
        proc.stderr.close()
        if proc.poll() is None:
            proc.kill()
        proc.wait()


def xlsx_records(data, sheet_name, limit=100000):
    """Lecture XML d'un petit classeur : valeurs texte, aucune inference FINESS."""
    archive = ZipFile(io.BytesIO(data))
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    relns = '{http://schemas.openxmlformats.org/package/2006/relationships}'
    docrel = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    try:
        if sum(item.file_size for item in archive.infolist()) > 32 * 1024 * 1024:
            raise ValueError('Classeur decompresse trop volumineux')
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            root = ET.fromstring(archive.read('xl/sharedStrings.xml'))
            strings = [u''.join(t.text or u'' for t in si.findall('.//' + ns + 't'))
                       for si in root.findall(ns + 'si')]
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        sheets = [s for s in workbook.findall('.//' + ns + 'sheet') if s.get('name') == sheet_name]
        if len(sheets) != 1:
            raise ValueError('Feuille XLSX absente ou ambigue')
        relations = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets = dict((r.get('Id'), r.get('Target')) for r in relations.findall(relns + 'Relationship'))
        target = targets[sheets[0].get(docrel)]
        target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
        if '..' in target.split('/'):
            raise ValueError('Chemin XLSX invalide')
        root = ET.fromstring(archive.read(target))
        rows = []
        for row in root.findall('.//' + ns + 'sheetData/' + ns + 'row'):
            cells = {}
            for cell in row.findall(ns + 'c'):
                column = ''.join(c for c in cell.get('r', '') if c.isalpha())
                index = 0
                for char in column.upper():
                    index = index * 26 + ord(char) - 64
                if index == 0:
                    raise ValueError('Adresse de cellule XLSX invalide')
                value = cell.find(ns + 'v')
                value = value.text if value is not None else ''
                if cell.get('t') == 's':
                    value = strings[int(value)]
                elif cell.get('t') == 'inlineStr':
                    value = u''.join(t.text or u'' for t in cell.findall('.//' + ns + 't'))
                # Un resultat de formule non calcule ne doit pas devenir NULL.
                if cell.find(ns + 'f') is not None and not value:
                    raise ValueError('Formule XLSX sans valeur calculee')
                cells[index - 1] = value or ''
            if cells and any(cells.values()):
                width = max(cells) + 1
                rows.append([cells.get(i, '') for i in range(width)])
            if len(rows) > limit + 1:
                raise ValueError('Trop de lignes pour le lecteur XLSX borne')
        if not rows:
            raise ValueError('Classeur vide')
        header, data_rows = rows[0], rows[1:]
        for row in data_rows:
            if len(row) > len(header):
                raise ValueError('Ligne XLSX plus large que son en-tete')
            row.extend([''] * (len(header) - len(row)))
        return header, data_rows
    finally:
        archive.close()


def read_records(sc, path, source_id, spec, small_limit):
    """Retourne RDD[(record_id stable, dict colonnes)]."""
    if spec.get('small') or spec.get('format') == 'xlsx':
        content = bounded_hdfs_read(path, small_limit)
        if spec.get('format') == 'xlsx':
            header, data = xlsx_records(content, spec.get('sheet', 'Resultats'))
        else:
            rows = list(csv_records(content.decode(spec['encoding']), spec['delimiter']))
            if not rows:
                raise ValueError('Source vide : ' + source_id)
            header, data = rows[0], rows[1:]
        header = [clean(h) for h in header]
        check_header(header, spec)
        records = []
        for index, values in enumerate(data):
            if len(values) != len(header):
                raise ValueError('Structure invalide : ' + source_id)
            records.append(('%s:record:%d' % (source_id, index + 1), dict(zip(header, values))))
        return sc.parallelize(records, min(4, max(1, len(records))))

    # TextInputFormat sait distribuer un fichier unique sur ses blocs HDFS.
    rdd = sc.newAPIHadoopFile(path,
        'org.apache.hadoop.mapreduce.lib.input.TextInputFormat',
        'org.apache.hadoop.io.LongWritable', 'org.apache.hadoop.io.Text')
    if spec.get('header', True):
        head = rdd.filter(lambda item: item[0] == 0).take(2)
        if len(head) != 1:
            raise ValueError('Un seul fichier physique est attendu : ' + source_id)
        line = head[0][1].lstrip(u'\ufeff')
        parsed = list(csv_records(line, spec['delimiter']))
        if len(parsed) != 1:
            raise ValueError('En-tete invalide : ' + source_id)
        header = [clean(h) for h in parsed[0]]
        check_header(header, spec)
        rdd = rdd.filter(lambda item: item[0] != 0)
    else:
        header = spec['columns']

    def parse(item):
        offset, line = item
        values = parse_line(line, spec['delimiter'], len(header))
        return ('%s:offset:%d' % (source_id, offset), dict(zip(header, values)))
    return rdd.map(parse)


def check_header(header, spec):
    if None in header or len(header) != len(set(header)):
        raise ValueError('Colonnes vides ou repetees')
    required = [clean(name) for name in spec.get('required', spec.get('columns', []))]
    missing = set(required) - set(header)
    if missing:
        raise ValueError(u'Colonnes requises absentes : ' + u', '.join(sorted(missing)))



# -*- coding: utf-8 -*-
"""Execution Spark 1.6 : traceabilite, controles, sorties immuables par tentative."""
import hashlib
import json
import time

META = [('_record_id', 'STRING'), ('_status', 'STRING'), ('_motif', 'STRING'),
        ('_warnings', 'STRING'), ('_payload', 'STRING')]


class Run(silver_controles.Checks):
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

    def normalized(self, source, kind, spec, options=None, records=None, compute_payload=True):
        """Une passe Python par partition ; pas de relecture par attribut/UDF."""
        import silver_hors_deces as rules
        import silver_deces as death_rules
        key = self.key
        opts = dict(options or {})
        opts['excluded'] = self.excluded
        names = [name for name, unused in spec]
        records = records if records is not None else self.records(source)

        def batch(iterator):
            for record_id, row in iterator:
                if kind == 'deces':
                    values, status, motif, warnings = death_rules.transform_deces(row)
                else:
                    values, status, motif, warnings = rules.transform(kind, row, key, opts)
                business = [values.get(name) for name in names]
                payload = rules.payload_hash(business) if compute_payload else None
                yield tuple(business + [record_id, status, motif, warnings, payload])
        return self.sql.createDataFrame(records.mapPartitions(batch), C.schema(spec + META))

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

    def save(self, table, df, expected=None, extra_quality=None):
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
        if readback.schema != C.schema(C.TABLES[table]):
            # ORC peut rendre nullable une colonne non nullable ; notre
            # contrat utilise nullable=True, seuls noms/types sont imposes.
            actual_schema = [(f.name, f.dataType.simpleString()) for f in readback.schema.fields]
            expected_schema = [(f.name, f.dataType.simpleString()) for f in C.schema(C.TABLES[table]).fields]
            if actual_schema != expected_schema:
                raise ValueError('Schema relu incompatible : ' + table)
        # Meme bilan qu'auparavant, mais une seule lecture ORC pour le nombre
        # de lignes, les NULL et les compteurs specifiques demandes.
        row_count = '__chu_rows'
        columns = C.names(table)
        extra_quality = extra_quality or {}
        if row_count in columns or set(extra_quality).intersection(columns + [row_count]):
            raise ValueError('Nom de compteur reserve deja utilise')
        expressions = [F.count(F.lit(1)).alias(row_count)]
        expressions.extend(F.sum(F.when(F.col(name).isNull(), 1).otherwise(0)).alias(name)
                           for name in columns)
        expressions.extend(extra_quality[name].alias(name) for name in sorted(extra_quality))
        summary = readback.agg(*expressions).collect()[0].asDict()
        actual = int(summary[row_count])
        if expected is not None and actual != expected:
            raise ValueError('Cardinalite modifiee pour ' + table)
        nulls = dict((name, int(summary[name] or 0)) for name in columns)
        self.outputs[table] = {'path': path, 'rows': actual, 'nulls': nulls,
            'completeness': dict((name, (float(actual - n) / actual if actual else None))
                                 for name, n in nulls.items()),
            'seconds': round(time.time() - started, 3), 'partitions_requested': partitions,
            'schema': C.TABLES[table]}
        return dict((name, int(summary[name] or 0)) for name in extra_quality)

    def load(self, table):
        if table not in self.outputs:
            raise ValueError('Dependance non produite : ' + table)
        return self.sql.read.orc(self.outputs[table]['path'])


# -*- coding: utf-8 -*-
"""Remplace le Silver publie apres validation, avec retour arriere sur echec."""
import json
import os
import subprocess
import tempfile
import uuid


def publish(run):
    live = run.config['publication_root'].rstrip('/')
    if live != '/user/cloudera/chu/silver':
        raise ValueError('Racine Silver non autorisee')
    parent = live.rsplit('/', 1)[0]
    token = uuid.uuid4().hex
    stage = parent + '/.silver_publish_' + token
    previous = parent + '/.silver_previous_' + token
    lock = run.Path(parent + '/.silver_publication.lock')
    # create(false) echoue si une publication est deja en cours.
    stream = run.fs.create(lock, False)
    stream.close()
    switched = False
    had_previous = False
    old_views = []

    def exists(path):
        return run.fs.exists(run.Path(path))

    def move(source, target):
        if not run.fs.rename(run.Path(source), run.Path(target)):
            raise IOError('Renommage HDFS refuse')

    def copy(source, target):
        if not exists(source) or exists(target):
            raise ValueError('Source absente ou destination deja presente')
        run.fs.mkdirs(run.Path(target).getParent())
        ok = run.sc._jvm.org.apache.hadoop.fs.FileUtil.copy(
            run.fs, run.Path(source), run.fs, run.Path(target), False,
            run.sc._jsc.hadoopConfiguration())
        if not ok:
            raise IOError('Copie HDFS refusee')
        # Compare chaque fichier copie via le checksum HDFS, sans lire les
        # donnees dans Python. Les chemins relatifs doivent aussi correspondre.
        def inventory(base):
            result = {}
            def visit(path, relative):
                for status in run.fs.listStatus(run.Path(path)):
                    name = status.getPath().getName()
                    child = path + '/' + name
                    rel = relative + '/' + name
                    if status.isDirectory():
                        visit(child, rel)
                    else:
                        checksum = run.fs.getFileChecksum(run.Path(child))
                        result[rel] = (status.getLen(), checksum.toString() if checksum else None)
            visit(base, '')
            return result
        if inventory(source) != inventory(target):
            raise ValueError('La copie HDFS differe de la source')

    def hive(text):
        fd, filename = tempfile.mkstemp(prefix='chu_silver_', suffix='.hql')
        try:
            out = os.fdopen(fd, 'wb')
            out.write(text.encode('utf-8'))
            out.close()
            process = subprocess.Popen(['beeline', '-u', 'jdbc:hive2://localhost:10000/default',
                '-n', 'cloudera', '--force=false', '--silent=true', '--showHeader=false',
                '--outputformat=tsv2', '-f', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode:
                raise RuntimeError('Publication Hive refusee: ' + stderr.decode('utf-8', 'replace')[-2000:])
            return stdout.decode('utf-8', 'replace')
        finally:
            os.remove(filename)

    try:
        if set(run.outputs) != set(C.TABLES):
            raise ValueError('Le Silver doit contenir les 14 tables validees')
        run.fs.mkdirs(run.Path(stage + '/tables'))
        run.fs.mkdirs(run.Path(stage + '/rejets'))
        run.fs.mkdirs(run.Path(stage + '/audit'))
        roots = set([run.root])
        for name, info in sorted(run.outputs.items()):
            source = info['path']
            if not source.startswith(parent + '/') or '/tables/' not in source:
                raise ValueError('Sortie source hors du projet')
            if not exists(source + '/_SUCCESS'):
                raise ValueError('Table incomplete: ' + name)
            copy(source, stage + '/tables/' + name)
            root = source.split('/tables/')[0]
            if root.endswith('/enrichissement_satisfaction'):
                root = root.rsplit('/', 1)[0]
            roots.add(root)
        # Rejets et qualite des phases effectivement utilisees.
        reject_sources = {}
        for root in sorted(roots):
            if exists(root + '/rejets'):
                for status in run.fs.listStatus(run.Path(root + '/rejets')):
                    name = status.getPath().getName()
                    source = root + '/rejets/' + name
                    if name in reject_sources:
                        owner = run.outputs.get(name, {}).get('path', '').split('/tables/')[0]
                        if root == owner:
                            reject_sources[name] = source
                        elif reject_sources[name].rsplit('/rejets/', 1)[0] != owner:
                            raise ValueError('Origine des rejets ambigue: ' + name)
                    else:
                        reject_sources[name] = source
            if exists(root + '/audit'):
                for status in run.fs.listStatus(run.Path(root + '/audit')):
                    name = status.getPath().getName()
                    if name.startswith('qualite_'):
                        target = stage + '/audit/' + name
                        if exists(target):
                            continue
                        # Fichier simple : copie, checksum verifie par HDFS.
                        copied = run.sc._jvm.org.apache.hadoop.fs.FileUtil.copy(run.fs, status.getPath(),
                            run.fs, run.Path(target), False, run.sc._jsc.hadoopConfiguration())
                        if not copied:
                            raise IOError('Copie du bilan qualite refusee : ' + name)
                        original = run.fs.getFileChecksum(status.getPath())
                        copied_sum = run.fs.getFileChecksum(run.Path(target))
                        if (original is None or copied_sum is None or
                                original.toString() != copied_sum.toString() or
                                status.getLen() != run.fs.getFileStatus(run.Path(target)).getLen()):
                            raise ValueError('Copie du bilan qualite differente : ' + name)
        for name, source in sorted(reject_sources.items()):
            copy(source, stage + '/rejets/' + name)
        registry = run.config['keys_root']
        if exists(registry):
            copy(registry, stage + '/audit/technical_keys')
        outputs = dict((name, dict(info, path=live + '/tables/' + name))
                       for name, info in run.outputs.items())
        metrics = json.loads(json.dumps(run.metrics))
        old_registry = metrics.get('deces', {}).get('key_registry', '')
        if '/technical_keys/' in old_registry:
            metrics['deces']['key_registry'] = live + '/audit/technical_keys/' + old_registry.split('/technical_keys/', 1)[1]
        report = {'status': 'PUBLISHED', 'mode': 'FULL_REPLACE', 'lot_id': run.lot,
                  'attempt_id': run.attempt, 'inputs_id': run.input_id,
                  'key_version': run.key_version, 'outputs': outputs,
                  'metrics': metrics, 'indicateurs': run.indicateurs, 'hive_database': 'silver'}
        run.write_text(stage + '/audit/rapport_final.json', json.dumps(report, sort_keys=True, indent=2))
        run.write_text(stage + '/audit/manifest_entrees.json', json.dumps(run.fingerprints, sort_keys=True, indent=2))
        # Capture les vues existantes pour permettre leur restauration.
        tables = hive('CREATE DATABASE IF NOT EXISTS silver; SHOW TABLES IN silver;')
        for name in sorted(C.TABLES):
            if name in tables.split():
                ddl = hive('SHOW CREATE TABLE silver.`%s`;' % name)
                if 'CREATE VIEW' in ddl.upper():
                    old_views.append((name, ddl.strip().rstrip(';') + ';'))
        had_previous = exists(live)
        if had_previous:
            move(live, previous)
        try:
            move(stage, live)
        except Exception:
            if had_previous:
                move(previous, live)
            raise
        switched = True
        statements = []
        for name, ddl in old_views:
            statements.append('DROP VIEW silver.`%s`;' % name)
        # Creation dans silver directement : plus de base par tentative.
        statements.append(C.publication_sql('silver', dict((n, live + '/tables/' + n) for n in C.TABLES))
            .replace('CREATE EXTERNAL TABLE ', 'CREATE EXTERNAL TABLE IF NOT EXISTS ')
            .replace('CREATE VIEW ', 'CREATE OR REPLACE VIEW '))
        hive('\n'.join(statements))
        # Les ORC ont ete verifies par Spark puis copies avec checksums identiques.
        # Verification du contrat du metastore apres la bascule.
        for name in sorted(C.TABLES):
            description = hive('DESCRIBE silver.`%s`;' % name)
            actual = [tuple(line.split()[:2]) for line in description.splitlines() if line.strip()]
            expected = [(field, kind.lower()) for field, kind in C.TABLES[name]]
            if actual[:len(expected)] != expected:
                raise ValueError('Schema Hive divergent: ' + name)
        if had_previous:
            run.fs.delete(run.Path(previous), True)
        # Ne retire que les tentatives effectivement consommees, apres succes.
        for root in sorted(roots):
            if root.startswith(parent + '/.silver_work/runs/'):
                run.fs.delete(run.Path(root), True)
        # Retire uniquement les dossiers temporaires devenus vides.
        for path in (parent + '/.silver_work/runs/' + run.lot,
                     parent + '/.silver_work/runs', parent + '/.silver_work'):
            if exists(path) and not run.fs.listStatus(run.Path(path)):
                run.fs.delete(run.Path(path), False)
        print('SILVER_REPLACED : ' + live)
    except Exception:
        if switched:
            move(live, stage)
            if had_previous:
                move(previous, live)
            for name, ddl in old_views:
                hive('DROP TABLE IF EXISTS silver.`%s`; %s' % (name, ddl))
        raise
    finally:
        run.fs.delete(lock, False)



# -*- coding: utf-8 -*-
# Configuration partageable : aucune cle ni donnee personnelle.
CONFIG = {'bronze_root': '/user/cloudera/chu/bronze',
 'keys_root': '/user/cloudera/chu/silver/audit/technical_keys',
 'max_communes_driver': 50000,
 'output_partitions': {'activite': 8,
                       'codes_postaux': 2,
                       'commune': 2,
                       'consultation': 8,
                       'deces': 16,
                       'defunt': 16,
                       'diagnostic': 2,
                       'etablissement': 4,
                       'hospitalisation': 1,
                       'patient': 4,
                       'professionnel': 8,
                       'region': 1,
                       'satisfaction': 1,
                       'specialite': 1},
 'publication_root': '/user/cloudera/chu/silver',
 'region_aliases': {'IDF': 'Ile-de-France', 'PACA': "Provence-Alpes-Cote d'Azur"},
 'runs_root': '/user/cloudera/chu/.silver_work/runs',
 'shuffle_partitions': 16,
 'small_file_limit_bytes': 8388608,
 'sources': {'activite': {'delimiter': ';',
                          'encoding': 'utf-8',
                          'path': 'etablissements/activite_professionnel_sante.csv',
                          'required': ['identifiant', 'identifiant_organisation', 'mode_exercice']},
             'codes_postaux': {'delimiter': ';',
                               'encoding': 'cp1252',
                               'path': 'referentiels_geographiques/codes_postaux_laposte_extrait_2026-11-03.csv',
                               'required': ['#Code_commune_INSEE',
                                            'Nom_de_la_commune',
                                            'Code_postal',
                                            'Libellé_d_acheminement'],
                               'small': True},
             'cog_communes': {'delimiter': ',',
                              'encoding': 'utf-8',
                              'path': 'referentiels_geographiques/v_commune_2024.csv',
                              'required': ['TYPECOM', 'COM', 'REG', 'DEP', 'LIBELLE', 'COMPARENT']},
             'cog_regions': {'delimiter': ',',
                             'encoding': 'utf-8',
                             'path': 'referentiels_geographiques/v_region_2024.csv',
                             'required': ['REG', 'LIBELLE']},
             'consultation': {'columns': ['Num_consultation',
                                          'Id_mut',
                                          'Id_patient',
                                          'Id_prof_sante',
                                          'Code_diag',
                                          'Motif',
                                          'Date',
                                          'Heure_debut',
                                          'Heure_fin'],
                              'delimiter': ';',
                              'encoding': 'utf-8',
                              'header': False,
                              'path': 'postgres/consultations/consultations.txt'},
             'deces': {'delimiter': ',',
                       'encoding': 'utf-8',
                       'path': 'deces/deces.csv',
                       'required': ['nom',
                                    'prenom',
                                    'sexe',
                                    'date_naissance',
                                    'code_lieu_naissance',
                                    'lieu_naissance',
                                    'pays_naissance',
                                    'date_deces',
                                    'code_lieu_deces',
                                    'numero_acte_deces']},
             'diagnostic': {'columns': ['Code_diag', 'Diagnostic'],
                            'delimiter': ';',
                            'encoding': 'utf-8',
                            'header': False,
                            'path': 'postgres/diagnostic/diagnostic.txt'},
             'etablissement': {'delimiter': ';',
                               'encoding': 'utf-8',
                               'path': 'etablissements/etablissement_sante.csv',
                               'required': ['identifiant_organisation',
                                            'raison_sociale_site',
                                            'finess_site',
                                            'finess_etablissement_juridique',
                                            'code_commune',
                                            'commune',
                                            'code_postal',
                                            'adresse',
                                            'cedex',
                                            'complement_destinataire',
                                            'complement_point_geographique',
                                            'email',
                                            'enseigne_commerciale_site',
                                            'indice_repetition_voie',
                                            'mention_distribution',
                                            'numero_voie',
                                            'pays',
                                            'siren_site',
                                            'siret_site',
                                            'telecopie',
                                            'telephone',
                                            'telephone_2',
                                            'type_voie',
                                            'voie']},
             'hospitalisation': {'delimiter': ';',
                                 'encoding': 'utf-8',
                                 'path': 'csv_sante/Hospitalisations.csv',
                                 'required': ['Num_Hospitalisation',
                                              'Id_patient',
                                              'identifiant_organisation',
                                              'Code_diagnostic',
                                              'Suite_diagnostic_consultation',
                                              'Date_Entree',
                                              'Jour_Hospitalisation']},
             'patient': {'columns': ['Id_patient',
                                     'Nom',
                                     'Prenom',
                                     'Sexe',
                                     'Adresse',
                                     'Ville',
                                     'Code_postal',
                                     'Pays',
                                     'EMail',
                                     'Tel',
                                     'Date',
                                     'Age',
                                     'Num_Secu',
                                     'Groupe_sanguin',
                                     'Poid',
                                     'Taille'],
                         'delimiter': ';',
                         'encoding': 'utf-8',
                         'header': False,
                         'path': 'postgres/patients/patients.txt'},
             'professionnel': {'columns': ['Identifiant',
                                           'Civilite',
                                           'Categorie_professionnelle',
                                           'Nom',
                                           'Prenom',
                                           'Profession',
                                           'Type_identifiant',
                                           'Code_specialite'],
                               'delimiter': ';',
                               'encoding': 'utf-8',
                               'header': False,
                               'path': 'postgres/professionnels/professionnels.txt'},
             'satisfaction_2017': {'delimiter': ';',
                                   'encoding': 'cp1252',
                                   'path': 'satisfaction/2017/ESATIS48H_MCO_recueil2017_donnees.csv',
                                   'required': ['finess_geo',
                                                'region',
                                                'score_all_rea_ajust',
                                                'nb_rep_score_all_rea_ajust'],
                                   'small': True},
             'satisfaction_2019': {'delimiter': ';',
                                   'encoding': 'cp1252',
                                   'path': 'satisfaction/2019/resultats-esatis48h-mco-open-data-2019.csv',
                                   'required': ['finess_geo',
                                                'region',
                                                'score_all_rea_ajust',
                                                'nb_rep_score_all_rea_ajust'],
                                   'small': True},
             'satisfaction_2020': {'format': 'xlsx',
                                   'path': 'satisfaction/2020/resultats-esatis48h-mco-open-data-2020.xlsx',
                                   'required': ['finess_geo',
                                                'region',
                                                'score_all_rea_ajust',
                                                'nb_rep_score_all_rea_ajust'],
                                   'sheet': 'Resultats'},
             'specialite': {'columns': ['Code_specialite', 'Fonction', 'Specialite'],
                            'delimiter': ';',
                            'encoding': 'utf-8',
                            'header': False,
                            'path': 'postgres/specialites/specialites.txt'}}}



import posixpath
from optparse import OptionParser

CORE_TABLES = set(C.TABLES) - set(['deces', 'defunt'])

def code_digest():
    result = hashlib.sha256()
    for name in ('silver_pipeline.py', 'silver_hors_deces.py', 'silver_deces.py', 'silver_controles.py'):
        result.update(name.encode('ascii'))
        with open(os.path.join(os.getcwd(), name), 'rb') as stream:
            result.update(stream.read().replace(b'\r\n', b'\n'))
    return result.hexdigest()

def validate_setup(config):
    roots = [config[name] for name in ('bronze_root', 'runs_root', 'keys_root')]
    for root in roots:
        if not root.startswith('/') or root == '/' or posixpath.normpath(root) != root:
            raise ValueError('Utiliser des chemins HDFS absolus normalises, differents de la racine')
    for i, root in enumerate(roots):
        for other in roots[i + 1:]:
            if root == other or root.startswith(other + '/') or other.startswith(root + '/'):
                raise ValueError('Bronze, sorties et registre doivent etre dans des espaces disjoints')


def read_key_and_exclusions(options):
    with open(options.key_file, 'rb') as stream:
        key = stream.read(4097)
    if len(key) < 32 or len(key) > 4096:
        raise ValueError('Cle HMAC invalide : utiliser un fichier binaire de 32 a 4096 octets')
    excluded = set()
    if options.exclude_file:
        with open(options.exclude_file, 'rb') as stream:
            for line in stream:
                value = line.decode('ascii').strip()
                if not re.match(r'^[0-9a-f]{64}$', value):
                    raise ValueError('Pseudonyme exclu invalide')
                excluded.add(value)
                if len(excluded) > 100000:
                    raise ValueError('Liste des exclusions trop volumineuse pour cette implementation')
    return key, excluded


def digest(value):
    serialized = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(serialized.encode('ascii')).hexdigest()


def key_proof(key):
    return hmac.new(key, b'CHU-SILVER-CHECKPOINT-KEY-V1', hashlib.sha256).hexdigest()


def checkpoint_identity(run):
    return {'input_id': run.input_id, 'config_digest': digest(run.config),
            'code_digest': code_digest(), 'key_proof': key_proof(run.key),
            'key_version': run.key_version, 'excluded_digest': digest(sorted(run.excluded))}


def same_identity(expected, actual):
    for name in ('input_id', 'config_digest', 'code_digest', 'key_proof',
                 'key_version', 'excluded_digest'):
        if expected.get(name) != actual.get(name):
            raise ValueError('Reprise refusee : parametre ou version different : ' + name)


def read_json(run, path):
    target = run.Path(path)
    if not run.fs.exists(target) or run.fs.getFileStatus(target).getLen() > 8 * 1024 * 1024:
        raise ValueError('Checkpoint manquant ou trop volumineux : ' + path)
    reader = run.sc._jvm.java.io.BufferedReader(
        run.sc._jvm.java.io.InputStreamReader(run.fs.open(target), 'UTF-8'))
    lines = []
    try:
        line = reader.readLine()
        while line is not None:
            lines.append(line)
            line = reader.readLine()
    finally:
        reader.close()
    return json.loads('\n'.join(lines))


def attempt_root(run, attempt):
    if not attempt or not re.match(r'^[a-z0-9_]{1,32}$', attempt):
        raise ValueError('Identifiant de tentative invalide')
    if attempt == run.attempt:
        raise ValueError('Une reprise doit utiliser une nouvelle tentative')
    return run.config['runs_root'].rstrip('/') + '/' + run.lot + '/' + attempt


def validate_outputs(run, outputs, required):
    if set(outputs) != required:
        raise ValueError('Tables du checkpoint incompletes ou inattendues')
    prefix = run.config['runs_root'].rstrip('/') + '/' + run.lot + '/'
    for name, entry in outputs.items():
        path = entry.get('path', '')
        if (not path.startswith(prefix) or posixpath.normpath(path) != path or
                not run.fs.exists(run.Path(path + '/_SUCCESS'))):
            raise ValueError('Sortie absente ou hors du lot : ' + name)
        actual = [(f.name, f.dataType.simpleString()) for f in run.sql.read.orc(path).schema.fields]
        expected = [(f.name, f.dataType.simpleString()) for f in C.schema(C.TABLES[name]).fields]
        if actual != expected:
            raise ValueError('Schema incompatible : ' + name)


def saved_checkpoint(run, attempt, stage):
    root = attempt_root(run, attempt)
    state = read_json(run, root + '/audit/checkpoint_' + stage + '.json')
    if state.get('stage') != stage or state.get('attempt') != attempt or state.get('lot') != run.lot:
        raise ValueError('Checkpoint incoherent')
    same_identity(state['identity'], checkpoint_identity(run))
    expected = CORE_TABLES if stage == '01' else set(C.TABLES)
    validate_outputs(run, state['outputs'], expected)
    return state


def write_checkpoint(run, stage, source_attempt):
    validate_outputs(run, run.outputs, CORE_TABLES if stage == '01' else set(C.TABLES))
    state = {'stage': stage, 'lot': run.lot, 'attempt': run.attempt,
             'source_attempt': source_attempt, 'identity': checkpoint_identity(run), 'outputs': run.outputs,
             'metrics': run.metrics}
    run.write_json('checkpoint_' + stage + '.json', state)
    print('SILVER_CHECKPOINT_' + stage + ' : ' + run.audit)


def phase_main(stage):
    parser = OptionParser()
    parser.add_option('--lot-id', dest='lot')
    parser.add_option('--attempt-id', dest='attempt')
    parser.add_option('--source-attempt', dest='source_attempt')
    parser.add_option('--hmac-key-file', dest='key_file')
    parser.add_option('--key-version', dest='key_version')
    parser.add_option('--exclude-pseudonyms-file', dest='exclude_file')
    options, extra = parser.parse_args()
    if extra or not all([options.lot, options.attempt, options.key_file, options.key_version]):
        parser.error('lot-id, attempt-id, hmac-key-file et key-version sont obligatoires')
    for value in (options.lot, options.attempt):
        if not re.match(r'^[a-z0-9_]{1,32}$', value):
            parser.error('Identifiant invalide : utiliser a-z, 0-9 et _')
    if (stage == '01' and options.source_attempt) or (stage != '01' and not options.source_attempt):
        parser.error('source-attempt est requis uniquement pour les phases 02 et 03')
    config = CONFIG
    validate_setup(config)
    key, excluded = read_key_and_exclusions(options)
    from pyspark import SparkConf, SparkContext
    from pyspark.sql import HiveContext
    conf = SparkConf().setAppName('CHU_Silver_%s_%s' % (stage, options.lot))
    conf.set('spark.sql.shuffle.partitions', str(config.get('shuffle_partitions', 16)))
    conf.set('spark.hadoop.orc.compress', 'SNAPPY')
    conf.set('spark.sql.orc.filterPushdown', 'true')
    sc = SparkContext(conf=conf)
    run = None
    try:
        if sc.version.split('.')[:2] != ['1', '6']:
            raise ValueError('Cette livraison cible Spark 1.6')
        sc.setLogLevel('WARN')
        sql = HiveContext(sc)
        silver_controles.verifier_hmac(sc, key)
        run = Run(sc, sql, config, options.lot, options.attempt, key, options.key_version, excluded)
        if stage == '01':
            from silver_hors_deces import PIPELINES
            for step, function in PIPELINES:
                print('SILVER_STEP_START ' + step)
                function(run)
                run.write_json('progression_' + step + '.json', {'step': step, 'outputs': run.outputs, 'metrics': run.metrics})
                print('SILVER_STEP_OK ' + step)
            write_checkpoint(run, '01', None)
        elif stage == '02':
            state = saved_checkpoint(run, options.source_attempt, '01')
            run.outputs, run.metrics = state['outputs'], state['metrics']
            from silver_deces import deces
            print('SILVER_STEP_START 07')
            deces(run)
            run.write_json('progression_07.json', {'step': '07', 'outputs': run.outputs, 'metrics': run.metrics})
            print('SILVER_STEP_OK 07')
            write_checkpoint(run, '02', options.source_attempt)
        elif stage == '03':
            state = saved_checkpoint(run, options.source_attempt, '02')
            run.outputs, run.metrics = state['outputs'], state['metrics']
            run.write_json('lineage.json', {'phase_02': options.source_attempt, 'phase_01': state.get('source_attempt')})
            silver_controles.verifier_professionnels(run)
            run.complete()
            publish(run)
        else:
            raise ValueError('Phase inconnue')
    except Exception:
        if run is not None:
            try:
                run.write_json('ECHEC.json', {'status': 'FAILED', 'exception_type': sys.exc_info()[0].__name__})
            except Exception:
                pass
        raise
    finally:
        sc.stop()

def main():
    """Controle les prerequis puis lance les trois phases dans l'ordre."""
    parser = OptionParser()
    parser.add_option('--lot-id', dest='lot')
    parser.add_option('--hmac-key-file', dest='key_file')
    parser.add_option('--key-version', dest='key_version')
    parser.add_option('--exclude-pseudonyms-file', dest='exclude_file')
    options, extra = parser.parse_args()
    if extra or not all([options.lot, options.key_file, options.key_version]):
        parser.error('lot-id, hmac-key-file et key-version sont obligatoires')
    if not re.match(r'^[a-z0-9_]{1,32}$', options.lot):
        parser.error('lot-id invalide : utiliser a-z, 0-9 et _')
    validate_setup(CONFIG)
    read_key_and_exclusions(options)
    silver_controles.verifier_avant(CONFIG)
    common = ['--lot-id', options.lot, '--hmac-key-file', options.key_file,
              '--key-version', options.key_version]
    if options.exclude_file:
        common.extend(['--exclude-pseudonyms-file', options.exclude_file])
    import uuid
    run_id = uuid.uuid4().hex[:12]
    files = 'silver_pipeline.py,silver_hors_deces.py,silver_deces.py,silver_controles.py'
    base = ['spark-submit', '--master', 'yarn', '--deploy-mode', 'client',
            '--driver-memory', '1g', '--executor-memory', '1536m',
            '--executor-cores', '2', '--num-executors', '1',
            '--conf', 'spark.dynamicAllocation.enabled=false',
            '--conf', 'spark.yarn.executor.memoryOverhead=1024', '--py-files', files]
    phases = [('silver_hors_deces.py', 'h_' + run_id, None),
              ('silver_deces.py', 'd_' + run_id, 'h_' + run_id),
              ('silver_controles.py', 'c_' + run_id, 'd_' + run_id)]
    for script, attempt, source in phases:
        cmd = base + [script] + common + ['--attempt-id', attempt]
        if source:
            cmd.extend(['--source-attempt', source])
        print('SILVER_PHASE_START : ' + script)
        sys.stdout.flush()
        if subprocess.call(cmd) != 0:
            raise RuntimeError('Phase Silver echouee : ' + script)
        print('SILVER_PHASE_OK : ' + script)
        sys.stdout.flush()

if __name__ == '__main__':
    main()
