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


-- Lecture seule. Lancer apres le DML concerne. Les anomalies doivent valoir 0.

-- Un nombre de rejets non nul doit etre explique avant de poursuivre.

SELECT 'consultation' AS controle,
       SUM(CASE WHEN origine='silver' THEN n ELSE 0 END) AS lignes_silver,
       SUM(CASE WHEN origine='gold' THEN n ELSE 0 END) AS lignes_gold,
       SUM(CASE WHEN origine='rejets' THEN n ELSE 0 END) AS lignes_rejetees,
       SUM(CASE WHEN origine='silver' THEN n ELSE -n END) AS ecart_attendu_zero
FROM (
    SELECT 'silver' AS origine, COUNT(*) AS n FROM silver.consultation
    UNION ALL SELECT 'gold' AS origine, COUNT(*) AS n FROM fait_consultation
    UNION ALL SELECT 'rejets' AS origine, COUNT(*) AS n FROM rejets_fait_consultation
) bilan;

SELECT 'hospitalisation' AS controle,
       SUM(CASE WHEN origine='silver' THEN n ELSE 0 END) AS lignes_silver,
       SUM(CASE WHEN origine='gold' THEN n ELSE 0 END) AS lignes_gold,
       SUM(CASE WHEN origine='rejets' THEN n ELSE 0 END) AS lignes_rejetees,
       SUM(CASE WHEN origine='silver' THEN n ELSE -n END) AS ecart_attendu_zero
FROM (
    SELECT 'silver' AS origine, COUNT(*) AS n FROM silver.hospitalisation
    UNION ALL SELECT 'gold' AS origine, COUNT(*) AS n FROM fait_hospitalisation
    UNION ALL SELECT 'rejets' AS origine, COUNT(*) AS n FROM rejets_fait_hospitalisation
) bilan;

SELECT 'deces' AS controle,
       SUM(CASE WHEN origine='silver' THEN n ELSE 0 END) AS lignes_silver,
       SUM(CASE WHEN origine='gold' THEN n ELSE 0 END) AS lignes_gold,
       SUM(CASE WHEN origine='rejets' THEN n ELSE 0 END) AS lignes_rejetees,
       SUM(CASE WHEN origine='silver' THEN n ELSE -n END) AS ecart_attendu_zero
FROM (
    SELECT 'silver' AS origine, COUNT(*) AS n FROM silver.deces
    UNION ALL SELECT 'gold' AS origine, COUNT(*) AS n FROM fait_deces
    UNION ALL SELECT 'rejets' AS origine, COUNT(*) AS n FROM rejets_fait_deces
) bilan;

SELECT 'satisfaction' AS controle,
       SUM(CASE WHEN origine='silver' THEN n ELSE 0 END) AS lignes_silver,
       SUM(CASE WHEN origine='gold' THEN n ELSE 0 END) AS lignes_gold,
       SUM(CASE WHEN origine='rejets' THEN n ELSE 0 END) AS lignes_rejetees,
       SUM(CASE WHEN origine='silver' THEN n ELSE -n END) AS ecart_attendu_zero
FROM (
    SELECT 'silver' AS origine, COUNT(*) AS n FROM silver.satisfaction
    UNION ALL SELECT 'gold' AS origine, COUNT(*) AS n FROM fait_satisfaction
    UNION ALL SELECT 'rejets' AS origine, COUNT(*) AS n FROM rejets_fait_satisfaction
) bilan;

SELECT 'dim_patient_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT id_patient FROM dim_patient GROUP BY id_patient HAVING COUNT(*) > 1) d;

SELECT 'dim_diagnostic_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT code_diag FROM dim_diagnostic GROUP BY code_diag HAVING COUNT(*) > 1) d;

SELECT 'dim_professionnel_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT id_prof_sante FROM dim_professionnel GROUP BY id_prof_sante HAVING COUNT(*) > 1) d;

SELECT 'dim_etablissement_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT identifiant_organisation FROM dim_etablissement GROUP BY identifiant_organisation HAVING COUNT(*) > 1) d;

SELECT 'dim_defunt_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT defunt_key FROM dim_defunt GROUP BY defunt_key HAVING COUNT(*) > 1) d;

SELECT 'dim_lieu_deces_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT code_commune_insee FROM dim_lieu_deces GROUP BY code_commune_insee HAVING COUNT(*) > 1) d;

SELECT 'dim_temps_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT `date` FROM dim_temps GROUP BY `date` HAVING COUNT(*) > 1) d;

SELECT 'dim_temps_deces_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT `date` FROM dim_temps_deces GROUP BY `date` HAVING COUNT(*) > 1) d;

SELECT 'dim_temps_satisfaction_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT annee FROM dim_temps_satisfaction GROUP BY annee HAVING COUNT(*) > 1) d;

SELECT 'dim_region_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT region FROM dim_region GROUP BY region HAVING COUNT(*) > 1) d;

SELECT 'pont_activite_pro_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT id_prof_sante, identifiant_organisation FROM pont_activite_pro GROUP BY id_prof_sante, identifiant_organisation HAVING COUNT(*) > 1) d;

SELECT 'fait_consultation_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT num_consultation FROM fait_consultation GROUP BY num_consultation HAVING COUNT(*) > 1) d;

SELECT 'fait_hospitalisation_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT num_hospitalisation FROM fait_hospitalisation GROUP BY num_hospitalisation HAVING COUNT(*) > 1) d;

SELECT 'fait_deces_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT deces_key FROM fait_deces GROUP BY deces_key HAVING COUNT(*) > 1) d;

SELECT 'fait_satisfaction_doublons' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT identifiant_organisation, annee FROM fait_satisfaction GROUP BY identifiant_organisation, annee HAVING COUNT(*) > 1) d;

SELECT 'fait_consultation_id_patient_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM fait_consultation f LEFT JOIN dim_patient d ON d.id_patient=f.id_patient WHERE d.id_patient IS NULL;

SELECT 'fait_consultation_code_diag_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM fait_consultation f LEFT JOIN dim_diagnostic d ON d.code_diag=f.code_diag WHERE d.code_diag IS NULL;

SELECT 'fait_consultation_id_prof_sante_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM fait_consultation f LEFT JOIN dim_professionnel d ON d.id_prof_sante=f.id_prof_sante WHERE d.id_prof_sante IS NULL;

SELECT 'fait_consultation_date_consultation_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM fait_consultation f LEFT JOIN dim_temps d ON d.`date`=f.date_consultation WHERE d.`date` IS NULL;

SELECT 'fait_hospitalisation_id_patient_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM fait_hospitalisation f LEFT JOIN dim_patient d ON d.id_patient=f.id_patient WHERE d.id_patient IS NULL;

SELECT 'fait_hospitalisation_code_diag_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM fait_hospitalisation f LEFT JOIN dim_diagnostic d ON d.code_diag=f.code_diag WHERE d.code_diag IS NULL;

SELECT 'fait_hospitalisation_identifiant_organisation_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM fait_hospitalisation f LEFT JOIN dim_etablissement d ON d.identifiant_organisation=f.identifiant_organisation WHERE d.identifiant_organisation IS NULL;

SELECT 'fait_hospitalisation_date_entree_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM fait_hospitalisation f LEFT JOIN dim_temps d ON d.`date`=f.date_entree WHERE d.`date` IS NULL;

SELECT 'fait_deces_defunt_key_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM fait_deces f LEFT JOIN dim_defunt d ON d.defunt_key=f.defunt_key WHERE d.defunt_key IS NULL;

SELECT 'fait_deces_date_deces_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM fait_deces f LEFT JOIN dim_temps_deces d ON d.`date`=f.date_deces WHERE d.`date` IS NULL;

SELECT 'fait_deces_code_commune_deces_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM fait_deces f LEFT JOIN dim_lieu_deces d ON d.code_commune_insee=f.code_commune_deces WHERE d.code_commune_insee IS NULL;

SELECT 'fait_satisfaction_annee_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM fait_satisfaction f LEFT JOIN dim_temps_satisfaction d ON d.annee=f.annee WHERE d.annee IS NULL;

SELECT 'fait_satisfaction_region_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM fait_satisfaction f LEFT JOIN dim_region d ON d.region=f.region WHERE d.region IS NULL;

SELECT 'pont_activite_pro_id_prof_sante_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM pont_activite_pro f LEFT JOIN dim_professionnel d ON d.id_prof_sante=f.id_prof_sante WHERE d.id_prof_sante IS NULL;

SELECT 'pont_activite_pro_identifiant_organisation_orphelins' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM pont_activite_pro f LEFT JOIN dim_etablissement d ON d.identifiant_organisation=f.identifiant_organisation WHERE d.identifiant_organisation IS NULL;

SELECT 'professionnels_sans_pont' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM dim_professionnel p LEFT JOIN (SELECT DISTINCT id_prof_sante FROM pont_activite_pro) a
ON a.id_prof_sante=p.id_prof_sante WHERE a.id_prof_sante IS NULL;

SELECT 'pont_inconnu_et_site_reel' AS controle, COUNT(*) AS anomalies_attendues_zero
FROM (SELECT id_prof_sante FROM pont_activite_pro GROUP BY id_prof_sante
HAVING MAX(CASE WHEN identifiant_organisation='inconnu' THEN 1 ELSE 0 END)=1 AND COUNT(*)>1) d;

-- Bilan de couverture : les lieux sans region sont conserves, aucun filtre d'exclusion.
SELECT l.categorie_localisation, l.code_region, l.libelle_region, COUNT(*) AS deces_2019
FROM fait_deces d JOIN dim_lieu_deces l ON l.code_commune_insee=d.code_commune_deces
WHERE year(d.date_deces)=2019
GROUP BY l.categorie_localisation,l.code_region,l.libelle_region;

-- Un score absent reste NULL ; son poids ne participe pas a la moyenne BI.
SELECT annee, COUNT(*) AS sites,
SUM(CASE WHEN score_all_rea_ajust IS NOT NULL AND nb_rep_score_all_rea_ajust>0 THEN 1 ELSE 0 END) AS sites_avec_score_ponderable
FROM fait_satisfaction GROUP BY annee;
