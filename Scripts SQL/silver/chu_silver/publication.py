# -*- coding: utf-8 -*-
"""Remplace le Silver publie apres validation, avec retour arriere sur echec."""
import json
import os
import subprocess
import tempfile
import uuid
from . import contracts as C


def publish(run):
    live = run.config['publication_root'].rstrip('/')
    if live != '/user/cloudera/chu/silver':
        raise ValueError('Racine Silver non autorisee')
    parent = live.rsplit('/', 1)[0]
    token = uuid.uuid4().hex
    stage = parent + '/.silver_publish_' + token
    previous = parent + '/.silver_previous_' + token
    lock = run.Path(parent + '/.silver_publication.lock')
    # create(false) echoue si une publication est deja en cours.
    stream = run.fs.create(lock, False)
    stream.close()
    switched = False
    had_previous = False
    old_views = []

    def exists(path):
        return run.fs.exists(run.Path(path))

    def move(source, target):
        if not run.fs.rename(run.Path(source), run.Path(target)):
            raise IOError('Renommage HDFS refuse')

    def copy(source, target):
        if not exists(source) or exists(target):
            raise ValueError('Source absente ou destination deja presente')
        run.fs.mkdirs(run.Path(target).getParent())
        ok = run.sc._jvm.org.apache.hadoop.fs.FileUtil.copy(
            run.fs, run.Path(source), run.fs, run.Path(target), False,
            run.sc._jsc.hadoopConfiguration())
        if not ok:
            raise IOError('Copie HDFS refusee')
        # Compare chaque fichier copie via le checksum HDFS, sans lire les
        # donnees dans Python. Les chemins relatifs doivent aussi correspondre.
        def inventory(base):
            result = {}
            def visit(path, relative):
                for status in run.fs.listStatus(run.Path(path)):
                    name = status.getPath().getName()
                    child = path + '/' + name
                    rel = relative + '/' + name
                    if status.isDirectory():
                        visit(child, rel)
                    else:
                        checksum = run.fs.getFileChecksum(run.Path(child))
                        result[rel] = (status.getLen(), checksum.toString() if checksum else None)
            visit(base, '')
            return result
        if inventory(source) != inventory(target):
            raise ValueError('La copie HDFS differe de la source')

    def hive(text):
        fd, filename = tempfile.mkstemp(prefix='chu_silver_', suffix='.hql')
        try:
            out = os.fdopen(fd, 'wb')
            out.write(text.encode('utf-8'))
            out.close()
            process = subprocess.Popen(['beeline', '-u', 'jdbc:hive2://localhost:10000/default',
                '-n', 'cloudera', '--silent=true', '--showHeader=false',
                '--outputformat=tsv2', '-f', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode:
                raise RuntimeError('Publication Hive refusee: ' + stderr.decode('utf-8', 'replace')[-2000:])
            return stdout.decode('utf-8', 'replace')
        finally:
            os.remove(filename)

    try:
        if set(run.outputs) != set(C.TABLES):
            raise ValueError('Le Silver doit contenir les 14 tables validees')
        run.fs.mkdirs(run.Path(stage + '/tables'))
        run.fs.mkdirs(run.Path(stage + '/rejets'))
        run.fs.mkdirs(run.Path(stage + '/audit'))
        roots = set([run.root])
        for name, info in sorted(run.outputs.items()):
            source = info['path']
            if not source.startswith(parent + '/') or '/tables/' not in source:
                raise ValueError('Sortie source hors du projet')
            if not exists(source + '/_SUCCESS'):
                raise ValueError('Table incomplete: ' + name)
            copy(source, stage + '/tables/' + name)
            root = source.split('/tables/')[0]
            if root.endswith('/enrichissement_satisfaction'):
                root = root.rsplit('/', 1)[0]
            roots.add(root)
        # Rejets et qualite des phases effectivement utilisees.
        reject_sources = {}
        for root in sorted(roots):
            if exists(root + '/rejets'):
                for status in run.fs.listStatus(run.Path(root + '/rejets')):
                    name = status.getPath().getName()
                    source = root + '/rejets/' + name
                    if name in reject_sources:
                        owner = run.outputs.get(name, {}).get('path', '').split('/tables/')[0]
                        if root == owner:
                            reject_sources[name] = source
                        elif reject_sources[name].rsplit('/rejets/', 1)[0] != owner:
                            raise ValueError('Origine des rejets ambigue: ' + name)
                    else:
                        reject_sources[name] = source
            if exists(root + '/audit'):
                for status in run.fs.listStatus(run.Path(root + '/audit')):
                    name = status.getPath().getName()
                    if name.startswith('qualite_'):
                        target = stage + '/audit/' + name
                        if exists(target):
                            continue
                        # Fichier simple : copie, checksum verifie par HDFS.
                        run.sc._jvm.org.apache.hadoop.fs.FileUtil.copy(run.fs, status.getPath(),
                            run.fs, run.Path(target), False, run.sc._jsc.hadoopConfiguration())
        for name, source in sorted(reject_sources.items()):
            copy(source, stage + '/rejets/' + name)
        registry = run.config['keys_root']
        if exists(registry):
            copy(registry, stage + '/audit/technical_keys')
        outputs = dict((name, dict(info, path=live + '/tables/' + name))
                       for name, info in run.outputs.items())
        metrics = json.loads(json.dumps(run.metrics))
        old_registry = metrics.get('deces', {}).get('key_registry', '')
        if '/technical_keys/' in old_registry:
            metrics['deces']['key_registry'] = live + '/audit/technical_keys/' + old_registry.split('/technical_keys/', 1)[1]
        report = {'status': 'PUBLISHED', 'mode': 'FULL_REPLACE', 'lot_id': run.lot,
                  'attempt_id': run.attempt, 'inputs_id': run.input_id,
                  'key_version': run.key_version, 'outputs': outputs,
                  'metrics': metrics, 'hive_database': 'silver'}
        run.write_text(stage + '/audit/rapport_final.json', json.dumps(report, sort_keys=True, indent=2))
        run.write_text(stage + '/audit/manifest_entrees.json', json.dumps(run.fingerprints, sort_keys=True, indent=2))
        # Capture les vues existantes pour permettre leur restauration.
        tables = hive('CREATE DATABASE IF NOT EXISTS silver; SHOW TABLES IN silver;')
        for name in sorted(C.TABLES):
            if name in tables.split():
                ddl = hive('SHOW CREATE TABLE silver.`%s`;' % name)
                if 'CREATE VIEW' in ddl.upper():
                    old_views.append((name, ddl.strip().rstrip(';') + ';'))
        had_previous = exists(live)
        if had_previous:
            move(live, previous)
        try:
            move(stage, live)
        except Exception:
            if had_previous:
                move(previous, live)
            raise
        switched = True
        statements = []
        for name, ddl in old_views:
            statements.append('DROP VIEW silver.`%s`;' % name)
        # Creation dans silver directement : plus de base par tentative.
        statements.append(C.publication_sql('silver', dict((n, live + '/tables/' + n) for n in C.TABLES))
            .replace('CREATE EXTERNAL TABLE ', 'CREATE EXTERNAL TABLE IF NOT EXISTS ')
            .replace('CREATE VIEW ', 'CREATE OR REPLACE VIEW '))
        hive('\n'.join(statements))
        # Les ORC ont ete verifies par Spark puis copies avec checksums identiques.
        # Verification du contrat du metastore apres la bascule.
        for name in sorted(C.TABLES):
            description = hive('DESCRIBE silver.`%s`;' % name)
            actual = [tuple(line.split()[:2]) for line in description.splitlines() if line.strip()]
            expected = [(field, kind.lower()) for field, kind in C.TABLES[name]]
            if actual[:len(expected)] != expected:
                raise ValueError('Schema Hive divergent: ' + name)
        if had_previous:
            run.fs.delete(run.Path(previous), True)
        # Ne retire que les tentatives effectivement consommees, apres succes.
        for root in sorted(roots):
            if root.startswith(parent + '/.silver_work/runs/'):
                run.fs.delete(run.Path(root), True)
        # Retire uniquement les dossiers temporaires devenus vides.
        for path in (parent + '/.silver_work/runs/' + run.lot,
                     parent + '/.silver_work/runs', parent + '/.silver_work'):
            if exists(path) and not run.fs.listStatus(run.Path(path)):
                run.fs.delete(run.Path(path), False)
        print('SILVER_REPLACED : ' + live)
    except Exception:
        if switched:
            move(live, stage)
            if had_previous:
                move(previous, live)
            for name, ddl in old_views:
                hive('DROP TABLE IF EXISTS silver.`%s`; %s' % (name, ddl))
        raise
    finally:
        run.fs.delete(lock, False)
