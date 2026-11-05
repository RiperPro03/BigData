# -*- coding: utf-8 -*-
"""Branche deces et registre HDFS, deux executions sur quatre lignes fictives."""
import os
import datetime
import subprocess
import tempfile
import uuid
from pyspark import SparkConf, SparkContext
from pyspark.sql import HiveContext
from chu_silver import contracts as C
from chu_silver.runtime import Run
from chu_silver.pipelines import deces
from chu_silver.rules import pseudonym

conf = SparkConf().setAppName('CHU_Silver_Deces_Fictifs').set('spark.sql.shuffle.partitions', '2')
sc = SparkContext(conf=conf)
sc.setLogLevel('WARN')
sql = HiveContext(sc)
base = '/user/cloudera/chu/tests_silver_fictifs/' + uuid.uuid4().hex
lot = 'fictif_' + uuid.uuid4().hex[:8]
directory = tempfile.mkdtemp(prefix='chu_deces_fixture_')
filename = os.path.join(directory, 'deces.csv')
try:
    with open(filename, 'w') as stream:
        stream.write('nom,prenom,sexe,date_naissance,code_lieu_naissance,lieu_naissance,pays_naissance,date_deces,code_lieu_deces,numero_acte_deces\n')
        stream.write('FICTIF,TEST,1,1900-01-01,75056,Paris,France,2019-01-01,75056,1\n')
        stream.write('FICTIF,TEST,1,1900-01-01,75056,Paris,France,2019-01-01,75056,1\n')
        stream.write('FICTIF,TEST,2,1900-00-00,75056,Paris,France,2019-01-02,99999,\n')
        stream.write('FICTIF,TEST,1,1900-01-01,75056,Paris,France,2019-02-30,75056,2\n')
    subprocess.check_call(['hdfs', 'dfs', '-mkdir', '-p', base + '/bronze'])
    subprocess.check_call(['hdfs', 'dfs', '-put', filename, base + '/bronze/deces.csv'])
    config = {'bronze_root': base + '/bronze', 'runs_root': base + '/runs', 'keys_root': base + '/keys',
              'output_partitions': {'commune': 1, 'deces': 1, 'defunt': 1},
              'sources': {'deces': {'path': 'deces.csv', 'delimiter': u',', 'encoding': 'utf-8', 'required': C.DECES}}}
    first = None
    for attempt in ('a1', 'a2'):
        run = Run(sc, sql, config, lot, attempt, b'0' * 32, 'fictive', set())
        geo = [('75056', 'COM', None, 'Paris', '75', '11', 'Ile-de-France', 'COG_2024')]
        run.save('commune', sql.createDataFrame(geo, C.schema(C.TABLES['commune'])), 1)
        deces(run)
        assert run.metrics['deces']['read'] == 4
        assert run.metrics['deces']['VALID'] == 3
        assert run.metrics['deces']['REJECT'] == 1
        assert run.outputs['deces']['rows'] == run.outputs['defunt']['rows'] == 3
        run.check_unique('deces')
        run.check_unique('defunt')
        keys = sorted(row['deces_key'] for row in run.load('deces').select('deces_key').collect())
        assert len(set(keys)) == 3
        if first is None:
            first = keys
        else:
            assert first == keys
        assert run.load('deces').filter('code_region IS NULL').count() == 1
        assert run.load('defunt').filter('date_naissance IS NULL').count() == 1
    # Finalisation 08 : contrats et references de toutes les autres tables,
    # a partir d'une seule ligne fictive coherente par table.
    patient = pseudonym('1', b'0' * 32)
    org, prof = 'F010000001', '012345678'
    site = dict((name, None) for name in C.ETABLISSEMENT)
    site['identifiant_organisation'] = org
    fixtures = {
        'patient': [(patient, 'M', 30)],
        'diagnostic': [('D1', 'FICTIF')],
        'specialite': [('S1', 'FICTIF', 'FICTIF')],
        'professionnel': [(prof, 'FICTIF', 'FICTIF', 'FICTIF')],
        'etablissement': [tuple(site[name] for name in C.ETABLISSEMENT)],
        'activite': [(prof, org, 'FICTIF')],
        'consultation': [(1, datetime.date(2019, 1, 1), patient, 'D1', prof)],
        'hospitalisation': [(1, datetime.date(2019, 1, 1), patient, 'D1', org)],
        'satisfaction': [('010000001', org, 2020, 'Ile-de-France', '11', 75.0, 10)],
        'region': [('11', 'Ile-de-France')],
        'codes_postaux': [('75056', 'Paris', '75001', 'Paris')]
    }
    for table, rows in fixtures.items():
        run.config['output_partitions'][table] = 1
        run.save(table, sql.createDataFrame(rows, C.schema(C.TABLES[table])), len(rows))
    run.complete()
    print('CHU_PUBLICATION_FICTIVE_HQL : ' + run.audit + '/publication.hql')
    print('CHU_DECES_REGISTRE_OK : ' + base)
finally:
    sc.stop()
    if os.path.exists(filename):
        os.remove(filename)
    os.rmdir(directory)
