USE gold;

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
    sexe                STRING,
    date_naissance      DATE,
    code_lieu_naissance STRING,
    lieu_naissance      STRING,
    pays_naissance      STRING
)
CLUSTERED BY (defunt_key) SORTED BY (defunt_key) INTO 16 BUCKETS
STORED AS ORC
LOCATION '/gold/dim_defunt_bucket';

INSERT OVERWRITE TABLE dim_defunt_bucket
SELECT defunt_key, sexe, date_naissance, code_lieu_naissance, lieu_naissance, pays_naissance
FROM dim_defunt;

CREATE EXTERNAL TABLE IF NOT EXISTS fait_deces_bucket (
    deces_key          INT,
    date_deces         DATE,
    code_commune_deces STRING,
    defunt_key         INT,
    numero_acte_deces  STRING
)
CLUSTERED BY (defunt_key) SORTED BY (defunt_key) INTO 16 BUCKETS
STORED AS ORC
LOCATION '/gold/fait_deces_bucket';

INSERT OVERWRITE TABLE fait_deces_bucket
SELECT deces_key, date_deces, code_commune_deces, defunt_key, numero_acte_deces
FROM fait_deces;