# Silver — traitements PySpark CHU

Implementation Bronze → Silver pour **Spark 1.6.0 / Python 2.6.6 / Java 7 / Hive 1.1 CDH 5.12**. Base analysee : les scripts finaux `main/Scripts SQL`, commit `7ed0f68`.

**Statut : code ecrit, tests metier et integration Spark passes sur la VM. Voir VALIDATION.md pour les essais reels, la lecture Hive et la validation des gros volumes restant a effectuer.** Le precedent test PySpark/HMAC de l'utilisateur etait un test fictif local ; ce n'etait pas une execution de ces scripts.

## Organisation

```text
silver/
  run_silver.py               # point d'entree spark-submit, etapes 01 a 08
  build_package.py            # construit le ZIP de code pour les executeurs
  prepare_runtime.py          # exporte le code vers un dossier sans espaces
  config/exemple.json         # 15 fichiers reels Bronze, sans secret
  chu_silver/
    contracts.py             # tables, types, cles et alias attendus par Gold
    rules.py                 # pseudonymisation et regles metier pures
    readers.py               # CSV distribue et petits cp1252/XLSX bornes
    runtime.py               # qualite, rejets, sorties immuables, HQL de publication
    pipelines.py             # branches metier et leurs dependances
  tests/
    test_rules.py            # tests locaux sans Spark, donnees fictives
    integration_spark.py     # test Spark fictif a executer sur la VM
    integration_deces.py     # registre HDFS, homonymes et stabilite des cles
  sql/correctifs_gold.patch  # corrections proposees, non appliquees au Gold
  ANALYSE_SQL_MAIN.md         # analyse des 12 SQL et du document de performance
  GUIDE_EXECUTION.md          # preparation, lancement, lecture des rapports et publication
  VALIDATION.md               # controles effectivement executes et limites
```

Les huit etapes sont des fonctions pilotees par un lanceur commun, pour partager les contrats et eviter de recopier le code de lecture/HMAC dans plusieurs scripts.

| Etape | Sources / traitement | Tables Silver produites |
|---|---|---|
| 01 Referentiels | Diagnostic, specialites, codes postaux, COG communes et regions | diagnostic, specialite, codes_postaux, commune, region |
| 02 Patients | HMAC-SHA256 complet, sexe/age, retrait des identifiants directs | patient |
| 03 Professionnels / sites | ADELI/RPPS, specialites, 24 colonnes etablissements, liens d'activite | professionnel, etablissement, activite |
| 04 Consultations | Date, HMAC commun, references, unicite | consultation |
| 05 Hospitalisations | Date francaise stricte, HMAC commun, references, unicite | hospitalisation |
| 06 Satisfaction | CSV 2017/2019 et XLSX 2020, FINESS y compris Corse, regions, scores NULL conserves | satisfaction et reference region completee |
| 07 Deces | CSV distribue, dates ISO, retrait des noms, registre stable des occurrences, geographie | deces, defunt |
| 08 Qualite / publication | Unicite, schemas, compteurs, empreintes source, generation des HQL | rapport final et HQL, sans activation automatique |

Les dates et les noms de colonnes sont ceux attendus par Gold. Six alias (`s1_consultation`, `s2_hospitalisation`, `s2_etablissement`, `s2_activite`, `s3_satisfaction`, `s4_deces`) couvrent les noms prefixes encore utilises dans les DML. Les patients sont en **STRING**, conformement au HMAC complet deja decide.

## Resultat d'une execution

Les sorties sont en ORC sous `/user/cloudera/chu/silver_runs/<lot>/<tentative>/`. Le format columnar conserve les types ; les tables externes Hive sont explicites. Les partitions de sortie Spark reglent le nombre de fichiers. Cette premiere livraison ne partitionne pas les dossiers Silver par annee : les variantes annuelles et les buckets Gold sont construits par les scripts de performance du groupe, sans multiplier inutilement les fichiers Silver.

Chaque tentative cree ses propres sorties et son audit. Elle n'ecrase ni Bronze ni un resultat precedent. Une relance utilise une nouvelle tentative ; elle rejoue les dependances et reutilise le registre de cles deces pour le meme fichier. Les entrees sont empreintees avant/apres traitement. Un lot partiel ou en echec n'est pas publie.

La grande source deces est lue sur les blocs HDFS : aucune collecte des faits au driver. Seuls les petits fichiers cp1252/XLSX (limite 8 Mio) et le COG borne (50 000 lignes maximum) utilisent une preparation sur le driver. Les grosses references sont jointes par Spark ; seules les petites specialites et la correspondance COG sont diffusees. Le nombre de partitions est configurable, avec persistance sur disque pour les donnees reutilisees.

## Regles protegeant les resultats

- Meme HMAC-SHA256, normalisation et cle dans Patient, Consultation et Hospitalisations. Cle fournie par fichier externe ; aucune valeur par defaut dans le code ou Git.
- Les noms de patients/professionnels et de defunts ne sont pas repris. Patient ne publie que pseudonyme, sexe et age ; le motif libre des consultations est exclu.
- Chaque rejet contient une reference technique, une categorie et un motif, sans recopier la ligne brute.
- Les repetitions identiques autorisees sont distinguees des conflits de cle ; tous les membres d'un conflit sont rejetes. Les relations multisites restent multiples dans l'activite, sans multiplication des consultations.
- Les homonymes et occurrences de deces identiques restent distincts. Un registre persistant attribue une cle INT par offset du fichier source, pas par nom ni numero d'acte.
- Score e-Satis manquant → NULL ; un poids manquant/nul est signale. Aucune moyenne regionale ni taux de soins n'est calcule en Silver.
- Le COG est ramene a une correspondance par code : les variantes TYPECOM sont tracees pour eviter de multiplier les deces. Les lieux inconnus et historiques non resolus restent presents.

## A lire avant Gold

[ANALYSE_SQL_MAIN.md](ANALYSE_SQL_MAIN.md) detaille les ecarts des SQL finaux : INT patient, GROUP BY incomplets, commentaire SQL invalide, region des deces et controle du defunt. Le patch fourni est une proposition de correction des scripts ; il ne migre aucune table deja chargee et n'a pas ete applique au Gold.

[GUIDE_EXECUTION.md](GUIDE_EXECUTION.md) contient les commandes de test et de lancement. [VALIDATION.md](VALIDATION.md) distingue les tests deja passes de ceux restant a executer sur la VM.

Les quatre documents de conception initiaux restent consultables : [transformations](TRANSFORMATIONS.md), [contrats](CONTRATS_ENTREES_SORTIES.md), [qualite](QUALITE_ET_PUBLICATION.md), [decisions](ECARTS_ET_DECISIONS.md). Ils decrivent la cible et les evolutions possibles ; ce README et le guide precisent ce que cette livraison implemente effectivement. A la demande du groupe, les reglages generaux de securite Spark et la finalisation documentaire RGPD sont reportes ; la pseudonymisation et la minimisation sont deja dans le code.
