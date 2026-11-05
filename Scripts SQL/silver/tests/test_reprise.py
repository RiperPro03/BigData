# -*- coding: utf-8 -*-
"""Controles sans Spark ni donnees de projet ; compatible Python 2.6."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chu_silver import split


class ResumeChecks(unittest.TestCase):
    def setUp(self):
        self.identity = {'input_id': 'a', 'config_digest': 'b', 'code_digest': 'c',
                         'key_proof': 'd', 'key_version': 'v1', 'excluded_digest': 'e'}

    def test_identical_identity_is_accepted(self):
        split.same_identity(self.identity, copy.deepcopy(self.identity))

    def test_each_modified_identity_is_refused(self):
        for name in self.identity:
            other = copy.deepcopy(self.identity)
            other[name] = 'different'
            self.assertRaises(ValueError, split.same_identity, self.identity, other)

    def test_key_proof_is_stable_and_key_dependent(self):
        self.assertEqual(split.key_proof(b'a' * 32), split.key_proof(b'a' * 32))
        self.assertNotEqual(split.key_proof(b'a' * 32), split.key_proof(b'b' * 32))

    def test_attempt_is_confined_to_same_lot(self):
        class Fake(object):
            config = {'runs_root': '/runs'}
            lot = 'lot_1'
            attempt = 'courante'
        run = Fake()
        self.assertEqual(split.attempt_root(run, 'ancienne_1'), '/runs/lot_1/ancienne_1')
        for invalid in ('', '../autre', 'courante', 'avec espace'):
            self.assertRaises(ValueError, split.attempt_root, run, invalid)

    def test_code_digest_and_config_digest_are_deterministic(self):
        self.assertEqual(split.code_digest(), split.code_digest())
        self.assertEqual(split.digest({'a': 1, 'b': 2}), split.digest({'b': 2, 'a': 1}))


if __name__ == '__main__':
    unittest.main()
