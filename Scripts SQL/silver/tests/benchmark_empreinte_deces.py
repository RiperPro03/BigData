# -*- coding: utf-8 -*-
"""Micro-mesure CPU locale sur des deces fictifs, pas un benchmark Spark."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chu_silver import contracts as C
from chu_silver import rules

record = {'nom': 'FICTIF', 'prenom': 'TEST', 'sexe': '1',
          'date_naissance': '1900-01-01', 'code_lieu_naissance': '75056',
          'lieu_naissance': 'Paris', 'pays_naissance': 'France',
          'date_deces': '2019-01-01', 'code_lieu_deces': '75056',
          'numero_acte_deces': '1'}
names = [name for name, unused in C.TABLES['deces'] + C.TABLES['defunt'][1:]]
iterations = 100000


def measure(with_hash):
    start = time.time()
    valid = 0
    for unused in range(iterations):
        values, status, motif, warnings = rules.transform('deces', record)
        business = [values.get(name) for name in names]
        if with_hash:
            rules.payload_hash(business)
        valid += (status == 'VALID')
    return time.time() - start, valid


old_times, new_times = [], []
for sequence in ((True, False), (False, True)):
    for with_hash in sequence:
        elapsed, valid = measure(with_hash)
        if valid != iterations:
            raise AssertionError('Fixture invalide')
        (old_times if with_hash else new_times).append(elapsed)
old, new = sum(old_times) / len(old_times), sum(new_times) / len(new_times)
print('BENCH_FICTIF : %s lignes, moyenne de deux passages' % iterations)
print('AVANT_HASH_SECONDES %.3f' % old)
print('APRES_SANS_HASH_SECONDES %.3f' % new)
print('RAPPORT_AVANT_SUR_APRES %.3f' % (old / new))
