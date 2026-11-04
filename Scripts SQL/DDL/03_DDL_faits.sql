CREATE DATABASE IF NOT EXISTS gold;
USE gold;

-- ORC = Optimized Row Columnar, format de stockage en colonnes, optimisé pour les requêtes analytiques.

-- CONSTELLATION

CREATE EXTERNAL TABLE IF NOT EXISTS fait_consultation (
    num_consultation INT,
    date_consultation DATE,
    id_patient INT,
    code_diag STRING,
    id_prof_sante STRING
)
STORED AS ORC
LOCATION '/gold/fait_consultation';

CREATE EXTERNAL TABLE IF NOT EXISTS fait_hospitalisation (
    num_hospitalisation INT,
    date_entree DATE,
    id_patient INT,
    code_diag STRING,
    identifiant_organisation STRING
)
STORED AS ORC
LOCATION '/gold/fait_hospitalisation';

-- SATISFACTION

CREATE EXTERNAL TABLE IF NOT EXISTS fait_satisfaction (
    identifiant_organisation STRING,
    annee SMALLINT,
    region STRING,
    score_all_rea_ajust DOUBLE,
    nb_rep_score_all_rea_ajust INT
)
STORED AS ORC
LOCATION '/gold/fait_satisfaction';

-- DECES

CREATE EXTERNAL TABLE IF NOT EXISTS fait_deces (
    deces_key INT,
    date_deces DATE,
    code_commune_deces STRING,
    defunt_key INT,
    numero_acte_deces STRING
)
STORED AS ORC
LOCATION '/gold/fait_deces';