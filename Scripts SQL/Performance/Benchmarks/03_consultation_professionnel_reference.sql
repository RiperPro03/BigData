-- Consultations et patients distincts par professionnel pseudonymise.
SELECT c.id_prof_sante, COUNT(*) AS consultations, COUNT(DISTINCT c.id_patient) AS patients
FROM gold.fait_consultation c
WHERE c.date_consultation >= '2021-01-01' AND c.date_consultation < '2022-01-01'

GROUP BY c.id_prof_sante
ORDER BY c.id_prof_sante LIMIT 20;
