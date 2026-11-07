-- Consultations attribuees aux sites sur la periode [debut, fin[.
-- Un professionnel rattache a N sites repart chaque consultation a 1/N.
-- Ceci est une estimation : le site reel de la consultation n'est pas connu.
-- Un patient peut etre compte sur plusieurs sites attribues.
WITH sites AS (
    SELECT id_prof_sante, identifiant_organisation,
           COUNT(*) OVER (PARTITION BY id_prof_sante) AS nombre_sites
    FROM gold.pont_activite_pro
), mesures AS (
    SELECT s.identifiant_organisation,
           SUM(CAST(1.0 AS DOUBLE) / s.nombre_sites) AS consultations_ponderees,
           COUNT(DISTINCT c.id_patient) AS patients_distincts
    FROM gold.fait_consultation c
    JOIN sites s ON c.id_prof_sante = s.id_prof_sante
    WHERE c.date_consultation >= '2021-01-01'
      AND c.date_consultation <  '2022-01-01'
    GROUP BY s.identifiant_organisation
)
SELECT identifiant_organisation,
       ROUND(consultations_ponderees, 8) AS consultations_ponderees,
       patients_distincts,
       CASE WHEN patients_distincts > 0
            THEN ROUND(consultations_ponderees / patients_distincts, 4)
            ELSE NULL END AS consultations_par_patient
FROM mesures
ORDER BY identifiant_organisation;
