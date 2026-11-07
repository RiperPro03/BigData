-- Hospitalisations et patients distincts sur [debut, fin[.
WITH mesures AS (
    SELECT COUNT(*) AS hospitalisations,
           COUNT(DISTINCT id_patient) AS patients_distincts
    FROM gold.fait_hospitalisation
    WHERE date_entree >= '2017-01-01'
      AND date_entree <  '2018-01-01'
)
SELECT hospitalisations, patients_distincts,
       CASE WHEN patients_distincts > 0
            THEN ROUND(1.0 * hospitalisations / patients_distincts, 4)
            ELSE NULL END AS hospitalisations_par_patient
FROM mesures;
