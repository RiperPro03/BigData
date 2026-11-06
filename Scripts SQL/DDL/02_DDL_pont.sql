CREATE DATABASE IF NOT EXISTS gold LOCATION '/user/cloudera/chu/gold';
USE gold;

-- CONSTELLATION

-- ORC = Optimized Row Columnar, format de stockage en colonnes, optimisé pour les requêtes analytiques.

CREATE EXTERNAL TABLE IF NOT EXISTS pont_activite_pro (
    id_prof_sante STRING,
    identifiant_organisation STRING,
    mode_exercice STRING
)
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/pont_activite_pro';
