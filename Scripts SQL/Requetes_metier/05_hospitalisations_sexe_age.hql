-- Age fourni dans la source patient, non recalcule a la date du sejour.
WITH sejours AS (
    SELECT h.id_patient, COALESCE(p.sexe, 'inconnu') AS sexe,
           CASE WHEN p.age IS NULL THEN 'inconnu'
                WHEN p.age < 18 THEN 'moins_18'
                WHEN p.age < 65 THEN '18_64'
                ELSE '65_et_plus' END AS tranche_age
    FROM gold.fait_hospitalisation h
    LEFT JOIN gold.dim_patient p ON h.id_patient = p.id_patient
    WHERE h.date_entree >= '2017-01-01'
      AND h.date_entree <  '2018-01-01'
), mesures AS (
    SELECT sexe, tranche_age, COUNT(*) AS hospitalisations,
           COUNT(DISTINCT id_patient) AS patients_distincts
    FROM sejours
    GROUP BY sexe, tranche_age
)
SELECT sexe, tranche_age, hospitalisations, patients_distincts,
       CASE WHEN patients_distincts > 0
            THEN ROUND(1.0 * hospitalisations / patients_distincts, 4)
            ELSE NULL END AS hospitalisations_par_patient
FROM mesures
ORDER BY sexe, tranche_age;
