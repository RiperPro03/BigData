USE gold;

-- CONSULTATION

FROM (
    -- controle_cles : chaque consultation + les témoins de ses 4 clés
    SELECT consultation.num_consultation,
           consultation.date_consultation,
           consultation.id_patient,
           consultation.code_diag,
           consultation.id_prof_sante,
           calendrier.`date`           AS date_trouvee,
           patient.id_patient          AS patient_trouve,
           diagnostic.code_diag        AS diagnostic_trouve,
           professionnel.id_prof_sante AS professionnel_trouve
    FROM silver.consultation consultation
    LEFT JOIN dim_temps calendrier
           ON calendrier.`date`           = consultation.date_consultation
    LEFT JOIN dim_patient patient
           ON patient.id_patient          = consultation.id_patient
    LEFT JOIN dim_diagnostic diagnostic
           ON diagnostic.code_diag        = consultation.code_diag
    LEFT JOIN dim_professionnel professionnel
           ON professionnel.id_prof_sante = consultation.id_prof_sante
) controle_cles

INSERT OVERWRITE TABLE fait_consultation
SELECT controle_cles.num_consultation,
       controle_cles.date_consultation,
       controle_cles.id_patient,
       controle_cles.code_diag,
       controle_cles.id_prof_sante
WHERE controle_cles.num_consultation IS NOT NULL
  AND controle_cles.date_trouvee IS NOT NULL
  AND controle_cles.patient_trouve IS NOT NULL
  AND controle_cles.diagnostic_trouve IS NOT NULL
  AND controle_cles.professionnel_trouve IS NOT NULL

-- Consultations refusées, avec le motif et l'heure
INSERT OVERWRITE TABLE rejets_fait_consultation
SELECT CAST(controle_cles.num_consultation  AS STRING),
       CAST(controle_cles.date_consultation AS STRING),
       controle_cles.id_patient,
       controle_cles.code_diag,
       controle_cles.id_prof_sante,
       -- motif : un texte par clé manquante, assemblés avec une virgule
       concat_ws(', ',
           CASE WHEN controle_cles.num_consultation IS NULL THEN 'num_consultation absent' END,
           CASE WHEN controle_cles.date_trouvee IS NULL THEN 'date absente de dim_temps' END,
           CASE WHEN controle_cles.patient_trouve IS NULL THEN 'patient absent de dim_patient' END,
           CASE WHEN controle_cles.diagnostic_trouve IS NULL THEN 'diagnostic absent de dim_diagnostic' END,
           CASE WHEN controle_cles.professionnel_trouve IS NULL THEN 'professionnel absent de dim_professionnel' END),
       from_unixtime(unix_timestamp()) -- horodatage du chargement
WHERE controle_cles.num_consultation IS NULL
   OR controle_cles.date_trouvee IS NULL
   OR controle_cles.patient_trouve IS NULL
   OR controle_cles.diagnostic_trouve IS NULL
   OR controle_cles.professionnel_trouve IS NULL;

-- HOSPITALISATION

FROM (
    SELECT hospitalisation.num_hospitalisation,
           hospitalisation.date_entree,
           hospitalisation.id_patient,
           hospitalisation.code_diag,
           hospitalisation.identifiant_organisation,
           calendrier.`date` AS date_trouvee,
           -- accents grave sur "date" car c'est un mot réservé
           patient.id_patient AS patient_trouve,
           diagnostic.code_diag AS diagnostic_trouve,
           etablissement.identifiant_organisation AS etablissement_trouve
    FROM silver.hospitalisation hospitalisation
    LEFT JOIN dim_temps calendrier
           ON calendrier.`date` = hospitalisation.date_entree
    LEFT JOIN dim_patient patient
           ON patient.id_patient = hospitalisation.id_patient
    LEFT JOIN dim_diagnostic diagnostic
           ON diagnostic.code_diag = hospitalisation.code_diag
    LEFT JOIN dim_etablissement etablissement
           ON etablissement.identifiant_organisation = hospitalisation.identifiant_organisation
) controle_cles

INSERT OVERWRITE TABLE fait_hospitalisation
SELECT controle_cles.num_hospitalisation,
       controle_cles.date_entree,
       controle_cles.id_patient,
       controle_cles.code_diag,
       controle_cles.identifiant_organisation
WHERE controle_cles.num_hospitalisation IS NOT NULL
  AND controle_cles.date_trouvee IS NOT NULL
  AND controle_cles.patient_trouve IS NOT NULL
  AND controle_cles.diagnostic_trouve IS NOT NULL
  AND controle_cles.etablissement_trouve IS NOT NULL

INSERT OVERWRITE TABLE rejets_fait_hospitalisation
SELECT CAST(controle_cles.num_hospitalisation AS STRING),
       CAST(controle_cles.date_entree AS STRING),
       controle_cles.id_patient,
       controle_cles.code_diag,
       controle_cles.identifiant_organisation,
       concat_ws(', ', -- concatène plusieurs motifs avec une virgule comme séparateur
           CASE WHEN controle_cles.num_hospitalisation IS NULL THEN 'num_hospitalisation absent' END,
           CASE WHEN controle_cles.date_trouvee IS NULL THEN 'date absente de dim_temps' END,
           CASE WHEN controle_cles.patient_trouve IS NULL THEN 'patient absent de dim_patient' END,
           CASE WHEN controle_cles.diagnostic_trouve IS NULL THEN 'diagnostic absent de dim_diagnostic' END,
           CASE WHEN controle_cles.etablissement_trouve IS NULL THEN 'etablissement absent de dim_etablissement' END),
       from_unixtime(unix_timestamp())
WHERE controle_cles.num_hospitalisation IS NULL
   OR controle_cles.date_trouvee IS NULL
   OR controle_cles.patient_trouve IS NULL
   OR controle_cles.diagnostic_trouve IS NULL
   OR controle_cles.etablissement_trouve IS NULL;


-- DECES

FROM (
    SELECT deces.deces_key,
           deces.date_deces,
           deces.code_commune_deces,
           deces.defunt_key,
           calendrier_deces.`date` AS date_trouvee,
           lieu.code_commune_insee AS lieu_trouve,
           defunt.defunt_key AS defunt_trouve
    FROM silver.deces deces
    LEFT JOIN dim_defunt defunt
           ON defunt.defunt_key = deces.defunt_key
    LEFT JOIN dim_temps_deces calendrier_deces
           ON calendrier_deces.`date` = deces.date_deces
    LEFT JOIN dim_lieu_deces lieu
           ON lieu.code_commune_insee = deces.code_commune_deces
) controle_cles

INSERT OVERWRITE TABLE fait_deces
SELECT controle_cles.deces_key,
       controle_cles.date_deces,
       controle_cles.code_commune_deces,
       controle_cles.defunt_key
WHERE controle_cles.deces_key IS NOT NULL
  AND controle_cles.defunt_key IS NOT NULL
  AND controle_cles.defunt_trouve IS NOT NULL
  AND controle_cles.date_trouvee IS NOT NULL
  AND controle_cles.lieu_trouve IS NOT NULL

INSERT OVERWRITE TABLE rejets_fait_deces
SELECT CAST(controle_cles.deces_key  AS STRING),
       CAST(controle_cles.date_deces AS STRING),
       controle_cles.code_commune_deces,
       CAST(controle_cles.defunt_key AS STRING),
       concat_ws(', ',
           CASE WHEN controle_cles.deces_key IS NULL THEN 'deces_key absent' END,
           CASE WHEN controle_cles.defunt_key IS NULL OR controle_cles.defunt_trouve IS NULL THEN 'defunt absent de dim_defunt' END,
           CASE WHEN controle_cles.date_trouvee IS NULL THEN 'date absente de dim_temps_deces' END,
           CASE WHEN controle_cles.lieu_trouve IS NULL THEN 'lieu absent de dim_lieu_deces' END),
       from_unixtime(unix_timestamp())
WHERE controle_cles.deces_key IS NULL
   OR controle_cles.defunt_key IS NULL
   OR controle_cles.defunt_trouve IS NULL
   OR controle_cles.date_trouvee IS NULL
   OR controle_cles.lieu_trouve IS NULL;

-- SATISFACTION

FROM (
    SELECT satisfaction.identifiant_organisation,
           satisfaction.finess_geo,
           satisfaction.annee,
           satisfaction.region,
           satisfaction.score_all_rea_ajust,
           satisfaction.nb_rep_score_all_rea_ajust,
           annees.annee AS annee_trouvee,
           regions.region AS region_trouvee
    FROM silver.satisfaction satisfaction
    LEFT JOIN dim_temps_satisfaction annees
           ON annees.annee   = satisfaction.annee
    LEFT JOIN dim_region regions
           ON regions.region = satisfaction.region
) controle_cles

INSERT OVERWRITE TABLE fait_satisfaction
SELECT controle_cles.identifiant_organisation,
       controle_cles.annee,
       controle_cles.region,
       controle_cles.score_all_rea_ajust,
       controle_cles.nb_rep_score_all_rea_ajust
WHERE controle_cles.finess_geo IS NOT NULL
  AND controle_cles.annee_trouvee IS NOT NULL
  AND controle_cles.region_trouvee IS NOT NULL

INSERT OVERWRITE TABLE rejets_fait_satisfaction
SELECT controle_cles.identifiant_organisation,
       CAST(controle_cles.annee AS STRING),
       controle_cles.region,
       CAST(controle_cles.score_all_rea_ajust AS STRING),
       CAST(controle_cles.nb_rep_score_all_rea_ajust AS STRING),
       concat_ws(', ',
           CASE WHEN controle_cles.finess_geo IS NULL THEN 'finess_geo absent' END,
           CASE WHEN controle_cles.annee_trouvee IS NULL THEN 'annee absente de dim_temps_satisfaction' END,
           CASE WHEN controle_cles.region_trouvee IS NULL THEN 'region absente de dim_region' END),
       from_unixtime(unix_timestamp())
WHERE controle_cles.finess_geo IS NULL
   OR controle_cles.annee_trouvee IS NULL
   OR controle_cles.region_trouvee IS NULL;
