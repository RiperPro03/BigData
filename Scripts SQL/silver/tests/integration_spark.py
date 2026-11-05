# -*- coding: utf-8 -*-
"""Test a lancer avec spark-submit sur la VM. Pas de lecture du Bronze.

Valide joins, conflits, rejets, lecture CSV offset, DATE et aller-retour ORC.
Les sorties sont uniquement des donnees fictives dans un repertoire temporaire.
"""
import datetime
import json
import os
import shutil
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyspark import SparkContext, StorageLevel
from pyspark.sql import HiveContext
from chu_silver import contracts as C
from chu_silver.runtime import Run
from chu_silver.readers import read_records

sc = SparkContext(appName='CHU_Silver_Integration_Fictive')
sc.setLogLevel('WARN')
sql = HiveContext(sc)
work = tempfile.mkdtemp(prefix='chu_silver_integration_')
try:
    run = Run.__new__(Run)
    run.sc, run.sql = sc, sql
    run.key = b'0123456789abcdef0123456789abcdef'
    run.excluded, run.pending_cache = set(), []
    run.level = StorageLevel.DISK_ONLY
    # Repetition exacte, conflit de sexe et reference orpheline.
    source = [('a', {'Id_patient': '1', 'Age': '30', 'Sexe': 'M'}),
              ('b', {'Id_patient': '1', 'Age': '30', 'Sexe': 'M'}),
              ('c', {'Id_patient': '2', 'Age': '40', 'Sexe': 'M'}),
              ('d', {'Id_patient': '2', 'Age': '40', 'Sexe': 'F'}),
              ('e', {'Id_patient': '', 'Age': '40', 'Sexe': 'F'})]
    df = run.normalized('test', 'patient', C.TABLES['patient'], records=sc.parallelize(source, 2))
    df = run.unique(df, ['id_patient'])
    counts = dict((r['_status'], r['count']) for r in df.groupBy('_status').count().collect())
    assert counts == {'VALID': 1, 'DUPLICATE': 1, 'REJECT': 3}, counts
    reference = df.filter("_status = 'VALID'").select('id_patient')
    joined = run.reference(df, 'id_patient', reference, 'REFERENCE_PATIENT_ABSENTE')
    assert joined.count() == 5
    for cached in run.pending_cache:
        cached.unpersist()
    # Le CSV reste decoupe par enregistrement, avec offset stable.
    filename = os.path.join(work, 'source.csv')
    with open(filename, 'w') as stream:
        stream.write('id;libelle\n1;"test; cite"\n2;autre\n')
    records = read_records(sc, 'file://' + filename, 'fictif',
        {'delimiter': json.loads('";"'), 'encoding': 'utf-8', 'required': ['id', 'libelle']}, 1024).collect()
    assert len(records) == 2
    assert records[0][0] != records[1][0]
    assert any(row[1]['libelle'] == 'test; cite' for row in records)
    # Dates historiques et schemas explicitement relus.
    df = sql.createDataFrame([(1, datetime.date(1882, 1, 1), 'inconnu', 1, None, None, None, 'NON_RESOLU')],
                             C.schema(C.TABLES['deces']))
    path = 'file://' + os.path.join(work, 'orc')
    df.write.orc(path)
    result = sql.read.orc(path).collect()[0]
    assert result['date_deces'] == datetime.date(1882, 1, 1)
    assert 'numero_acte_deces' not in result.asDict()
    print('CHU_SILVER_INTEGRATION_OK')
finally:
    sc.stop()
    # Repertoire explicitement cree par ce test, jamais un chemin HDFS/projet.
    if os.path.realpath(work).startswith(os.path.realpath(tempfile.gettempdir()) + os.sep + 'chu_silver_integration_'):
        shutil.rmtree(work)
