# Alimentation Silver

Quatre scripts compatibles avec Spark 1.6 et Python 2.6 :

| Script | Rôle |
| --- | --- |
| `silver_pipeline.py` | Vérifie les prérequis, lance les phases dans l'ordre et publie le Silver après validation. Contient aussi la configuration, les schémas et les services partagés. |
| `silver_hors_deces.py` | Prépare les référentiels, patients, professionnels, consultations, hospitalisations et la satisfaction. |
| `silver_deces.py` | Prépare les décès et les défunts, et conserve le registre des clés techniques. |
| `silver_controles.py` | Regroupe les contrôles préalables, les règles de qualité utilisées pendant le traitement et les contrôles finaux. |

Les contrôles de lignes restent exécutés pendant les transformations pour diriger les anomalies vers les rejets. La phase finale vérifie les tables, les clés, les références, les bilans et l'identité du lot avant la publication. Les décès utilisent les référentiels préparés par la première phase : les deux traitements sont séparés, mais ils ne peuvent pas être lancés en parallèle.

Le contrôle final ajoute au rapport JSON le nombre de lignes de satisfaction avec et sans établissement correspondant, ainsi que le taux de correspondance par `identifiant_organisation`. Ce bilan est informatif : il ne rejette pas les sites absents du référentiel, dont le périmètre peut différer.

## Lancement

Copier les quatre fichiers dans un même dossier **sans espace** sur la VM. Par exemple :

```bash
cd /home/cloudera/chu_silver
python silver_pipeline.py \
  --lot-id lot_20261110 \
  --hmac-key-file /home/cloudera/.chu/hmac-test.key \
  --key-version test_v1
```

Adapter le lot et la version de clé. Utiliser la même clé que le Silver existant si l'on souhaite conserver les pseudonymes. Ne pas copier la clé dans Git. Une option facultative `--exclude-pseudonyms-file` reprend le fichier d'exclusions de l'ancienne version. Le pipeline alloue automatiquement des identifiants distincts pour les trois tentatives et échoue immédiatement si une phase échoue.

Avant les traitements, le pipeline vérifie la configuration, la clé, l'état d'écriture HDFS, la présence des fichiers Bronze et la connexion HiveServer2. Les contrôles de schéma des fichiers et le test HMAC entre driver et workers restent également actifs dans Spark. Les erreurs de données sont suivies par motif dans les audits et les rejets ; une erreur technique interrompt le lot.

## Publication et vérification

La phase finale publie seulement si tous les contrôles réussissent. Elle prépare une nouvelle version, vérifie les copies, remplace `/user/cloudera/chu/silver/` et tente de restaurer la version précédente en cas d'échec pendant la bascule. Les chemins publiés restent :

```text
/user/cloudera/chu/silver/tables/
/user/cloudera/chu/silver/rejets/
/user/cloudera/chu/silver/audit/
```

Le message `SILVER_REPLACED` confirme la fin de la publication. `SILVER_READY` indique seulement que les contrôles préalables à la publication sont passés. Les tentatives de travail restent isolées ; en cas d'échec, l'identifiant du lot et les journaux facilitent le diagnostic. Un nouveau lancement utilise de nouvelles tentatives.

Le traitement remplace entièrement le Silver : Bronze doit contenir toutes les données à conserver. Suspendre les lectures et chargements Gold pendant la publication. Le registre des clés décès et la clé HMAC doivent être conservés ; les chemins Silver et le format ORC restent compatibles avec Gold.
