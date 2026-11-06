-- Hospitalisations et patients distincts par diagnostic en 2017.
SELECT h.code_diag, COUNT(*) AS hospitalisations, COUNT(DISTINCT h.id_patient) AS patients
FROM gold.fait_hospitalisation h
WHERE h.date_entree >= '2017-01-01' AND h.date_entree < '2018-01-01'

GROUP BY h.code_diag ORDER BY h.code_diag;
