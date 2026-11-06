-- L'age est l'attribut de la source patient, pas un age recalcule au sejour.
SELECT p.sexe,
       CASE WHEN p.age < 18 THEN 'moins_18' WHEN p.age < 65 THEN '18_64'
            WHEN p.age >= 65 THEN '65_et_plus' ELSE 'inconnu' END AS tranche_age,
       COUNT(*) AS hospitalisations, COUNT(DISTINCT h.id_patient) AS patients
FROM gold.fait_hospitalisation h JOIN gold.dim_patient p ON p.id_patient=h.id_patient
WHERE h.date_entree >= '2017-01-01' AND h.date_entree < '2018-01-01'

GROUP BY p.sexe, CASE WHEN p.age < 18 THEN 'moins_18' WHEN p.age < 65 THEN '18_64'
                     WHEN p.age >= 65 THEN '65_et_plus' ELSE 'inconnu' END
ORDER BY p.sexe, tranche_age;
