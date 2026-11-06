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
             '03_silver_controles.py', 'build_package.py', 'configuration.py']
    files += ['chu_silver/' + name for name in os.listdir(os.path.join(source, 'chu_silver'))
              if name.endswith('.py')]
    for relative in files:
        dest = os.path.join(target, relative)
        if not os.path.isdir(os.path.dirname(dest)):
            os.makedirs(os.path.dirname(dest))
        shutil.copy2(os.path.join(source, relative), dest)
    subprocess.check_call([sys.executable, os.path.join(target, 'build_package.py')], cwd=target)
    print('SILVER_RUNTIME : ' + target)


if __name__ == '__main__':
    main()
