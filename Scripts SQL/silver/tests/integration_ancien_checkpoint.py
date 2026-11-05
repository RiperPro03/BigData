# -*- coding: utf-8 -*-
"""Lecture seule du lot historique documente ; lance explicitement sur la VM."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyspark import SparkConf, SparkContext, StorageLevel
from pyspark.sql import HiveContext
from chu_silver.runtime import Run
from chu_silver import split

if len(sys.argv) != 3:
    raise ValueError('Usage : test <config.json> <fichier-cle>')
with open(sys.argv[1], 'rb') as stream:
    config = json.loads(stream.read().decode('utf-8'))
with open(os.path.expanduser(sys.argv[2]), 'rb') as stream:
    key = stream.read()
sc = SparkContext(conf=SparkConf().setAppName('CHU_Silver_Legacy_Resume_Validation')
                  .set('spark.sql.shuffle.partitions', '16'))
sc.setLogLevel('WARN')
try:
    run = Run.__new__(Run)
    run.sc, run.sql, run.config = sc, HiveContext(sc), config
    run.lot, run.attempt = 'initial_20261105', 'test_lecture_seule'
    run.key, run.key_version, run.excluded = key, 'test_v1', set()
    run.level, run.pending_cache = StorageLevel.DISK_ONLY, []
    run.Path = sc._jvm.org.apache.hadoop.fs.Path
    run.fs = run.Path(config['bronze_root']).getFileSystem(sc._jsc.hadoopConfiguration())
    run.fingerprints = {}
    for name, spec in sorted(config['sources'].items()):
        run.fingerprints[name] = run.fingerprint(run.path(spec))
    state = split.load_legacy(run, split.LEGACY_ATTEMPT)
    assert set(state['outputs']) == split.CORE_TABLES
    assert state['legacy_unverified_pro']
    print('CHU_SILVER_LEGACY_CHECKPOINT_OK')
finally:
    sc.stop()
