-- Le professionnel est identifie par son pseudonyme, jamais par son nom.
WITH mesures AS (
    SELECT id_prof_sante, COUNT(*) AS consultations,
           COUNT(DISTINCT id_patient) AS patients_distincts
    FROM gold.fait_consultation
    WHERE date_consultation >= '2021-01-01'
      AND date_consultation <  '2022-01-01'
    GROUP BY id_prof_sante
)
SELECT id_prof_sante, consultations, patients_distincts,
       CASE WHEN patients_distincts > 0
            THEN ROUND(1.0 * consultations / patients_distincts, 4)
            ELSE NULL END AS consultations_par_patient
FROM mesures;
