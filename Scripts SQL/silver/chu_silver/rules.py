# -*- coding: utf-8 -*-
"""Regles metier testables sans Spark. Aucune donnee personnelle journalisee."""
import datetime
import hashlib
import hmac
import json
import math
import re
import unicodedata

try:
    text_type = unicode
except NameError:
    text_type = str


class Invalid(ValueError):
    pass


def clean(value):
    if value is None:
        return None
    if not isinstance(value, text_type):
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        else:
            value = text_type(value)
    return value.strip().lstrip(u'\ufeff') or None


def token(value):
    value = clean(value) or u''
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', value)
                  .encode('ascii', 'ignore').decode('ascii').lower())


def integer(value, required=False, minimum=None):
    value = clean(value)
    if value is None and not required:
        return None
    if value is None or not re.match(r'^-?[0-9]+$', value):
        raise Invalid('ENTIER_INVALIDE')
    result = int(value)
    if result < -2147483648 or result > 2147483647:
        raise Invalid('ENTIER_HORS_CAPACITE')
    if minimum is not None and result < minimum:
        raise Invalid('ENTIER_HORS_DOMAINE')
    return result


def patient_id(value):
    # Source PostgreSQL INT : 00042 et 42 representent la meme identite.
    return text_type(integer(value, required=True))


def pseudonym(value, key):
    if not key or len(key) < 32:
        raise ValueError('Cle HMAC absente ou trop courte (32 octets minimum)')
    return hmac.new(key, patient_id(value).encode('utf-8'), hashlib.sha256).hexdigest()


def pro_pseudonym(identifier, key):
    """HMAC-SHA256 de l'identifiant professionnel deja normalise (prof_id).

    Prefixe de domaine 'pro:' : meme cle que le patient mais jamais le meme
    pseudonyme, donc pas de recoupement professionnel/patient.
    """
    if not key or len(key) < 32:
        raise ValueError('Cle HMAC absente ou trop courte (32 octets minimum)')
    return hmac.new(key, (u'pro:' + identifier).encode('utf-8'), hashlib.sha256).hexdigest()


def prof_id(value, kind=None):
    value = clean(value)
    if value is None:
        raise Invalid('IDENTIFIANT_PRO_INVALIDE')
    kind = token(kind)
    if kind not in ('', 'adeli', 'rpps'):
        raise Invalid('TYPE_IDENTIFIANT_PRO_INCONNU')
    # La source contient aussi des ADELI alphanumeriques de neuf caracteres.
    # Ils restent opaques : aucune suppression de lettre ni conversion INT.
    if kind != 'rpps':
        if re.match(r'^[0-9]{8}$', value):
            return value.zfill(9)
        if re.match(r'^[0-9A-Za-z]{9}$', value):
            return value
    if kind != 'adeli' and re.match(r'^[0-9]{11}$', value):
        return value
    raise Invalid('IDENTIFIANT_PRO_INVALIDE')


def finess(value):
    value = clean(value)
    if value is None:
        raise Invalid('FINESS_ABSENT')
    # Excel peut serialiser un entier en decimal ; pas de notation scientifique.
    if re.match(r'^[0-9]+\.0+$', value):
        value = value.split('.')[0]
    # Les sources e-Satis fournies comportent des FINESS corses 2A/2B.
    # Ne pas les rejeter avec une validation exclusivement numerique.
    if re.match(r'^2[AB][0-9]{7}$', value):
        return value
    if not re.match(r'^[0-9]{1,9}$', value) or int(value) == 0:
        raise Invalid('FINESS_INVALIDE')
    return value.zfill(9)


def date_value(value, pattern='iso', required=False):
    value = clean(value)
    if value is None and not required:
        return None
    try:
        if pattern == 'iso' and re.match(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$', value or ''):
            return datetime.date(int(value[:4]), int(value[5:7]), int(value[8:10]))
        if pattern == 'fr' and re.match(r'^[0-9]{2}/[0-9]{2}/[0-9]{4}$', value or ''):
            return datetime.date(int(value[6:10]), int(value[3:5]), int(value[:2]))
    except ValueError:
        pass
    raise Invalid('DATE_INVALIDE')


def sex(value):
    return {'m': 'M', 'male': 'M', 'masculin': 'M', '1': 'M',
            'f': 'F', 'female': 'F', 'feminin': 'F', '2': 'F'}.get(token(value), 'inconnu')


def number(value):
    value = clean(value)
    if value is None:
        return None
    try:
        result = float(value.replace(',', '.'))
        if math.isnan(result) or math.isinf(result):
            raise ValueError()
        return result
    except ValueError:
        raise Invalid('NOMBRE_INVALIDE')


def department(code):
    code = clean(code)
    if not code or code == 'inconnu':
        return None
    if not re.match(r'^(?:[0-9]{5}|2[AB][0-9]{3})$', code):
        return None
    return code[:3] if code.startswith(('97', '98')) else code[:2]


def required(value, motif='CLE_OBLIGATOIRE_ABSENTE'):
    result = clean(value)
    if result is None:
        raise Invalid(motif)
    return result


def payload_hash(values):
    def encode(value):
        if isinstance(value, datetime.date):
            return value.isoformat()
        raise TypeError('Type non serialisable')
    data = json.dumps(values, ensure_ascii=True, separators=(',', ':'), default=encode)
    return hashlib.sha256(data.encode('ascii')).hexdigest()


def transform(source, row, key=None, options=None):
    """Retourne (valeurs metier, statut, motifs, avertissements).

    Les noms/adresses ne sont jamais copies dans le resultat ni les erreurs.
    Les exceptions techniques remontent ; seules Invalid sont des rejets metier.
    """
    options = options or {}
    out, warnings = {}, []
    try:
        if source in ('patient', 'consultation', 'hospitalisation'):
            out['id_patient'] = pseudonym(row.get('Id_patient'), key)
            if out['id_patient'] in options.get('excluded', set()):
                return {}, 'EXCLUDE', 'EXCLUSION_AUTORISEE', ''
        if source == 'patient':
            out['sexe'] = sex(row.get('Sexe'))
            try:
                out['age'] = integer(row.get('Age'), minimum=0)
            except Invalid:
                out['age'] = None
                warnings.append('AGE_INVALIDE')
            if out['sexe'] == 'inconnu':
                warnings.append('SEXE_INCONNU')
        elif source == 'diagnostic':
            out = {'code_diag': required(row.get('Code_diag')), 'libelle': clean(row.get('Diagnostic'))}
        elif source == 'specialite':
            out = {'code_specialite': required(row.get('Code_specialite')),
                   'fonction': clean(row.get('Fonction')), 'specialite': clean(row.get('Specialite'))}
        elif source == 'professionnel':
            out = {'id_prof_sante': pro_pseudonym(
                       prof_id(row.get('Identifiant'), row.get('Type_identifiant')), key),
                   'categorie': clean(row.get('Categorie_professionnelle')),
                   'profession': clean(row.get('Profession')),
                   'code_specialite': clean(row.get('Code_specialite')),
                   '_original_id': clean(row.get('Identifiant'))}
        elif source == 'etablissement':
            out = dict((name, clean(value)) for name, value in row.items())
            out['identifiant_organisation'] = required(row.get('identifiant_organisation'))
        elif source == 'activite':
            out = {'id_prof_sante': pro_pseudonym(prof_id(row.get('identifiant')), key),
                   'identifiant_organisation': required(row.get('identifiant_organisation')),
                   'mode_exercice': clean(row.get('mode_exercice')) or 'inconnu'}
        elif source == 'consultation':
            out.update({'num_consultation': integer(row.get('Num_consultation'), True),
                        'date_consultation': date_value(row.get('Date'), required=True),
                        'code_diag': required(row.get('Code_diag')),
                        'id_prof_sante': pro_pseudonym(prof_id(row.get('Id_prof_sante')), key)})
        elif source == 'hospitalisation':
            out.update({'num_hospitalisation': integer(row.get('Num_Hospitalisation'), True),
                        'date_entree': date_value(row.get('Date_Entree'), 'fr', True),
                        'code_diag': required(row.get('Code_diagnostic')),
                        'identifiant_organisation': required(row.get('identifiant_organisation'))})
        elif source == 'satisfaction':
            site = finess(row.get('finess_geo'))
            score = number(row.get('score_all_rea_ajust'))
            count = integer(row.get('nb_rep_score_all_rea_ajust'), minimum=0)
            if score is not None and not 0 <= score <= 100:
                raise Invalid('SCORE_HORS_DOMAINE')
            if score is not None and not count:
                warnings.append('POIDS_NON_EXPLOITABLE')
            out = {'finess_geo': site, 'identifiant_organisation': 'F' + site,
                   'annee': options['year'], 'region': clean(row.get('region')) or 'inconnu',
                   'code_region': None, 'score_all_rea_ajust': score,
                   'nb_rep_score_all_rea_ajust': count}
        elif source == 'deces':
            death = date_value(row.get('date_deces'), required=True)
            try:
                birth = date_value(row.get('date_naissance'))
            except Invalid:
                birth = None
                warnings.append('NAISSANCE_INVALIDE')
            if birth is not None and birth > death:
                raise Invalid('NAISSANCE_APRES_DECES')
            code = clean(row.get('code_lieu_deces')) or 'inconnu'
            # RGPD / plan de gouvernance 5.3 : la naissance ne sert qu'au controle
            # de coherence ci-dessus ; naissance et numero d'acte ne sont pas publies.
            out = {'date_deces': death, 'sexe': sex(row.get('sexe')),
                   'code_commune_deces': code, 'code_departement': department(code)}
        elif source == 'codes_postaux':
            normalized = dict((token(k), v) for k, v in row.items())
            postal = required(normalized.get('codepostal'))
            if not re.match(r'^[0-9]{5}$', postal):
                raise Invalid('CODE_POSTAL_INVALIDE')
            out = {'code_commune_insee': required(normalized.get('codecommuneinsee')),
                   'nom_de_la_commune': clean(normalized.get('nomdelacommune')),
                   'code_postal': postal,
                   'libelle_d_acheminement': clean(normalized.get('libelledacheminement'))}
        else:
            raise ValueError('Source inconnue : ' + source)
        return out, 'VALID', '', '|'.join(warnings)
    except Invalid as error:
        return {}, 'REJECT', str(error), '|'.join(warnings)
