-- Hospitalisations et patients distincts par diagnostic sur [debut, fin[.
WITH mesures AS (
    SELECT code_diag, COUNT(*) AS hospitalisations,
           COUNT(DISTINCT id_patient) AS patients_distincts
    FROM gold.fait_hospitalisation
    WHERE date_entree >= '2017-01-01'
      AND date_entree <  '2018-01-01'
    GROUP BY code_diag
)
SELECT m.code_diag, d.libelle, m.hospitalisations, m.patients_distincts,
       CASE WHEN m.patients_distincts > 0
            THEN ROUND(1.0 * m.hospitalisations / m.patients_distincts, 4)
            ELSE NULL END AS hospitalisations_par_patient
FROM mesures m
LEFT JOIN gold.dim_diagnostic d ON m.code_diag = d.code_diag
ORDER BY m.code_diag;
