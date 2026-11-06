# -*- coding: utf-8 -*-
"""Phase 02 : traitement des deces et registre des cles."""
import hashlib
import json
import silver_hors_deces as C

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

if __name__ == '__main__':
    C.phase_main('02')
