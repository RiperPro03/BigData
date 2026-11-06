-- Jointure supplementaire pour mesurer les buckets ; ne remplace pas l'indicateur regional.
SELECT p.sexe, COUNT(*) AS deces
FROM gold.fait_deces_bucket d JOIN gold.dim_defunt_bucket p ON p.defunt_key=d.defunt_key
WHERE d.date_deces >= '2019-01-01' AND d.date_deces < '2020-01-01'
GROUP BY p.sexe ORDER BY p.sexe;
