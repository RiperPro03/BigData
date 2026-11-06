-- Attribution ponderee 1 / nombre de sites, incluant le site inconnu.
SELECT p.identifiant_organisation,
       ROUND(SUM(CAST(1 AS DECIMAL(20,10)) / p.nombre_sites), 6) AS consultations_ponderees,
       COUNT(DISTINCT c.id_patient) AS patients
FROM gold.fait_consultation c
JOIN (
    SELECT id_prof_sante, identifiant_organisation,
           COUNT(*) OVER (PARTITION BY id_prof_sante) AS nombre_sites
    FROM gold.pont_activite_pro
) p ON p.id_prof_sante = c.id_prof_sante
WHERE c.date_consultation >= '2021-01-01' AND c.date_consultation < '2022-01-01'

GROUP BY p.identifiant_organisation
ORDER BY p.identifiant_organisation LIMIT 20;
