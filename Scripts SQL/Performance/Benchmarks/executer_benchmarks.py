#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Benchmarks Hive 1.1 reproductibles ; n'enregistre aucune ligne de resultat."""
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from optparse import OptionParser

BASE=os.path.dirname(os.path.abspath(__file__))
NAMES=('01_consultation_diagnostic','02_consultation_etablissement',
       '03_consultation_professionnel','04_hospitalisation_diagnostic',
       '05_hospitalisation_sexe_age','06_deces_region','07_satisfaction_region',
       '08_deces_jointure_defunt')
SORTED=('03_consultation_professionnel','04_hospitalisation_diagnostic','06_deces_region')
ROOT='/user/cloudera/chu/gold/'
SOURCE=['tables/'+x for x in ('fait_consultation','fait_hospitalisation','fait_deces',
        'fait_satisfaction','dim_patient','dim_lieu_deces','dim_defunt','pont_activite_pro')]
VARIANTS=['tables/'+x for x in ('fait_consultation_part','fait_hospitalisation_part','fait_deces_part',
          'fait_consultation_part_trie','fait_hospitalisation_part_trie','fait_deces_part_trie',
          'fait_deces_bucket','dim_defunt_bucket')]+['index/index_consultation_diag']
SETTINGS='''USE gold;
SET hive.execution.engine=mr;
SET hive.auto.convert.join=false;
SET hive.optimize.ppd=true;
SET hive.optimize.ppd.storage=true;
SET mapreduce.map.memory.mb=1024;
SET mapreduce.map.java.opts=-Xmx768m -Djava.net.preferIPv4Stack=true;
SET mapreduce.reduce.memory.mb=1536;
SET mapreduce.reduce.java.opts=-Xmx1024m -Djava.net.preferIPv4Stack=true;
SET mapreduce.job.reduce.slowstart.completedmaps=1.0;
SET hive.exec.reducers.max=8;
'''

def snapshot(paths):
    process=subprocess.Popen(['hdfs','dfs','-ls','-R']+[ROOT+p for p in paths],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err=process.communicate()
    if process.returncode:raise RuntimeError('Inventaire HDFS impossible : '+err.decode('utf-8','replace')[-1200:])
    lines=sorted(x.strip() for x in out.splitlines() if x.startswith((b'-',b'd')))
    if not lines:raise ValueError('Inventaire HDFS vide')
    return hashlib.sha256(b'\n'.join(lines)).hexdigest()

def save(path,report):
    temporary=path+'.tmp'
    with open(temporary,'w') as stream:json.dump(report,stream,sort_keys=True,indent=2)
    os.rename(temporary,path)

def main():
    parser=OptionParser()
    parser.add_option('--phase',dest='phase')
    parser.add_option('--output',dest='output')
    options,extra=parser.parse_args()
    if extra or options.phase not in ('reference','comparaison') or not options.output:
        parser.error('--phase reference|comparaison et --output requis')
    output=os.path.abspath(options.output)
    if os.path.exists(output):
        with open(output,'r') as stream:report=json.load(stream)
    else:
        report={'version':1,'engine':'Hive 1.1 / MapReduce',
                'measure':'temps mur VM, lancement Beeline et lecture des resultats inclus',
                'cache':'non vide, ordre chronologique conserve', 'runs':[]}
    runner_hash=hashlib.sha256(open(os.path.abspath(__file__),'rb').read()).hexdigest()
    if report.get('runner_sha256',runner_hash)!=runner_hash:
        raise ValueError('Programme de benchmark modifie depuis le debut')
    report['runner_sha256']=runner_hash
    for old in report['runs']:
        if old['status']=='OK':
            old_path=os.path.join(BASE,old['scenario']+'_'+old['variant']+'.sql')
            if hashlib.sha256(open(old_path,'rb').read()).hexdigest()!=old['query_sha256']:
                raise ValueError('Requete modifiee depuis le debut : '+old_path)
    source=snapshot(SOURCE)
    if report.get('source_fingerprint',source)!=source:
        raise ValueError('Tables de reference modifiees depuis le debut du benchmark')
    report['source_fingerprint']=source
    if options.phase=='comparaison':
        variants=snapshot(VARIANTS)
        if report.get('variant_fingerprint',variants)!=variants:
            raise ValueError('Variantes modifiees pendant le benchmark')
        report['variant_fingerprint']=variants
    if options.phase=='reference':
        schedule=[(name,'reference',1) for name in NAMES]
    else:
        schedule=[]
        for name in NAMES:
            schedule.extend([(name,'optimise',1),(name,'reference',2),
                             (name,'optimise',2),(name,'reference',3),(name,'optimise',3)])
            if name in SORTED:
                schedule.extend((name,'trie',i) for i in (1,2,3))
            if name==NAMES[0]:
                schedule.extend((name,'index',i) for i in (1,2,3))
    for name,variant,iteration in schedule:
        done=[r for r in report['runs'] if r['scenario']==name and r['variant']==variant and r['iteration']==iteration and r['status']=='OK']
        if done:continue
        query_path=os.path.join(BASE,name+'_'+variant+'.sql')
        with open(query_path,'rb') as stream:query=stream.read()
        # Meme filtrage ORC dans les deux cas ; seul le seuil d'eligibilite de
        # l'index compact change pour l'essai index sur cette petite maquette.
        flags=('SET hive.optimize.index.filter=true;\nSET hive.optimize.index.filter.compact.minsize=0;\n'
               if variant=='index' else 'SET hive.optimize.index.filter=true;\nSET hive.optimize.index.filter.compact.minsize=5368709120;\n')
        fd,temporary=tempfile.mkstemp(prefix='chu_gold_bench_',suffix='.hql')
        with os.fdopen(fd,'wb') as stream:stream.write((SETTINGS+flags).encode('utf-8')+query)
        started=time.time()
        started_utc=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        sys.stdout.write('DEBUT %s %s %s\n'%(name,variant,iteration));sys.stdout.flush()
        try:
            process=subprocess.Popen(['beeline','-u','jdbc:hive2://localhost:10000/default','-n','cloudera',
                '--force=false','--silent=true','--showHeader=false','--outputformat=tsv2','-f',temporary],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out,err=process.communicate()
        finally:
            os.remove(temporary)
        elapsed=round(time.time()-started,3)
        # Beeline 1.1 emet parfois des indicateurs de progression \rnull sur stdout.
        # Ils ne font pas partie du resultat SQL et varient selon la duree.
        clean=re.sub(b'\\rnull[ \t]*',b'',out).replace(b'\r\n',b'\n')
        rows=[x.strip() for x in clean.splitlines() if x.strip()]
        result=hashlib.sha256(b'\n'.join(rows)).hexdigest()
        item={'scenario':name,'variant':variant,'iteration':iteration,'seconds':elapsed,
              'started_utc':started_utc,
              'query_sha256':hashlib.sha256(query).hexdigest(),'result_sha256':result,
              'result_rows':len(rows),'status':'OK' if process.returncode==0 else 'ERROR'}
        report['runs'].append(item)
        if process.returncode or not rows:
            item['status']='ERROR'
            item['error']=err.decode('utf-8','replace')[-1800:] or 'Resultat vide'
            save(output,report);raise RuntimeError('Echec de '+name+' '+variant)
        # Meme question et meme jeu de donnees : une difference bloque la mesure.
        reference=[r for r in report['runs'] if r['scenario']==name and r['variant']=='reference' and r['status']=='OK']
        if reference and any(r['result_sha256']!=result for r in reference):
            item['status']='MISMATCH';save(output,report)
            raise ValueError('Resultats differents : '+name+' '+variant)
        save(output,report)
        sys.stdout.write('TERMINE %s %s %s %.3fs lignes=%s sha256=%s\n'%(name,variant,iteration,elapsed,len(rows),result));sys.stdout.flush()
    if snapshot(SOURCE)!=source:raise ValueError('Source modifiee pendant le benchmark')
    if options.phase=='comparaison' and snapshot(VARIANTS)!=variants:
        raise ValueError('Variante modifiee pendant le benchmark')
    report[options.phase+'_complete']=True
    save(output,report)
    sys.stdout.write('BENCHMARK_'+options.phase.upper()+'_OK\n');sys.stdout.flush()

if __name__=='__main__':main()
