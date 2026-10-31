CREATE DATABASE IF NOT EXISTS gold;
USE gold;

-- CONSTELLATION

CREATE TABLE IF NOT EXISTS dim_temps (
    `date` DATE,
    annee SMALLINT,
    mois SMALLINT,
    jour SMALLINT
);

CREATE TABLE IF NOT EXISTS dim_patient (
    id_patient INT,
    sexe STRING,
    age INT
);

CREATE TABLE IF NOT EXISTS dim_diagnostic (
    code_diag STRING,
    libelle STRING
);

CREATE TABLE IF NOT EXISTS dim_etablissement (
    identifiant_organisation STRING,
    raison_sociale_site STRING,
    finess_site STRING,
    finess_etablissement_juridique STRING,
    code_commune STRING,
    commune STRING,
    code_postal STRING
);

CREATE TABLE IF NOT EXISTS dim_professionnel (
    id_prof_sante STRING,
    categorie STRING,
    profession STRING,
    specialite STRING
);

-- SATISFACTION

CREATE TABLE IF NOT EXISTS dim_temps_satisfaction (
    annee SMALLINT
);

CREATE TABLE IF NOT EXISTS dim_region (
    region STRING
);

-- DECES
CREATE TABLE IF NOT EXISTS dim_temps_deces (
    `date` DATE,
    annee SMALLINT,
    mois SMALLINT,
    jour SMALLINT
);

CREATE TABLE IF NOT EXISTS dim_defunt (
    defunt_key INT,
    sexe STRING,
    date_naissance DATE,
    code_lieu_naissance STRING,
    lieu_naissance STRING,
    pays_naissance STRING
);

CREATE TABLE IF NOT EXISTS dim_lieu_deces (
    code_commune_insee STRING,
    nom_de_la_commune STRING,
    code_postal STRING,
    libelle_d_acheminement STRING,
    code_departement STRING
);