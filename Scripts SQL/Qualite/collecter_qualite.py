# -*- coding: utf-8 -*-
"""Collecte les agrégats Silver et les contrôles Hive Gold, sans écrire dans les tables.

Compatible Python 2.6 sur la VM. Les résultats sont enregistrés dans un
nouveau répertoire local. La filiation Gold/Silver n'est pas présumée.
"""
from __future__ import unicode_literals
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from optparse import OptionParser

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SILVER='/user/cloudera/chu/silver/audit/rapport_final.json'

def command(args):
    process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err=process.communicate()
    if process.returncode:
        raise RuntimeError('Commande échouée : %s (code %s) : %s' %
                           (args[0],process.returncode,err.decode('utf-8','replace')[-1000:]))
    return out

def clean_beeline(output):
    """Supprime les indicateurs de progression CR/null émis par Hive 1.1."""
    if not isinstance(output,type(u'')):output=output.decode('utf-8','replace')
    return re.sub(r'\rnull[ \t]*','',output)

def checks_from_output(output, expected):
    found={}
    output=clean_beeline(output)
    for line in output.splitlines():
        cols=line.strip().split('\t')
        if not cols or cols[0] not in expected:continue
        if len(cols) not in (2,5) or not all(re.match(r'^-?\d+$',x.strip()) for x in cols[1:]):
            raise ValueError('Résultat invalide pour le contrôle : '+cols[0])
        values=[int(x) for x in cols[1:]]
        if len(values)==4:
            if any(x < 0 for x in values[:3]) or values[0]-values[1]-values[2]!=values[3]:
                raise ValueError('Bilan incohérent pour le contrôle : '+cols[0])
        elif values[0] < 0:
            raise ValueError('Nombre d’anomalies négatif : '+cols[0])
        if cols[0] in found:
            raise ValueError('Contrôle en double : '+cols[0])
        found[cols[0]]={'values':values,'source':'beeline'}
    missing=[n for n in expected if n not in found]
    if missing:raise ValueError('Résultats de contrôle manquants : '+', '.join(missing))
    return found

def gold_tables():
    """Lit le contrat des tables Gold à partir des DDL versionnés."""
    pattern=re.compile(r"CREATE\s+EXTERNAL\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)\s*\((.*?)\)\s*STORED\s+AS\s+ORC\s*LOCATION\s*'([^']+)'",re.I|re.S)
    tables={}
    for filename in ('01_DDL_dimensions.sql','02_DDL_pont.sql','03_DDL_faits.sql','04_DDL_rejets.sql'):
        with open(os.path.join(ROOT,'DDL',filename),'rb') as stream:
            text=stream.read().decode('utf-8')
        for match in pattern.finditer(text):
            name,columns,location=match.groups()
            fields=[]
            for column in columns.split(','):
                parts=column.strip().split()
                if len(parts)!=2:raise ValueError('Colonne DDL non reconnue : '+name)
                fields.append((parts[0].strip('`').lower(),parts[1].lower()))
            if name in tables:raise ValueError('Table DDL répétée : '+name)
            tables[name]=(fields,location)
    if len(tables)!=19:raise ValueError('Le modèle Gold attendu doit contenir 19 tables')
    return tables

def completeness_sql(tables):
    statements=[]
    for name,(columns,location) in sorted(tables.items()):
        if '/tables/' not in location:continue
        sums=["COALESCE(SUM(CASE WHEN `%s` IS NULL THEN 1 ELSE 0 END),0)" % col for col,_ in columns]
        statements.append("SELECT 'QCOMPLET_%s', COUNT(*), %s FROM `%s`;" % (name,', '.join(sums),name))
    return '\n'.join(statements)

def completeness_from_output(output,tables):
    output=clean_beeline(output)
    expected=dict((name,fields) for name,(fields,location) in tables.items() if '/tables/' in location)
    result={}
    for line in output.splitlines():
        cols=line.strip().split('\t')
        if not cols[0].startswith('QCOMPLET_'):continue
        name=cols[0][len('QCOMPLET_'):]
        if name not in expected or name in result:raise ValueError('Table de complétude inattendue : '+name)
        if len(cols)!=len(expected[name])+2 or not all(re.match(r'^\d+$',x.strip()) for x in cols[1:]):
            raise ValueError('Résultat de complétude invalide : '+name)
        counts=[int(x) for x in cols[1:]];rows=counts[0]
        if any(n>rows for n in counts[1:]):raise ValueError('Nombre de NULL invalide : '+name)
        result[name]={'rows':rows,'nulls':dict((c[0],n) for c,n in zip(expected[name],counts[1:])),
                      'completeness':dict((c[0],float(rows-n)/rows if rows else None)
                                          for c,n in zip(expected[name],counts[1:]))}
    missing=sorted(set(expected)-set(result))
    if missing:raise ValueError('Complétude Gold manquante : '+', '.join(missing))
    return result

def collect(output_dir,database='gold',sql_path=None,tables=None):
    if not re.match(r'^[a-z][a-z0-9_]{0,63}$',database):
        raise ValueError('Nom de base Hive invalide')
    sql_path=sql_path or os.path.join(ROOT,'Controles','30_controles_gold.sql')
    sql_bytes=open(sql_path,'rb').read()
    sql=sql_bytes.decode('utf-8')
    expected=re.findall(r"SELECT\s+'([^']+)'\s+AS\s+controle",sql,re.I)
    if not expected or len(set(expected))!=len(expected):
        raise ValueError('Liste de contrôles SQL vide ou répétée')
    silver_bytes=command(['hdfs','dfs','-cat',SILVER])
    silver=json.loads(silver_bytes.decode('utf-8'))
    if silver.get('status')!='PUBLISHED' or not silver.get('lot_id'):
        raise ValueError('Silver non publié ou lot absent')
    if not os.path.isdir(output_dir):os.makedirs(output_dir,448)
    if any(os.path.exists(os.path.join(output_dir,n)) for n in ('silver.json','gold.json','Rapport_Qualite_Donnees.docx')):
        raise ValueError('Ce répertoire contient déjà des résultats : choisir un nouveau dossier')
    sql=re.sub(r'(?im)^\s*USE\s+gold\s*;', 'USE `%s`;' % database,sql,count=1)
    tables=tables or gold_tables()
    extra_sql=completeness_sql(tables)
    sql+='\n-- Complétude : une lecture par table Gold.\n'+extra_sql+'\n'
    fd,path=tempfile.mkstemp(prefix='chu_controles_',suffix='.sql')
    try:
        f=os.fdopen(fd,'wb');f.write(sql.encode('utf-8'));f.close()
        out=command(['beeline','-u','jdbc:hive2://localhost:10000/default','-n','cloudera',
                     '--force=false','--silent=true','--showHeader=false','--outputformat=tsv2','-f',path])
    finally:
        os.remove(path)
    with open(os.path.join(output_dir,'controles_beeline.tsv'),'wb') as stream:
        stream.write(out)
    checks=checks_from_output(out,expected)
    completeness=completeness_from_output(out,tables)
    if command(['hdfs','dfs','-cat',SILVER])!=silver_bytes:
        raise ValueError('L’audit Silver a changé pendant les contrôles')
    anomalies=dict((name,val['values'][-1]) for name,val in checks.items() if val['values'][-1]!=0)
    rejects=dict((name,val['values'][2]) for name,val in checks.items()
                 if len(val['values'])==4 and val['values'][2]!=0)
    gold={'status':'ECHEC' if anomalies else ('REJETS_A_EXAMINER' if rejects else 'CONTROLES_OK'),
          'date':datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
          'origine':'Contrôles Hive exécutés en lecture seule sur la base '+database+'.',
          'silver_lot_certifie':False,'lot_silver_observe':silver['lot_id'],
          'silver_sha256':hashlib.sha256(silver_bytes).hexdigest(),
          'sql_sha256':hashlib.sha256(sql_bytes).hexdigest(),
          'completeness_sql_sha256':hashlib.sha256(extra_sql.encode('utf-8')).hexdigest(),
          'completeness':completeness,
          'checks':checks,'expected':expected,'missing':[],'anomalies':anomalies,'rejets_a_examiner':rejects}
    for name,data in [('silver.json',silver),('gold.json',gold)]:
        f=open(os.path.join(output_dir,name),'wb')
        try:f.write(json.dumps(data,sort_keys=True,indent=2,ensure_ascii=True).encode('ascii'))
        finally:f.close()
    return gold

def main():
    parser=OptionParser()
    parser.add_option('--output-dir',dest='output_dir')
    parser.add_option('--database',dest='database',default='gold')
    opts,extra=parser.parse_args()
    if extra or not opts.output_dir:parser.error('--output-dir est obligatoire')
    result=collect(os.path.abspath(opts.output_dir),opts.database)
    import rapport_docx
    base=os.path.abspath(opts.output_dir)
    silver=json.load(open(os.path.join(base,'silver.json'),'rb'))
    template=os.path.join(os.path.dirname(os.path.abspath(__file__)),'modele_rapport.docx')
    rapport_docx.generate(silver,result,template,os.path.join(base,'Rapport_Qualite_Donnees.docx'))
    print('RAPPORT_WORD : '+os.path.join(base,'Rapport_Qualite_Donnees.docx'))
    print('CONTROLES_GOLD : '+result['status'])
    if result['status']!='CONTROLES_OK':sys.exit(1)

if __name__=='__main__':main()
