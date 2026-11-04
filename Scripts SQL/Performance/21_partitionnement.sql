USE gold;

-- Autorise Hive à créer les partitions automatiquement à l'insertion
SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;

-- NOTIONS
-- ORC = Optimized Row Columnar, format de stockage en colonnes, optimisé pour les requêtes analytiques.
-- Partitionnement = au lieu de mettre tous les fichiers dans un seul dossier, Hive crée un sous-dossier par valeur d’une colonne.
-- Bucket = un fichier dans lequel Hive range les lignes selon un calcul fait sur une colonne.
-- Indexation = Hive crée un index sur une colonne pour retrouver plus vite les lignes qui contiennent une valeur donnée.

-- FAIT CONSULTATION PARTITIONNÉ

CREATE EXTERNAL TABLE IF NOT EXISTS fait_consultation_part (
    num_consultation  INT,
    date_consultation DATE,
    id_patient        STRING,
    code_diag         STRING,
    id_prof_sante     STRING
)
PARTITIONED BY (annee_consultation SMALLINT)
STORED AS ORC
LOCATION '/gold/fait_consultation_part';

INSERT OVERWRITE TABLE fait_consultation_part PARTITION (annee_consultation)
SELECT num_consultation, date_consultation, id_patient, code_diag, id_prof_sante,
       CAST(year(date_consultation) AS SMALLINT) AS annee_consultation
FROM fait_consultation
DISTRIBUTE BY year(date_consultation);
-- DISTRIBUTE BY : toutes les lignes d'une même année vont au même reducer,
-- ce qui évite qu'un reducer écrive dans des dizaines de partitions à la fois.

-- FAIT HOSPITALISATION PARTITIONNÉ

CREATE EXTERNAL TABLE IF NOT EXISTS fait_hospitalisation_part (
    num_hospitalisation      INT,
    date_entree              DATE,
    id_patient               STRING,
    code_diag                STRING,
    identifiant_organisation STRING
)
PARTITIONED BY (annee_hospitalisation SMALLINT)
STORED AS ORC
LOCATION '/gold/fait_hospitalisation_part';

INSERT OVERWRITE TABLE fait_hospitalisation_part PARTITION (annee_hospitalisation)
SELECT num_hospitalisation, date_entree, id_patient, code_diag, identifiant_organisation,
       CAST(year(date_entree) AS SMALLINT) AS annee_hospitalisation
FROM fait_hospitalisation
DISTRIBUTE BY year(date_entree);

-- FAIT DECES PARTITIONNÉ

CREATE EXTERNAL TABLE IF NOT EXISTS fait_deces_part (
    deces_key          INT,
    date_deces         DATE,
    code_commune_deces STRING,
    defunt_key         INT,
    numero_acte_deces  STRING
)
PARTITIONED BY (annee_deces SMALLINT)
STORED AS ORC
LOCATION '/gold/fait_deces_part';

INSERT OVERWRITE TABLE fait_deces_part PARTITION (annee_deces)
SELECT deces_key, date_deces, code_commune_deces, defunt_key, numero_acte_deces,
       CAST(year(date_deces) AS SMALLINT) AS annee_deces
FROM fait_deces
DISTRIBUTE BY year(date_deces);