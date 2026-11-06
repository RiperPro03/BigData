# Alimentation Silver

Trois fichiers suffisent pour l'alimentation complete :

- `configuration.py` : chemins, fichiers sources et parametres Spark.
- `transformations.py` : lecture Bronze, regles de transformation, controles,
  rejets et publication Silver. Les sections sont identifiees dans le fichier.
- `run_silver.py` : lance et enchaine l'alimentation complete.

## Execution sur la VM

Les trois fichiers doivent se trouver dans un meme dossier sans espace, par
exemple `/home/cloudera/chu_silver_final` (contrainte observee avec Spark 1.6).
Depuis ce dossier, utiliser un nouvel identifiant de lot pour chaque execution :

```bash
cd /home/cloudera/chu_silver_final
spark-submit --master yarn --deploy-mode client \
  --driver-memory 1g --executor-memory 1536m \
  --executor-cores 2 --num-executors 1 \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.yarn.executor.memoryOverhead=1024 \
  --py-files transformations.py run_silver.py \
  --config configuration.py --lot-id lot_20261106 \
  --hmac-key-file /home/cloudera/.chu/hmac-test.key --key-version test_v1
```

L'identifiant `lot_20261106` est un exemple a adapter. La cle HMAC reste hors
Git : conserver la meme cle pour assurer la stabilite des pseudonymes. Le
message `SILVER_REPLACED` confirme la publication ; `SILVER_READY` ne suffit pas.

Le traitement lit toutes les sources Bronze, applique les transformations et
controles, ecrit les rejets, puis remplace entierement Silver apres validation.
Il ne s'agit pas d'une mise a jour incrementale : Bronze doit contenir toutes
les donnees a conserver. Le registre des cles deces est conserve entre les lots.

```text
/user/cloudera/chu/
  bronze/
  silver/
    tables/                  tables ORC exposees dans Hive : silver.*
    rejets/
    audit/                   rapport, qualite et registre des cles deces
```

La publication utilise temporairement des dossiers de travail et conserve
l'ancienne version pour restauration en cas d'echec de bascule. Une seule
alimentation Silver doit etre executee a la fois ; suspendre les lectures Gold
pendant la publication, qui n'est pas une transaction commune HDFS/Hive.
