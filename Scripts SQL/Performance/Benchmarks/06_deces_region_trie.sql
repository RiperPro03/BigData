-- Conserve et distingue les localisations sans region INSEE.
SELECT l.categorie_localisation, l.code_region, l.libelle_region, COUNT(*) AS deces
FROM gold.fait_deces_part_trie d JOIN gold.dim_lieu_deces l ON l.code_commune_insee=d.code_commune_deces
WHERE d.date_deces >= '2019-01-01' AND d.date_deces < '2020-01-01' AND d.annee_deces=2019
GROUP BY l.categorie_localisation,l.code_region,l.libelle_region
ORDER BY l.categorie_localisation,l.code_region,l.libelle_region;
