USE gold;

-- CONSTELLATION
-- TODO : dim_temps

INSERT OVERWRITE TABLE dim_patient
SELECT id_patient, sexe, age
FROM silver.patient
WHERE id_patient IS NOT NULL
GROUP BY id_patient;

INSERT OVERWRITE TABLE dim_diagnostic
SELECT code_diag, libelle
FROM silver.diagnostic
WHERE code_diag IS NOT NULL
GROUP BY code_diag;

-- TODO : dim_etablissement

INSERT OVERWRITE TABLE dim_professionnel
SELECT id_prof_sante, categorie, profession, specialite
FROM silver.professionnel
WHERE id_prof_sante IS NOT NULL
GROUP BY id_prof_sante;

-- SATISFACTION
INSERT OVERWRITE TABLE dim_temps_satisfaction
SELECT DISTINCT annee
FROM silver.satisfaction
WHERE annee IS NOT NULL;

INSERT OVERWRITE TABLE dim_region
SELECT region
FROM silver.region
WHERE region IS NOT NULL
GROUP BY region;

--- DECES
--- TODO : dim_temps_deces

INSERT OVERWRITE TABLE dim_defunt
SELECT defunt_key, sexe, date_naissance, code_lieu_naissance, lieu_naissance, pays_naissance
FROM silver.defunt
WHERE defunt_key IS NOT NULL;

-- TODO : dim_lieu_deces