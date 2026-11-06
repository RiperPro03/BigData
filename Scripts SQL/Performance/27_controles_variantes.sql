-- Controle exhaustif des lignes des variantes par rapport au Gold de reference.
-- Les cles sources ont deja ete controlees uniques dans les controles Gold.
USE gold;
SET hive.execution.engine=mr;
SET hive.auto.convert.join=false;
SET hive.optimize.index.filter=false;
SET mapreduce.map.memory.mb=1024;
SET mapreduce.map.java.opts=-Xmx768m -Djava.net.preferIPv4Stack=true;
SET mapreduce.reduce.memory.mb=1536;
SET mapreduce.reduce.java.opts=-Xmx1024m -Djava.net.preferIPv4Stack=true;
SET mapreduce.job.reduce.slowstart.completedmaps=1.0;
SET hive.exec.reducers.max=8;

SELECT 'fait_consultation_part' AS controle, COUNT(v.num_consultation) AS lignes_variante,
       SUM(CASE WHEN b.num_consultation IS NULL OR v.num_consultation IS NULL OR NOT (b.date_consultation <=> v.date_consultation) OR NOT (b.id_patient <=> v.id_patient) OR NOT (b.code_diag <=> v.code_diag) OR NOT (b.id_prof_sante <=> v.id_prof_sante) OR NOT (v.annee_consultation <=> CAST(YEAR(b.date_consultation) AS SMALLINT)) THEN 1 ELSE 0 END) AS differences
FROM fait_consultation b FULL OUTER JOIN fait_consultation_part v ON b.num_consultation = v.num_consultation;

SELECT 'fait_consultation_part_trie' AS controle, COUNT(v.num_consultation) AS lignes_variante,
       SUM(CASE WHEN b.num_consultation IS NULL OR v.num_consultation IS NULL OR NOT (b.date_consultation <=> v.date_consultation) OR NOT (b.id_patient <=> v.id_patient) OR NOT (b.code_diag <=> v.code_diag) OR NOT (b.id_prof_sante <=> v.id_prof_sante) OR NOT (v.annee_consultation <=> CAST(YEAR(b.date_consultation) AS SMALLINT)) THEN 1 ELSE 0 END) AS differences
FROM fait_consultation b FULL OUTER JOIN fait_consultation_part_trie v ON b.num_consultation = v.num_consultation;

SELECT 'fait_hospitalisation_part' AS controle, COUNT(v.num_hospitalisation) AS lignes_variante,
       SUM(CASE WHEN b.num_hospitalisation IS NULL OR v.num_hospitalisation IS NULL OR NOT (b.date_entree <=> v.date_entree) OR NOT (b.id_patient <=> v.id_patient) OR NOT (b.code_diag <=> v.code_diag) OR NOT (b.identifiant_organisation <=> v.identifiant_organisation) OR NOT (v.annee_hospitalisation <=> CAST(YEAR(b.date_entree) AS SMALLINT)) THEN 1 ELSE 0 END) AS differences
FROM fait_hospitalisation b FULL OUTER JOIN fait_hospitalisation_part v ON b.num_hospitalisation = v.num_hospitalisation;

SELECT 'fait_hospitalisation_part_trie' AS controle, COUNT(v.num_hospitalisation) AS lignes_variante,
       SUM(CASE WHEN b.num_hospitalisation IS NULL OR v.num_hospitalisation IS NULL OR NOT (b.date_entree <=> v.date_entree) OR NOT (b.id_patient <=> v.id_patient) OR NOT (b.code_diag <=> v.code_diag) OR NOT (b.identifiant_organisation <=> v.identifiant_organisation) OR NOT (v.annee_hospitalisation <=> CAST(YEAR(b.date_entree) AS SMALLINT)) THEN 1 ELSE 0 END) AS differences
FROM fait_hospitalisation b FULL OUTER JOIN fait_hospitalisation_part_trie v ON b.num_hospitalisation = v.num_hospitalisation;

SELECT 'fait_deces_part' AS controle, COUNT(v.deces_key) AS lignes_variante,
       SUM(CASE WHEN b.deces_key IS NULL OR v.deces_key IS NULL OR NOT (b.date_deces <=> v.date_deces) OR NOT (b.code_commune_deces <=> v.code_commune_deces) OR NOT (b.defunt_key <=> v.defunt_key) OR NOT (v.annee_deces <=> CAST(YEAR(b.date_deces) AS SMALLINT)) THEN 1 ELSE 0 END) AS differences
FROM fait_deces b FULL OUTER JOIN fait_deces_part v ON b.deces_key = v.deces_key;

SELECT 'fait_deces_part_trie' AS controle, COUNT(v.deces_key) AS lignes_variante,
       SUM(CASE WHEN b.deces_key IS NULL OR v.deces_key IS NULL OR NOT (b.date_deces <=> v.date_deces) OR NOT (b.code_commune_deces <=> v.code_commune_deces) OR NOT (b.defunt_key <=> v.defunt_key) OR NOT (v.annee_deces <=> CAST(YEAR(b.date_deces) AS SMALLINT)) THEN 1 ELSE 0 END) AS differences
FROM fait_deces b FULL OUTER JOIN fait_deces_part_trie v ON b.deces_key = v.deces_key;

SELECT 'fait_deces_bucket' AS controle, COUNT(v.deces_key) AS lignes_variante,
       SUM(CASE WHEN b.deces_key IS NULL OR v.deces_key IS NULL OR NOT (b.date_deces <=> v.date_deces) OR NOT (b.code_commune_deces <=> v.code_commune_deces) OR NOT (b.defunt_key <=> v.defunt_key) THEN 1 ELSE 0 END) AS differences
FROM fait_deces b FULL OUTER JOIN fait_deces_bucket v ON b.deces_key = v.deces_key;

SELECT 'dim_defunt_bucket' AS controle, COUNT(v.defunt_key) AS lignes_variante,
       SUM(CASE WHEN b.defunt_key IS NULL OR v.defunt_key IS NULL OR NOT (b.sexe <=> v.sexe) THEN 1 ELSE 0 END) AS differences
FROM dim_defunt b FULL OUTER JOIN dim_defunt_bucket v ON b.defunt_key = v.defunt_key;
