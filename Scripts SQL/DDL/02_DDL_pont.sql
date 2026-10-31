CREATE DATABASE IF NOT EXISTS gold;
USE gold;

-- CONSTELLATION

CREATE TABLE IF NOT EXISTS pont_activite_pro (
    id_prof_sante STRING,
    identifiant_organisation STRING,
    mode_exercice STRING
);