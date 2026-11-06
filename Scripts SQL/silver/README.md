# Alimentation Silver en trois etapes

- `silver_hors_deces.py` : sources et transformations hors deces ; il contient
  aussi la configuration et les fonctions communes de lecture et de controle.
- `silver_deces.py` : traite les deces et conserve le registre des cles.
- `silver_controles.py` : controle les resultats des deux phases et publie Silver.

Les trois fichiers doivent etre dans le meme dossier sans espace sur la VM.
Ils sont concus pour Spark 1.6 / Python 2.6. Voici un exemple avec un meme lot :

```bash
cd /home/cloudera/chu_silver_final
spark-submit --master yarn --deploy-mode client --driver-memory 1g \
  --executor-memory 1536m --executor-cores 2 --num-executors 1 \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.yarn.executor.memoryOverhead=1024 \
  --py-files silver_hors_deces.py,silver_deces.py,silver_controles.py \
  silver_hors_deces.py --lot-id lot_exemple --attempt-id hors_deces_01 \
  --hmac-key-file /home/cloudera/.chu/hmac-test.key --key-version test_v1

spark-submit --master yarn --deploy-mode client --driver-memory 1g \
  --executor-memory 1536m --executor-cores 2 --num-executors 1 \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.yarn.executor.memoryOverhead=1024 \
  --py-files silver_hors_deces.py,silver_deces.py,silver_controles.py \
  silver_deces.py --lot-id lot_exemple --attempt-id deces_01 \
  --source-attempt hors_deces_01 \
  --hmac-key-file /home/cloudera/.chu/hmac-test.key --key-version test_v1

spark-submit --master yarn --deploy-mode client --driver-memory 1g \
  --executor-memory 1536m --executor-cores 2 --num-executors 1 \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.yarn.executor.memoryOverhead=1024 \
  --py-files silver_hors_deces.py,silver_deces.py,silver_controles.py \
  silver_controles.py --lot-id lot_exemple --attempt-id controles_01 \
  --source-attempt deces_01 \
  --hmac-key-file /home/cloudera/.chu/hmac-test.key --key-version test_v1
```

Utiliser le meme lot, la meme cle HMAC, la meme version de cle et le meme code
aux trois etapes. Chaque tentative doit avoir un identifiant nouveau. Les
checkpoints verifient que les sources Bronze, la configuration et le code ne
changent pas entre les phases. Un echec peut etre rejoue avec un nouvel
`attempt-id` et la meme tentative source, tant que ces conditions restent vraies.

Apres les controles, la phase 03 remplace entierement l'ancien Silver :
`/user/cloudera/chu/silver/tables`, `rejets` et `audit`. Bronze doit contenir
toutes les donnees a conserver. Le registre des cles deces et la meme cle HMAC
sont conserves. `SILVER_REPLACED` confirme la publication ; `SILVER_READY` seul
indique seulement que les controles sont passes. Ne pas lancer deux alimentations
Silver en meme temps et suspendre les lectures Gold pendant la publication.
