# -*- coding: utf-8 -*-
"""Trois lancements independants, avec checkpoints HDFS immuables.

Les calculs metier restent dans pipelines.py et runtime.py. Les anciens lots
ne contiennent pas de preuve de cle ni de version : leur import reste limite
au lot VM documente et ne permet pas une publication consideree conforme.
"""
import hashlib
import hmac
import json
import os
import posixpath
import pkgutil
import re
import sys

from . import contracts as C
from . import rules
from .runtime import Run
from .pipelines import PIPELINES
from run_silver import arguments

LEGACY_ATTEMPT = 'a20261105193046f8b2a7'
LEGACY_CONFIG = '439b32dee1b69a027efa5a5bd4e179ac420d816631669850611ff1a7d314a82f'
LEGACY_COMMIT = 'ef70957f161ee5b408719196e89e9c1dd9fccc2d'
CORE_TABLES = set(C.TABLES) - set(['deces', 'defunt'])


def digest(value):
    serialized = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(serialized.encode('ascii')).hexdigest()


def code_digest():
    result = hashlib.sha256()
    for name in ('__init__.py', 'contracts.py', 'pipelines.py', 'readers.py',
                 'rules.py', 'runtime.py', 'split.py'):
        result.update(name.encode('ascii'))
        data = pkgutil.get_data('chu_silver', name)
        if data is None:
            raise ValueError('Fichier de code manquant : ' + name)
        result.update(data.replace(b'\r\n', b'\n'))
    return result.hexdigest()


def key_proof(key):
    return hmac.new(key, b'CHU-SILVER-CHECKPOINT-KEY-V1', hashlib.sha256).hexdigest()


def checkpoint_identity(run):
    return {'input_id': run.input_id, 'config_digest': digest(run.config),
            'code_digest': code_digest(), 'key_proof': key_proof(run.key),
            'key_version': run.key_version, 'excluded_digest': digest(sorted(run.excluded))}


def same_identity(expected, actual):
    for name in ('input_id', 'config_digest', 'code_digest', 'key_proof',
                 'key_version', 'excluded_digest'):
        if expected.get(name) != actual.get(name):
            raise ValueError('Reprise refusee : parametre ou version different : ' + name)


def read_json(run, path):
    target = run.Path(path)
    if not run.fs.exists(target) or run.fs.getFileStatus(target).getLen() > 8 * 1024 * 1024:
        raise ValueError('Checkpoint manquant ou trop volumineux : ' + path)
    reader = run.sc._jvm.java.io.BufferedReader(
        run.sc._jvm.java.io.InputStreamReader(run.fs.open(target), 'UTF-8'))
    lines = []
    try:
        line = reader.readLine()
        while line is not None:
            lines.append(line)
            line = reader.readLine()
    finally:
        reader.close()
    return json.loads('\n'.join(lines))


def attempt_root(run, attempt):
    if not attempt or not re.match(r'^[a-z0-9_]{1,32}$', attempt):
        raise ValueError('Identifiant de tentative invalide')
    if attempt == run.attempt:
        raise ValueError('Une reprise doit utiliser une nouvelle tentative')
    return run.config['runs_root'].rstrip('/') + '/' + run.lot + '/' + attempt


def validate_outputs(run, outputs, required):
    if set(outputs) != required:
        raise ValueError('Tables du checkpoint incompletes ou inattendues')
    prefix = run.config['runs_root'].rstrip('/') + '/' + run.lot + '/'
    for name, entry in outputs.items():
        path = entry.get('path', '')
        if (not path.startswith(prefix) or posixpath.normpath(path) != path or
                not run.fs.exists(run.Path(path + '/_SUCCESS'))):
            raise ValueError('Sortie absente ou hors du lot : ' + name)
        actual = [(f.name, f.dataType.simpleString()) for f in run.sql.read.orc(path).schema.fields]
        expected = [(f.name, f.dataType.simpleString()) for f in C.schema(C.TABLES[name]).fields]
        if actual != expected:
            raise ValueError('Schema incompatible : ' + name)


def saved_checkpoint(run, attempt, stage):
    root = attempt_root(run, attempt)
    state = read_json(run, root + '/audit/checkpoint_' + stage + '.json')
    if state.get('stage') != stage or state.get('attempt') != attempt or state.get('lot') != run.lot:
        raise ValueError('Checkpoint incoherent')
    same_identity(state['identity'], checkpoint_identity(run))
    expected = CORE_TABLES if stage == '01' else set(C.TABLES)
    validate_outputs(run, state['outputs'], expected)
    return state


def load_legacy(run, attempt):
    """Import explicite du seul resultat v5 documente ; jamais de reecriture."""
    if attempt != LEGACY_ATTEMPT or digest(run.config) != LEGACY_CONFIG or run.excluded:
        raise ValueError('Import ancien limite a la tentative VM v5 et a sa configuration connue')
    root = attempt_root(run, attempt)
    manifest = read_json(run, root + '/audit/manifest_entrees.json')
    if manifest != run.fingerprints:
        raise ValueError('Bronze a change depuis la tentative historique')
    state = read_json(run, root + '/audit/progression_06.json')
    if state.get('step') != '06':
        raise ValueError('La phase hors deces historique est incomplete')
    outputs = state['outputs']
    validate_outputs(run, outputs, CORE_TABLES)
    # L'ancien audit n'a pas de preuve de cle : reconstruire seulement les
    # identifiants acceptes des patients pour comparer les ensembles exacts.
    from pyspark.sql import functions as F
    patients = run.normalized('patient', 'patient', C.TABLES['patient'])
    patients = run.unique(patients, ['id_patient'])
    expected = patients.filter(F.col('_status') == 'VALID').select('id_patient').distinct()
    actual = run.sql.read.orc(outputs['patient']['path']).select('id_patient').distinct()
    if not actual.limit(1).count() or expected.subtract(actual).limit(1).count() or actual.subtract(expected).limit(1).count():
        raise ValueError('Cle HMAC ou selection patient incompatible avec la tentative historique')
    for item in run.pending_cache:
        item.unpersist()
    run.pending_cache = []
    return {'outputs': outputs, 'metrics': state['metrics'],
            'legacy_unverified_pro': True, 'source_attempt': attempt,
            'source_code': LEGACY_COMMIT}


def write_checkpoint(run, stage, source_attempt, legacy):
    validate_outputs(run, run.outputs, CORE_TABLES if stage == '01' else set(C.TABLES))
    state = {'stage': stage, 'lot': run.lot, 'attempt': run.attempt,
             'source_attempt': source_attempt, 'legacy_unverified_pro': legacy,
             'identity': checkpoint_identity(run), 'outputs': run.outputs,
             'metrics': run.metrics}
    run.write_json('checkpoint_' + stage + '.json', state)
    print('SILVER_CHECKPOINT_' + stage + ' : ' + run.audit)


def main(stage):
    options = arguments()
    if options.until != '08':
        raise ValueError('--until est reserve au lanceur historique')
    if stage == '01' and (options.source_attempt or options.legacy_attempt):
        raise ValueError('La phase 01 cree un lot ; aucun lot source ne doit etre fourni')
    if stage == '02' and bool(options.source_attempt) == bool(options.legacy_attempt):
        raise ValueError('Phase 02 : fournir exactement --source-attempt ou --legacy-attempt')
    if stage == '03' and (not options.source_attempt or options.legacy_attempt):
        raise ValueError('Phase 03 : fournir --source-attempt de la phase 02')
    with open(options.config, 'rb') as stream:
        config = json.loads(stream.read().decode('utf-8'))
    # Les memes validations de chemins, de cle et de contexte que le lanceur
    # historique restent partagees, sans changement des regles metier.
    from run_silver import validate_setup, read_key_and_exclusions
    validate_setup(config)
    key, excluded = read_key_and_exclusions(options)
    from pyspark import SparkConf, SparkContext
    from pyspark.sql import HiveContext
    conf = SparkConf().setAppName('CHU_Silver_%s_%s' % (stage, options.lot))
    conf.set('spark.sql.shuffle.partitions', str(config.get('shuffle_partitions', 16)))
    conf.set('spark.hadoop.orc.compress', 'SNAPPY')
    conf.set('spark.sql.orc.filterPushdown', 'true')
    sc = SparkContext(conf=conf)
    run = None
    try:
        if sc.version.split('.')[:2] != ['1', '6']:
            raise ValueError('Cette livraison cible Spark 1.6')
        sc.setLogLevel('WARN')
        sql = HiveContext(sc)
        expected = rules.pseudonym('42', key)
        if sc.parallelize(['42'], 1).map(lambda x: rules.pseudonym(x, key)).collect() != [expected]:
            raise ValueError('Test HMAC driver/worker non concordant')
        run = Run(sc, sql, config, options.lot, options.attempt, key, options.key_version, excluded)
        if stage == '01':
            for step, function in PIPELINES:
                if step == '07':
                    break
                print('SILVER_STEP_START ' + step)
                function(run)
                run.write_json('progression_' + step + '.json', {'step': step, 'outputs': run.outputs, 'metrics': run.metrics})
                print('SILVER_STEP_OK ' + step)
            write_checkpoint(run, '01', None, False)
        elif stage == '02':
            state = (load_legacy(run, options.legacy_attempt) if options.legacy_attempt
                     else saved_checkpoint(run, options.source_attempt, '01'))
            run.outputs, run.metrics = state['outputs'], state['metrics']
            legacy = state.get('legacy_unverified_pro', False)
            if legacy:
                print('ATTENTION : ancien lot sans pseudonymisation des professionnels ; controle final bloquera la publication')
            print('SILVER_STEP_START 07')
            dict(PIPELINES)['07'](run)
            run.write_json('progression_07.json', {'step': '07', 'outputs': run.outputs, 'metrics': run.metrics})
            print('SILVER_STEP_OK 07')
            write_checkpoint(run, '02', options.legacy_attempt or options.source_attempt, legacy)
        else:
            state = saved_checkpoint(run, options.source_attempt, '02')
            run.outputs, run.metrics = state['outputs'], state['metrics']
            run.write_json('lineage.json', {'phase_02': options.source_attempt,
                'phase_01': state.get('source_attempt'), 'legacy_unverified_pro': state.get('legacy_unverified_pro', False)})
            if state.get('legacy_unverified_pro'):
                run.complete(prepare_publication=False)
                run.write_json('incompatibilite_professionnels.json', {'status': 'NOT_READY',
                    'reason': 'Ancien lot sans HMAC professionnel : retraitement requis avant publication.'})
                print('SILVER_NOT_READY : professionnels non pseudonymises selon main')
                return
            from pyspark.sql import functions as F
            for table in ('professionnel', 'consultation', 'activite'):
                invalid = (F.col('id_prof_sante').isNull() |
                           ~F.col('id_prof_sante').rlike('^[0-9a-f]{64}$'))
                if run.load(table).filter(invalid).limit(1).count():
                    raise ValueError('Pseudonyme professionnel invalide : ' + table)
            run.complete()
    except Exception:
        if run is not None:
            try:
                run.write_json('ECHEC.json', {'status': 'FAILED', 'exception_type': sys.exc_info()[0].__name__})
            except Exception:
                pass
        raise
    finally:
        sc.stop()
