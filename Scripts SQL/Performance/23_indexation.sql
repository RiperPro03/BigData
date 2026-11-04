USE gold;

-- NOTIONS
-- ORC = Optimized Row Columnar, format de stockage en colonnes, optimisé pour les requêtes analytiques.
-- Indexation = Hive crée un index sur une colonne pour retrouver plus vite les lignes qui contiennent une valeur donnée.
-- DISTRIBUTE BY : toutes les lignes d'une même année vont au même reducer, ce qui évite qu'un reducer écrive dans des dizaines de partitions à la fois.

SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;

-- FAIT CONSULTATION INDEXATION

INSERT OVERWRITE TABLE fait_consultation_part PARTITION (annee_consultation)
SELECT num_consultation, date_consultation, id_patient, code_diag, id_prof_sante,
       CAST(year(date_consultation) AS SMALLINT) AS annee_consultation
FROM fait_consultation
DISTRIBUTE BY year(date_consultation)
SORT BY id_prof_sante;

-- FAIT HOSPITALISATION INDEXATION

INSERT OVERWRITE TABLE fait_hospitalisation_part PARTITION (annee_hospitalisation)
SELECT num_hospitalisation, date_entree, id_patient, code_diag, identifiant_organisation,
       CAST(year(date_entree) AS SMALLINT) AS annee_hospitalisation
FROM fait_hospitalisation
DISTRIBUTE BY year(date_entree)
SORT BY code_diag;

-- FAIT DECES INDEXATION

INSERT OVERWRITE TABLE fait_deces_part PARTITION (annee_deces)
SELECT deces_key, date_deces, code_commune_deces, defunt_key, numero_acte_deces,
       CAST(year(date_deces) AS SMALLINT) AS annee_deces
FROM fait_deces
DISTRIBUTE BY year(date_deces)
SORT BY code_commune_deces;