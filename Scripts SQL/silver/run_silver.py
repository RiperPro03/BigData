#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""spark-submit --py-files chu_silver.zip run_silver.py --config ...

Ne depend ni de SparkSession, ni d'argparse, ni de pandas, ni de Python 3.
"""
import datetime
import json
import os
import re
import sys
import uuid
import posixpath
from optparse import OptionParser


def arguments():
    parser = OptionParser()
    parser.add_option('--config', dest='config', help='Configuration JSON locale')
    parser.add_option('--lot-id', dest='lot', help='Identifiant du lot [a-z0-9_], 32 caracteres max')
    parser.add_option('--attempt-id', dest='attempt', help='Optionnel : identifiant unique de tentative')
    parser.add_option('--hmac-key-file', dest='key_file', help='Fichier binaire local, jamais sa valeur')
    parser.add_option('--key-version', dest='key_version', help='Version logique publique de la cle')
    parser.add_option('--exclude-pseudonyms-file', dest='exclude_file', help='Liste locale des HMAC exclus, un par ligne')
    parser.add_option('--until', dest='until', default='08', help='Arret apres 01..08 (08 = complet)')
    parser.add_option('--source-attempt', dest='source_attempt', help='Tentative achevee de la phase precedente')
    parser.add_option('--legacy-attempt', dest='legacy_attempt', help='Import explicite du lot historique documente')
    options, positional = parser.parse_args()
    if positional or not all([options.config, options.lot, options.key_file, options.key_version]):
        parser.error('--config, --lot-id, --hmac-key-file et --key-version sont obligatoires')
    if not re.match(r'^[a-z0-9_]{1,32}$', options.lot):
        parser.error('lot-id invalide')
    options.attempt = options.attempt or ('a' + datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S') + uuid.uuid4().hex[:6])
    if not re.match(r'^[a-z0-9_]{1,32}$', options.attempt):
        parser.error('attempt-id invalide')
    if options.until not in ['01', '02', '03', '04', '05', '06', '07', '08']:
        parser.error('until doit etre entre 01 et 08')
    return options


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


def main():
    options = arguments()
    if options.source_attempt or options.legacy_attempt:
        raise ValueError('Utiliser les trois lanceurs Silver pour une reprise par phase')
    with open(options.config, 'rb') as stream:
        config = json.loads(stream.read().decode('utf-8'))
    validate_setup(config)
    key, excluded = read_key_and_exclusions(options)
    from pyspark import SparkConf, SparkContext
    from pyspark.sql import HiveContext
    from chu_silver.runtime import Run
    from chu_silver.pipelines import PIPELINES
    from chu_silver.rules import pseudonym
    conf = SparkConf().setAppName('CHU_Silver_' + options.lot)
    conf.set('spark.sql.shuffle.partitions', str(config.get('shuffle_partitions', 16)))
    conf.set('spark.hadoop.orc.compress', 'SNAPPY')
    conf.set('spark.sql.orc.filterPushdown', 'true')
    sc = SparkContext(conf=conf)
    run = None
    try:
        if sc.version.split('.')[:2] != ['1', '6']:
            raise ValueError('Cette livraison cible Spark 1.6 : verifier la compatibilite avant migration')
        sc.setLogLevel('WARN')
        sql = HiveContext(sc)
        # Verifie l'execution Python et la meme primitive HMAC driver/worker.
        expected = pseudonym('42', key)
        probe = sc.parallelize(['42'], 1).map(lambda value: pseudonym(value, key)).collect()
        if probe != [expected]:
            raise ValueError('Test HMAC driver/worker non concordant')
        run = Run(sc, sql, config, options.lot, options.attempt, key, options.key_version, excluded)
        for step, function in PIPELINES:
            if step > options.until:
                break
            print('SILVER_STEP_START ' + step)
            function(run)
            run.write_json('progression_' + step + '.json', {'step': step, 'outputs': run.outputs, 'metrics': run.metrics})
            print('SILVER_STEP_OK ' + step)
        if options.until == '08':
            run.complete()
        else:
            run.write_json('rapport_partiel.json', {'status': 'PARTIAL_NOT_PUBLISHED', 'until': options.until,
                            'outputs': run.outputs, 'metrics': run.metrics})
            print('SILVER_PARTIAL : ' + run.audit)
    except Exception:
        if run is not None:
            # Ne pas serialiser la valeur d'une exception contenant des donnees.
            try:
                run.write_json('ECHEC.json', {'status': 'FAILED', 'exception_type': sys.exc_info()[0].__name__})
            except Exception:
                pass
        raise
    finally:
        sc.stop()


if __name__ == '__main__':
    main()
