#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Construit uniquement le paquet Python de code, jamais config/donnees/cles."""
import os
from zipfile import ZipFile, ZIP_DEFLATED

base = os.path.dirname(os.path.abspath(__file__))
archive = ZipFile(os.path.join(base, 'chu_silver.zip'), 'w', ZIP_DEFLATED)
try:
    package = os.path.join(base, 'chu_silver')
    for name in sorted(os.listdir(package)):
        if name.endswith('.py'):
            archive.write(os.path.join(package, name), 'chu_silver/' + name)
finally:
    archive.close()
print('chu_silver.zip : paquet de code cree')
