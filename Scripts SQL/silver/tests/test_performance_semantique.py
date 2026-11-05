# -*- coding: utf-8 -*-
"""Verifie le contournement de l'empreinte sans Spark ni donnees reelles."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chu_silver import contracts as C
from chu_silver import rules
from chu_silver.runtime import Run


class RDD(object):
    def __init__(self, rows):
        self.rows = rows

    def mapPartitions(self, transform):
        return list(transform(iter(self.rows)))


class SQL(object):
    def createDataFrame(self, rows, schema):
        return rows


class PerformanceSemantics(unittest.TestCase):
    def test_death_payload_is_optional_without_changing_business_or_rejects(self):
        run = Run.__new__(Run)
        run.key, run.excluded, run.sql = b'0' * 32, set(), SQL()
        source = {'sexe': '1', 'date_naissance': '1900-01-01',
                  'date_deces': '2019-01-01', 'code_lieu_deces': '75056'}
        invalid = dict(source, date_deces='2019-02-30')
        warning = dict(source, date_naissance='1900-00-00')
        records = [('ligne1', source), ('ligne2', source), ('ligne3', invalid), ('ligne4', warning)]
        spec = C.TABLES['deces'] + C.TABLES['defunt'][1:]
        original_schema = C.schema
        try:
            C.schema = lambda fields: fields
            before = run.normalized('deces', 'deces', spec, records=RDD(records))
            original_hash = rules.payload_hash
            try:
                def fail_if_called(values):
                    raise AssertionError('L empreinte des deces ne doit pas etre calculee')
                rules.payload_hash = fail_if_called
                after = run.normalized('deces', 'deces', spec, records=RDD(records), compute_payload=False)
            finally:
                rules.payload_hash = original_hash
        finally:
            C.schema = original_schema
        self.assertEqual([row[:-1] for row in before], [row[:-1] for row in after])
        self.assertEqual([row[-1] for row in after], [None] * len(records))
        self.assertTrue(all(row[-1] for row in before))
        self.assertEqual([row[-4] for row in after], ['VALID', 'VALID', 'REJECT', 'VALID'])


if __name__ == '__main__':
    unittest.main()
