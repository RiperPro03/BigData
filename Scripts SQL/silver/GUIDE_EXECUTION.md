# Tester et executer Silver sur la VM

**Pour une reprise en trois phases, utiliser en priorite
[REPRISE_EN_TROIS_PHASES.md](REPRISE_EN_TROIS_PHASES.md).** Les commandes
`run_silver.py` ci-dessous decrivent le lanceur historique monolithique : une
relance avec lui recalcule les etapes precedentes.

Les commandes utilisent l'environnement confirme du groupe : Spark 1.6.0, Python 2.6.6, Java 7. Pas de `pip install pyspark` ni de mise a niveau systeme requise par ces scripts.

**Spark 1.6 sur cette VM refuse les URI de scripts contenant des espaces (`Scripts%20SQL`).** Depuis le dossier `Scripts SQL/silver` du depot, preparer un nouveau dossier d'execution sans espaces :

```bash
python prepare_runtime.py ~/chu_silver_runtime_v1
cd ~/chu_silver_runtime_v1
```

Le preparateur copie uniquement une liste explicite de fichiers de code, la configuration exemple et les trois DML de reference pour les tests. Les configurations locales, cles et donnees ne sont pas copiees. Il refuse d'ecraser un dossier existant ; utiliser un nouveau suffixe lors d'une nouvelle livraison. Les commandes de test et de lancement suivantes se lancent dans ce dossier.

## 1. Tests sur donnees fictives

```bash
python tests/test_rules.py
python build_package.py
spark-submit --master 'local[2]' --py-files chu_silver.zip tests/integration_spark.py
```

Le dernier test doit afficher `CHU_SILVER_INTEGRATION_OK`. Il controle les categories de doublons/conflits, les jointures, la lecture CSV par offset et une date de 1882 en ORC. Il cree uniquement des donnees fictives dans un repertoire temporaire local. Spark peut produire ses propres journaux d'evenements selon la configuration du cluster.

Ce test a ete execute avec succes sur la VM. Le relancer apres une modification des lecteurs ou du moteur. Le precedent test utilisateur PySpark/HMAC reussi ne couvrait pas ces operations. Un second test couvre le registre des deces : `spark-submit --master 'local[2]' --conf spark.dynamicAllocation.enabled=false --py-files chu_silver.zip tests/integration_deces.py`. Il cree quatre lignes fictives dans un espace HDFS de test dedie et conserve son audit.

## 2. Cle de test persistante

La cle est commune aux trois sources patient. La creer une seule fois hors du depot, puis conserver le meme fichier pour les relances. Le bloc suivant refuse d'ecraser une cle existante :

```bash
python - <<'PY'
import os
folder = os.path.expanduser('~/.chu')
if not os.path.isdir(folder):
    os.mkdir(folder, 0o700)
path = os.path.join(folder, 'hmac-test.key')
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
try:
    os.write(fd, os.urandom(32))
finally:
    os.close(fd)
print('Cle de test creee ; conserver ce fichier sans le versionner.')
PY
```

Si ce fichier existe deja, **le reutiliser**, sans relancer sa creation. La cle n'est ni un argument en clair, ni un parametre du JSON. Le chemin et la version logique de cle passent au lanceur. Cette implementation transmet la cle necessaire aux fonctions Python via les taches Spark ; une gestion de secrets plus avancee fait partie de la securisation reportee par le groupe. Ne pas journaliser les objets ou fermetures contenant la cle.

Un remplacement de cle modifie tous les pseudonymes : reexecuter les trois branches et reconstruire le Gold dependant dans un lot coherent. Ne pas remplacer uniquement la dimension patient.

## 3. Configuration du lot

Relire `config/exemple.json` : chemins reels des 15 fichiers Bronze, compte d'execution et espaces de sortie. Les trois racines Bronze, sorties et registre doivent etre distinctes, sans imbrication. Le lanceur le verifie.

Les repertoires sont crees par le traitement si le compte d'execution a les droits necessaires. Les tests de HMAC et de lecture s'executent dans Spark, sans modifier Bronze. Les sorties sont des tables ORC non partitionnees en dossiers annuels ; `output_partitions` controle seulement le nombre de fichiers. Le partitionnement annuel des faits reste realise dans Gold par le groupe.

Les valeurs 16 partitions de shuffle, 16 fichiers deces et 8 fichiers consultations sont des points de depart pour cette VM, pas un optimum mesure. Adapter apres observation de la memoire, des durees et des tailles de fichiers. Les petites tables peuvent avoir un seul fichier ; les deces n'utilisent pas `coalesce(1)`.

## 4. Premier lancement limite aux references et patients

Le paquet doit etre reconstruit apres toute modification des modules. Pour tester les trois premieres etapes via YARN :

```bash
spark-submit \
  --master yarn \
  --deploy-mode client \
  --driver-memory 1g \
  --executor-memory 1g \
  --executor-cores 2 \
  --num-executors 1 \
  --conf spark.dynamicAllocation.enabled=false \
  --py-files chu_silver.zip \
  run_silver.py \
  --config config/exemple.json \
  --lot-id initial_20261105 \
  --hmac-key-file ~/.chu/hmac-test.key \
  --key-version test_v1 \
  --until 03
```

Le ResourceManager observe dispose de 3 072 Mio et 3 vcores au total. La commande demande un seul executeur avec deux coeurs, plutot que deux executeurs dont le second reste sans allocation memoire. Ces parametres ne modifient pas la configuration globale de YARN.

Une tentative unique est generee automatiquement, par exemple `a20261105153000abcdef`. Sa racine est imprimee dans le message final `SILVER_PARTIAL`. Ce lancement ne publie aucune table commune pour Gold.

## 5. Lot complet

Relancer la meme commande **sans `--until 03`** pour les etapes 01 a 08. Une nouvelle tentative rejoue toutes les dependances ; elle ne reutilise pas un melange de sorties de plusieurs essais. `--attempt-id` permet de nommer une tentative, mais reutiliser une tentative existante est refuse.

Le registre des deces est conserve sous `technical_keys/deces/<empreinte>`. Il associe l'offset technique du fichier a une cle INT. Une relance du meme fichier reutilise cette correspondance ; un changement de repartition Spark ne doit pas recreer les identites. Les fichiers differents constituent des instantanes distincts ; la reconciliation incrementale d'un meme evenement entre deux extractions n'est pas implementee. Le pipeline charge un instantane complet, sans append des memes faits.

Si une premiere creation du registre echoue, un verrou ou un dossier staging peut rester. Examiner le journal et l'etat de cette tentative avant reprise ; ne jamais supprimer le registre publie pour contourner l'erreur. Le registre et ses sauvegardes doivent etre conserves aussi longtemps que les lots qui utilisent ses cles.

## 6. Resultats et qualite

```text
silver_runs/<lot>/<tentative>/
  tables/<table>/                         ORC des sorties principales
  enrichissement_satisfaction/tables/region/
  intermediaires/satisfaction_<annee>/    detail harmonise par campagne
  rejets/<source>/                       reference technique, categorie et motif
  audit/
    manifest_entrees.json
    qualite_<source>.json
    progression_<etape>.json
    rapport_final.json                    READY_NOT_PUBLISHED
    publication.hql
    activation.hql
```

Le rapport final detaille volumes, NULL et completude par colonne, durees d'ecriture/relecture, categories exclusives de rejet et empreintes source. Le nombre de deces et de defunts doit correspondre aux occurrences de deces acceptees. Les scores NULL restent comptes dans la satisfaction.

Les lignes rejeteees ne contiennent ni noms ni identifiant patient original. Leur `record_id` permet de retrouver l'occurrence dans Bronze : offset pour les grands CSV, rang d'enregistrement pour les petits fichiers/classeurs. Les categories `DUPLICATE`, `ALTERNATIVE`, `REJECT`, `EXCLUDE` sont distinctes.

Un `rapport_partiel.json` ou un fichier `ECHEC.json` ne vaut pas validation de Silver. Les journaux du traitement sont necessaires pour corriger une erreur technique. Une tentative ne s'autopublie pas en cas d'echec.

## 7. Publication Hive apres controle

Dans les chemins ci-dessous, remplacer `<lot>` et `<tentative>` par ceux du message `SILVER_READY`. Copier les scripts generes dans le dossier ignore `artifacts` :

```bash
mkdir -p artifacts
hdfs dfs -cat '/user/cloudera/chu/silver_runs/<lot>/<tentative>/audit/publication.hql' > artifacts/publication.hql
hdfs dfs -cat '/user/cloudera/chu/silver_runs/<lot>/<tentative>/audit/activation.hql' > artifacts/activation.hql
hive -f artifacts/publication.hql
```

Cette premiere commande Hive cree une **base propre au lot** avec 14 tables externes et six alias. Tester sa lecture, les types DATE/STRING, les comptes et les agregats avant activation. Par exemple remplacer `<base_du_lot>` par le nom indique dans le rapport :

```sql
SELECT COUNT(*) FROM <base_du_lot>.deces;
SELECT COUNT(*) FROM <base_du_lot>.defunt;
SELECT MIN(date_deces), MAX(date_deces) FROM <base_du_lot>.deces;
SELECT annee, COUNT(*), COUNT(score_all_rea_ajust)
FROM <base_du_lot>.satisfaction GROUP BY annee;
```

Ensuite, dans une fenetre ou les chargements/lecteurs Gold sont arretes, activer les vues communes :

```bash
hive -f artifacts/activation.hql
```

Cette bascule de plusieurs vues n'est pas atomique. Garder le script d'activation du precedent lot pour revenir en arriere si necessaire. Si une table physique `silver.*` existe deja a la place d'une vue, la commande echoue : analyser l'objet existant et preparer sa migration, sans `DROP` automatique. Le rapport generé par Spark reste `READY_NOT_PUBLISHED` : la lecture et l'activation Hive doivent etre ajoutees au journal d'exploitation comme preuves separees.

## 8. Avant les DML Gold

Lire [ANALYSE_SQL_MAIN.md](ANALYSE_SQL_MAIN.md). Le patch `sql/correctifs_gold.patch` corrige quatre fichiers SQL du groupe mais n'est pas applique automatiquement. En particulier, conserver le HMAC dans les INT du DDL de base est impossible. Une migration ou un rechargement coherent de Gold est necessaire si des anciennes tables sont deja presentes.

Apres Gold : rapport de qualite mesure, requetes de benchmark couvrant les besoins, mesures avant/apres avec resultats identiques et graphiques. Le Silver ne remplace pas ces elements du livrable 2.
