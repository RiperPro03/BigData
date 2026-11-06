#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Exporte une liste fermee de code vers un nouveau dossier sans espaces.

Spark 1.6 sur la VM ne relit pas correctement les URI contenant %20.
Ne copie jamais les cles, donnees, configurations locales ou journaux.
"""
import os
import shutil
import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        raise ValueError('Usage : python prepare_runtime.py /chemin/sans_espaces')
    target = os.path.abspath(sys.argv[1])
    if any(char.isspace() for char in target) or os.path.exists(target):
        raise ValueError('La destination doit etre nouvelle et sans espaces')
    source = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(target)
    files = ['run_silver.py', '01_silver_hors_deces.py', '02_silver_deces.py',
             '03_silver_controles.py', 'build_package.py', 'config/exemple.json',
             'maintenance/__init__.py', 'maintenance/pseudonymiser_professionnels_legacy.py',
             'tests/test_rules.py', 'tests/test_reprise.py', 'tests/test_performance_semantique.py',
             'tests/integration_spark.py', 'tests/integration_deces.py',
             'tests/integration_reprise.py', 'tests/integration_ancien_checkpoint.py',
             'tests/integration_performance_equivalence.py', 'tests/benchmark_empreinte_deces.py',
             'tests/integration_migration_professionnels.py']
    files += ['chu_silver/' + name for name in os.listdir(os.path.join(source, 'chu_silver'))
              if name.endswith('.py')]
    for relative in files:
        dest = os.path.join(target, relative)
        if not os.path.isdir(os.path.dirname(dest)):
            os.makedirs(os.path.dirname(dest))
        shutil.copy2(os.path.join(source, relative), dest)
    # Copies de reference pour le test de contrat ; jamais executees en Gold.
    parent = os.path.dirname(source)
    if os.path.isdir(os.path.join(parent, 'DML')):
        dest = os.path.join(target, 'gold_reference', 'DML')
        os.makedirs(dest)
        for name in ('11_DML_dimensions.sql', '12_DML_pont.sql', '13_DML_faits.sql'):
            shutil.copy2(os.path.join(parent, 'DML', name), os.path.join(dest, name))
    subprocess.check_call([sys.executable, os.path.join(target, 'build_package.py')], cwd=target)
    print('SILVER_RUNTIME : ' + target)


if __name__ == '__main__':
    main()
