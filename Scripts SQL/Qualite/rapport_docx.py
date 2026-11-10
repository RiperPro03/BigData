# -*- coding: utf-8 -*-
"""Génère un rapport Word éditable avec Python 2.6 et la bibliothèque standard.

Entrées : agrégats silver.json et gold.json, jamais de données individuelles.
Le modèle Word et ce script restent ensemble dans le dossier Qualite.
"""
from __future__ import unicode_literals
import datetime
import json
import os
import re
import sys
import zipfile
from optparse import OptionParser
from xml.sax.saxutils import escape

try:text_type=unicode
except NameError:text_type=str

def txt(v):
    return escape(text_type(v))

def number(v):
    return re.sub(r'(?<=\d)(?=(?:\d{3})+$)',' ',str(int(v)))

def percent(v):
    return 'Non disponible' if v is None else ('%.2f %%' % (float(v)*100)).replace('.',',')

def para(value,style=None,bold=False):
    prop='<w:pPr><w:pStyle w:val="%s"/></w:pPr>' % style if style else '<w:pPr><w:spacing w:after="100" w:line="240" w:lineRule="auto"/></w:pPr>'
    run='<w:rPr><w:b/></w:rPr>' if bold else ''
    return '<w:p>'+prop+'<w:r>'+run+'<w:t xml:space="preserve">'+txt(value)+'</w:t></w:r></w:p>'

def heading(value,level=1):return para(value,'Titre%d'%level)

def table(headers,rows,widths):
    borders=''.join('<w:%s w:val="single" w:sz="4" w:color="D9D9D9"/>'%name for name in ('top','left','bottom','right','insideH','insideV'))
    result=['<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblBorders>'+borders+'</w:tblBorders><w:tblCellMar><w:top w:w="70" w:type="dxa"/><w:left w:w="90" w:type="dxa"/><w:bottom w:w="70" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>'+''.join('<w:gridCol w:w="%d"/>'%w for w in widths)+'</w:tblGrid>']
    for i,row in enumerate([headers]+list(rows)):
        result.append('<w:tr><w:trPr><w:cantSplit/>' + ('<w:tblHeader/>' if i==0 else '')+'</w:trPr>')
        for j,value in enumerate(row):
            fill='F2A97F' if i==0 else ('F4F5F7' if i%2==0 else 'FFFFFF')
            result.append('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/><w:shd w:fill="%s"/><w:vAlign w:val="center"/></w:tcPr><w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:sz w:val="19"/>'%(widths[j],fill)+('<w:b/>' if i==0 else '')+'</w:rPr><w:t xml:space="preserve">'+txt(value)+'</w:t></w:r></w:p></w:tc>')
        result.append('</w:tr>')
    result.append('</w:tbl><w:p/>')
    return ''.join(result)

def bar(accepted,rejected,total):
    if not total:return para('Aucune ligne d’activité disponible.')
    other=total-accepted-rejected
    if min(accepted,rejected,other)<0:raise ValueError('Bilan activité incohérent')
    # Tableau Word éditable : les autres statuts ne sont pas comptés comme rejets.
    values=[(n,c) for n,c in ((accepted,'557965'),(rejected,'C47553'),(other,'8B92A0')) if n]
    segments=[];remaining=9072
    for index,(value,color) in enumerate(values):
        width=remaining if index==len(values)-1 else max(1,min(remaining-(len(values)-index-1),int(9072*float(value)/total)))
        segments.append((width,color));remaining-=width
    return ('<w:tbl><w:tblPr><w:tblW w:w="9072" w:type="dxa"/><w:tblLayout w:type="fixed"/></w:tblPr>'
        '<w:tblGrid>'+''.join('<w:gridCol w:w="%d"/>'%width for width,_ in segments)+'</w:tblGrid><w:tr>'+
        ''.join('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/><w:shd w:fill="%s"/></w:tcPr><w:p><w:r><w:t> </w:t></w:r></w:p></w:tc>'%(w,c) for w,c in segments)+
        '</w:tr></w:tbl>'+para('Acceptées : '+number(accepted)+' ('+percent(float(accepted)/total)+')    Rejetées : '+number(rejected)+' ('+percent(float(rejected)/total)+')    Autres statuts : '+number(other)+' ('+percent(float(other)/total)+')'))

def build(silver,gold):
    outputs=silver.get('outputs',{});metrics=silver.get('metrics',{});checks=gold.get('checks',{})
    if not outputs or not metrics:raise ValueError('Audit Silver incomplet')
    expected=gold.get('expected',[]);missing=gold.get('missing',[])
    activity=metrics.get('activite',{}); deaths=metrics.get('deces',{})
    if any(k not in activity for k in ('read','VALID','REJECT')) or 'VALID' not in deaths:
        raise ValueError('Comptages Silver activité ou décès manquants')
    for name,item in outputs.items():
        if 'rows' not in item or 'completeness' not in item or 'nulls' not in item:
            raise ValueError('Complétude Silver incomplète : '+name)
        if set(item['completeness']) != set(item['nulls']):
            raise ValueError('Attributs et valeurs NULL incohérents : '+name)
        for column,value in item['completeness'].items():
            nulls=item['nulls'][column]
            if nulls < 0 or nulls > item['rows'] or (value is not None and not 0 <= value <= 1):
                raise ValueError('Complétude invalide : '+name+'.'+column)
    read=activity['read'];accepted=activity['VALID'];rejected=activity['REJECT']
    cert='La stabilité de l’audit Silver a été vérifiée pendant le traitement.' if gold.get('silver_lot_certifie') else 'La correspondance exacte des contrôles Gold avec ce lot Silver n’est pas certifiée.'
    origin=gold.get('origine','Origine non indiquée')
    chunks=['<w:p><w:r><w:br w:type="page"/></w:r></w:p>',heading('Synthèse du contrôle qualité')]
    chunks.append(para('Ce rapport présente la complétude, la cohérence des références, les FINESS, les doublons et les rejets des données Silver et Gold. Il contient uniquement des indicateurs agrégés.'))
    chunks.append(para('Lot Silver : '+text_type(silver.get('lot_id','inconnu'))+' ; statut : '+text_type(silver.get('status','inconnu'))+'. Contrôles Gold : '+text_type(gold.get('date','date non indiquée'))+'. '+text_type(origin)+' '+cert))
    zero=sum(1 for x in checks.values() if x.get('values') and x['values'][-1]==0)
    info=silver.get('indicateurs',{}).get('finess_correspondance')
    rows=[('Tables et attributs Silver',str(len(outputs))+' tables ; '+str(sum(len(x.get('completeness',{})) for x in outputs.values()))+' attributs'),
          ('Activités rejetées',number(rejected)+' sur '+number(read)),
          ('Décès acceptés',number(deaths['VALID'])),
          ('Contrôles Gold',str(zero)+' à zéro sur '+str(len(checks))+' retrouvés ; '+str(len(missing))+' manquants'),
          ('État des contrôles Gold',text_type(gold.get('status','NON_DISPONIBLE'))),
          ('Correspondance FINESS',percent(info.get('taux_correspondance')) if info else 'Non disponible dans cet audit')]
    chunks.append(table(['Indicateur','Résultat'],rows,[4000,5072]))
    chunks.append(para('Les rejets d’activité doivent être analysés et leur impact sur l’attribution des consultations aux établissements évalué avant validation métier.'))
    chunks.append(heading('1 Qualité des lignes intégrées'))
    chunks.append(para('Chaque source distingue les lignes acceptées, rejetées, en doublon, alternatives et exclues. Les avertissements ne sont pas des catégories supplémentaires.'))
    chunks.append(bar(accepted,rejected,read))
    rows=[]
    for name,item in sorted(metrics.items()):
        if name.startswith('cog_'):continue
        required=('read','VALID','REJECT','DUPLICATE','ALTERNATIVE','EXCLUDE')
        if any(key not in item for key in required):raise ValueError('Comptages manquants : '+name)
        rows.append((name,number(item['read']),number(item['VALID']),number(item['REJECT']),number(item['DUPLICATE']),number(item['ALTERNATIVE']),number(item['EXCLUDE'])))
    chunks.append(table(['Source','Lues','Acceptées','Rejets','Doublons','Variantes','Exclusions'],rows,[1872,1200,1200,1200,1200,1200,1200]))
    reasons=[(x.get('motif') or 'Non renseigné',number(x.get('count',0))) for x in activity.get('details',[]) if x.get('status')=='REJECT']
    chunks.append(heading('Motifs des rejets d’activité',2));chunks.append(table(['Motif','Lignes'],reasons,[6072,3000]))
    chunks.append(para('Le premier motif rencontré classe chaque ligne ; une ligne rejetée peut aussi présenter d’autres anomalies. Les variantes postales correspondent à une règle de sélection et ne sont pas systématiquement des erreurs.'))
    chunks.append(heading('2 Complétude par attribut'))
    chunks.append(para('Complétude = (lignes Silver acceptées − valeurs NULL) / lignes Silver acceptées. Une valeur « inconnu », vide ou incorrecte mais non NULL peut compter comme renseignée. Ce taux ne décrit pas à lui seul la source brute.'))
    for name,item in sorted(outputs.items()):
        chunks.append(heading(name+'  '+number(item.get('rows',0))+' lignes',2))
        comp=item.get('completeness',{});nulls=item.get('nulls',{})
        chunks.append(table(['Attribut','NULL','Complétude'],[(c,number(nulls[c]),percent(comp[c])) for c in sorted(comp)],[4800,2000,2272]))
    chunks.append(heading('Complétude des attributs Gold',2))
    gold_outputs=gold.get('completeness')
    if not gold_outputs:
        chunks.append(para('Non disponible dans les contrôles historiques. Ce bilan sera calculé lors de la prochaine alimentation Gold.'))
    else:
        chunks.append(para('Une valeur non NULL est considérée comme renseignée. Une table vide n’a pas de taux de complétude calculable.'))
        for name,item in sorted(gold_outputs.items()):
            comp=item['completeness'];nulls=item['nulls']
            if set(comp)!=set(nulls):raise ValueError('Complétude Gold incomplète : '+name)
            chunks.append(heading(name+'  '+number(item['rows'])+' lignes',2))
            chunks.append(table(['Attribut','NULL','Complétude'],[(c,number(nulls[c]),percent(comp[c])) for c in sorted(comp)],[4800,2000,2272]))
    chunks.append(heading('3 FINESS et contrôles Gold'))
    if info:
        chunks.append(table(['Correspondance satisfaction vers établissement','Résultat'],[('Lignes analysées',number(info['lignes_satisfaction'])),('Avec établissement',number(info['lignes_avec_etablissement'])),('Sans établissement',number(info['lignes_sans_etablissement'])),('Taux de correspondance',percent(info.get('taux_correspondance')))],[6072,3000]))
        chunks.append(para('La comparaison utilise identifiant_organisation. Les écarts sont indicatifs et peuvent provenir de différences de périmètre entre sources.'))
    else:chunks.append(para('La correspondance FINESS entre satisfaction et établissements est indisponible dans cet audit. Elle doit être mesurée par la version récente du Silver.'))
    balances=[]
    for name in ('consultation','hospitalisation','deces','satisfaction'):
        values=checks.get(name,{}).get('values')
        balances.append((name,)+(tuple(number(x) for x in values) if values and len(values)==4 else ('Non disponible','—','—','—')))
    chunks.append(heading('Réconciliation Silver vers Gold',2))
    chunks.append(table(['Fait','Silver','Gold','Rejets','Écart'],balances,[1872,2000,2000,1600,1600]))
    chunks.append(para('Silver = Gold + rejets ; l’écart attendu est nul. Un rejet non nul doit être expliqué.'))
    rest=[(name,number(x['values'][-1])) for name,x in sorted(checks.items()) if name not in ('consultation','hospitalisation','deces','satisfaction') and x.get('values')]
    chunks.append(heading('Doublons et références',2));chunks.append(table(['Contrôle','Anomalies'],rest,[7072,2000]))
    chunks.append(heading('4 Méthode et limites'))
    chunks.append(para('Audit Silver : /user/cloudera/chu/silver/audit/rapport_final.json. Contrôles Gold : 30_controles_gold.sql. '+text_type(origin)+' '+cert))
    chunks.append(para(str(len(checks))+' résultats Gold retrouvés sur '+str(len(expected))+' attendus ; '+str(len(missing))+' manquants. La validation des résultats exige leur rattachement au lot et à la version de code effectivement utilisés.'))
    unresolved=deaths.get('region_2019_unresolved')
    if unresolved is not None:chunks.append(para('Décès 2019 acceptés sans région : '+number(unresolved)+'. Ces occurrences restent dans les données et ne sont pas attribuées à une région arbitraire.'))
    chunks.append(para('Le rapport ne contient aucune clé HMAC ni ligne individuelle. Examiner les anomalies, les champs facultatifs et les rejets avant de conclure à la qualité du lot.'))
    return ''.join(chunks)

def generate(silver,gold,template,output):
    source=zipfile.ZipFile(template,'r')
    try:
        document=source.read('word/document.xml').decode('utf-8')
        marker='<w:p><w:r><w:t>__CONTENU_QUALITE__</w:t></w:r></w:p>'
        if document.count(marker)!=1 or '__DATE_RAPPORT__' not in document:
            raise ValueError('Modèle Word incorrect ou incomplet')
        document=document.replace(marker,build(silver,gold))
        document=document.replace('__DATE_RAPPORT__',datetime.date.today().strftime('%d/%m/%Y'))
        temporary=output+'.tmp'
        target=zipfile.ZipFile(temporary,'w')
        try:
            for item in source.infolist():
                data=document.encode('utf-8') if item.filename=='word/document.xml' else source.read(item.filename)
                target.writestr(item,data)
        finally:target.close()
    finally:source.close()
    os.rename(temporary,output)

def main():
    p=OptionParser();p.add_option('--input-dir',dest='input_dir');p.add_option('--output',dest='output')
    p.add_option('--template',dest='template',default=os.path.join(os.path.dirname(os.path.abspath(__file__)),'modele_rapport.docx'))
    opts,extra=p.parse_args()
    if extra or not opts.input_dir or not opts.output:p.error('--input-dir et --output sont obligatoires')
    silver=json.load(open(os.path.join(opts.input_dir,'silver.json'),'rb'))
    gold=json.load(open(os.path.join(opts.input_dir,'gold.json'),'rb'))
    generate(silver,gold,opts.template,opts.output)
    print('RAPPORT_WORD : '+opts.output)

if __name__=='__main__':main()
