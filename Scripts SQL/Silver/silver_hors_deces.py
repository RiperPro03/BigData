# -*- coding: utf-8 -*-
"""Regles et transformations Silver hors deces."""
import sys
import silver_pipeline as C
rules = sys.modules[__name__]

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
        df = run.sql.createDataFrame(df.rdd.map(normalize_region), C.schema(C.TABLES['satisfaction'] + C.META))
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




PIPELINES = [('01', referentiels), ('02', patients), ('03', professionnels_etablissements),
             ('04', consultations), ('05', hospitalisations), ('06', satisfaction)]



if __name__ == '__main__':
    C.phase_main('01')
