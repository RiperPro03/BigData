# -*- coding: utf-8 -*-
"""Construit Gold en zone isolée, contrôle, publie et génère le rapport qualité.

Compatible Python 2.6 / Hive 1.1. Exécuter sur la VM et suspendre les lectures
Gold et les alimentations Silver jusqu'à la fin de la publication.
"""
from __future__ import unicode_literals
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from optparse import OptionParser

HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.dirname(HERE)
QUALITY=os.path.join(ROOT,'Qualite')
sys.path.insert(0,QUALITY)
import collecter_qualite
import rapport_docx

try:text_type=unicode
except NameError:text_type=str

HDFS='/user/cloudera/chu'
GOLD=HDFS+'/gold'
SILVER=HDFS+'/silver/audit/rapport_final.json'
LOCK=HDFS+'/.gold_pipeline.lock'
SILVER_LOCK=HDFS+'/.silver_publication.lock'
FILES=['Database/Create_Database.sql','DDL/01_DDL_dimensions.sql',
       'DDL/02_DDL_pont.sql','DDL/03_DDL_faits.sql','DDL/04_DDL_rejets.sql',
       'DML/11_DML_dimensions.sql','DML/12_DML_pont.sql','DML/13_DML_faits.sql']
TRACKED=FILES+['Controles/30_controles_gold.sql','Gold/pipeline_gold.py',
               'Qualite/collecter_qualite.py','Qualite/rapport_docx.py',
               'Qualite/modele_rapport.docx']

class RollbackIncomplete(RuntimeError):
    pass

def call(args, input_data=None):
    process=subprocess.Popen(args,stdin=subprocess.PIPE if input_data is not None else None,
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err=process.communicate(input_data)
    if process.returncode:
        raise RuntimeError('Commande échouée (%s) : %s' % (args[0],err.decode('utf-8','replace')[-1600:]))
    return out

def hdfs(*args):return call(['hdfs','dfs']+list(args))

def exists(path):
    process=subprocess.Popen(['hdfs','dfs','-ls','-d',path],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err=process.communicate()
    if process.returncode==0:return True
    message=err.decode('utf-8','replace')
    if 'No such file or directory' in message:return False
    raise RuntimeError('Vérification HDFS impossible : '+path+' : '+message[-1000:])

def beeline(sql, log_path=None):
    fd,path=tempfile.mkstemp(prefix='chu_gold_',suffix='.sql')
    try:
        stream=os.fdopen(fd,'wb');stream.write(sql.encode('utf-8'));stream.close()
        args=['beeline','-u','jdbc:hive2://localhost:10000/default','-n','cloudera',
              '--force=false','--silent=true','--showHeader=false','--outputformat=tsv2','-f',path]
        proc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out,err=proc.communicate()
        if log_path:
            stream=open(log_path,'wb')
            try:stream.write(out+b'\n--- stderr ---\n'+err)
            finally:stream.close()
        if proc.returncode:raise RuntimeError('Hive : étape échouée, consulter '+(log_path or 'les journaux'))
        return out.decode('utf-8','replace')
    finally:os.remove(path)

def read_sql(name):
    path=os.path.join(ROOT,*name.split('/'))
    stream=open(path,'rb')
    try:return stream.read().decode('utf-8')
    finally:stream.close()

def file_hash(name):
    stream=open(os.path.join(ROOT,*name.split('/')),'rb')
    try:return hashlib.sha256(stream.read()).hexdigest()
    finally:stream.close()

def expected_tables():
    return collecter_qualite.gold_tables()

def validate_live_metadata(expected, audit_dir):
    """Ne bascule que si les objets existants pointent vers les chemins prévus."""
    for table,(fields,location) in sorted(expected.items()):
        description=beeline('DESCRIBE FORMATTED gold.`%s`;' % table,
                            os.path.join(audit_dir,'schema_'+table+'.log'))
        actual=[]
        for line in description.splitlines():
            cells=[x.strip() for x in line.split('\t')]
            if cells and cells[0].startswith('# Detailed'):break
            if len(cells)>=2 and cells[1].lower() in ('string','int','smallint','double','date','bigint'):
                actual.append((cells[0].strip('`').lower(),cells[1].lower()))
        if actual!=fields or location not in description or 'EXTERNAL_TABLE' not in description or 'OrcInputFormat' not in description:
            raise ValueError('Schéma, format ou chemin Gold divergent : '+table)

def stage_sql(sql,database,path):
    sql=re.sub(r'(?i)\bCREATE\s+DATABASE\s+IF\s+NOT\s+EXISTS\s+gold\b',
               'CREATE DATABASE IF NOT EXISTS '+database,sql)
    sql=re.sub(r'(?im)^\s*USE\s+gold\s*;', 'USE '+database+';',sql)
    return sql.replace(GOLD,path)

def list_paths(path):
    out=hdfs('-ls',path).decode('utf-8','replace')
    result=[]
    for line in out.splitlines():
        parts=line.split()
        if len(parts)>=8 and parts[0][0] in ('d','-'):
            child=parts[-1];name=child.rsplit('/',1)[-1]
            if not re.match(r'^[A-Za-z0-9_.-]+$',name):raise ValueError('Nom HDFS inattendu')
            result.append((name,child))
    return result

def atomic_copy(source,destination):
    temporary=destination+'.tmp'
    shutil.copyfile(source,temporary)
    os.rename(temporary,destination)

def write_json(path,value):
    tmp=path+'.tmp'
    stream=open(tmp,'wb')
    try:
        stream.write(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=True).encode('ascii'))
        stream.flush()
        os.fsync(stream.fileno())
    finally:stream.close()
    os.rename(tmp,path)

def publish(stage,backup,expected,state=None,status_path=None):
    """Bascule HDFS avec rollback ; les lecteurs Gold doivent être suspendus."""
    def record(action):
        if state is not None:
            state['publication_action']=action
            write_json(status_path,state)
    hdfs('-mkdir','-p',backup)
    try:
        for group in ('tables','rejets'):
            live=GOLD+'/'+group;old=backup+'/'+group;new=stage+'/'+group
            if not exists(live) or not exists(new) or exists(old):
                raise ValueError('Etat initial Gold invalide : '+group)
            record('AVANT_SAUVEGARDE_'+group)
            hdfs('-mv',live,old)
            record('AVANT_PUBLICATION_'+group)
            hdfs('-mv',new,live)
            record('PUBLIE_'+group)
        for name,(_,location) in expected.items():
            if not exists(location):raise ValueError('Table publiée absente : '+name)
    except Exception as original:
        try:
            # Une commande peut avoir réussi côté HDFS avant une erreur réseau.
            # Déterminer la marche arrière à partir des chemins réels, pas
            # seulement des commandes dont le client a reçu une confirmation.
            for group in ('rejets','tables'):
                live=GOLD+'/'+group;old=backup+'/'+group;new=stage+'/'+group
                present=(exists(live),exists(old),exists(new))
                if present==(True,True,False):
                    hdfs('-mv',live,new)
                    present=(False,True,True)
                if present==(False,True,True):
                    hdfs('-mv',old,live)
                    present=(True,False,True)
                if present!=(True,False,True):
                    raise ValueError('Etat HDFS ambigu pendant le retour arrière : '+group)
        except Exception as rollback_error:
            raise RollbackIncomplete('Bascule : %s ; retour arrière incomplet : %s' % (original,rollback_error))
        raise

def run(lot):
    if not re.match(r'^[a-z0-9_]{1,32}$',lot):raise ValueError('Lot invalide')
    now=datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    token=uuid.uuid4().hex[:12]
    run_id=now+'_'+token
    database='gold_work_'+token
    stage=GOLD+'/.gold_work/'+run_id
    backup=GOLD+'/.gold_previous_'+run_id
    audit=os.path.expanduser('~/.chu/gold_runs/'+run_id)
    os.makedirs(audit,448)
    files_hash=dict((name,file_hash(name)) for name in TRACKED)
    state={'lot':lot,'run_id':run_id,'status':'STARTED','sql_sha256':files_hash,
           'stage':stage,'database':database,'backup':backup}
    status_path=os.path.join(audit,'execution.json')
    write_json(status_path,state)
    locked=False
    silver_locked=False
    lock_token=(run_id+'\n').encode('ascii')
    try:
        print('GOLD_PREFLIGHT_START');sys.stdout.flush()
        if exists(LOCK):raise ValueError('Une alimentation Gold est déjà en cours')
        hdfs('-mkdir',LOCK);locked=True
        if exists(SILVER_LOCK):raise ValueError('Publication Silver en cours')
        fd,lock_file=tempfile.mkstemp(prefix='chu_gold_lock_')
        try:
            stream=os.fdopen(fd,'wb');stream.write(lock_token);stream.close()
            hdfs('-put',lock_file,SILVER_LOCK)
            silver_locked=True
        finally:os.remove(lock_file)
        silver_bytes=hdfs('-cat',SILVER)
        silver=json.loads(silver_bytes.decode('utf-8'))
        if silver.get('status')!='PUBLISHED' or not silver.get('lot_id'):
            raise ValueError('Silver non publié')
        if silver['lot_id']!=lot:
            raise ValueError('Le lot Silver publié ne correspond pas au lot demandé')
        safe=call(['hdfs','dfsadmin','-safemode','get']).decode('utf-8','replace')
        if 'OFF' not in safe.upper():raise ValueError('HDFS est en mode sans écriture')
        expected=expected_tables()
        validate_live_metadata(expected,audit)
        state.update({'status':'PRECHECK_OK','silver_lot':silver['lot_id'],
                      'silver_sha256':hashlib.sha256(silver_bytes).hexdigest()})
        write_json(status_path,state)
        hdfs('-mkdir','-p',stage+'/tables',stage+'/rejets')
        for idx,name in enumerate(FILES):
            print('GOLD_STEP_START : '+name);sys.stdout.flush()
            sql=read_sql(name)
            if file_hash(name)!=files_hash[name]:
                raise ValueError('Script SQL modifié pendant le chargement : '+name)
            beeline(stage_sql(sql,database,stage),os.path.join(audit,'%02d.log'%idx))
            print('GOLD_STEP_OK : '+name);sys.stdout.flush()
        if hdfs('-cat',SILVER_LOCK)!=lock_token or hdfs('-cat',SILVER)!=silver_bytes:
            raise ValueError('Silver a changé pendant le chargement Gold')
        quality_dir=os.path.join(audit,'qualite')
        gold=collecter_qualite.collect(quality_dir,database,tables=expected)
        if gold['silver_sha256']!=state['silver_sha256']:
            raise ValueError('Les contrôles ne correspondent pas au Silver initial')
        if hdfs('-cat',SILVER_LOCK)!=lock_token or hdfs('-cat',SILVER)!=silver_bytes:
            raise ValueError('Silver a changé pendant les contrôles Gold')
        for name in TRACKED:
            if file_hash(name)!=files_hash[name]:
                raise ValueError('Script ou modèle modifié pendant le chargement : '+name)
        gold['silver_lot_certifie']=True
        gold['origine']='Contrôles du Gold préparé pour le lot Silver indiqué ; la bascule exige la suspension des lectures.'
        gold['run_id']=run_id
        write_json(os.path.join(quality_dir,'gold.json'),gold)
        word=os.path.join(quality_dir,'Rapport_Qualite_Donnees.docx')
        rapport_docx.generate(silver,gold,os.path.join(QUALITY,'modele_rapport.docx'),word)
        if gold['status']!='CONTROLES_OK':
            raise ValueError('Contrôles Gold non validés : '+gold['status']+' ; rapport : '+word)
        # Sauvegarde les variantes existantes ; elles deviennent obsolètes après rechargement.
        base=set(name for name,(_,location) in expected.items() if '/tables/' in location)
        for name,path in list_paths(GOLD+'/tables'):
            if name not in base:
                print('GOLD_CONSERVE_VARIANTE : '+name);sys.stdout.flush()
                hdfs('-cp',path,stage+'/tables/'+name)
        state['status']='PUBLISHING';state['publication_action']='PREPARE';write_json(status_path,state)
        publish(stage,backup,expected,state,status_path)
        state['status']='PUBLISHED';write_json(status_path,state)
        # Rapport versionné par lancement, puis remplacement de la version courante.
        reports=os.path.expanduser('~/.chu/qualite')
        if not os.path.isdir(reports):os.makedirs(reports,448)
        atomic_copy(word,os.path.join(reports,'Rapport_Qualite_Donnees.docx'))
        state['status']='PUBLISHED_REPORT_READY';write_json(status_path,state)
        print('GOLD_REPLACED : '+GOLD)
        print('RAPPORT_QUALITE : '+os.path.join(reports,'Rapport_Qualite_Donnees.docx'))
        print('ATTENTION : variantes et index Gold a reconstruire apres rechargement')
        print('SAUVEGARDE_HDFS : '+backup)
    except Exception as error:
        state['error']=text_type(error)
        if isinstance(error,RollbackIncomplete):state['status']='ROLLBACK_FAILED'
        elif state.get('status')=='PUBLISHED_REPORT_READY':state['status']='PUBLISHED_REPORT_READY_WITH_WARNING'
        elif state.get('status')=='PUBLISHED':state['status']='PUBLISHED_REPORT_FAILED'
        else:state['status']='FAILED'
        write_json(status_path,state)
        print('GOLD_FAILED : '+state['status'])
        raise
    finally:
        if state.get('status')!='ROLLBACK_FAILED':
            if silver_locked:
                if hdfs('-cat',SILVER_LOCK)!=lock_token:raise RuntimeError('Verrou Silver modifié : intervention nécessaire')
                hdfs('-rm',SILVER_LOCK)
            if locked:hdfs('-rmdir',LOCK)

def main():
    parser=OptionParser();parser.add_option('--lot-id',dest='lot')
    opts,extra=parser.parse_args()
    if extra or not opts.lot:parser.error('--lot-id est obligatoire')
    run(opts.lot)

if __name__=='__main__':main()
