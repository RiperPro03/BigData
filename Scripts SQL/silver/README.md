# Alimentation Silver

Talend depose les sources dans Bronze. Ces scripts PySpark 1.6 / Python 2.6
transforment les donnees et remplacent integralement la version Silver publiee.

## Fichiers

- `configuration.py` : chemins HDFS, sources, formats et nombre de fichiers de sortie.
- `01_silver_hors_deces.py`, `02_silver_deces.py`, `03_silver_controles.py` : trois phases normales.
- `run_silver.py` : execution complete en une commande.
- `chu_silver/` : lecteurs, transformations, contrats, controles et publication.
- `prepare_runtime.py`, `build_package.py` : preparation du code pour Spark.

## Stockage et remplacement

```text
/user/cloudera/chu/
  bronze/
  silver/
    tables/                  14 tables ORC disponibles dans Hive : silver.*
    rejets/                  rejets du lot publie
    audit/                   rapport_final.json, manifeste, bilans qualite
      technical_keys/deces/  registre persistant des cles deces
```

Chaque alimentation complete recalcule un instantane depuis Bronze. Elle ne
fait ni append ni mise a jour ligne par ligne. Bronze doit donc contenir toutes
les donnees a conserver, y compris les annees historiques.

Les calculs et checkpoints des trois phases sont temporaires dans
`/user/cloudera/chu/.silver_work/runs/<lot>/<tentative>/`. Apres les controles,
la publication copie les 14 tables et les rejets dans un dossier temporaire,
compare les checksums HDFS, remplace Silver par renommage et verifie les schemas
Hive. L'ancienne version est supprimee apres succes. En cas d'echec pendant la
bascule, elle est restauree ; les donnees temporaires restent pour diagnostic.
Les dossiers temporaires vides sont retires apres publication.

Le registre des cles deces est conserve a chaque remplacement pour que les memes
occurrences gardent leurs identifiants. Conserver egalement la meme cle HMAC,
hors du depot. La version initiale est `test_v1` sur la maquette.

Executer une seule alimentation Silver a la fois et suspendre les lectures Gold
pendant la publication : les renommages HDFS successifs et la premiere creation
des objets Hive ne constituent pas une transaction commune.

## Preparation sur la VM

Depuis le dossier `Scripts SQL/silver` :

```bash
python prepare_runtime.py /home/cloudera/chu_silver_final
cd /home/cloudera/chu_silver_final
```

La destination doit etre nouvelle et sans espaces. Aucun secret n'est copie.

## Execution complete

```bash
spark-submit --master yarn --deploy-mode client \
  --driver-memory 1g --executor-memory 1536m \
  --executor-cores 2 --num-executors 1 \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.yarn.executor.memoryOverhead=1024 \
  --py-files chu_silver.zip run_silver.py \
  --config configuration.py --lot-id initial_20261105 \
  --hmac-key-file /home/cloudera/.chu/hmac-test.key --key-version test_v1
```

Le message `SILVER_REPLACED` confirme la publication. `SILVER_READY` seul indique
que les calculs ont passe les controles, avant la publication finale.

## Execution en trois phases

Utiliser les memes options Spark et HMAC que ci-dessus, avec :

1. `01_silver_hors_deces.py --attempt-id hors_deces_01`
2. `02_silver_deces.py --attempt-id deces_01 --source-attempt hors_deces_01`
3. `03_silver_controles.py --attempt-id controles_01 --source-attempt deces_01`

Passer le meme `--lot-id` et la meme configuration aux trois phases. La phase 03
publie automatiquement apres succes des controles. Les deux premieres phases
conservent leurs checkpoints temporaires pour la suite. Choisir des identifiants
nouveaux a chaque execution ; une tentative existante est refusee. Une reprise
exige les memes sources, le meme code, la meme configuration et la meme cle.
Apres publication, ces checkpoints temporaires sont retires.

## Controles

Les traitements conservent les regles de typage, normalisation, pseudonymisation
HMAC-SHA256, dedoublonnage autorise et quarantaine. Ils verifient les schemas,
les comptes, l'unicite, les references, la reconciliation source/sorties et les
empreintes Bronze. Le rapport du lot publie est dans `silver/audit/rapport_final.json`.
Le Gold reste une etape distincte a valider avec ses propres SQL.
