-- Variante optionnelle apres validation du Gold de reference.
-- Tri intra-partition : ne cree aucun index. Conserve la variante partitionnee initiale.
USE gold;

-- Ressources de session : noeud YARN de 4096 Mio, conteneur maximal de 3072 Mio.
-- Aucun changement de la configuration globale du cluster.
SET hive.execution.engine=mr;
-- Evite la preparation locale des map joins, forcee a 50 Mio par cet environnement.
-- Les jointures distribuees conservent les memes lignes et les memes controles.
SET hive.auto.convert.join=false;
SET mapreduce.map.memory.mb=1024;
SET mapreduce.map.java.opts=-Xmx768m -Djava.net.preferIPv4Stack=true;
SET mapreduce.reduce.memory.mb=1536;
SET mapreduce.reduce.java.opts=-Xmx1024m -Djava.net.preferIPv4Stack=true;
SET mapreduce.job.reduce.slowstart.completedmaps=1.0;
SET hive.exec.reducers.max=8;


-- Autorise Hive à créer les partitions automatiquement à l'insertion
SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;

-- NOTIONS
-- ORC = Optimized Row Columnar, format de stockage en colonnes, optimisé pour les requêtes analytiques.
-- Partitionnement = au lieu de mettre tous les fichiers dans un seul dossier, Hive crée un sous-dossier par valeur d’une colonne.

-- FAIT CONSULTATION PARTITIONNÉ

CREATE EXTERNAL TABLE IF NOT EXISTS fait_consultation_part_trie (
    num_consultation  INT,
    date_consultation DATE,
    id_patient        STRING,
    code_diag         STRING,
    id_prof_sante     STRING
)
PARTITIONED BY (annee_consultation SMALLINT)
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/fait_consultation_part_trie';

INSERT OVERWRITE TABLE fait_consultation_part_trie PARTITION (annee_consultation)
SELECT num_consultation, date_consultation, id_patient, code_diag, id_prof_sante,
       CAST(year(date_consultation) AS SMALLINT) AS annee_consultation
FROM fait_consultation
DISTRIBUTE BY year(date_consultation)
SORT BY id_prof_sante;
-- DISTRIBUTE BY : toutes les lignes d'une même année vont au même reducer,
-- ce qui évite qu'un reducer écrive dans des dizaines de partitions à la fois.

-- FAIT HOSPITALISATION PARTITIONNÉ

CREATE EXTERNAL TABLE IF NOT EXISTS fait_hospitalisation_part_trie (
    num_hospitalisation      INT,
    date_entree              DATE,
    id_patient               STRING,
    code_diag                STRING,
    identifiant_organisation STRING
)
PARTITIONED BY (annee_hospitalisation SMALLINT)
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/fait_hospitalisation_part_trie';

INSERT OVERWRITE TABLE fait_hospitalisation_part_trie PARTITION (annee_hospitalisation)
SELECT num_hospitalisation, date_entree, id_patient, code_diag, identifiant_organisation,
       CAST(year(date_entree) AS SMALLINT) AS annee_hospitalisation
FROM fait_hospitalisation
DISTRIBUTE BY year(date_entree)
SORT BY code_diag;

-- FAIT DECES PARTITIONNÉ

CREATE EXTERNAL TABLE IF NOT EXISTS fait_deces_part_trie (
    deces_key          INT,
    date_deces         DATE,
    code_commune_deces STRING,
    defunt_key         INT
)
PARTITIONED BY (annee_deces SMALLINT)
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/fait_deces_part_trie';

INSERT OVERWRITE TABLE fait_deces_part_trie PARTITION (annee_deces)
SELECT deces_key, date_deces, code_commune_deces, defunt_key,
       CAST(year(date_deces) AS SMALLINT) AS annee_deces
FROM fait_deces
DISTRIBUTE BY year(date_deces)
SORT BY code_commune_deces;
