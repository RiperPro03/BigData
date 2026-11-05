# -*- coding: utf-8 -*-
"""Compare les versions historique et optimisee sur donnees fictives.

Test Spark 1.6 explicite : ne lit ni les sources ni les resultats reels. Les
donnees de test sont conservees dans un dossier HDFS unique pour audit.
"""
import datetime
import os
import subprocess
import tempfile
import time
import uuid

from pyspark import SparkConf, SparkContext
from pyspark.sql import HiveContext, functions as F
from chu_silver import contracts as C
from chu_silver.runtime import Run
from chu_silver.pipelines import deces


class LegacyRun(Run):
    """Methode de calcul avant optimisation, conservee pour comparaison."""
    def normalized(self, source, kind, spec, options=None, records=None, compute_payload=True):
        return Run.normalized(self, source, kind, spec, options, records, compute_payload=True)

    def save(self, table, df, expected=None, extra_quality=None):
        started = time.time()
        df = df.select(*C.names(table))
        path = self.root + '/tables/' + table
        partitions = self.config.get('output_partitions', {}).get(table, 4)
        if partitions < 1:
            raise ValueError('Nombre de partitions invalide')
        df.repartition(partitions).write.mode('error').orc(path)
        readback = self.sql.read.orc(path)
        actual = readback.count()
        if expected is not None and actual != expected:
            raise ValueError('Cardinalite modifiee pour ' + table)
        if readback.schema != C.schema(C.TABLES[table]):
            actual_schema = [(f.name, f.dataType.simpleString()) for f in readback.schema.fields]
            expected_schema = [(f.name, f.dataType.simpleString()) for f in C.schema(C.TABLES[table]).fields]
            if actual_schema != expected_schema:
                raise ValueError('Schema relu incompatible : ' + table)
        completeness = readback.agg(*[
            F.sum(F.when(F.col(name).isNull(), 1).otherwise(0)).alias(name)
            for name in C.names(table)]).collect()[0].asDict()
        nulls = dict((name, int(value or 0)) for name, value in completeness.items())
        self.outputs[table] = {'path': path, 'rows': actual, 'nulls': nulls,
            'completeness': dict((name, (float(actual - n) / actual if actual else None))
                                 for name, n in nulls.items()),
            'seconds': round(time.time() - started, 3), 'partitions_requested': partitions,
            'schema': C.TABLES[table]}
        if extra_quality:
            # L'ancien pipeline effectuait ce comptage dans une lecture separee.
            return {'__chu_region_2019_unresolved': readback.filter(
                (F.year('date_deces') == 2019) & F.col('code_region').isNull()).count()}
        return {}


def rows(df):
    """Inclut les doublons ; collect uniquement de notre fixture fictive."""
    return sorted([tuple(row) for row in df.collect()], key=repr)


def output_quality(output):
    return dict((name, value) for name, value in output.items()
                if name not in ('path', 'seconds'))


conf = SparkConf().setAppName('CHU_Silver_Equivalence_Fictive')
conf.set('spark.sql.shuffle.partitions', '2')
sc = SparkContext(conf=conf)
sc.setLogLevel('WARN')
sql = HiveContext(sc)
base = '/user/cloudera/chu/tests_silver_fictifs/perf_' + uuid.uuid4().hex
lot = 'comparaison'
directory = tempfile.mkdtemp(prefix='chu_perf_fixture_')
filename = os.path.join(directory, 'deces.csv')
copies = int(os.environ.get('CHU_PERF_FIXTURE_COPIES', '100'))
if copies < 1 or copies > 10000:
    raise ValueError('CHU_PERF_FIXTURE_COPIES doit etre entre 1 et 10000')
try:
    with open(filename, 'w') as stream:
        stream.write('nom,prenom,sexe,date_naissance,code_lieu_naissance,lieu_naissance,pays_naissance,date_deces,code_lieu_deces,numero_acte_deces\n')
        for unused in range(copies):
            stream.write('FICTIF,A,1,1900-01-01,75056,Paris,France,2019-01-01,75056,1\n')
            stream.write('FICTIF,A,1,1900-01-01,75056,Paris,France,2019-01-01,75056,1\n')
            stream.write('FICTIF,B,2,1900-00-00,75056,Paris,France,2019-01-02,99999,\n')
            stream.write('FICTIF,C,1,1900-01-01,75056,Paris,France,2019-02-30,75056,2\n')
            stream.write('FICTIF,D,2,2020-01-01,75056,Paris,France,2019-01-02,75056,3\n')
            stream.write('FICTIF,E,?,,,,France,2018-01-01,,4\n')
            stream.write('FICTIF,F,1,1900-01-01,75056,Paris,France,,75056,5\n')
    subprocess.check_call(['hdfs', 'dfs', '-mkdir', '-p', base + '/bronze'])
    subprocess.check_call(['hdfs', 'dfs', '-put', filename, base + '/bronze/deces.csv'])
    config = {'bronze_root': base + '/bronze', 'runs_root': base + '/runs',
              'keys_root': base + '/keys', 'shuffle_partitions': 2,
              'output_partitions': {'commune': 1, 'deces': 2, 'defunt': 2, 'diagnostic': 1},
              'sources': {'deces': {'path': 'deces.csv', 'delimiter': u',',
                                    'encoding': 'utf-8', 'required': C.DECES}}}
    runs = []
    for cls, attempt in ((LegacyRun, 'avant'), (Run, 'apres')):
        run = cls(sc, sql, config, lot, attempt, b'0' * 32, 'fictive', set())
        geo = [('75056', 'COM', None, 'Paris', '75', '11', 'Ile-de-France', 'COG_2024')]
        run.save('commune', sql.createDataFrame(geo, C.schema(C.TABLES['commune'])), 1)
        deces(run)
        runs.append(run)
    before, after = runs
    assert before.metrics == after.metrics, (before.metrics, after.metrics)
    assert before.metrics['deces']['read'] == 7 * copies
    assert before.metrics['deces']['VALID'] == 4 * copies
    assert before.metrics['deces']['REJECT'] == 3 * copies
    assert before.metrics['deces']['region_2019_unresolved'] == copies
    for table in ('deces', 'defunt', 'commune'):
        assert rows(before.load(table)) == rows(after.load(table)), table
        assert output_quality(before.outputs[table]) == output_quality(after.outputs[table]), table
    old_rejects = sql.read.orc(before.root + '/rejets/deces')
    new_rejects = sql.read.orc(after.root + '/rejets/deces')
    assert rows(old_rejects) == rows(new_rejects)
    assert len(rows(before.load('deces'))) == 4 * copies
    # Table de reference contenant des NULL : memes comptes et completudes.
    data = [(None, None), ('D1', None), ('D2', 'Libelle')]
    for run in runs:
        frame = sql.createDataFrame(data, C.schema(C.TABLES['diagnostic']))
        run.save('diagnostic', frame, len(data))
    assert rows(before.load('diagnostic')) == rows(after.load('diagnostic'))
    assert output_quality(before.outputs['diagnostic']) == output_quality(after.outputs['diagnostic'])
    # Comparer aussi une table sans ligne ; les deux versions doivent produire
    # le meme bilan, ou echouer de la meme facon sur cette version de Spark.
    empty_results = []
    for cls, attempt in ((LegacyRun, 'vide_avant'), (Run, 'vide_apres')):
        run = cls(sc, sql, config, lot, attempt, b'0' * 32, 'fictive', set())
        frame = sql.createDataFrame(data, C.schema(C.TABLES['diagnostic'])).filter(F.lit(False))
        try:
            run.save('diagnostic', frame, 0)
            empty_results.append(('OK', output_quality(run.outputs['diagnostic'])))
        except Exception as error:
            empty_results.append(('ERROR', type(error).__name__))
    assert empty_results[0] == empty_results[1], empty_results
    mismatch_results = []
    for cls, attempt in ((LegacyRun, 'mismatch_avant'), (Run, 'mismatch_apres')):
        run = cls(sc, sql, config, lot, attempt, b'0' * 32, 'fictive', set())
        frame = sql.createDataFrame(data, C.schema(C.TABLES['diagnostic']))
        try:
            run.save('diagnostic', frame, len(data) + 1)
            mismatch_results.append('ACCEPTE')
        except ValueError as error:
            mismatch_results.append(str(error))
    assert mismatch_results == ['Cardinalite modifiee pour diagnostic'] * 2, mismatch_results
    print('CHU_PERFORMANCE_EQUIVALENCE_OK : ' + base)
finally:
    sc.stop()
    if os.path.exists(filename):
        os.remove(filename)
    os.rmdir(directory)
