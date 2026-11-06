USE gold;

-- Les couples de Silver sont deja uniques et sans reference orpheline.
-- Pas de MAX(mode_exercice) : les conflits ont ete isoles en Silver.
-- La ponderation 1 / nombre de sites est calculee dans Power BI.
INSERT OVERWRITE TABLE pont_activite_pro
SELECT pont.id_prof_sante, pont.identifiant_organisation, pont.mode_exercice
FROM (
SELECT a.id_prof_sante, a.identifiant_organisation, a.mode_exercice
FROM silver.activite a
JOIN dim_professionnel p ON p.id_prof_sante = a.id_prof_sante
JOIN dim_etablissement e ON e.identifiant_organisation = a.identifiant_organisation
WHERE a.identifiant_organisation <> 'inconnu'
UNION ALL
-- Les professionnels sans site valide restent presents dans les analyses.
SELECT p.id_prof_sante, 'inconnu' AS identifiant_organisation, 'inconnu' AS mode_exercice
FROM dim_professionnel p
LEFT JOIN (
    SELECT DISTINCT a.id_prof_sante
    FROM silver.activite a
    JOIN dim_etablissement e ON e.identifiant_organisation = a.identifiant_organisation
    WHERE a.identifiant_organisation <> 'inconnu'
) connus ON connus.id_prof_sante = p.id_prof_sante
WHERE connus.id_prof_sante IS NULL
) pont;
