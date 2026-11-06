# -*- coding: utf-8 -*-
"""Teste la reprise professionnelle sur des lignes fictives uniquement."""
import hashlib
import hmac
import os
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyspark import SparkConf, SparkContext
from pyspark.sql import HiveContext
from chu_silver import contracts as C, split
from chu_silver.runtime import Run
from maintenance.pseudonymiser_professionnels_legacy import pseudonymize_frame, migrate_checkpoint

key = b'0' * 32
conf = SparkConf().setAppName('CHU_Migration_Professionnels_Fictive')
conf.set('spark.sql.shuffle.partitions', '2')
sc = SparkContext(conf=conf)
sc.setLogLevel('WARN')
sql = HiveContext(sc)
try:
    pro_ids = ['012345678', '12345678901']
    datasets = {
        'professionnel': [(pro_ids[0], 'FICTIF', 'P1', 'S1'),
                          (pro_ids[1], 'FICTIF', 'P2', 'S2')],
        'activite': [(pro_ids[0], 'F000000001', 'A'),
                     (pro_ids[1], 'F000000002', 'B')],
        'consultation': [(1, None, 'patient_1', 'D1', pro_ids[0]),
                         (2, None, 'patient_2', 'D2', pro_ids[1])]
    }
    for table, data in datasets.items():
        frame = sql.createDataFrame(data, C.schema(C.TABLES[table]))
        transformed = pseudonymize_frame(frame, key)
        actual = sorted([tuple(row) for row in transformed.collect()], key=repr)
        index = C.names(table).index('id_prof_sante')
        expected = []
        for row in data:
            values = list(row)
            values[index] = hmac.new(key, ('pro:' + values[index]).encode('utf-8'), hashlib.sha256).hexdigest()
            expected.append(tuple(values))
        assert actual == sorted(expected, key=repr), table
        assert transformed.schema == frame.schema
    bad = sql.createDataFrame([(None, 'FICTIF', 'P', 'S')], C.schema(C.TABLES['professionnel']))
    try:
        pseudonymize_frame(bad, key)
        raise AssertionError('Identifiant absent accepte')
    except ValueError:
        pass
    bad = sql.createDataFrame([('123', 'FICTIF', 'P', 'S')], C.schema(C.TABLES['professionnel']))
    try:
        pseudonymize_frame(bad, key)
        raise AssertionError('Identifiant invalide accepte')
    except ValueError:
        pass
    # Test de la reprise complete avec 14 tables fictives et un checkpoint 02.
    base = '/user/cloudera/chu/tests_silver_fictifs/pro_' + uuid.uuid4().hex
    local = tempfile.mkdtemp(prefix='chu_pro_fixture_')
    filename = os.path.join(local, 'source.csv')
    try:
        with open(filename, 'w') as stream:
            stream.write('x\n1\n')
        subprocess.check_call(['hdfs', 'dfs', '-mkdir', '-p', base + '/bronze'])
        subprocess.check_call(['hdfs', 'dfs', '-put', filename, base + '/bronze/source.csv'])
        config = {'bronze_root': base + '/bronze', 'runs_root': base + '/runs',
                  'keys_root': base + '/keys', 'output_partitions': {},
                  'sources': {'source': {'path': 'source.csv'}}}
        source = Run(sc, sql, config, 'fictifpro', 'source_02', key, 'fictive', set())
        for name in sorted(C.TABLES):
            path = source.root + '/tables/' + name
            example = datasets[name][0] if name in datasets else tuple([None] * len(C.TABLES[name]))
            sql.createDataFrame([example], C.schema(C.TABLES[name])).write.orc(path)
            source.outputs[name] = {'path': path, 'rows': 1}
            config['output_partitions'][name] = 1
        # Les options font partie de l'identite : elles sont fixees avant le checkpoint.
        split.write_checkpoint(source, '02', 'phase_01', True)
        target = Run(sc, sql, config, 'fictifpro', 'reprise_pro', key, 'fictive', set())
        migrate_checkpoint(target, 'source_02')
        checkpoint = split.read_json(target, target.audit + '/checkpoint_02.json')
        assert not checkpoint['legacy_unverified_pro']
        assert checkpoint['migrated_from_attempt'] == 'source_02'
        assert checkpoint['source_attempt'] == 'phase_01'
        for name in ('professionnel', 'activite', 'consultation'):
            actual = target.sql.read.orc(target.outputs[name]['path']).collect()[0].asDict()
            expected = hmac.new(key, ('pro:' + pro_ids[0]).encode('utf-8'), hashlib.sha256).hexdigest()
            assert actual['id_prof_sante'] == expected, name
            assert target.outputs[name]['rows'] == 1
            original = source.sql.read.orc(source.outputs[name]['path']).collect()[0].asDict()
            assert original['id_prof_sante'] == pro_ids[0]
            for field in C.names(name):
                if field != 'id_prof_sante':
                    assert actual[field] == original[field], (name, field)
        for name in set(C.TABLES) - set(datasets):
            assert target.outputs[name]['path'] == source.outputs[name]['path'], name
        print('CHU_MIGRATION_PRO_CHECKPOINT_OK : ' + base)
    finally:
        if os.path.exists(filename):
            os.remove(filename)
        os.rmdir(local)
    print('CHU_MIGRATION_PRO_EQUIVALENCE_OK')
finally:
    sc.stop()
