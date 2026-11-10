# -*- coding: utf-8 -*-
"""Enchaîne Silver, Gold puis le rapport qualité sur la VM Cloudera."""
from __future__ import unicode_literals
import os
import re
import subprocess
import sys
from optparse import OptionParser

ROOT=os.path.dirname(os.path.abspath(__file__))
SILVER='/home/cloudera/chu_silver'

def main():
    parser=OptionParser()
    parser.add_option('--lot-id',dest='lot')
    parser.add_option('--hmac-key-file',dest='key_file')
    parser.add_option('--key-version',dest='key_version')
    parser.add_option('--exclude-pseudonyms-file',dest='exclude_file')
    opts,extra=parser.parse_args()
    if extra or not all([opts.lot,opts.key_file,opts.key_version]):
        parser.error('--lot-id, --hmac-key-file et --key-version sont obligatoires')
    if not re.match(r'^[a-z0-9_]{1,32}$',opts.lot):parser.error('Identifiant de lot invalide')
    silver=['python',os.path.join(SILVER,'silver_pipeline.py'),'--lot-id',opts.lot,
            '--hmac-key-file',opts.key_file,'--key-version',opts.key_version]
    if opts.exclude_file:silver.extend(['--exclude-pseudonyms-file',opts.exclude_file])
    print('PIPELINE_COMPLET : debut Silver');sys.stdout.flush()
    if subprocess.call(silver,cwd=SILVER)!=0:
        raise RuntimeError('Silver a échoué : Gold et le rapport ne sont pas lancés')
    print('PIPELINE_COMPLET : debut Gold');sys.stdout.flush()
    gold=['python',os.path.join(ROOT,'Gold','pipeline_gold.py'),'--lot-id',opts.lot]
    if subprocess.call(gold,cwd=ROOT)!=0:
        raise RuntimeError('Gold a échoué : consulter le journal et le rapport de diagnostic')
    print('PIPELINE_COMPLET_OK : Silver, Gold et rapport qualite')

if __name__=='__main__':main()
