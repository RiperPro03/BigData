# Contrats d'entrée et de sortie Silver

Référence du lot initial : audit Bronze du 4 novembre 2026. Les nombres servent à rapprocher ce lot, pas à imposer une volumétrie immuable aux suivants. Aucun compte de lignes Silver n'a encore été mesuré.

## 1. Les 15 fichiers Bronze

Racine constatée : **`/user/cloudera/chu/bronze/`**. Tous les chemins ci-dessous sont relatifs à cette racine. Lire les fichiers par schéma et non par un masque réunissant des structures différentes.

| N° | Chemin | Format | En-tête | Lignes source de référence |
|---|---|---|---|---:|
| 1 | `postgres/diagnostic/diagnostic.txt` | UTF-8, `;` | Non | 15 490 |
| 2 | `postgres/specialites/specialites.txt` | UTF-8, `;` | Non | 93 |
| 3 | `postgres/professionnels/professionnels.txt` | UTF-8, `;` | Non | 1 048 575 |
| 4 | `postgres/patients/patients.txt` | UTF-8, `;` | Non | 100 000 |
| 5 | `postgres/consultations/consultations.txt` | UTF-8, `;` | Non | 1 027 157 |
| 6 | `etablissements/etablissement_sante.csv` | UTF-8, `;` | Oui | 416 665 |
| 7 | `etablissements/activite_professionnel_sante.csv` | UTF-8, `;` | Oui | 1 823 588 |
| 8 | `csv_sante/Hospitalisations.csv` | UTF-8, `;` | Oui | 2 479 |
| 9 | `satisfaction/2017/ESATIS48H_MCO_recueil2017_donnees.csv` | Windows-1252, `;` | Oui | 1 157 |
| 10 | `satisfaction/2019/resultats-esatis48h-mco-open-data-2019.csv` | Windows-1252, `;` | Oui | 1 152 |
| 11 | `satisfaction/2020/resultats-esatis48h-mco-open-data-2020.xlsx` | XLSX, feuille `Resultats` | Oui | 1 150 |
| 12 | `deces/deces.csv` | UTF-8 avec BOM éventuel, `,` | Oui | 25 088 208 |
| 13 | `referentiels_geographiques/codes_postaux_laposte_extrait_2026-11-03.csv` | Windows-1252, `;` | Oui | 39 192 |
| 14 | `referentiels_geographiques/v_commune_2024.csv` | UTF-8, `,` | Oui | 37 544 |
| 15 | `referentiels_geographiques/v_region_2024.csv` | UTF-8, `,` | Oui | 18 |

Les comptes des cinq exports PostgreSQL ont été rapprochés avec la base. Les dix autres fichiers ont été comparés octet pour octet aux copies locales ; leurs comptes de lignes proviennent du profil des sources ou de l'inspection des références. Ce sont des preuves distinctes.

### Particularités de lecture

- Exports PostgreSQL : ordre des colonnes ci-dessous obligatoire ; ne pas mettre `header=true`. Dans ce lot, les NULL sont exportés sous forme de champs vides et aucune chaîne vide d'origine n'a été observée. Rétablir NULL selon cette convention. L'export texte simple n'échappe pas un séparateur ou une nouvelle ligne dans une valeur ; recontrôler la structure à chaque acquisition.
- CSV : contrôler BOM, guillemets, nombre de champs et caractères de fin de ligne. Ne pas utiliser un `split(';')` générique pour les fichiers pouvant contenir des valeurs citées.
- XLSX : un fichier Excel n'est pas un CSV. Une éventuelle conversion intermédiaire garde les identifiants en texte et son rapport rapproche le nombre de lignes et les mesures ; elle ne remplace pas le fichier Bronze.
- Aucune détection implicite du schéma n'est considérée comme un contrat ; vérifier les noms de colonnes, puis convertir explicitement.

## 2. Ordre des colonnes PostgreSQL

| Export | Colonnes, dans l'ordre exact |
|---|---|
| Diagnostic | `Code_diag`, `Diagnostic` |
| Specialites | `Code_specialite`, `Fonction`, `Specialite` |
| Professionnels | `Identifiant`, `Civilite`, `Categorie_professionnelle`, `Nom`, `Prenom`, `Profession`, `Type_identifiant`, `Code_specialite` |
| Patients | `Id_patient`, `Nom`, `Prenom`, `Sexe`, `Adresse`, `Ville`, `Code_postal`, `Pays`, `EMail`, `Tel`, `Date`, `Age`, `Num_Secu`, `Groupe_sanguin`, `Poid`, `Taille` |
| Consultations | `Num_consultation`, `Id_mut`, `Id_patient`, `Id_prof_sante`, `Code_diag`, `Motif`, `Date`, `Heure_debut`, `Heure_fin` |

Les huit autres tables PostgreSQL ne sont pas attendues dans le périmètre du rendu : Mutuelle, Adher, Medicaments, Prescription, Laboratoire, Salle, AAAA, date. Le fichier `professionnel_sante.csv` n'est pas une sixième source à ajouter au flux, qui utilise déjà la table PostgreSQL des professionnels.

## 3. Colonnes requises des fichiers

| Source | Contrat utile au traitement |
|---|---|
| Hospitalisations | `Num_Hospitalisation`, `Id_patient`, `identifiant_organisation`, `Code_diagnostic`, `Suite_diagnostic_consultation`, `Date_Entree`, `Jour_Hospitalisation` |
| Activité | `identifiant`, `identifiant_organisation`, `mode_exercice` |
| Établissements | Les 24 colonnes listées ci-dessous |
| e-Satis, chaque campagne | Au minimum `finess_geo`, `region`, `score_all_rea_ajust`, `nb_rep_score_all_rea_ajust` ; les colonnes supplémentaires sont connues par schéma de campagne |
| Décès | `nom`, `prenom`, `sexe`, `date_naissance`, `code_lieu_naissance`, `lieu_naissance`, `pays_naissance`, `date_deces`, `code_lieu_deces`, `numero_acte_deces` |
| Codes postaux | Correspondance explicite vers `code_commune_insee`, `nom_de_la_commune`, `code_postal`, `libelle_d_acheminement` ; `Ligne_5` non reprise |
| COG communes | Au minimum `TYPECOM`, `COM`, `REG`, `DEP`, `LIBELLE`, `COMPARENT` |
| COG régions | Au minimum `REG`, `LIBELLE` |

Les 24 colonnes établissements à conserver en Silver :

```text
adresse, cedex, code_commune, code_postal, commune,
complement_destinataire, complement_point_geographique, email,
enseigne_commerciale_site, finess_etablissement_juridique, finess_site,
identifiant_organisation, indice_repetition_voie, mention_distribution,
numero_voie, pays, raison_sociale_site, siren_site, siret_site,
telecopie, telephone, telephone_2, type_voie, voie
```

## 4. Contrat des tables Silver proposées

Base Hive logique proposée : **`silver`**. Utiliser ces noms canoniques dans les futurs scripts et adapter explicitement Gold ; ne pas créer des copies pour chaque ancien préfixe `s1_`, `s2_`, etc. Les métadonnées de provenance et de qualité s'ajoutent à ce contrat métier sans revenir dans les dimensions Gold par défaut.

| Table | Grain / clé contrôlée | Colonnes métier de sortie |
|---|---|---|
| `silver.diagnostic` | Une ligne par `code_diag` | `code_diag STRING`, `libelle STRING` |
| `silver.specialite` | Une ligne par `code_specialite` | `code_specialite STRING`, `fonction STRING`, `specialite STRING` |
| `silver.codes_postaux` | Une ligne par `code_commune_insee` | `code_commune_insee STRING`, `nom_de_la_commune STRING`, `code_postal STRING`, `libelle_d_acheminement STRING` |
| `silver.commune` | Une correspondance univoque par code source | `code_commune_insee STRING`, `type_commune STRING`, `code_commune_parent STRING`, `libelle_commune STRING`, `code_departement STRING`, `code_region STRING`, `libelle_region STRING`, `statut_rattachement STRING` |
| `silver.region` | Une ligne par région canonique, plus `inconnu` | `code_region STRING`, `region STRING` ; unicité des libellés utilisés en jointure |
| `silver.patient` | Une ligne par pseudonyme patient | `id_patient STRING` (HMAC 64 hex), `sexe STRING`, `age INT` |
| `silver.professionnel` | Une ligne par professionnel normalisé | `id_prof_sante STRING`, `categorie STRING`, `profession STRING`, `specialite STRING` |
| `silver.etablissement` | Une ligne par `identifiant_organisation` | Les 24 colonnes source, en `STRING`, normalisées ; enrichissements géographiques éventuels en colonnes distinctes |
| `silver.activite` | Une ligne par couple professionnel–organisation | `id_prof_sante STRING`, `identifiant_organisation STRING`, `mode_exercice STRING` |
| `silver.consultation` | Une ligne par consultation | `num_consultation INT`, `date_consultation DATE`, `id_patient STRING`, `code_diag STRING`, `id_prof_sante STRING` |
| `silver.hospitalisation` | Une ligne par hospitalisation | `num_hospitalisation INT`, `date_entree DATE`, `id_patient STRING`, `code_diag STRING`, `identifiant_organisation STRING` |
| `silver.satisfaction` | Une ligne par site–année | `finess_geo STRING`, `identifiant_organisation STRING`, `annee SMALLINT`, `region STRING`, `code_region STRING`, `score_all_rea_ajust DOUBLE`, `nb_rep_score_all_rea_ajust INT` |
| `silver.deces` | Une ligne par occurrence de décès acceptée | `deces_key INT`, `date_deces DATE`, `code_commune_deces STRING`, `defunt_key INT`, `numero_acte_deces STRING`, `code_departement STRING`, `code_region STRING`, `libelle_region STRING`, `statut_rattachement STRING` |
| `silver.defunt` | Une ligne par occurrence acceptée, sans fusion d'identité | `defunt_key INT`, `sexe STRING`, `date_naissance DATE`, `code_lieu_naissance STRING`, `lieu_naissance STRING`, `pays_naissance STRING` |

Le couple `code_region`/`region` de la satisfaction provient d'une correspondance contrôlée ; un libellé source non reconnu ne doit pas recevoir un code officiel inventé. Les colonnes de région ajoutées aux décès permettent l'indicateur régional manquant du modèle initial. Elles ne créent pas une jointure entre décès et patients.

Les clés techniques décès restent en INT pour rester compatibles avec le modèle rendu, sous contrôle de capacité et avec un registre persistant ; une évolution de type exige une modification coordonnée Silver/Gold. Les identifiants patients, en revanche, passent bien en STRING selon la décision HMAC déjà prise.

## 5. Espaces HDFS proposés

Ces destinations sont à créer/configurer ; elles ne sont pas présentées comme des dossiers déjà existants.

```text
/user/cloudera/chu/
  bronze/                               # sources existantes, laissées intactes
  silver_work/<lot_id>/<table>/          # tentative avant validation
  silver_lots/<lot_id>/<table>/          # tables d'un lot validé
  rejets/silver/<lot_id>/<source>/       # lignes minimisées et motifs
  quarantaine/silver/<lot_id>/<source>/  # originaux seulement si nécessaires, accès renforcé
  audit/silver/<lot_id>/                 # compteurs, versions, durées et manifeste
```

Les tables `silver.*` pointeront vers les répertoires du lot publié. Ne pas recopier mécaniquement les anciens chemins absolus `/silver` ou `/gold` sans vérifier les droits et la convention commune. Les registres de clés et les correspondances techniques ont un stockage contrôlé et persistant distinct des journaux publics. La clé HMAC ne réside dans aucun de ces répertoires de données.

Parquet est le format cible proposé pour Silver, sous réserve d'un test de compatibilité Spark/Hive, notamment pour DATE et les dates historiques. Gold reste en ORC dans les DDL du groupe. Les noms de colonnes, types et partitions des tables externes devront correspondre exactement aux fichiers écrits.
