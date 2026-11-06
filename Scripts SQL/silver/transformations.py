# -*- coding: utf-8 -*-
"""Lecture, transformations, controles et publication Silver (Spark 1.6)."""
import sys

# Alias conserves pour rendre explicite l origine des regles et contrats.
C = rules = sys.modules[__name__]
__version__ = "1.0.0"


# ==================== CONTRATS DES TABLES ====================
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


# ==================== REGLES DE TRANSFORMATION ====================
# -*- coding: utf-8 -*-
"""Regles metier testables sans Spark. Aucune donnee personnelle journalisee."""
import datetime
import hashlib
import hmac
import json
import math
import re
import unicodedata

try:
    text_type = unicode
except NameError:
    text_type = str


class Invalid(ValueError):
    pass


def clean(value):
    if value is None:
        return None
    if not isinstance(value, text_type):
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        else:
            value = text_type(value)
    return value.strip().lstrip(u'\ufeff') or None


def token(value):
    value = clean(value) or u''
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', value)
                  .encode('ascii', 'ignore').decode('ascii').lower())


def integer(value, required=False, minimum=None):
    value = clean(value)
    if value is None and not required:
        return None
    if value is None or not re.match(r'^-?[0-9]+$', value):
        raise Invalid('ENTIER_INVALIDE')
    result = int(value)
    if result < -2147483648 or result > 2147483647:
        raise Invalid('ENTIER_HORS_CAPACITE')
    if minimum is not None and result < minimum:
        raise Invalid('ENTIER_HORS_DOMAINE')
    return result


def patient_id(value):
    # Source PostgreSQL INT : 00042 et 42 representent la meme identite.
    return text_type(integer(value, required=True))


def pseudonym(value, key):
    if not key or len(key) < 32:
        raise ValueError('Cle HMAC absente ou trop courte (32 octets minimum)')
    return hmac.new(key, patient_id(value).encode('utf-8'), hashlib.sha256).hexdigest()


def pro_pseudonym(identifier, key):
    """HMAC-SHA256 de l'identifiant professionnel deja normalise (prof_id).

    Prefixe de domaine 'pro:' : meme cle que le patient mais jamais le meme
    pseudonyme, donc pas de recoupement professionnel/patient.
    """
    if not key or len(key) < 32:
        raise ValueError('Cle HMAC absente ou trop courte (32 octets minimum)')
    return hmac.new(key, (u'pro:' + identifier).encode('utf-8'), hashlib.sha256).hexdigest()


def prof_id(value, kind=None):
    value = clean(value)
    if value is None:
        raise Invalid('IDENTIFIANT_PRO_INVALIDE')
    kind = token(kind)
    if kind not in ('', 'adeli', 'rpps'):
        raise Invalid('TYPE_IDENTIFIANT_PRO_INCONNU')
    # La source contient aussi des ADELI alphanumeriques de neuf caracteres.
    # Ils restent opaques : aucune suppression de lettre ni conversion INT.
    if kind != 'rpps':
        if re.match(r'^[0-9]{8}$', value):
            return value.zfill(9)
        if re.match(r'^[0-9A-Za-z]{9}$', value):
            return value
    if kind != 'adeli' and re.match(r'^[0-9]{11}$', value):
        return value
    raise Invalid('IDENTIFIANT_PRO_INVALIDE')


def finess(value):
    value = clean(value)
    if value is None:
        raise Invalid('FINESS_ABSENT')
    # Excel peut serialiser un entier en decimal ; pas de notation scientifique.
    if re.match(r'^[0-9]+\.0+$', value):
        value = value.split('.')[0]
    # Les sources e-Satis fournies comportent des FINESS corses 2A/2B.
    # Ne pas les rejeter avec une validation exclusivement numerique.
    if re.match(r'^2[AB][0-9]{7}$', value):
        return value
    if not re.match(r'^[0-9]{1,9}$', value) or int(value) == 0:
        raise Invalid('FINESS_INVALIDE')
    return value.zfill(9)


def date_value(value, pattern='iso', required=False):
    value = clean(value)
    if value is None and not required:
        return None
    try:
        if pattern == 'iso' and re.match(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$', value or ''):
            return datetime.date(int(value[:4]), int(value[5:7]), int(value[8:10]))
        if pattern == 'fr' and re.match(r'^[0-9]{2}/[0-9]{2}/[0-9]{4}$', value or ''):
            return datetime.date(int(value[6:10]), int(value[3:5]), int(value[:2]))
    except ValueError:
        pass
    raise Invalid('DATE_INVALIDE')


def sex(value):
    return {'m': 'M', 'male': 'M', 'masculin': 'M', '1': 'M',
            'f': 'F', 'female': 'F', 'feminin': 'F', '2': 'F'}.get(token(value), 'inconnu')


def number(value):
    value = clean(value)
    if value is None:
        return None
    try:
        result = float(value.replace(',', '.'))
        if math.isnan(result) or math.isinf(result):
            raise ValueError()
        return result
    except ValueError:
        raise Invalid('NOMBRE_INVALIDE')


def department(code):
    code = clean(code)
    if not code or code == 'inconnu':
        return None
    if not re.match(r'^(?:[0-9]{5}|2[AB][0-9]{3})$', code):
        return None
    return code[:3] if code.startswith(('97', '98')) else code[:2]


def required(value, motif='CLE_OBLIGATOIRE_ABSENTE'):
    result = clean(value)
    if result is None:
        raise Invalid(motif)
    return result


def payload_hash(values):
    def encode(value):
        if isinstance(value, datetime.date):
            return value.isoformat()
        raise TypeError('Type non serialisable')
    data = json.dumps(values, ensure_ascii=True, separators=(',', ':'), default=encode)
    return hashlib.sha256(data.encode('ascii')).hexdigest()


def transform(source, row, key=None, options=None):
    """Retourne (valeurs metier, statut, motifs, avertissements).

    Les noms/adresses ne sont jamais copies dans le resultat ni les erreurs.
    Les exceptions techniques remontent ; seules Invalid sont des rejets metier.
    """
    options = options or {}
    out, warnings = {}, []
    try:
        if source in ('patient', 'consultation', 'hospitalisation'):
            out['id_patient'] = pseudonym(row.get('Id_patient'), key)
            if out['id_patient'] in options.get('excluded', set()):
                return {}, 'EXCLUDE', 'EXCLUSION_AUTORISEE', ''
        if source == 'patient':
            out['sexe'] = sex(row.get('Sexe'))
            try:
                out['age'] = integer(row.get('Age'), minimum=0)
            except Invalid:
                out['age'] = None
                warnings.append('AGE_INVALIDE')
            if out['sexe'] == 'inconnu':
                warnings.append('SEXE_INCONNU')
        elif source == 'diagnostic':
            out = {'code_diag': required(row.get('Code_diag')), 'libelle': clean(row.get('Diagnostic'))}
        elif source == 'specialite':
            out = {'code_specialite': required(row.get('Code_specialite')),
                   'fonction': clean(row.get('Fonction')), 'specialite': clean(row.get('Specialite'))}
        elif source == 'professionnel':
            out = {'id_prof_sante': pro_pseudonym(
                       prof_id(row.get('Identifiant'), row.get('Type_identifiant')), key),
                   'categorie': clean(row.get('Categorie_professionnelle')),
                   'profession': clean(row.get('Profession')),
                   'code_specialite': clean(row.get('Code_specialite')),
                   '_original_id': clean(row.get('Identifiant'))}
        elif source == 'etablissement':
            out = dict((name, clean(value)) for name, value in row.items())
            out['identifiant_organisation'] = required(row.get('identifiant_organisation'))
        elif source == 'activite':
            out = {'id_prof_sante': pro_pseudonym(prof_id(row.get('identifiant')), key),
                   'identifiant_organisation': required(row.get('identifiant_organisation')),
                   'mode_exercice': clean(row.get('mode_exercice')) or 'inconnu'}
        elif source == 'consultation':
            out.update({'num_consultation': integer(row.get('Num_consultation'), True),
                        'date_consultation': date_value(row.get('Date'), required=True),
                        'code_diag': required(row.get('Code_diag')),
                        'id_prof_sante': pro_pseudonym(prof_id(row.get('Id_prof_sante')), key)})
        elif source == 'hospitalisation':
            out.update({'num_hospitalisation': integer(row.get('Num_Hospitalisation'), True),
                        'date_entree': date_value(row.get('Date_Entree'), 'fr', True),
                        'code_diag': required(row.get('Code_diagnostic')),
                        'identifiant_organisation': required(row.get('identifiant_organisation'))})
        elif source == 'satisfaction':
            site = finess(row.get('finess_geo'))
            score = number(row.get('score_all_rea_ajust'))
            count = integer(row.get('nb_rep_score_all_rea_ajust'), minimum=0)
            if score is not None and not 0 <= score <= 100:
                raise Invalid('SCORE_HORS_DOMAINE')
            if score is not None and not count:
                warnings.append('POIDS_NON_EXPLOITABLE')
            out = {'finess_geo': site, 'identifiant_organisation': 'F' + site,
                   'annee': options['year'], 'region': clean(row.get('region')) or 'inconnu',
                   'code_region': None, 'score_all_rea_ajust': score,
                   'nb_rep_score_all_rea_ajust': count}
        elif source == 'deces':
            death = date_value(row.get('date_deces'), required=True)
            try:
                birth = date_value(row.get('date_naissance'))
            except Invalid:
                birth = None
                warnings.append('NAISSANCE_INVALIDE')
            if birth is not None and birth > death:
                raise Invalid('NAISSANCE_APRES_DECES')
            code = clean(row.get('code_lieu_deces')) or 'inconnu'
            # RGPD / plan de gouvernance 5.3 : la naissance ne sert qu'au controle
            # de coherence ci-dessus ; naissance et numero d'acte ne sont pas publies.
            out = {'date_deces': death, 'sexe': sex(row.get('sexe')),
                   'code_commune_deces': code, 'code_departement': department(code)}
        elif source == 'codes_postaux':
            normalized = dict((token(k), v) for k, v in row.items())
            postal = required(normalized.get('codepostal'))
            if not re.match(r'^[0-9]{5}$', postal):
                raise Invalid('CODE_POSTAL_INVALIDE')
            out = {'code_commune_insee': required(normalized.get('codecommuneinsee')),
                   'nom_de_la_commune': clean(normalized.get('nomdelacommune')),
                   'code_postal': postal,
                   'libelle_d_acheminement': clean(normalized.get('libelledacheminement'))}
        else:
            raise ValueError('Source inconnue : ' + source)
        return out, 'VALID', '', '|'.join(warnings)
    except Invalid as error:
        return {}, 'REJECT', str(error), '|'.join(warnings)


# ==================== LECTURE DES SOURCES ====================
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
    missing = set(spec.get('required', spec.get('columns', []))) - set(header)
    if missing:
        raise ValueError('Colonnes requises absentes : ' + ', '.join(sorted(missing)))


# ==================== EXECUTION ET CONTROLES ====================
# -*- coding: utf-8 -*-
"""Execution Spark 1.6 : traceabilite, controles, sorties immuables par tentative."""
import hashlib
import json
import time

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

    def normalized(self, source, kind, spec, options=None, records=None, compute_payload=True):
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
                payload = rules.payload_hash(business) if compute_payload else None
                yield tuple(business + [record_id, status, motif, warnings, payload])
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
        if self.config.get('publication_root'):
            publish(self)


# ==================== TRANSFORMATIONS PAR SOURCE ====================
# -*- coding: utf-8 -*-
"""Les sept branches metier. Publication et qualite globale dans Run.complete."""
import hashlib
import json


def reference_data(run, source, table):
    df = run.normalized(source, table, C.TABLES[table])
    df = run.unique(df, C.KEYS[table])
    run.finish(source, df, table)


def resolve_communes(records, regions):
    """COG : cle officielle TYPECOM+COM ; lookup deces : un seul COM.

    Priorite documentee du referentiel actuel : COM, ARM, COMA, COMD.
    Un conflit a type identique bloque le traitement, sans choix arbitraire.
    """
    priority = {'COM': 0, 'ARM': 1, 'COMA': 2, 'COMD': 3}
    by_code = {}
    discarded = []
    for record_id, row in records:
        code = rules.required(row.get('COM'))
        kind = rules.required(row.get('TYPECOM'))
        if kind not in priority:
            raise ValueError('Type de commune non pris en charge')
        if code in by_code:
            previous_id, previous = by_code[code]
            previous_kind = previous['TYPECOM']
            if kind == previous_kind and previous != row:
                raise ValueError('Conflit de commune a TYPECOM identique')
            if priority[kind] < priority[previous_kind]:
                discarded.append(previous_id)
                by_code[code] = (record_id, row)
            else:
                discarded.append(record_id)
        else:
            by_code[code] = (record_id, row)
    result = []
    for code, pair in sorted(by_code.items()):
        unused, row = pair
        reg, dep = rules.clean(row.get('REG')), rules.clean(row.get('DEP'))
        current, visited = row, set([code])
        while (not reg or not dep) and rules.clean(current.get('COMPARENT')):
            parent = current['COMPARENT']
            if parent in visited:
                raise ValueError('Cycle de parents dans COG')
            visited.add(parent)
            if parent not in by_code:
                break
            current = by_code[parent][1]
            reg = reg or rules.clean(current.get('REG'))
            dep = dep or rules.clean(current.get('DEP'))
        label = regions.get(reg)
        result.append((code, row['TYPECOM'], rules.clean(row.get('COMPARENT')),
                       rules.clean(row.get('LIBELLE')), dep, reg, label,
                       'COG_2024' if label else 'NON_RESOLU'))
    return result, discarded


def referentiels(run):
    from pyspark.sql import functions as F
    reference_data(run, 'diagnostic', 'diagnostic')
    reference_data(run, 'specialite', 'specialite')
    # Le fichier regional compte 18 lignes : collecte bornee explicite.
    region_rows = run.records('cog_regions').take(101)
    if len(region_rows) > 100:
        raise ValueError('Referentiel regional anormalement volumineux')
    regions = {}
    for record_id, row in region_rows:
        code, label = rules.required(row.get('REG')), rules.required(row.get('LIBELLE'))
        if code in regions:
            raise ValueError('Code region repete')
        regions[code] = label
    run.save('region', run.sql.createDataFrame(
        list(sorted(regions.items())) + [(None, 'inconnu')], C.schema(C.TABLES['region'])),
        len(region_rows) + 1)
    cap = run.config.get('max_communes_driver', 50000)
    commune_rows = run.records('cog_communes').take(cap + 1)
    if len(commune_rows) > cap:
        raise ValueError('COG trop volumineux pour la resolution bornee')
    resolved, alternatives = resolve_communes(commune_rows, regions)
    run.save('commune', run.sql.createDataFrame(resolved, C.schema(C.TABLES['commune'])), len(resolved))
    alt_schema = C.schema([('_record_id', 'STRING'), ('motif', 'STRING')])
    run.sql.createDataFrame([(x, 'VARIANTE_TYPECOM_NON_RETENUE') for x in alternatives],
                            alt_schema).write.mode('error').orc(run.root + '/rejets/cog_variantes')
    run.metrics['cog_communes'] = {'read': len(commune_rows), 'VALID': len(resolved),
                                  'ALTERNATIVE': len(alternatives)}
    run.metrics['cog_regions'] = {'read': len(region_rows), 'VALID': len(region_rows),
                                'derived_unknown': 1}
    # S5 : plus petit code postal ; departage explicite des libelles.
    df = run.normalized('codes_postaux', 'codes_postaux', C.TABLES['codes_postaux'])
    rank = F.concat_ws('|', F.col('code_postal'),
                       F.coalesce(F.col('nom_de_la_commune'), F.lit('')),
                       F.coalesce(F.col('libelle_d_acheminement'), F.lit('')))
    df = df.withColumn('_rank', rank)
    best = df.filter("_status = 'VALID'").groupBy('code_commune_insee').agg(F.min('_rank').alias('_best'))
    df = df.join(best, 'code_commune_insee', 'left_outer')
    df = run.annotate(df, F.col('_rank') != F.col('_best'),
                      'ALTERNATIVE_POSTALE_NON_RETENUE', 'ALTERNATIVE')
    df = run.unique(df.drop('_rank').drop('_best'), ['code_commune_insee'])
    run.finish('codes_postaux', df, 'codes_postaux')


def patients(run):
    df = run.normalized('patient', 'patient', C.TABLES['patient'])
    df = run.unique(df, ['id_patient'])
    run.finish('patient', df, 'patient')


def professionnels_etablissements(run):
    from pyspark.sql import functions as F
    reference_data(run, 'etablissement', 'etablissement')
    spec = C.TABLES['professionnel'][:-1] + [('code_specialite', 'STRING'), ('_original_id', 'STRING')]
    df = run.normalized('professionnel', 'professionnel', spec)
    collisions = df.filter("_status = 'VALID'").groupBy('id_prof_sante').agg(
        F.countDistinct('_original_id').alias('_source_variants'))
    df = df.join(collisions, 'id_prof_sante', 'left_outer')
    df = run.annotate(df, F.col('_source_variants') > 1, 'COLLISION_IDENTIFIANT_PRO')
    specialites = run.load('specialite').select('code_specialite', 'specialite')
    df = df.join(F.broadcast(specialites), 'code_specialite', 'left_outer')
    df = df.withColumn('_warnings', F.when(
        (F.col('_status') == 'VALID') & F.col('specialite').isNull(),
        F.lit('SPECIALITE_NON_RESOLUE')).otherwise(F.col('_warnings')))
    df = df.withColumn('specialite', F.coalesce(F.col('specialite'), F.lit('inconnu')))
    df = run.unique(df, ['id_prof_sante'])
    run.finish('professionnel', df, 'professionnel')
    df = run.normalized('activite', 'activite', C.TABLES['activite'])
    df = run.reference(df, 'id_prof_sante', run.load('professionnel'), 'REFERENCE_PROFESSIONNEL_ABSENTE')
    df = run.reference(df, 'identifiant_organisation', run.load('etablissement'), 'REFERENCE_ETABLISSEMENT_ABSENTE')
    df = run.unique(df, ['id_prof_sante', 'identifiant_organisation'])
    run.finish('activite', df, 'activite')


def consultations(run):
    df = run.normalized('consultation', 'consultation', C.TABLES['consultation'])
    for key, table, motif in [
        ('id_patient', 'patient', 'REFERENCE_PATIENT_ABSENTE'),
        ('code_diag', 'diagnostic', 'REFERENCE_DIAGNOSTIC_ABSENTE'),
        ('id_prof_sante', 'professionnel', 'REFERENCE_PROFESSIONNEL_ABSENTE')]:
        df = run.reference(df, key, run.load(table), motif)
    df = run.unique(df, ['num_consultation'])
    run.finish('consultation', df, 'consultation')


def hospitalisations(run):
    df = run.normalized('hospitalisation', 'hospitalisation', C.TABLES['hospitalisation'])
    for key, table, motif in [
        ('id_patient', 'patient', 'REFERENCE_PATIENT_ABSENTE'),
        ('code_diag', 'diagnostic', 'REFERENCE_DIAGNOSTIC_ABSENTE'),
        ('identifiant_organisation', 'etablissement', 'REFERENCE_ETABLISSEMENT_ABSENTE')]:
        df = run.reference(df, key, run.load(table), motif)
    df = run.unique(df, ['num_hospitalisation'])
    run.finish('hospitalisation', df, 'hospitalisation')


def satisfaction(run):
    from pyspark.sql import functions as F
    rows = run.load('region').collect()  # reference de 19 lignes, jamais les faits.
    lookup = dict((rules.token(row['region']), (row['code_region'], row['region'])) for row in rows)
    aliases = run.config.get('region_aliases', {})
    for source, canonical in aliases.items():
        target = rules.token(canonical)
        if target not in lookup:
            raise ValueError('Alias regional sans cible : ' + source)
        lookup[rules.token(source)] = lookup[target]
    def normalize_region(row):
        data = row.asDict()
        original = data['region'] or 'inconnu'
        resolved = lookup.get(rules.token(original))
        if resolved:
            data['code_region'], data['region'] = resolved
        elif data['_status'] == 'VALID':
            data['_warnings'] = '|'.join(filter(None, [data['_warnings'], 'REGION_NON_RESOLUE']))
        values = [data[name] for name in C.names('satisfaction')]
        data['_payload'] = rules.payload_hash(values)
        return tuple([data[name] for name in C.names('satisfaction')] +
                     [data[name] for name, unused in META])
    combined = None
    for year in (2017, 2019, 2020):
        df = run.normalized('satisfaction_' + str(year), 'satisfaction', C.TABLES['satisfaction'], {'year': year})
        df = run.sql.createDataFrame(df.rdd.map(normalize_region), C.schema(C.TABLES['satisfaction'] + META))
        df = run.unique(df, ['finess_geo', 'annee'])
        # Bilan separe par campagne, puis reunion sans perdre le grain site/annee.
        accepted, cached = run.finish('satisfaction_' + str(year), df)
        path = run.root + '/intermediaires/satisfaction_' + str(year)
        accepted.select(*C.names('satisfaction')).write.mode('error').orc(path)
        cached.unpersist()
        current = run.sql.read.orc(path)
        combined = current if combined is None else combined.unionAll(current)
    expected = sum(run.metrics['satisfaction_' + str(y)]['VALID'] for y in (2017, 2019, 2020))
    run.save('satisfaction', combined, expected)
    # Les libelles non resolus, ex. Ocean Indien, restent exploitables sans
    # attribution arbitraire a une seule region INSEE (Reunion/Mayotte).
    observed = combined.select('code_region', F.col('region')).distinct()
    regions = run.load('region').unionAll(observed).distinct()
    # Pas de reecriture de la sortie physique precedente.
    initial = run.outputs.pop('region')
    run.outputs['region_reference'] = initial
    old_save_root = run.root
    run.root = old_save_root + '/enrichissement_satisfaction'
    try:
        run.save('region', regions)
    finally:
        run.root = old_save_root
        run.outputs.pop('region_reference')


def deces(run):
    from pyspark.sql import functions as F
    spec = C.TABLES['deces'] + C.TABLES['defunt'][1:]
    # code departement calcule dans la passe Python ; region enrichie ensuite.
    # Les deces conservent toutes les occurrences : unique() n'utilise donc
    # pas leur empreinte de doublon interne, absente des sorties et des rejets.
    df = run.normalized('deces', 'deces', spec, compute_payload=False).persist(run.level)
    fingerprint = run.fingerprints['deces']
    identity = {'checksum': fingerprint['checksum'], 'length': fingerprint['length'],
                'parser_contract': 'hadoop_text_offset_csv_v1'}
    file_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode('utf-8')).hexdigest()
    registry = run.config['keys_root'].rstrip('/') + '/deces/' + file_id
    target = run.Path(registry)
    if run.fs.exists(target):
        if not run.fs.exists(run.Path(registry + '/_SUCCESS')):
            raise ValueError('Registre de cles incomplet : intervention necessaire')
        mapping = run.sql.read.orc(registry)
    else:
        lock = run.Path(registry + '.lock')
        run.fs.mkdirs(lock.getParent())
        stream = run.fs.create(lock, False)  # verrou exclusif inter-processus
        stream.close()
        # Seules les references techniques sont indexees, pas les noms/valeurs.
        ids = df.select('_record_id').rdd.map(lambda row: row['_record_id']).zipWithIndex()
        mapping = run.sql.createDataFrame(ids.map(lambda pair: (pair[0], pair[1] + 1)),
            C.schema([('_record_id', 'STRING'), ('_allocated_key', 'BIGINT')]))
        maximum = mapping.agg(F.max('_allocated_key').alias('maximum')).collect()[0]['maximum'] or 0
        if maximum > 2147483647:
            raise ValueError('Registre deces depasse INT : migration BIGINT necessaire')
        staging = registry + '.staging_' + run.attempt
        mapping.write.mode('error').orc(staging)
        if run.fs.exists(target) or not run.fs.rename(run.Path(staging), target):
            raise ValueError('Publication du registre impossible')
        run.fs.delete(lock, False)
        mapping = run.sql.read.orc(registry)
    if mapping.groupBy('_record_id').count().filter('count > 1').limit(1).count():
        raise ValueError('Registre duplique')
    joined = df.join(mapping, '_record_id', 'left_outer')
    if joined.filter(F.col('_allocated_key').isNull()).limit(1).count():
        raise ValueError('Registre incompatible avec la lecture source')
    joined = (joined.withColumn('deces_key', F.col('_allocated_key').cast('int'))
              .withColumn('defunt_key', F.col('_allocated_key').cast('int')))
    geo = run.load('commune').select(
        F.col('code_commune_insee').alias('_commune'),
        F.col('code_departement').alias('_dep'),
        F.col('code_region').alias('_reg'), F.col('libelle_region').alias('_lib'))
    joined = joined.join(F.broadcast(geo), joined['code_commune_deces'] == geo['_commune'], 'left_outer')
    joined = (joined.withColumn('code_departement', F.coalesce(F.col('_dep'), F.col('code_departement')))
              .withColumn('code_region', F.col('_reg'))
              .withColumn('libelle_region', F.col('_lib'))
              .withColumn('statut_rattachement', F.when(F.col('_lib').isNull(), F.lit('NON_RESOLU')).otherwise(F.lit('COG_2024'))))
    accepted, cached = run.finish('deces', joined)
    count = run.metrics['deces']['VALID']
    missing_region_2019 = F.sum(F.when(
        (F.year('date_deces') == 2019) & F.col('code_region').isNull(), 1).otherwise(0))
    quality = run.save('deces', accepted, count,
                       extra_quality={'__chu_region_2019_unresolved': missing_region_2019})
    run.save('defunt', accepted, count)
    cached.unpersist()
    df.unpersist()
    run.metrics['deces']['key_registry'] = registry
    run.metrics['deces']['region_2019_unresolved'] = quality['__chu_region_2019_unresolved']


PIPELINES = [('01', referentiels), ('02', patients), ('03', professionnels_etablissements),
             ('04', consultations), ('05', hospitalisations), ('06', satisfaction), ('07', deces)]


# ==================== PUBLICATION DE SILVER ====================
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
                '-n', 'cloudera', '--silent=true', '--showHeader=false',
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
                        run.sc._jvm.org.apache.hadoop.fs.FileUtil.copy(run.fs, status.getPath(),
                            run.fs, run.Path(target), False, run.sc._jsc.hadoopConfiguration())
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
                  'metrics': metrics, 'hive_database': 'silver'}
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
