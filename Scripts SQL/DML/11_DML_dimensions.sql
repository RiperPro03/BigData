USE gold;

-- Ressources de session : noeud YARN de 4096 Mio, conteneur maximal de 3072 Mio.
-- Aucun changement de la configuration globale du cluster.
SET hive.execution.engine=mr;
SET mapreduce.map.memory.mb=1024;
SET mapreduce.map.java.opts=-Xmx768m -Djava.net.preferIPv4Stack=true;
SET mapreduce.reduce.memory.mb=1536;
SET mapreduce.reduce.java.opts=-Xmx1024m -Djava.net.preferIPv4Stack=true;
SET mapreduce.job.reduce.slowstart.completedmaps=1.0;
SET hive.exec.reducers.max=8;


-- Silver a deja qualifie les cles et les references. Gold conserve ce grain.
-- Calendrier des soins : une ligne par jour entre les bornes des evenements.
INSERT OVERWRITE TABLE dim_temps
SELECT CAST(date_add(CAST(b.date_debut AS STRING), n.position) AS DATE),
       CAST(year(date_add(CAST(b.date_debut AS STRING), n.position)) AS SMALLINT),
       CAST(month(date_add(CAST(b.date_debut AS STRING), n.position)) AS SMALLINT),
       CAST(day(date_add(CAST(b.date_debut AS STRING), n.position)) AS SMALLINT)
FROM (
    SELECT MIN(d.date_evenement) AS date_debut, MAX(d.date_evenement) AS date_fin
    FROM (
        SELECT date_consultation AS date_evenement FROM silver.consultation
        UNION ALL
        SELECT date_entree AS date_evenement FROM silver.hospitalisation
    ) d
) b
LATERAL VIEW posexplode(split(space(datediff(b.date_fin, b.date_debut)), ' ')) n AS position, valeur;

-- HMAC integral : STRING. L'age est celui fourni par la source patient.
INSERT OVERWRITE TABLE dim_patient
SELECT id_patient, sexe, age FROM silver.patient;

INSERT OVERWRITE TABLE dim_diagnostic
SELECT code_diag, libelle FROM silver.diagnostic;

-- Pas de choix arbitraire par row_number : Silver garantit une cle unique.
INSERT OVERWRITE TABLE dim_etablissement
SELECT e.identifiant_organisation, e.raison_sociale_site, e.finess_site,
       e.finess_etablissement_juridique, e.code_commune, e.commune, e.code_postal
FROM (
SELECT identifiant_organisation, raison_sociale_site, finess_site,
       finess_etablissement_juridique, code_commune, commune, code_postal
FROM silver.etablissement
WHERE identifiant_organisation <> 'inconnu'
UNION ALL
SELECT 'inconnu' AS identifiant_organisation, 'inconnu' AS raison_sociale_site,
       CAST(NULL AS STRING) AS finess_site,
       CAST(NULL AS STRING) AS finess_etablissement_juridique,
       CAST(NULL AS STRING) AS code_commune, CAST(NULL AS STRING) AS commune,
       CAST(NULL AS STRING) AS code_postal
FROM (SELECT COUNT(*) AS n FROM silver.etablissement) singleton
) e;

INSERT OVERWRITE TABLE dim_professionnel
SELECT id_prof_sante, categorie, profession, specialite FROM silver.professionnel;

INSERT OVERWRITE TABLE dim_temps_satisfaction
SELECT DISTINCT annee FROM silver.satisfaction;

-- Les libelles observes non resolus (ex. Ocean Indien) restent presents.
INSERT OVERWRITE TABLE dim_region
SELECT region FROM silver.region;

-- Calendrier separe des deces, dont l'historique est plus ancien.
INSERT OVERWRITE TABLE dim_temps_deces
SELECT CAST(date_add(CAST(b.date_debut AS STRING), n.position) AS DATE),
       CAST(year(date_add(CAST(b.date_debut AS STRING), n.position)) AS SMALLINT),
       CAST(month(date_add(CAST(b.date_debut AS STRING), n.position)) AS SMALLINT),
       CAST(day(date_add(CAST(b.date_debut AS STRING), n.position)) AS SMALLINT)
FROM (
    SELECT MIN(date_deces) AS date_debut, MAX(date_deces) AS date_fin
    FROM silver.deces
) b
LATERAL VIEW posexplode(split(space(datediff(b.date_fin, b.date_debut)), ' ')) n AS position, valeur;

-- Choix du groupe : aucun age, date/lieu de naissance ou numero d'acte.
-- Une occurrence de defunt par occurrence de deces acceptee en Silver.
INSERT OVERWRITE TABLE dim_defunt
SELECT defunt_key, sexe FROM silver.defunt;

-- Une ligne par code du lieu de deces, meme sans commune postale connue.
-- Le COG 2024 utilise par Silver n'est pas une geographie historique de 2019.
-- NULL dans code_region signifie qu'aucune region INSEE n'a ete attribuee.
-- Le libelle de remplacement n'est jamais utilise comme faux code INSEE.
INSERT OVERWRITE TABLE dim_lieu_deces
SELECT d.code_commune_deces, p.nom_de_la_commune, p.code_postal,
       p.libelle_d_acheminement, d.code_departement, d.code_region,
       COALESCE(d.libelle_region, 'Region non resolue'),
       CASE WHEN d.code_region IS NOT NULL THEN 'REGION_FRANCAISE'
            WHEN substr(d.code_commune_deces, 1, 2) = '99' THEN 'CODE_PAYS'
            WHEN d.code_departement IN ('975','977','978','984','986','987','988')
                 THEN 'OUTRE_MER_HORS_REGIONS'
            ELSE 'NON_RESOLU' END
FROM (
    SELECT DISTINCT code_commune_deces, code_departement, code_region, libelle_region
    FROM silver.deces
) d
LEFT JOIN silver.codes_postaux p ON p.code_commune_insee = d.code_commune_deces;
