USE gold;

-- ORC = Optimized Row Columnar, format de stockage en colonnes, optimisé pour les requêtes analytiques.

-- CONSTELLATION

CREATE EXTERNAL TABLE IF NOT EXISTS rejets_fait_consultation (
    num_consultation STRING,
    date_consultation STRING,
    id_patient STRING,
    code_diag STRING,
    id_prof_sante STRING,
    motif STRING,
    horodatage STRING
)
STORED AS ORC
LOCATION '/gold/rejets_fait_consultation';

CREATE EXTERNAL TABLE IF NOT EXISTS rejets_fait_hospitalisation (
    num_hospitalisation STRING,
    date_entree STRING,
    id_patient STRING,
    code_diag STRING,
    identifiant_organisation STRING,
    motif STRING,
    horodatage STRING
)
STORED AS ORC
LOCATION '/gold/rejets_fait_hospitalisation';

-- SATISFACTION

CREATE EXTERNAL TABLE IF NOT EXISTS rejets_fait_satisfaction (
    identifiant_organisation STRING,
    annee STRING,
    region STRING,
    score_all_rea_ajust STRING,
    nb_rep_score_all_rea_ajust STRING,
    motif STRING,
    horodatage STRING
)
STORED AS ORC
LOCATION '/gold/rejets_fait_satisfaction';

-- DECES

CREATE EXTERNAL TABLE IF NOT EXISTS rejets_fait_deces (
    deces_key STRING,
    date_deces STRING,
    code_commune_deces STRING,
    defunt_key STRING,
    numero_acte_deces STRING,
    motif STRING,
    horodatage STRING
)
STORED AS ORC
LOCATION '/gold/rejets_fait_deces';