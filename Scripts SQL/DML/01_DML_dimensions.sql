USE gold;

-- CONSTELLATION
INSERT OVERWRITE TABLE dim_temps
SELECT calendrier.jour_date,                            -- date
       CAST(year(calendrier.jour_date)  AS SMALLINT),   -- annee
       CAST(month(calendrier.jour_date) AS SMALLINT),   -- mois
       CAST(day(calendrier.jour_date)   AS SMALLINT)    -- jour
FROM (
    SELECT CAST(date_add(CAST(bornes.date_debut AS STRING),
                         numerotation.nb_jours) AS DATE) AS jour_date
    FROM (
        -- Calcul des bornes
        SELECT MIN(dates_des_faits.date_evenement) AS date_debut,
               MAX(dates_des_faits.date_evenement) AS date_fin
        FROM (
            SELECT date_consultation AS date_evenement FROM silver.consultation
            UNION ALL
            SELECT date_entree       AS date_evenement FROM silver.hospitalisation
        ) dates_des_faits
    ) bornes

    -- Calcul des jours à couvrir

    -- datediff(date_fin, date_debut) : calcul du nombre de jours entre les deux bornes
    -- space() : crée un texte contenant autant d'espaces que de jours à couvrir
    -- split() : transforme le texte en tableau de chaînes de caractères
    -- posexplode() : transforme le tableau en lignes, avec un numéro de position (nb_jours) et la valeur (inutile)
    -- LATERAL VIEW : permet de "coller" les lgines générées par posexplode()
    LATERAL VIEW posexplode(split(space(datediff(bornes.date_fin, bornes.date_debut)), ' '))
        numerotation AS nb_jours, valeur_inutilisee
) calendrier;

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
INSERT OVERWRITE TABLE dim_temps_deces
SELECT calendrier.jour_date,                                    -- -> date
       CAST(year(calendrier.jour_date)  AS SMALLINT),           -- -> annee
       CAST(month(calendrier.jour_date) AS SMALLINT),           -- -> mois
       CAST(day(calendrier.jour_date)   AS SMALLINT)            -- -> jour
FROM (
    SELECT CAST(date_add(CAST(bornes.date_debut AS STRING),
                         numerotation.nb_jours) AS DATE) AS jour_date
    FROM (
        SELECT MIN(date_deces) AS date_debut,
               MAX(date_deces) AS date_fin
        FROM silver.deces
    ) bornes

    LATERAL VIEW posexplode(split(space(datediff(bornes.date_fin, bornes.date_debut)), ' '))
        numerotation AS nb_jours, valeur_inutilisee
) calendrier;

INSERT OVERWRITE TABLE dim_defunt
SELECT defunt_key, sexe, date_naissance, code_lieu_naissance, lieu_naissance, pays_naissance
FROM silver.defunt
WHERE defunt_key IS NOT NULL;

-- TODO : dim_lieu_deces