# Silver

Structure de transformation **Bronze → Silver avec PySpark**, établie le 5 novembre 2026 après relecture de l'énoncé, du livrable 1 rendu, de son dictionnaire Gold, de l'audit Bronze et des scripts SQL du dépôt.

**Statut : conception détaillée. Les scripts Python décrits ci-dessous ne sont pas encore implémentés ni exécutés.** Les documents rendus au livrable 1 et les scripts Gold existants ne sont pas modifiés par ce plan.

## Le rôle de Silver

Talend a chargé les sources brutes dans HDFS. Spark lit ces fichiers sur le cluster, contrôle leur structure, pseudonymise les patients, retire les données nominatives inutiles, harmonise les formats et vérifie les références. Il écrit des tables de détail fiables pour construire Gold, puis les indicateurs dans Power BI.

```text
Sources → Talend → Bronze brut HDFS
                       ↓
                 PySpark : Silver
                 ├─ données valides, typées et pseudonymisées
                 ├─ rejets et exclusions tracés
                 └─ rapport qualité et réconciliation
                       ↓
                 Hive : modèle Gold → Power BI
```

Le calcul des taux, des moyennes régionales et des tranches d'âge reste dans Gold/BI. Silver conserve le détail nécessaire aux huit besoins métier du sujet, y compris décès et satisfaction, optionnels dans l'énoncé mais retenus dans le livrable 1.

## Les huit traitements à construire

| Ordre / futur script | Fonction | Sorties logiques principales |
|---|---|---|
| `01_referentiels.py` | Diagnostics, spécialités, codes postaux, communes et régions | `diagnostic`, `specialite`, `codes_postaux`, `commune`, `region` |
| `02_patients.py` | HMAC-SHA256, retrait des identifiants directs, sexe et âge | `patient` |
| `03_professionnels_etablissements.py` | Identifiants professionnels, spécialités, établissements et relations d'activité | `professionnel`, `etablissement`, `activite` |
| `04_consultations.py` | Dates, pseudonyme patient, unicité et références | `consultation` |
| `05_hospitalisations.py` | Dates d'entrée, pseudonyme patient, diagnostic et établissement | `hospitalisation` |
| `06_satisfaction.py` | Réunion e-Satis 48 h MCO 2017/2019/2020, FINESS, régions et mesures | `satisfaction` |
| `07_deces.py` | Lecture distribuée, retrait des noms, dates, lieux et clés stables | `deces`, `defunt` |
| `08_qualite_publication.py` | Réconciliation, qualité, lecture Hive et publication d'un lot cohérent | Rapport qualité, manifeste du lot, tables Silver validées |

Ce sont huit unités de traitement, pas huit rechargements Bronze. Un futur `run_silver.py` pilotera leurs dépendances et les précontrôles. Il pourra les lancer séparément pour les reprises.

## Documents de construction

1. [Transformations et dépendances](TRANSFORMATIONS.md) : règles détaillées de chaque branche et correspondance avec les indicateurs finaux.
2. [Contrats d'entrée et de sortie](CONTRATS_ENTREES_SORTIES.md) : les 15 chemins Bronze, leurs formats et les colonnes Silver attendues.
3. [Qualité, rejets et publication](QUALITE_ET_PUBLICATION.md) : règles de contrôle, conservation des lignes, stockage, tests et preuves pour le livrable 2.
4. [Écarts et décisions](ECARTS_ET_DECISIONS.md) : corrections nécessaires avant exécution, notamment dans les SQL Gold.

## Arborescence cible du code

Les seuls fichiers présents à ce stade sont les documents de conception. L'arborescence suivante décrit le code à réaliser :

```text
silver/
  run_silver.py
  01_referentiels.py
  02_patients.py
  03_professionnels_etablissements.py
  04_consultations.py
  05_hospitalisations.py
  06_satisfaction.py
  07_deces.py
  08_qualite_publication.py
  commun/
    configuration.py       # chemins, lot, schémas, versions des règles
    lecture.py             # lecture et validation des différents formats
    pseudonymisation.py    # HMAC commun aux trois sources patient
    normalisation.py       # dates, codes et identifiants professionnels
    qualite.py             # métriques, motifs et réconciliation
    publication.py         # lots validés, manifeste et reprise
  config/
    exemple.json           # configuration sans secret
  tests/
    donnees_fictives/
    test_regles.py
    test_integration.py
```

Les fichiers numérotés seront des points d'entrée ; la logique réutilisable sera importée depuis `commun`. Les secrets, les données réelles et les sorties d'exécution ne seront pas versionnés. Aucun HMAC fictif ou traitement vide ne doit être présenté comme un script opérationnel.

## Ordre pratique de réalisation

1. Relever les versions réelles Spark/Python/Hive et vérifier les accès à Bronze, aux espaces de travail et au secret HMAC.
2. Fixer les contrats et les écarts listés dans [ECARTS_ET_DECISIONS.md](ECARTS_ET_DECISIONS.md).
3. Construire `01`, `02`, puis `03` ; tester la pseudonymisation commune et les clés.
4. Construire `04` et `05`, puis `06` et `07` ; la branche décès sera testée sur un échantillon fictif avant le volume complet.
5. Construire `08`, publier un lot Silver contrôlé, puis adapter et exécuter les DDL/DML Gold.
6. Produire les mesures de qualité, les requêtes de benchmark et les comparaisons de performance demandées pour le livrable 2.

Les précontrôles et le rapport qualité sont nécessaires dès les premiers scripts ; `08` en consolide les résultats.

## Références et priorité des choix

- Énoncé « Projet — Cloud Healthcare Unit », sections besoins utilisateurs et livrables attendus ; copie locale dans `Projet/consignes/pages/02-projet.md`.
- **Rapport réellement rendu** : `Perso/Livrable1_Groupe 1/Livrable1_Groupe 1/Livrable 1.docx`, notamment les trois groupes Gold et les règles S1 à S5 ; dictionnaire dans `MLD/Dictionnaire_Gold.xlsx` du même rendu.
- Décision du groupe : **Bronze brut, transformations Silver avec PySpark** ; décision HMAC du 3 novembre : pseudonyme complet, identifiants patients Silver/Gold en `STRING`.
- Audit du 4 novembre : `Projet/diagnostics/2026-11-04/audit-bronze/Audit-Bronze-2026-11-04.md` ; profil `Projet/analyses/longueurs/profil_sources.json`.
- Scripts Gold du dépôt relus à partir du commit `7ed0f68`.

Les décisions explicites du groupe priment sur les anciens plans Talend/Hive de transformation. Le README général du dépôt contient encore des descriptions anciennes ; il ne remplace pas le rapport rendu ni les décisions ci-dessus. Les corrections de cohérence sont explicitées, sans réécriture silencieuse du livrable 1.
