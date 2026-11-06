#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Reprise unique d'un checkpoint historique dont les professionnels sont en clair.

Les trois tables anciennes sont lues et reecrites dans une nouvelle tentative,
en appliquant strictement la primitive HMAC professionnelle de rules.py. Toutes
les autres tables, notamment les deces, restent referencees sans reecriture.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run_silver import arguments, read_key_and_exclusions, validate_setup
from chu_silver import contracts as C, rules, split
from chu_silver.runtime import Run


def pseudonymize_frame(df, key):
    """Rejette toute cle historique absente/inattendue avant pseudonymisation."""
    from pyspark.sql import functions as F, types as T
    identifier = F.col('id_prof_sante')
    valid_format = identifier.rlike(r'^([0-9A-Za-z]{9}|[0-9]{11})$')
    if df.filter(identifier.isNull() | ~valid_format).limit(1).count():
        raise ValueError('Identifiant professionnel historique invalide')
    convert = F.udf(lambda value: rules.pro_pseudonym(value, key), T.StringType())
    return df.withColumn('id_prof_sante', convert(identifier))


def migrate_checkpoint(run, source_attempt):
    state = split.saved_checkpoint(run, source_attempt, '02')
    if not state.get('legacy_unverified_pro', False):
        raise ValueError('Le checkpoint ne necessite pas cette reprise historique')
    run.outputs, run.metrics = state['outputs'], state['metrics']
    source_paths, target_paths = {}, {}
    for table in ('professionnel', 'activite', 'consultation'):
        previous = run.outputs[table]
        source_paths[table] = previous['path']
        df = run.sql.read.orc(previous['path'])
        converted = pseudonymize_frame(df, run.key)
        print('MIGRATION_PRO_START ' + table)
        run.save(table, converted, previous['rows'])
        target_paths[table] = run.outputs[table]['path']
        print('MIGRATION_PRO_OK ' + table)
    split.validate_outputs(run, run.outputs, set(C.TABLES))
    source_file = __file__[:-1] if __file__.endswith(('.pyc', '.pyo')) else __file__
    with open(source_file, 'rb') as stream:
        code_sha = hashlib.sha256(stream.read().replace(b'\r\n', b'\n')).hexdigest()
    migration = {'source_checkpoint_02': source_attempt,
                 'algorithm': 'HMAC-SHA256', 'domain': 'pro:',
                 'tables': sorted(source_paths), 'input_paths': source_paths,
                 'output_paths': target_paths, 'script_sha256': code_sha}
    run.write_json('migration_professionnels.json', migration)
    checkpoint = {'stage': '02', 'lot': run.lot, 'attempt': run.attempt,
                  'source_attempt': state.get('source_attempt'),
                  'migrated_from_attempt': source_attempt,
                  'legacy_unverified_pro': False, 'identity': split.checkpoint_identity(run),
                  'outputs': run.outputs, 'metrics': run.metrics}
    run.write_json('checkpoint_02.json', checkpoint)
    print('SILVER_PRO_MIGRATION_OK : ' + run.audit)


def main():
    options = arguments()
    if not options.source_attempt or options.legacy_attempt or options.until != '08':
        raise ValueError('Fournir --source-attempt du checkpoint 02 historique')
    with open(options.config, 'rb') as stream:
        config = json.loads(stream.read().decode('utf-8'))
    validate_setup(config)
    key, excluded = read_key_and_exclusions(options)
    from pyspark import SparkConf, SparkContext
    from pyspark.sql import HiveContext
    conf = SparkConf().setAppName('CHU_Silver_Migration_Professionnels_' + options.lot)
    conf.set('spark.sql.shuffle.partitions', str(config.get('shuffle_partitions', 16)))
    conf.set('spark.hadoop.orc.compress', 'SNAPPY')
    conf.set('spark.sql.orc.filterPushdown', 'true')
    sc = SparkContext(conf=conf)
    run = None
    try:
        if sc.version.split('.')[:2] != ['1', '6']:
            raise ValueError('Cette reprise cible Spark 1.6')
        sc.setLogLevel('WARN')
        sql = HiveContext(sc)
        run = Run(sc, sql, config, options.lot, options.attempt, key, options.key_version, excluded)
        migrate_checkpoint(run, options.source_attempt)
    except Exception:
        if run is not None:
            try:
                run.write_json('ECHEC.json', {'status': 'FAILED', 'exception_type': sys.exc_info()[0].__name__})
            except Exception:
                pass
        raise
    finally:
        sc.stop()


if __name__ == '__main__':
    main()
