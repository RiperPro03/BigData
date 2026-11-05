# -*- coding: utf-8 -*-
"""Contrats explicites derives des DDL/DML main (7ed0f68) et des sources.

Un tuple (nom, type Hive) sert aussi a construire le StructType Spark.
Les colonnes de provenance ne font pas partie des tables metier publiees.
"""
PG = {
    "diagnostic": "Code_diag Diagnostic".split(),
    "specialite": "Code_specialite Fonction Specialite".split(),
    "professionnel": "Identifiant Civilite Categorie_professionnelle Nom Prenom Profession Type_identifiant Code_specialite".split(),
    "patient": "Id_patient Nom Prenom Sexe Adresse Ville Code_postal Pays EMail Tel Date Age Num_Secu Groupe_sanguin Poid Taille".split(),
    "consultation": "Num_consultation Id_mut Id_patient Id_prof_sante Code_diag Motif Date Heure_debut Heure_fin".split()
}
ETABLISSEMENT = "adresse cedex code_commune code_postal commune complement_destinataire complement_point_geographique email enseigne_commerciale_site finess_etablissement_juridique finess_site identifiant_organisation indice_repetition_voie mention_distribution numero_voie pays raison_sociale_site siren_site siret_site telecopie telephone telephone_2 type_voie voie".split()
HOSPITALISATION = "Num_Hospitalisation Id_patient identifiant_organisation Code_diagnostic Suite_diagnostic_consultation Date_Entree Jour_Hospitalisation".split()
DECES = "nom prenom sexe date_naissance code_lieu_naissance lieu_naissance pays_naissance date_deces code_lieu_deces numero_acte_deces".split()
SATISFACTION = "finess_geo region score_all_rea_ajust nb_rep_score_all_rea_ajust".split()


def fields(text):
    return [tuple(item.split(':')) for item in text.split()]


TABLES = {
    "diagnostic": fields("code_diag:STRING libelle:STRING"),
    "specialite": fields("code_specialite:STRING fonction:STRING specialite:STRING"),
    "patient": fields("id_patient:STRING sexe:STRING age:INT"),
    # Colonnes auxiliaires retirees apres enrichissement par specialite.
    "professionnel": fields("id_prof_sante:STRING categorie:STRING profession:STRING specialite:STRING"),
    "etablissement": [(name, "STRING") for name in ETABLISSEMENT],
    "activite": fields("id_prof_sante:STRING identifiant_organisation:STRING mode_exercice:STRING"),
    "consultation": fields("num_consultation:INT date_consultation:DATE id_patient:STRING code_diag:STRING id_prof_sante:STRING"),
    "hospitalisation": fields("num_hospitalisation:INT date_entree:DATE id_patient:STRING code_diag:STRING identifiant_organisation:STRING"),
    "satisfaction": fields("finess_geo:STRING identifiant_organisation:STRING annee:SMALLINT region:STRING code_region:STRING score_all_rea_ajust:DOUBLE nb_rep_score_all_rea_ajust:INT"),
    "deces": fields("deces_key:INT date_deces:DATE code_commune_deces:STRING defunt_key:INT code_departement:STRING code_region:STRING libelle_region:STRING statut_rattachement:STRING"),
    "defunt": fields("defunt_key:INT sexe:STRING"),
    "codes_postaux": fields("code_commune_insee:STRING nom_de_la_commune:STRING code_postal:STRING libelle_d_acheminement:STRING"),
    "commune": fields("code_commune_insee:STRING type_commune:STRING code_commune_parent:STRING libelle_commune:STRING code_departement:STRING code_region:STRING libelle_region:STRING statut_rattachement:STRING"),
    "region": fields("code_region:STRING region:STRING")
}
KEYS = {
    "diagnostic": ["code_diag"], "specialite": ["code_specialite"],
    "patient": ["id_patient"], "professionnel": ["id_prof_sante"],
    "etablissement": ["identifiant_organisation"],
    "activite": ["id_prof_sante", "identifiant_organisation"],
    "consultation": ["num_consultation"], "hospitalisation": ["num_hospitalisation"],
    "satisfaction": ["finess_geo", "annee"], "deces": ["deces_key"],
    "defunt": ["defunt_key"], "codes_postaux": ["code_commune_insee"],
    "commune": ["code_commune_insee"], "region": ["region"]
}
ALIASES = {
    "s1_consultation": "consultation", "s2_hospitalisation": "hospitalisation",
    "s2_etablissement": "etablissement", "s2_activite": "activite",
    "s3_satisfaction": "satisfaction", "s4_deces": "deces"
}
STEPS = {
    "01": ["diagnostic", "specialite", "codes_postaux", "commune", "region"],
    "02": ["patient"], "03": ["professionnel", "etablissement", "activite"],
    "04": ["consultation"], "05": ["hospitalisation"],
    "06": ["satisfaction"], "07": ["deces", "defunt"]
}


def names(table):
    return [name for name, unused in TABLES[table]]


def schema(spec):
    from pyspark.sql import types as T
    types = {"STRING": T.StringType, "INT": T.IntegerType,
             "SMALLINT": T.ShortType, "DOUBLE": T.DoubleType,
             "DATE": T.DateType, "BIGINT": T.LongType}
    return T.StructType([T.StructField(name, types[kind](), True)
                         for name, kind in spec])


def publication_sql(database, locations):
    """Publication isolee par execution ; aucune commande DROP/INSERT Gold."""
    import re
    if not re.match(r'^[a-z][a-z0-9_]*$', database):
        raise ValueError("Nom de base invalide")
    lines = ["CREATE DATABASE IF NOT EXISTS `%s`;" % database]
    for table in sorted(TABLES):
        path = locations[table]
        if "'" in path or ";" in path or "\n" in path:
            raise ValueError("Chemin non autorise")
        columns = ', '.join('`%s` %s' % item for item in TABLES[table])
        lines.append("CREATE EXTERNAL TABLE `%s`.`%s` (%s) STORED AS ORC LOCATION '%s';" %
                     (database, table, columns, path))
    for alias, table in sorted(ALIASES.items()):
        lines.append("CREATE VIEW `%s`.`%s` AS SELECT * FROM `%s`.`%s`;" %
                     (database, alias, database, table))
    return '\n'.join(lines) + '\n'
