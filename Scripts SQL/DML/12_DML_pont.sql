USE gold;

INSERT OVERWRITE TABLE pont_activite_pro
SELECT pont.id_prof_sante,
       pont.identifiant_organisation,
       pont.mode_exercice
FROM (

    -- Les couples valides
    -- On part du fichier d'activité (qui exerce où) et on garde seulement les lignes dont le professionnel ET l'établissement existent dans leurs dimensions.
    SELECT activite.id_prof_sante,
           activite.identifiant_organisation,
           MAX(activite.mode_exercice) AS mode_exercice    -- MAX() = une seule valeur si le couple est en double
    FROM silver.s2_activite activite
    JOIN dim_professionnel professionnel
         ON professionnel.id_prof_sante = activite.id_prof_sante
    JOIN dim_etablissement etablissement
         ON etablissement.identifiant_organisation = activite.identifiant_organisation
    WHERE activite.identifiant_organisation <> 'inconnu'
    GROUP BY activite.id_prof_sante, activite.identifiant_organisation

    UNION ALL -- ALL prend les 2 requêtes boutà bout sans supprimer les doublons
    -- la première requête ne doit pas supprimer les professionnels sans établissement connu, sinon ils disparaîtraient du calcul par établissement

    -- Les professionnels qui n'ont aucun établissement connu
    SELECT professionnel.id_prof_sante,
           'inconnu' AS identifiant_organisation,
           'inconnu' AS mode_exercice
    FROM dim_professionnel professionnel
    LEFT JOIN (
        SELECT DISTINCT activite.id_prof_sante
        FROM silver.s2_activite activite
        JOIN dim_etablissement etablissement
             ON etablissement.identifiant_organisation = activite.identifiant_organisation
        WHERE activite.identifiant_organisation <> 'inconnu'
    ) professionnels_avec_etablissement
         ON professionnels_avec_etablissement.id_prof_sante = professionnel.id_prof_sante
    WHERE professionnels_avec_etablissement.id_prof_sante IS NULL

) pont;