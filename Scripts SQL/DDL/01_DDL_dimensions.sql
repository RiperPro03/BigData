CREATE DATABASE IF NOT EXISTS gold LOCATION '/user/cloudera/chu/gold';
USE gold;

-- ORC = Optimized Row Columnar, format de stockage en colonnes, optimisé pour les requêtes analytiques.

-- CONSTELLATION

CREATE EXTERNAL TABLE IF NOT EXISTS dim_temps (
    `date` DATE,
    annee SMALLINT,
    mois SMALLINT,
    jour SMALLINT
)
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/dim_temps';

CREATE EXTERNAL TABLE IF NOT EXISTS dim_patient (
    id_patient STRING,
    sexe STRING,
    age INT
)
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/dim_patient';

CREATE EXTERNAL TABLE IF NOT EXISTS dim_diagnostic (
    code_diag STRING,
    libelle STRING
)
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/dim_diagnostic';

CREATE EXTERNAL TABLE IF NOT EXISTS dim_etablissement (
    identifiant_organisation STRING,
    raison_sociale_site STRING,
    finess_site STRING,
    finess_etablissement_juridique STRING,
    code_commune STRING,
    commune STRING,
    code_postal STRING
)
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/dim_etablissement';

CREATE EXTERNAL TABLE IF NOT EXISTS dim_professionnel (
    id_prof_sante STRING,
    categorie STRING,
    profession STRING,
    specialite STRING
)
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/dim_professionnel';

-- SATISFACTION

CREATE EXTERNAL TABLE IF NOT EXISTS dim_temps_satisfaction (
    annee SMALLINT
)
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/dim_temps_satisfaction';

CREATE EXTERNAL TABLE IF NOT EXISTS dim_region (
    region STRING
)
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/dim_region';

-- DECES
CREATE EXTERNAL TABLE IF NOT EXISTS dim_temps_deces (
    `date` DATE,
    annee SMALLINT,
    mois SMALLINT,
    jour SMALLINT
)
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/dim_temps_deces';

CREATE EXTERNAL TABLE IF NOT EXISTS dim_defunt (
    defunt_key INT,
    sexe STRING
)
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/dim_defunt';

CREATE EXTERNAL TABLE IF NOT EXISTS dim_lieu_deces (
    code_commune_insee STRING,
    nom_de_la_commune STRING,
    code_postal STRING,
    libelle_d_acheminement STRING,
    code_departement STRING,
    code_region STRING,
    libelle_region STRING,
    categorie_localisation STRING
)
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/dim_lieu_deces';
