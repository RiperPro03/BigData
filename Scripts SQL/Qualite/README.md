# Alimentation Gold et rapport qualité

Ce dossier contient le collecteur et le générateur du rapport Word. Le modèle reprend la présentation du livrable 1. La VM utilise Python 2.6 : ces fichiers n'ont besoin d'aucune bibliothèque Python supplémentaire.

## Enchaîner Silver puis Gold

Après déploiement de `Scripts SQL` et des quatre scripts Silver aux emplacements prévus sur la VM :

```bash
cd "/home/cloudera/Scripts SQL"
python pipeline_complet.py \
  --lot-id lot_20261110 \
  --hmac-key-file /home/cloudera/.chu/hmac-test.key \
  --key-version test_v1
```

Choisir un identifiant de lot adapté, ainsi que la version de clé utilisée pour le Silver. Conserver la même clé HMAC et le registre des clés techniques décès si l'on souhaite conserver les identifiants existants. Ne jamais déposer la clé dans Git. L'option Silver `--exclude-pseudonyms-file` est également disponible.

L'enchaînement s'arrête si Silver échoue. Gold travaille ensuite dans une base et un répertoire de préparation distincts, vérifie le Silver publié, les schémas Gold, la réconciliation des quatre faits, les doublons, les références et les rejets. Il mesure aussi les valeurs NULL de chaque attribut des tables Gold. Si un contrôle est absent, invalide ou en anomalie, ou si Gold comporte des rejets, la publication est bloquée. Les rejets Silver sont décrits dans le rapport et nécessitent une analyse métier ; leur présence ne constitue pas à elle seule une erreur technique bloquante.

Les deux couches ne sont pas publiées dans une transaction commune. Si Silver est publié puis que Gold échoue, Silver contient le nouveau lot mais Gold conserve normalement l'ancien ; le rapport courant n'est pas mis à jour. Maintenir les lectures suspendues et examiner l'échec avant de relancer Gold pour ce lot. En cas de retour arrière incomplet, suivre les consignes de reprise ci-dessous.

Pour alimenter Gold seul avec le Silver déjà publié, utiliser **le même identifiant de lot** que celui inscrit dans l'audit Silver :

```bash
python Gold/pipeline_gold.py --lot-id IDENTIFIANT_DU_LOT_SILVER
```

## Rapport et suivi

Après une publication réussie, le dernier rapport est remplacé ici :

```text
/home/cloudera/.chu/qualite/Rapport_Qualite_Donnees.docx
```

Les journaux et les indicateurs agrégés de chaque exécution sont dans `/home/cloudera/.chu/gold_runs/<execution>/`. Le rapport contient les résultats du lot effectivement lu, la complétude des attributs Silver et Gold, le bilan FINESS disponible, les doublons, la cohérence référentielle et la réconciliation des faits. Les taux de complétude comptent les valeurs non NULL : ils ne garantissent pas la justesse des valeurs renseignées. La clé HMAC et les données individuelles ne sont pas incluses.

Le statut `PUBLISHED_REPORT_READY` confirme la publication et la mise à jour du rapport. Un rapport produit dans le dossier d'exécution avant publication sert au diagnostic : il ne prouve pas que Gold a été remplacé. Le statut `PUBLISHED_REPORT_FAILED` indique que Gold a été publié mais que le rapport courant n'a pas été remplacé ; le document généré avant publication reste disponible dans le sous-dossier `qualite` de cette exécution.

## Exploitation et reprise

Suspendre les lectures Hive et Power BI sur Gold ainsi que toute autre alimentation pendant l'exécution. Les verrouillages coordonnent les publications des scripts du projet, mais ne bloquent pas les requêtes externes ni les modifications manuelles. Les répertoires `tables` et `rejets` sont basculés séparément : leur remplacement n'est pas une transaction globale.

Le Gold précédent est conservé dans `/user/cloudera/chu/gold/.gold_previous_<execution>/` pour permettre une restauration en cas de problème ; prévoir suffisamment d'espace disque. Les variantes de performance sont conservées, mais leurs données et les index peuvent être obsolètes après une nouvelle alimentation : les reconstruire et refaire les mesures avant de s'y fier.

En cas d'arrêt brutal ou de statut `ROLLBACK_FAILED`, ne pas supprimer les verrous ni relancer immédiatement. Consulter `execution.json` dans le dossier d'exécution : il indique les chemins préparés, la sauvegarde et la dernière étape de publication enregistrée. Comparer ces chemins dans HDFS, puis restaurer une version cohérente des deux répertoires avant de lever les verrous et de reprendre les lectures. La dernière étape enregistrée peut précéder de peu un déplacement effectivement terminé : vérifier l'état réel des dossiers. Une interruption peut laisser une base Hive de préparation et son répertoire de travail, à examiner avant nettoyage.
