CREATE DATABASE IF NOT EXISTS gold;
USE gold;

-- CONSTELLATION

CREATE TABLE IF NOT EXISTS fait_consultation (
    num_consultation INT,
    date_consultation DATE,
    id_patient INT,
    code_diag STRING,
    id_prof_sante STRING
);

CREATE TABLE IF NOT EXISTS fait_hospitalisation (
    num_hospitalisation INT,
    date_entree DATE,
    id_patient INT,
    code_diag STRING,
    identifiant_organisation STRING
);

-- SATISFACTION

CREATE TABLE IF NOT EXISTS fait_satisfaction (
    identifiant_organisation STRING,
    annee SMALLINT,
    region STRING,
    score_all_rea_ajust DOUBLE,
    nb_rep_score_all_rea_ajust INT
);

-- DECES

CREATE TABLE IF NOT EXISTS fait_deces (
    deces_key INT,
    date_deces DATE,
    code_commune_deces STRING,
    defunt_key INT,
    numero_acte_deces STRING
);