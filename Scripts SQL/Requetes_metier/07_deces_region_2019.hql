-- Indicateur optionnel : conserver les deces sans region connue.
SELECT COALESCE(l.categorie_localisation, 'REFERENTIEL_ABSENT') AS categorie_localisation,
       l.code_region, l.libelle_region, COUNT(*) AS nombre_deces
FROM gold.fait_deces d
LEFT JOIN gold.dim_lieu_deces l ON d.code_commune_deces = l.code_commune_insee
WHERE d.date_deces >= '2019-01-01'
  AND d.date_deces <  '2020-01-01'
GROUP BY COALESCE(l.categorie_localisation, 'REFERENTIEL_ABSENT'),
         l.code_region, l.libelle_region
ORDER BY categorie_localisation, l.code_region, l.libelle_region;
