# Qualité, rejets et publication Silver

Ces contrôles font partie des traitements à développer ; ce document n'est pas un rapport de résultats mesurés sur Silver.

## 1. Précontrôles avant le premier traitement

| Vérification | Résultat attendu / conduite en cas d'échec |
|---|---|
| Versions réellement installées | Relever Spark, Python du driver/exécuteurs, Java et Hive ; arrêter si le code ou les dépendances ne sont pas compatibles. CDH 5.12 ne suffit pas à connaître la version Spark effective. |
| Manifestes d'entrée | Les 15 fichiers attendus sont identifiés individuellement avec schéma, campagne/version, taille et empreinte. Un changement après validation invalide le rapprochement du lot. |
| Lecture HDFS | Le compte d'exécution peut lire les seules entrées nécessaires et écrire dans les espaces autorisés ; vérifier le contexte d'identité effectif. |
| Protection des données | Vérifier les accès Bronze, sorties, temporaires, rejets et journaux. L'audit du 4 novembre avait relevé des droits larges 755/644 et l'absence de sécurité Hadoop activée ; ce plan ne constate pas leur correction. |
| Secret HMAC | Clé accessible au traitement par un mécanisme protégé et identique pour les trois sources, sans affichage ni stockage dans Git/HDFS avec les données. Version de clé tracée sans valeur du secret. |
| Identité patient | Même normalisation testée sur Patient, Consultation et Hospitalisations, avec identifiants fictifs et tests de valeurs invalides. |
| Formats particuliers | CSV Windows-1252, XLSX 2020, NULL des exports, format strict des dates et lecture des champs cités testés. |
| Capacité et reprise | Mémoire, espace disponible, paramètres d'exécution et registre persistant des clés décès vérifiés ; aucun écrasement du Bronze ou d'un lot publié. |

Les accès HDFS seuls ne constituent pas une preuve globale de conformité RGPD/HDS. Le rapport doit distinguer les protections mises en place des exigences de gouvernance restant à démontrer.

## 2. Une règle d'équilibrage qui empêche les pertes silencieuses

Pour chaque source, attribuer une catégorie terminale exclusive à chaque enregistrement :

```text
Lignes source lues
  = lignes acceptées au grain prévu
  + lignes rejetées / mises en quarantaine
  + répétitions écartées selon une règle autorisée
  + alternatives écartées par une réduction de grain documentée
  + exclusions métier ou droits des personnes explicitement autorisées
```

Un même enregistrement peut porter plusieurs motifs, mais il est compté **une seule fois** dans une catégorie terminale. Les lignes brutes physiquement illisibles sont comptées dans une catégorie d'erreur de lecture ; si la lecture n'est pas réconciliable, le traitement échoue. Une jointure qui augmente le nombre de faits est un échec de cardinalité, même si aucun enregistrement ne manque.

Cas particuliers :

- Spécialité jointe au professionnel : le nombre de professionnels acceptés reste identique après enrichissement.
- Activité : une relation refusée n'est pas une consultation refusée ; la référence professionnelle est conservée et le pont Gold traite les professionnels sans site valide.
- Codes postaux : les alternatives non retenues ne sont pas des doublons invalides. Rapprocher les 39 192 occurrences avec les communes produites et les catégories d'écart, sans compter deux fois les répétitions.
- Satisfaction : rapprocher chaque campagne avant la réunion, puis la somme des trois campagnes ; aucun score NULL n'est supprimé par un filtre implicite.
- Décès : les deux sorties `deces` et `defunt` décrivent les mêmes occurrences acceptées ; chacune doit avoir ce nombre de lignes. Ne pas additionner leurs comptes pour les comparer à la source.
- Tables de correspondance et lignes `inconnu` : leur nombre est contrôlé séparément ; ce sont des dérivations, pas de nouvelles occurrences d'événements source.

## 3. Qualité par source et par attribut

| Famille | Mesures à enregistrer |
|---|---|
| Complétude | Pour chaque attribut : nombre total, absents source, NULL en sortie et taux de complétude ; préciser le dénominateur et séparer les données absentes des conversions invalides. |
| Conversions | Dates impossibles, nombres illisibles, codes invalides, sexe non reconnu ; bilan avant/après et action effectuée. |
| Unicité | Clés nulles, clés dupliquées, répétitions exactes, conflits de contenu ; aucune clé multiple dans les références publiées. |
| HMAC | Format de 64 caractères hexadécimaux ; même patient source → même pseudonyme dans les trois flux ; aucune fusion d'identifiants distincts détectée. Aucun identifiant clair dans les sorties publiées. |
| Références soins | Consultations → Patient/Diagnostic/Professionnel ; hospitalisations → Patient/Diagnostic/Établissement ; activités → Professionnel/Établissement. Compter les orphelins avant rejet et vérifier zéro orphelin dans les jeux acceptés. |
| FINESS | Longueur/format, zéros initiaux, distinction site/juridique, cohérence `F + finess_geo`, couverture dans le fichier établissements. Publier les écarts sans supprimer automatiquement les sites e-Satis absents de cette référence. |
| Géographie | Unicité des correspondances, résolution des parents COG, communes non trouvées, codes région absents, part des décès 2019 rattachée à une région et part non résolue. |
| Satisfaction | Résultats par année, clé site–année, score NULL, poids NULL/nul/négatif, score présent sans poids exploitable, valeurs non numériques, correspondances de région. |
| Décès | Dates de décès refusées, dates de naissance mises à NULL, naissance après décès, clés uniques/stables et appariement exact décès–défunt. Homonymes conservés. |
| Confidentialité | Colonnes nominatives absentes des sorties prévues, absence de secret/valeur brute dans les logs et séparation des accès aux quarantaines. |
| Performance ETL | Durée de lecture/traitement/écriture, volumes lus/écrits, fichiers et partitions produits, éventuels échecs et reprises, versions et configuration. |

Les valeurs du livrable 1 (par exemple 358 814 activités sans organisation ou 646 dates de décès invalides) sont des repères historiques. Les résultats réels seront recalculés, comparés et expliqués ; ils ne sont pas des compteurs à recopier dans le rapport.

## 4. Contrat des rejets et journaux

Un rejet standard contient au minimum : `lot_id`, `source_id`, `source_record_id`, `etape`, `categorie`, `motifs`, `horodatage`, `version_regles`. Ajouter uniquement les valeurs nettoyées/pseudonymisées nécessaires à sa compréhension. Pour les patients invalides avant HMAC, conserver la référence technique du record plutôt que son identifiant clair.

Exemples de motifs à normaliser dans le code :

| Motif | Traitement |
|---|---|
| `STRUCTURE_INVALIDE`, `DATE_EVENEMENT_INVALIDE`, `CLE_OBLIGATOIRE_ABSENTE` | Rejet de la ligne et bilan explicite |
| `REFERENCE_PATIENT_ABSENTE`, `REFERENCE_DIAGNOSTIC_ABSENTE`, `REFERENCE_PROFESSIONNEL_ABSENTE`, `REFERENCE_ETABLISSEMENT_ABSENTE` | Rejet du fait ou de la relation concernés ; ne pas effacer les références valides |
| `CONFLIT_CLE` | Quarantaine du groupe contradictoire, sans sélection arbitraire |
| `REPETITION_IDENTIQUE` | Écartement seulement sur les sources où la règle l'autorise |
| `ALTERNATIVE_POSTALE_NON_RETENUE` | Réduction documentée du grain, pas déclaration d'invalidité |
| `NAISSANCE_INVALIDE`, `REGION_NON_RESOLUE`, `SPECIALITE_NON_RESOLUE` | Ligne conservée avec NULL/indicateur ou `inconnu` selon le contrat |
| `EXCLUSION_AUTORISEE` | Catégorie distincte des erreurs de qualité |

Un simple log contient des compteurs et des événements techniques, pas un `show()` des patients, des noms de défunts ou une trace d'exception incluant le secret. Les originaux nécessaires à une correction restent dans Bronze ou une quarantaine à accès renforcé, avec une durée de conservation définie. Ne pas dupliquer automatiquement toutes les lignes brutes dans les rejets ordinaires.

## 5. Tests utiles avant la volumétrie complète

Utiliser des exemples fictifs pour vérifier les cas qui changent réellement les résultats :

1. Même identifiant patient sous les formats autorisés dans les trois flux → même HMAC ; identifiant vide ou invalide → rejet ; une exclusion se propage aux trois flux.
2. Dates valides/invalides, année bissextile, naissance absente et naissance postérieure au décès ; tester aussi une date historique réellement couverte par la source.
3. ADELI de huit/neuf caractères et RPPS de onze caractères ; aucune collision après normalisation ; zéros FINESS préservés dans CSV et XLSX.
4. Référence absente et référence dupliquée : la ligne est soit expliquée en rejet, soit conservée selon sa règle, jamais perdue ou multipliée silencieusement.
5. Professionnel avec zéro, un et plusieurs sites : le futur pont n'augmente pas les lignes de consultation ; la somme des poids vaut 1 par professionnel.
6. Score NULL, score zéro réellement fourni, poids absent/nul et conflit site–année ; le score régional exclut les mêmes lignes de son numérateur et de son dénominateur.
7. Deux décès avec les mêmes valeurs métier, y compris après retrait des noms : deux occurrences conservées et clés inchangées à la relance ; aucun rapprochement avec Patient.
8. Commune déléguée/arrondissement, code corse, outre-mer et commune historique inconnue : rattachement univoque ou statut non résolu, sans perte d'un décès.
9. Échec d'une écriture au milieu du lot : le lot précédent reste celui utilisé ; la reprise ne publie pas des tables d'âges différents.
10. Aller-retour Spark → fichiers → table externe Hive : schéma, nombre de lignes, NULL, accents, codes, dates historiques et agrégats de contrôle identiques.

Les tests de performance se feront ensuite sur les volumes réels sans exporter les données dans Git.

## 6. Publication et stockage

1. Figer le manifeste des fichiers Bronze et un `lot_id`, vérifier que le même lot n'est pas déjà publié avec une autre configuration.
2. Écrire toutes les sorties dans `silver_work/<lot_id>/`, avec contrôles par branche. Conserver la provenance et le registre des clés.
3. Réconcilier les volumes, vérifier les clés/références et tester la lecture du format par Hive sur des tables de contrôle.
4. Produire le rapport qualité, les statuts d'acceptation et le manifeste des sorties ; un échec d'intégrité bloquant empêche la publication.
5. Déplacer/publier les sorties validées dans `silver_lots/<lot_id>/` sans écraser le précédent lot. Un renommage HDFS ne rend pas atomique une série de modifications du metastore Hive.
6. Effectuer la bascule des tables Hive dans une fenêtre contrôlée, avec sauvegarde des anciennes `LOCATION`, procédure de retour et vérification que toutes pointent sur le même lot. Gold n'est lancé qu'après cette barrière et ne lit pas pendant une bascule partielle. Le mécanisme précis doit être testé sur la version Hive installée.
7. Relire les tables publiées, rapprocher leur manifeste et marquer le lot publié. Garder l'ancien lot selon la politique de conservation avant toute purge.

Format proposé : Parquet pour Silver, ORC Gold conservé. Vérifier les types et les dates avant d'adopter le format sur tout le volume. Partitions candidates : année pour décès et événements de soins, année de campagne pour satisfaction, à justifier par la volumétrie et les requêtes. Les petites tables n'ont pas besoin de partitionnement systématique ; ne pas partitionner par patient. Conserver l'année métier même lorsqu'elle devient une colonne de partition et vérifier son exposition Hive.

Adapter le nombre de partitions/fichiers aux ressources réelles, éviter un fichier par ligne et `coalesce(1)` sur les décès. Réserver les éventuelles jointures broadcast aux références dont la taille en mémoire a été mesurée ; ne pas diffuser automatiquement un million de professionnels. Le cache n'est utile que si les données sont réutilisées et tiennent dans la mémoire disponible.

## 7. Ce qui reste nécessaire pour rendre le livrable 2

Le Silver fournit une partie des preuves ; il ne remplace pas les éléments SQL et de performance demandés :

- DDL des tables externes Silver et Gold, DML Gold commentés et versionnés, contrôles d'intégrité référentielle exécutés puisque les clés du modèle ne suffisent pas à les imposer.
- Rapport qualité mesuré, avec complétude par attribut, FINESS, doublons, orphelins, rejets et explication des écarts Bronze → Silver → Gold.
- Stratégie de partitionnement, fichiers et éventuels buckets adaptée à Hive/Spark ; ne pas proposer un index de type PostgreSQL sur HDFS par analogie. Mesurer les options effectivement supportées.
- Au moins cinq requêtes de benchmark représentatives des besoins métier. Proposition : consultations par établissement/période, consultations par diagnostic/période, hospitalisations globales/période, hospitalisations par diagnostic, hospitalisations par sexe/âge, consultations par professionnel ; ajouter décès région 2019 et satisfaction région 2020 pour couvrir tout le périmètre retenu.
- Mesures avant/après optimisation sur **les mêmes données et les mêmes règles métier**, résultats vérifiés identiques, configuration/état du cache documentés, plusieurs exécutions, graphiques comparatifs et interprétation.
- Rapport et ZIP avec scripts/configuration exemple/documentation/requêtes ; aucune clé, donnée réelle sensible ou quarantaine dans Git ou dans une archive distribuée sans autorisation.
