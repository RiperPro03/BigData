# -*- coding: utf-8 -*-
"""Donnees exclusivement fictives ; executable sans installation de Spark."""
import datetime
import hashlib
import hmac
import io
import json
import os
import sys
import unittest
from zipfile import ZipFile, ZIP_DEFLATED
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chu_silver import contracts as C
from chu_silver import rules as R
from chu_silver.readers import parse_line, csv_records, xlsx_records, check_header
from chu_silver.pipelines import resolve_communes

KEY = b'0123456789abcdef0123456789abcdef'


class RulesTests(unittest.TestCase):
    def test_hmac_reference(self):
        expected = hmac.new(KEY, b'42', hashlib.sha256).hexdigest()
        self.assertEqual(R.pseudonym('00042', KEY), expected)
        self.assertEqual(len(expected), 64)
        self.assertNotEqual(expected, R.pseudonym('43', KEY))

    def test_hmac_key_required(self):
        self.assertRaises(ValueError, R.pseudonym, '42', b'court')

    def test_invalid_patient_identifiers(self):
        for value in [None, '', '42.0', '42x', '2147483648']:
            self.assertRaises(R.Invalid, R.patient_id, value)
        self.assertEqual(R.patient_id('0'), '0')
        self.assertEqual(R.patient_id('-1'), '-1')

    def test_three_sources_same_pseudonym(self):
        rows = [('patient', {'Id_patient': '42', 'Sexe': 'female', 'Age': '29'}),
                ('consultation', {'Id_patient': '042', 'Num_consultation': '1',
                 'Id_prof_sante': '012345678', 'Code_diag': 'D1', 'Date': '2020-01-01'}),
                ('hospitalisation', {'Id_patient': '00042', 'Num_Hospitalisation': '2',
                 'identifiant_organisation': 'F010000001', 'Code_diagnostic': 'D1', 'Date_Entree': '01/01/2020'})]
        values = []
        for kind, row in rows:
            out, status, motif, warnings = R.transform(kind, row, KEY)
            self.assertEqual(status, 'VALID')
            values.append(out['id_patient'])
        self.assertEqual(len(set(values)), 1)
        for kind, row in rows:
            out, status, motif, warnings = R.transform(kind, row, KEY, {'excluded': set(values)})
            self.assertEqual(status, 'EXCLUDE')
            self.assertEqual(out, {})

    def test_patient_minimization_and_snapshot_age(self):
        row = {'Id_patient': '42', 'Nom': 'FICTIF', 'Prenom': 'TEST', 'Num_Secu': 'FAUX',
               'Date': 'sens inconnu', 'Age': 'abc', 'Sexe': 'unknown'}
        out, status, motif, warnings = R.transform('patient', row, KEY)
        self.assertEqual(set(out), set(['id_patient', 'sexe', 'age']))
        self.assertEqual(out['age'], None)
        self.assertEqual(out['sexe'], 'inconnu')
        self.assertEqual(status, 'VALID')
        self.assertTrue('AGE_INVALIDE' in warnings)

    def test_professional_identifiers(self):
        self.assertEqual(R.prof_id('12345678', 'ADELI'), '012345678')
        self.assertEqual(R.prof_id('012345678', 'ADELI'), '012345678')
        self.assertEqual(R.prof_id('12345678901', 'RPPS'), '12345678901')
        self.assertEqual(R.prof_id('99A999999', 'ADELI'), '99A999999')
        self.assertEqual(R.prof_id('99A999999'), '99A999999')
        self.assertEqual(R.prof_id('2A9999999', 'ADELI'), '2A9999999')
        self.assertRaises(R.Invalid, R.prof_id, '9,99E+99', 'ADELI')
        self.assertRaises(R.Invalid, R.prof_id, '12345678', 'RPPS')
        self.assertRaises(R.Invalid, R.prof_id, '12345678901', 'ADELI')

    def test_finess(self):
        self.assertEqual(R.finess('10000001'), '010000001')
        self.assertEqual(R.finess('10000001.0'), '010000001')
        self.assertEqual(R.finess('2A0000022'), '2A0000022')
        self.assertEqual(R.finess('2B0000012'), '2B0000012')
        for value in ['', '0', '1.2E8', '1234567890', 'NaN']:
            self.assertRaises(R.Invalid, R.finess, value)

    def test_strict_dates(self):
        self.assertEqual(R.date_value('1882-01-01'), datetime.date(1882, 1, 1))
        self.assertEqual(R.date_value('29/02/2020', 'fr'), datetime.date(2020, 2, 29))
        for value in ['2019-02-29', '2020-13-01', '2020-1-1', '2020-01-00']:
            self.assertRaises(R.Invalid, R.date_value, value)

    def test_deces_bad_birth_kept(self):
        row = {'date_deces': '2019-01-01', 'date_naissance': '1900-00-00',
               'code_lieu_deces': '2A004', 'nom': 'FICTIF', 'prenom': 'TEST'}
        out, status, motif, warnings = R.transform('deces', row)
        self.assertEqual(status, 'VALID')
        self.assertEqual(out['date_naissance'], None)
        self.assertEqual(out['code_departement'], '2A')
        self.assertFalse('nom' in out or 'prenom' in out)
        self.assertEqual(warnings, 'NAISSANCE_INVALIDE')
        row['date_naissance'] = '2020-01-01'
        self.assertEqual(R.transform('deces', row)[2], 'NAISSANCE_APRES_DECES')
        row['date_deces'] = '2019-02-30'
        self.assertEqual(R.transform('deces', row)[1], 'REJECT')

    def test_satisfaction_null_zero_and_weight(self):
        row = {'finess_geo': '10000001', 'region': 'PACA',
               'score_all_rea_ajust': '', 'nb_rep_score_all_rea_ajust': ''}
        out, status, motif, warnings = R.transform('satisfaction', row, options={'year': 2020})
        self.assertEqual(status, 'VALID')
        self.assertEqual(out['score_all_rea_ajust'], None)
        row['score_all_rea_ajust'] = '0'
        out, status, motif, warnings = R.transform('satisfaction', row, options={'year': 2020})
        self.assertEqual(out['score_all_rea_ajust'], 0.0)
        self.assertEqual(warnings, 'POIDS_NON_EXPLOITABLE')
        row['score_all_rea_ajust'] = '72,65'
        row['nb_rep_score_all_rea_ajust'] = '10'
        self.assertEqual(R.transform('satisfaction', row, options={'year': 2020})[0]['score_all_rea_ajust'], 72.65)
        for value in ['NaN', 'Infinity', 'abc', '101', '-1']:
            row['score_all_rea_ajust'] = value
            self.assertEqual(R.transform('satisfaction', row, options={'year': 2020})[1], 'REJECT')

    def test_department(self):
        for code, dep in [('75056', '75'), ('2B033', '2B'), ('97101', '971'), ('99100', '99')]:
            self.assertEqual(R.department(code), dep)
        self.assertEqual(R.department('inconnu'), None)

    def test_csv_quoted_fields(self):
        self.assertEqual(parse_line('"test; libelle";42', ';', 2), ['test; libelle', '42'])
        self.assertEqual(parse_line('1;2', json.loads('";"'), 2), ['1', '2'])
        self.assertRaises(ValueError, parse_line, '"debut sans fin', ';', 2)
        self.assertRaises(ValueError, parse_line, '1;2;3', ';', 2)
        self.assertEqual(len(list(csv_records('a;b\n"ligne\nsuivante";42\n', ';'))), 2)

    def test_header_contract(self):
        self.assertRaises(ValueError, check_header, ['a', 'a'], {'required': ['a']})
        self.assertRaises(ValueError, check_header, ['a'], {'required': ['b']})

    def test_cog_priority_and_parent(self):
        regions = {'11': 'Ile-de-France'}
        rows = [('a', {'COM': '75056', 'TYPECOM': 'COM', 'REG': '11', 'DEP': '75', 'LIBELLE': 'Paris', 'COMPARENT': ''}),
                ('b', {'COM': '75056', 'TYPECOM': 'COMD', 'REG': '', 'DEP': '', 'LIBELLE': 'Variante', 'COMPARENT': '75056'}),
                ('c', {'COM': '75101', 'TYPECOM': 'ARM', 'REG': '', 'DEP': '', 'LIBELLE': 'Paris 1', 'COMPARENT': '75056'})]
        resolved, alternatives = resolve_communes(rows, regions)
        self.assertEqual(len(resolved), 2)
        self.assertEqual(alternatives, ['b'])
        self.assertEqual([row for row in resolved if row[0] == '75101'][0][4:7], ('75', '11', 'Ile-de-France'))

    def test_cog_ambiguity_blocks(self):
        rows = [('a', {'COM': '00001', 'TYPECOM': 'COM', 'REG': '11'}),
                ('b', {'COM': '00001', 'TYPECOM': 'COM', 'REG': '22'})]
        self.assertRaises(ValueError, resolve_communes, rows, {})

    def test_xlsx_without_dependency(self):
        data = io.BytesIO()
        z = ZipFile(data, 'w', ZIP_DEFLATED)
        ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        z.writestr('xl/workbook.xml', '<workbook xmlns="%s" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Resultats" r:id="r1"/></sheets></workbook>' % ns)
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="%s"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>finess_geo</t></is></c></row><row r="2"><c r="A2"><v>10000001</v></c></row></sheetData></worksheet>' % ns)
        z.close()
        header, rows = xlsx_records(data.getvalue(), 'Resultats')
        self.assertEqual(header, ['finess_geo'])
        self.assertEqual(R.finess(rows[0][0]), '010000001')

    def test_all_gold_sources_available(self):
        import re
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        portable = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gold_reference')
        if os.path.isdir(portable):
            base = portable
        references = set()
        for filename in ['11_DML_dimensions.sql', '12_DML_pont.sql', '13_DML_faits.sql']:
            with io.open(os.path.join(base, 'DML', filename), encoding='utf-8-sig') as stream:
                references.update(re.findall(r'silver\.([a-z_0-9]+)', stream.read(), re.I))
        self.assertEqual(references - set(C.TABLES) - set(C.ALIASES), set())
        sql = C.publication_sql('silver_test', dict((t, '/test/' + t) for t in C.TABLES))
        for name in references:
            self.assertTrue('`%s`' % name in sql)
        self.assertFalse('DROP ' in sql or 'INSERT ' in sql)

    def test_config_paths_and_column_orders(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with io.open(os.path.join(root, 'config', 'exemple.json'), encoding='utf-8') as stream:
            config = json.load(stream)
        self.assertEqual(len(config['sources']), 15)
        for table, columns in C.PG.items():
            self.assertEqual(config['sources'][table]['columns'], columns)
        self.assertEqual(set(C.TABLES), set(C.KEYS))


if __name__ == '__main__':
    unittest.main()
