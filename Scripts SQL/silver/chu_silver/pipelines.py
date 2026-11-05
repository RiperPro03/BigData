# -*- coding: utf-8 -*-
"""Les sept branches metier. Publication et qualite globale dans Run.complete."""
import hashlib
import json
from . import contracts as C
from . import rules
from .runtime import META


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
    df = run.normalized('deces', 'deces', spec).persist(run.level)
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
    run.save('deces', accepted, count)
    run.save('defunt', accepted, count)
    cached.unpersist()
    df.unpersist()
    run.metrics['deces']['key_registry'] = registry
    run.metrics['deces']['region_2019_unresolved'] = run.load('deces').filter(
        (F.year('date_deces') == 2019) & F.col('code_region').isNull()).count()


PIPELINES = [('01', referentiels), ('02', patients), ('03', professionnels_etablissements),
             ('04', consultations), ('05', hospitalisations), ('06', satisfaction), ('07', deces)]
