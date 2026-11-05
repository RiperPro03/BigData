# -*- coding: utf-8 -*-
"""CSV distribue UTF-8 ; petits cp1252/XLSX bornes en memoire sur le driver.

Le lecteur distribue conserve l'offset HDFS. Il echoue sur un enregistrement
multiligne : aucune continuation CSV n'est acceptee comme une autre personne.
Une source multiligne demande un lecteur specifique avant publication.
"""
import csv
import io
import subprocess
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from .rules import clean

PY2 = sys.version_info[0] == 2


def csv_records(text, delimiter):
    # json.loads renvoie unicode en Python 2.6, mais _csv exige un byte str.
    if PY2:
        delimiter = delimiter.encode('ascii')
    if len(delimiter) != 1:
        raise ValueError('Separateur CSV invalide')
    if PY2:
        stream = io.BytesIO(text.encode('utf-8'))
    else:
        stream = io.StringIO(text)
    for row in csv.reader(stream, delimiter=delimiter, strict=True):
        yield [cell.decode('utf-8') if PY2 else cell for cell in row]


def parse_line(line, delimiter, width):
    try:
        rows = list(csv_records(line, delimiter))
    except csv.Error:
        raise ValueError('STRUCTURE_CSV_INVALIDE : champ cite non termine')
    if len(rows) != 1 or len(rows[0]) != width:
        raise ValueError('STRUCTURE_CSV_INVALIDE : nombre de champs ou ligne multiligne')
    return rows[0]


def bounded_hdfs_read(path, limit):
    proc = subprocess.Popen(['hdfs', 'dfs', '-cat', path], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    try:
        data = proc.stdout.read(limit + 1)
        if len(data) > limit:
            proc.kill()
            raise ValueError('Source trop volumineuse pour le lecteur borne')
        # stderr ne contient normalement que des messages de client HDFS.
        # Ne pas l'afficher : le chemin d'un fichier peut etre prive.
        proc.stderr.read()
        if proc.wait() != 0:
            raise IOError('Lecture HDFS impossible')
        return data
    finally:
        proc.stdout.close()
        proc.stderr.close()
        if proc.poll() is None:
            proc.kill()
        proc.wait()


def xlsx_records(data, sheet_name, limit=100000):
    """Lecture XML d'un petit classeur : valeurs texte, aucune inference FINESS."""
    archive = ZipFile(io.BytesIO(data))
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    relns = '{http://schemas.openxmlformats.org/package/2006/relationships}'
    docrel = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    try:
        if sum(item.file_size for item in archive.infolist()) > 32 * 1024 * 1024:
            raise ValueError('Classeur decompresse trop volumineux')
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            root = ET.fromstring(archive.read('xl/sharedStrings.xml'))
            strings = [u''.join(t.text or u'' for t in si.findall('.//' + ns + 't'))
                       for si in root.findall(ns + 'si')]
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        sheets = [s for s in workbook.findall('.//' + ns + 'sheet') if s.get('name') == sheet_name]
        if len(sheets) != 1:
            raise ValueError('Feuille XLSX absente ou ambigue')
        relations = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets = dict((r.get('Id'), r.get('Target')) for r in relations.findall(relns + 'Relationship'))
        target = targets[sheets[0].get(docrel)]
        target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
        if '..' in target.split('/'):
            raise ValueError('Chemin XLSX invalide')
        root = ET.fromstring(archive.read(target))
        rows = []
        for row in root.findall('.//' + ns + 'sheetData/' + ns + 'row'):
            cells = {}
            for cell in row.findall(ns + 'c'):
                column = ''.join(c for c in cell.get('r', '') if c.isalpha())
                index = 0
                for char in column.upper():
                    index = index * 26 + ord(char) - 64
                if index == 0:
                    raise ValueError('Adresse de cellule XLSX invalide')
                value = cell.find(ns + 'v')
                value = value.text if value is not None else ''
                if cell.get('t') == 's':
                    value = strings[int(value)]
                elif cell.get('t') == 'inlineStr':
                    value = u''.join(t.text or u'' for t in cell.findall('.//' + ns + 't'))
                # Un resultat de formule non calcule ne doit pas devenir NULL.
                if cell.find(ns + 'f') is not None and not value:
                    raise ValueError('Formule XLSX sans valeur calculee')
                cells[index - 1] = value or ''
            if cells and any(cells.values()):
                width = max(cells) + 1
                rows.append([cells.get(i, '') for i in range(width)])
            if len(rows) > limit + 1:
                raise ValueError('Trop de lignes pour le lecteur XLSX borne')
        if not rows:
            raise ValueError('Classeur vide')
        header, data_rows = rows[0], rows[1:]
        for row in data_rows:
            if len(row) > len(header):
                raise ValueError('Ligne XLSX plus large que son en-tete')
            row.extend([''] * (len(header) - len(row)))
        return header, data_rows
    finally:
        archive.close()


def read_records(sc, path, source_id, spec, small_limit):
    """Retourne RDD[(record_id stable, dict colonnes)]."""
    if spec.get('small') or spec.get('format') == 'xlsx':
        content = bounded_hdfs_read(path, small_limit)
        if spec.get('format') == 'xlsx':
            header, data = xlsx_records(content, spec.get('sheet', 'Resultats'))
        else:
            rows = list(csv_records(content.decode(spec['encoding']), spec['delimiter']))
            if not rows:
                raise ValueError('Source vide : ' + source_id)
            header, data = rows[0], rows[1:]
        header = [clean(h) for h in header]
        check_header(header, spec)
        records = []
        for index, values in enumerate(data):
            if len(values) != len(header):
                raise ValueError('Structure invalide : ' + source_id)
            records.append(('%s:record:%d' % (source_id, index + 1), dict(zip(header, values))))
        return sc.parallelize(records, min(4, max(1, len(records))))

    # TextInputFormat sait distribuer un fichier unique sur ses blocs HDFS.
    rdd = sc.newAPIHadoopFile(path,
        'org.apache.hadoop.mapreduce.lib.input.TextInputFormat',
        'org.apache.hadoop.io.LongWritable', 'org.apache.hadoop.io.Text')
    if spec.get('header', True):
        head = rdd.filter(lambda item: item[0] == 0).take(2)
        if len(head) != 1:
            raise ValueError('Un seul fichier physique est attendu : ' + source_id)
        line = head[0][1].lstrip(u'\ufeff')
        parsed = list(csv_records(line, spec['delimiter']))
        if len(parsed) != 1:
            raise ValueError('En-tete invalide : ' + source_id)
        header = [clean(h) for h in parsed[0]]
        check_header(header, spec)
        rdd = rdd.filter(lambda item: item[0] != 0)
    else:
        header = spec['columns']

    def parse(item):
        offset, line = item
        values = parse_line(line, spec['delimiter'], len(header))
        return ('%s:offset:%d' % (source_id, offset), dict(zip(header, values)))
    return rdd.map(parse)


def check_header(header, spec):
    if None in header or len(header) != len(set(header)):
        raise ValueError('Colonnes vides ou repetees')
    missing = set(spec.get('required', spec.get('columns', []))) - set(header)
    if missing:
        raise ValueError('Colonnes requises absentes : ' + ', '.join(sorted(missing)))
