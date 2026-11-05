# Écarts repérés et décisions de réalisation

État au 5 novembre 2026. Ce relevé permet de construire Silver et Gold sans propager les incohérences. Il ne modifie ni le livrable 1 rendu ni les scripts Gold du groupe. Les adaptations listées restent à implémenter.

## 1. Choix déjà pris par le groupe

| Sujet | Décision applicable |
|---|---|
| Répartition des outils | Talend charge les sources brutes en Bronze ; PySpark traite Bronze → Silver ; Hive expose les tables et construit Gold. Cette évolution remplace le nettoyage Silver Talend/Hive des anciens plans. |
| Patient | HMAC-SHA256 complet, 64 caractères hexadécimaux, même normalisation/clé pour Patient, Consultation et Hospitalisations. |
| Type patient | `STRING` en Silver et dans les trois colonnes patient Gold. Le `INT` du dictionnaire rendu est une erreur reconnue, pas une contrainte à reproduire. |
| Périmètre | Les 15 fichiers présents en Bronze ; seulement e-Satis 48 h MCO 2017/2019/2020 pour la satisfaction ; cinq tables PostgreSQL. |
| Conservation | Bronze reste brut et intact. Les rejets/exclusions sont traçables ; pas de suppression silencieuse des lignes. |

## 2. Adaptations nécessaires dans Gold

Les constats ci-dessous viennent des scripts du dépôt au commit `7ed0f68`.

| Fichier / constat | Adaptation nécessaire avant exécution |
|---|---|
| `DDL/01_DDL_dimensions.sql` et `DDL/03_DDL_faits.sql` : `dim_patient.id_patient`, `fait_consultation.id_patient`, `fait_hospitalisation.id_patient` en INT | Passer les trois colonnes en STRING pour accepter le HMAC complet ; vérifier aussi les tables déjà créées, car `CREATE IF NOT EXISTS` ne change pas leur type. |
| `DML/11_DML_dimensions.sql` lit `silver.consultation`, `silver.hospitalisation`, mais `DML/13_DML_faits.sql` lit `silver.s1_consultation`, `silver.s2_hospitalisation`, `silver.s3_satisfaction`, `silver.s4_deces` | Adopter les noms canoniques du contrat Silver partout. Le même problème concerne `silver.s2_etablissement` et `silver.s2_activite`. Ne pas supposer ces tables existantes. |
| `DML/11_DML_dimensions.sql` : `GROUP BY id_patient` avec `sexe, age` sélectionnés ; idem diagnostic/professionnel | SQL non valide pour ces colonnes non agrégées dans Hive. Silver fournit une clé unique contrôlée ; sélectionner les lignes validées ou grouper toutes les colonnes lorsque c'est justifié. |
| Même fichier : `WHERE numerotes.rang = 1 pour éviter ...` | Le texte d'explication n'est pas un commentaire SQL et empêche l'analyse de la requête. Le commenter ; le `row_number` ne remplace pas la résolution des conflits en Silver. |
| `DML/12_DML_pont.sql` : `MAX(mode_exercice)` pour une paire dupliquée | Remplacer la sélection arbitraire d'un libellé par la règle Silver de résolution des couples ; Gold consomme une relation déjà contrôlée. |
| `DDL/01_DDL_dimensions.sql`, `DML/11_DML_dimensions.sql` : lieu de décès sans région | Propager `code_region` et le libellé régional depuis Silver vers le lieu Gold et adapter le dictionnaire de mise en œuvre. Sans cela, le besoin décès par région 2019 n'est pas couvert. |
| `DML/13_DML_faits.sql` : contrôle décès sans jointure à `dim_defunt` | Ajouter le contrôle d'existence de `defunt_key` dans cette dimension, et pas seulement le test non NULL. |
| Tables externes `LOCATION '/gold/...'` | Confirmer les chemins et droits voulus pour Gold. Ne pas en déduire que `/user/cloudera/chu/...` et `/gold/...` désignent le même endroit. |
| Fichiers de performance/DDL | Vérifier la cohérence des colonnes et types une fois les contrats arrêtés ; leur présence dans Git ne prouve ni leur exécution ni un gain de performance mesuré. |

Ces problèmes ne justifient pas d'inventer des données Silver pour satisfaire un SQL incohérent. La correction Gold devra être coordonnée avec le membre du groupe qui en est responsable.

## 3. Points du rendu à expliciter dans le rapport de mise en œuvre

| Point | Règle retenue dans cette structure |
|---|---|
| Décès : le rapport remplace la région par le département faute de référence disponible | Le COG communes/régions est maintenant chargé : préparer le rattachement régional et sa couverture. Documenter l'amélioration et la limite d'un COG 2024 appliqué à de l'historique. |
| Consultations par établissement : un tableau écrit `1 + nombre d'établissements` | Coquille : le texte explicatif prévoit bien **`1 / nombre de sites`**. Tester la somme des poids et ne pas recopier les consultations dans le fait. |
| Déterminisme : « première ligne gardée » | Les répétitions identiques peuvent être réduites selon la règle de la source ; les conflits de même clé sont isolés tant qu'une priorité fiable n'existe pas. L'ordre Spark n'est pas une priorité métier. |
| Établissements : 16 clés en double annoncées dans Bronze, puis unicité annoncée dans Silver | Recalculer les doublons/conflits du lot réel ; ne pas tenir l'unicité pour acquise. |
| Décès : commentaire général de dédoublonnage, mais homonymes indiscernables | Conserver les occurrences ; aucun dédoublonnage automatique sur les noms ou sur les champs après retrait des noms. |
| Dictionnaire décès : colonnes de calendrier différentes du rapport et des DDL | Le rapport décrit `date, annee, mois, jour`. Partir de ce contrat ; trimestre/libellé du mois sont des ajouts possibles à justifier, pas un besoin de nettoyage source. |
| Dictionnaire satisfaction : identifiant intitulé `identifiant_satisfaction`, alors que rapport/DDL utilisent l'organisation | Le contrat de réalisation est le site `finess_geo`, `identifiant_organisation = F + finess_geo`, et `annee` ; aucune clé fondée sur FINESS juridique. |
| « Taux de satisfaction » | Mesure retenue : moyenne pondérée des scores globaux ajustés publiés. Ne pas la présenter comme une proportion directement calculée de patients satisfaits. |
| « Taux » de soins | Appliquer la définition événements/patients distincts prévue au rendu et l'annoncer clairement ; ce n'est pas un taux populationnel sans autre dénominateur. |
| Acquisition FTP | Bronze a reçu des copies depuis le PC ; aucune automatisation FTP n'est démontrée. Décrire cette limite de la maquette. |
| HDS et confidentialité | L'audit Bronze ne valide ni certification HDS ni restriction effective des accès ; les droits relevés doivent être vérifiés/corrigés avant de poursuivre les traitements sensibles. |

## 4. Détails à fixer avant d'écrire du code exécutable

- Version exacte Spark/Python/Hive/Java, méthode de soumission et dépendances disponibles ; ne pas partir d'une API Spark récente supposée disponible dans CDH 5.12.
- Mécanisme protégé de mise à disposition de la clé HMAC au driver/exécuteurs ; version de clé, rotation et traitement des exclusions, sans publier le secret.
- Contrat des dates réel pour chaque source, valeurs spéciales de satisfaction et règle de plausibilité de l'âge. `Patient.Date` et `Jour_Hospitalisation` ne reçoivent aucun sens métier inventé.
- Registre persistant et identification stable des occurrences décès, y compris les lignes identiques, avec test d'idempotence et capacité des clés INT.
- Lecteur XLSX 2020 ou conversion contrôlée compatible, préservant FINESS et mesures.
- Table de variantes régionales e-Satis et résolution des types de commune du COG ; bilan des codes historiques non reconnus.
- Règle métier éventuelle pour les conflits d'établissements, de professionnels, de couples activité et de site–année satisfaction. Sans règle validée, la quarantaine est explicite.
- Choix final de format Silver, partitions, chemins, DDL externes et protocole de publication cohérente de toutes les tables.

Ces points ne bloquent pas la documentation du traitement. Ils empêchent de présenter de futurs scripts comme prêts à tourner sur la VM avant leurs vérifications.
