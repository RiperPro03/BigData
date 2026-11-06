-- Optionnel : executer apres validation du Gold de reference et mesure initiale.
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


-- NOTIONS
-- ORC = Optimized Row Columnar, format de stockage en colonnes, optimisé pour les requêtes analytiques.
-- Bucket = un fichier dans lequel Hive range les lignes selon le hachage d'une colonne. Il sert à joindre des tables importantes plus rapidement.
-- CLUSTERED BY = clause de création de table qui indique la colonne de hachage pour le bucketing

-- Indispensable en Hive 1.1
SET hive.enforce.bucketing=true;
SET hive.enforce.sorting=true;

-- FAIT DECES BUCKETÉ

CREATE EXTERNAL TABLE IF NOT EXISTS dim_defunt_bucket (
    defunt_key          INT,
    sexe                STRING
)
CLUSTERED BY (defunt_key) SORTED BY (defunt_key) INTO 16 BUCKETS
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/dim_defunt_bucket';

INSERT OVERWRITE TABLE dim_defunt_bucket
SELECT defunt_key, sexe
FROM dim_defunt;

CREATE EXTERNAL TABLE IF NOT EXISTS fait_deces_bucket (
    deces_key          INT,
    date_deces         DATE,
    code_commune_deces STRING,
    defunt_key         INT
)
CLUSTERED BY (defunt_key) SORTED BY (defunt_key) INTO 16 BUCKETS
STORED AS ORC
LOCATION '/user/cloudera/chu/gold/tables/fait_deces_bucket';

INSERT OVERWRITE TABLE fait_deces_bucket
SELECT deces_key, date_deces, code_commune_deces, defunt_key
FROM fait_deces;
