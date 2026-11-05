# Reprendre Silver en trois phases

Les transformations existantes restent dans `chu_silver/pipelines.py` et
`chu_silver/rules.py`. Les trois lanceurs appellent ces memes fonctions :

1. `01_silver_hors_deces.py` : sources hors deces, etapes 01 a 06.
2. `02_silver_deces.py` : reprend les resultats de 01 et traite les deces.
3. `03_silver_controles.py` : verifications globales et, seulement si le lot
   est compatible, preparation des scripts Hive. Aucune activation automatique.

Chaque lancement ecrit une nouvelle tentative. Les checkpoints `01` et `02`
referencent les sorties precedentes, sans les copier ni les reecrire. Ne pas
supprimer les anciennes tentatives referencees : elles font partie du lot.
Les controles comparent les empreintes Bronze, le code, la configuration, la
cle, la version de cle et les exclusions ; ils verifient les schemas et les
marqueurs `_SUCCESS`. Ils supposent que les fichiers ORC deja valides restent
immuables : ils ne recalculent pas l'empreinte de chaque fichier de sortie.

## Avant de lancer sur la VM

- Retablir de l'espace disque et l'etat sain du NodeManager YARN. Ne pas lancer
  simultanement avec le job precedent en attente `application_1793864138399_0009`.
- Conserver Bronze, les tentatives Silver et le registre des cles deces.
- Les commandes suivantes concernent uniquement un environnement remis en etat.
  YARN a ete regle a 4096 Mio et 3 vCores virtuels. Un petit calcul fictif a
  reussi avec le parametrage ci-dessous ; les volumes reels restent a mesurer.
  La VM a 2 CPU virtuels : les 3 vCores YARN incluent notamment le conteneur
  ApplicationMaster et ne representent pas 3 processeurs physiques.
- Sur la VM CESI active, la version optimisee est deja preparee dans
  `~/chu_silver_runtime_v6`, depuis le commit de code
  `d55a63b2573f60419972262ad3395220282352a6` :

```bash
cd ~/chu_silver_runtime_v6
cat DEPLOYED_COMMIT.txt
python tests/test_reprise.py
spark-submit --master 'local[1]' --conf spark.dynamicAllocation.enabled=false --conf spark.eventLog.enabled=false tests/integration_reprise.py
```

Pour une livraison ulterieure, placer d'abord une copie a jour du depot Git sur
la VM, puis executer `python prepare_runtime.py ~/chu_silver_runtime_v7` depuis
son dossier `Scripts SQL/silver`. Le dossier `chu-bigdata-dev-20261105` peut
etre une copie simple et n'est pas necessairement une copie Git a jour.
`prepare_runtime.py` refuse une destination existante : choisir un nouveau
suffixe si besoin. Ne pas recreer ni remplacer
`~/.chu/hmac-test.key` : la meme cle est necessaire a chaque phase.

## Phase 01 — hors deces

Pour un nouveau lot complet. L'identifiant d'essai `hors_deces_v1` est un
exemple : il doit etre nouveau a chaque lancement.

```bash
spark-submit --master yarn --deploy-mode client \
  --driver-memory 1g --executor-memory 1536m --executor-cores 2 --num-executors 1 \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.yarn.executor.memoryOverhead=1024 \
  --py-files chu_silver.zip 01_silver_hors_deces.py \
  --config config/exemple.json --lot-id initial_20261105 \
  --attempt-id hors_deces_v1 \
  --hmac-key-file ~/.chu/hmac-test.key --key-version test_v1
```

Le message `SILVER_CHECKPOINT_01` confirme que la phase est terminee. Cela ne
publie pas les tables Hive et ne lance pas les deces.

## Phase 02 — deces

Pour reprendre une nouvelle phase 01, remplacer le dernier argument par
`--source-attempt hors_deces_v1`. Pour la tentative precedemment executee sur
la VM, utiliser plutot `--legacy-attempt` comme ci-dessous :

```bash
spark-submit --master yarn --deploy-mode client \
  --driver-memory 1g --executor-memory 1536m --executor-cores 2 --num-executors 1 \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.yarn.executor.memoryOverhead=1024 \
  --py-files chu_silver.zip 02_silver_deces.py \
  --config config/exemple.json --lot-id initial_20261105 \
  --attempt-id deces_reprise_v1 \
  --hmac-key-file ~/.chu/hmac-test.key --key-version test_v1 \
  --legacy-attempt a20261105193046f8b2a7
```

Cette reprise historique est volontairement limitee a cette tentative et a la
configuration VM connue. Le lanceur verifie les empreintes Bronze, les schemas,
et compare les pseudonymes patients de Bronze et Silver avec la cle fournie ;
il ne recalcule pas les autres tables. Il reutilise le registre des deces deja
termine pour le meme fichier. Les calculs et sorties de l'etape deces, encore
inacheves lors de l'arret precedent, sont rejoues dans une nouvelle tentative.

**Difference avec le `main` actuel :** cette tentative historique conserve les
identifiants professionnels normalises sans HMAC, alors que la version recente
des regles les pseudonymise. L'import ne change aucune donnee : le controle final
signalera `NOT_READY` et ne preparera pas la publication Hive. Il faudra ensuite
decider un retraitement coherent des tables professionnelles et consultations.
La comparaison des patients ne prouve pas a elle seule la provenance de tous
les parametres historiques ; cette tentative a ete associee au code VM
`ef70957f161ee5b408719196e89e9c1dd9fccc2d` lors de son execution documentee.

Le message `SILVER_CHECKPOINT_02` est requis avant la phase suivante. Si la
phase echoue, choisir un nouvel `--attempt-id` ; ne pas reutiliser ni effacer
la tentative en echec pour contourner le controle.

## Phase 03 — controles

```bash
spark-submit --master yarn --deploy-mode client \
  --driver-memory 1g --executor-memory 1536m --executor-cores 2 --num-executors 1 \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.yarn.executor.memoryOverhead=1024 \
  --py-files chu_silver.zip 03_silver_controles.py \
  --config config/exemple.json --lot-id initial_20261105 \
  --attempt-id controles_v1 \
  --hmac-key-file ~/.chu/hmac-test.key --key-version test_v1 \
  --source-attempt deces_reprise_v1
```

Cette phase execute les controles deja presents : unicite des cles, references,
comptages, identifiants patients, empreintes et reconciliation ; pour un lot
recent elle verifie aussi le format HMAC des identifiants professionnels.

- Lot recent compatible : `SILVER_READY` indique que les scripts Hive sont
  prepares ; la lecture et l'activation doivent encore etre validees.
- Lot historique importe : `SILVER_CHECKS_OK_NOT_READY` signifie que les
  controles existants sont passes, mais le lot n'est pas pret a etre publie a
  cause des identifiants professionnels non pseudonymises. Aucun HQL de
  publication n'est cree dans ce cas.
- Une erreur Spark ou `ECHEC.json` signifie que la phase n'est pas validee.

Les checkpoints et rapports ne remplacent pas les benchmarks Gold du livrable 2.
