# -*- coding: utf-8 -*-
"""Checkpoints en Spark local, uniquement des tables fictives."""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyspark import SparkContext
from pyspark.sql import HiveContext
from chu_silver import contracts as C
from chu_silver import split
from chu_silver.runtime import Run


def fake_run(sc, sql, work, attempt):
    run = Run.__new__(Run)
    run.sc, run.sql = sc, sql
    run.config = {'runs_root': os.path.join(work, 'runs')}
    run.lot, run.attempt, run.key_version = 'lot_fictif', attempt, 'test'
    run.key, run.excluded, run.input_id = b'k' * 32, set(), 'faux_manifest'
    run.root = run.config['runs_root'] + '/' + run.lot + '/' + attempt
    run.audit = run.root + '/audit'
    run.Path = sc._jvm.org.apache.hadoop.fs.Path
    run.fs = run.Path(run.root).getFileSystem(sc._jsc.hadoopConfiguration())
    run.fs.mkdirs(run.Path(run.audit))
    run.outputs, run.metrics = {}, {}
    return run


sc = SparkContext(appName='CHU_Silver_Reprise_Fictive')
sc.setLogLevel('WARN')
sc._jsc.hadoopConfiguration().set('fs.defaultFS', 'file:///')
sql = HiveContext(sc)
work = tempfile.mkdtemp(prefix='chu_silver_resume_test_')
try:
    first = fake_run(sc, sql, work, 'phase_01')
    for name in sorted(split.CORE_TABLES):
        path = first.root + '/tables/' + name
        sql.createDataFrame(sc.parallelize([tuple([None] * len(C.TABLES[name]))], 1),
                            C.schema(C.TABLES[name])).write.orc(path)
        first.outputs[name] = {'path': path, 'rows': 1}
    split.write_checkpoint(first, '01', None, False)
    second = fake_run(sc, sql, work, 'phase_02')
    state = split.saved_checkpoint(second, 'phase_01', '01')
    assert set(state['outputs']) == split.CORE_TABLES
    second.key = b'x' * 32
    try:
        split.saved_checkpoint(second, 'phase_01', '01')
        raise AssertionError('Une autre cle doit etre refusee')
    except ValueError:
        pass
    second.key = b'k' * 32
    second.outputs, second.metrics = state['outputs'], state['metrics']
    for name in ('deces', 'defunt'):
        path = second.root + '/tables/' + name
        sql.createDataFrame(sc.parallelize([tuple([None] * len(C.TABLES[name]))], 1),
                            C.schema(C.TABLES[name])).write.orc(path)
        second.outputs[name] = {'path': path, 'rows': 1}
    split.write_checkpoint(second, '02', 'phase_01', False)
    third = fake_run(sc, sql, work, 'phase_03')
    state = split.saved_checkpoint(third, 'phase_02', '02')
    assert set(state['outputs']) == set(C.TABLES)
    assert state['source_attempt'] == 'phase_01'
    print('CHU_SILVER_REPRISE_INTEGRATION_OK')
finally:
    sc.stop()
    if os.path.realpath(work).startswith(os.path.realpath(tempfile.gettempdir()) + os.sep + 'chu_silver_resume_test_'):
        shutil.rmtree(work)
