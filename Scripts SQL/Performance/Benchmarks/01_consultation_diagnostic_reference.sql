-- Consultations et patients distincts pour un diagnostic pendant 2021.
SELECT COUNT(*) AS consultations, COUNT(DISTINCT c.id_patient) AS patients
FROM gold.fait_consultation c
WHERE c.date_consultation >= '2021-01-01' AND c.date_consultation < '2022-01-01'
  AND c.code_diag = 'M4157' ;
