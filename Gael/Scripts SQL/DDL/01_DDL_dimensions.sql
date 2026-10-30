-- CONSTELLATION

CREATE TABLE dim_temps (
    `date` DATE,
    annee SMALLINT,
    mois SMALLINT,
    jour SMALLINT
);

CREATE TABLE dim_patient (
    id_patient INT,
    sexe STRING,
    age INT
);

CREATE TABLE dim_diagnostic (
    code_diag STRING,
    libelle STRING
);

CREATE TABLE dim_etablissement (
    identifiant_organisation STRING,
    raison_sociale_site STRING,
    finess_site STRING,
    finess_etablissement_juridique STRING,
    code_commune STRING,
    commune STRING,
    code_postal STRING
);

CREATE TABLE dim_professionnel (
    id_prof_sante STRING,
    categorie STRING,
    profession STRING,
    specialite STRING
);

-- SATISFACTION

CREATE TABLE dim_temps_satisfaction (
    annee SMALLINT
);

CREATE TABLE dim_region (
    region STRING
);

-- DECES
CREATE TABLE dim_temps_deces (
    `date` DATE,
    annee SMALLINT,
    mois SMALLINT,
    jour SMALLINT
);

CREATE TABLE dim_defunt (
    defunt_key INT,
    sexe STRING,
    date_naissance DATE,
    code_lieu_naissance STRING,
    lieu_naissance STRING,
    pays_naissance STRING
);

CREATE TABLE dim_lieu_deces (
    code_commune_insee STRING,
    nom_de_la_commune STRING,
    code_postal STRING,
    libelle_d_acheminement STRING,
    code_departement STRING
);