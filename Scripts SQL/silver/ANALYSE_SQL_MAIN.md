# Analyse des scripts finaux de main

Analyse du 5 novembre 2026, base `7ed0f68` : les 12 fichiers SQL et le document de justification du dossier `Scripts SQL` ont ete lus. Aucune execution des scripts Gold n'a ete faite pendant cette analyse.

## Contrats retenus pour Silver

| Fichier | Contenu et consequence |
|---|---|
| Database/Create_Database.sql | Cree `gold` ; Silver dispose d'une publication independante. |
| Database/Drop_Database.sql | Supprime `gold CASCADE` ; jamais appele par nos scripts Silver. |
| DDL/01_DDL_dimensions.sql | Dix dimensions : patient, diagnostic, temps, professionnel, etablissement, temps satisfaction, region, temps deces, defunt, lieu deces. Leurs noms/types guident les projections Silver. |
| DDL/02_DDL_pont.sql | Pont `pont_activite_pro` : professionnel, organisation, mode d'exercice. Silver conserve les relations multiples sans multiplier les consultations. |
| DDL/03_DDL_faits.sql | Quatre faits : consultation, hospitalisation, satisfaction, deces. Les grains des sources sont conserves ; aucun taux n'est pre-calcule dans Silver. |
| DDL/04_DDL_rejets.sql | Quatre tables de rejets Gold ; distinctes des rejets techniques minimises produits par Silver. |
| DML/11_DML_dimensions.sql | Attend `patient`, `diagnostic`, `professionnel`, `region`, `codes_postaux`, `defunt`, `consultation`, `hospitalisation`, `deces` et `s2_etablissement`. Calendriers et lignes inconnues sont construits en Gold. |
| DML/12_DML_pont.sql | Attend `s2_activite`. Ajoute un site inconnu aux professionnels sans site valide. Silver verifie deja les couples et les references. |
| DML/13_DML_faits.sql | Attend `s1_consultation`, `s2_hospitalisation`, `s3_satisfaction`, `s4_deces`. Six vues d'alias sont fournies pour les noms prefixes des DML, sans copier les donnees. |
| Performance/21_partitionnement.sql | Tables Gold separees partitionnees par annee des consultations, hospitalisations et deces. Les dates Silver sont des DATE. Pas de partition par patient. |
| Performance/22_buckets.sql | Versions Gold distinctes deces/defunt en 16 buckets. Silver ne declare pas ses fichiers bucketes : cela demande l'ecriture Hive appropriee et une mesure reelle. |
| Performance/23_indexation.sql | Reecrit les tables partitionnees avec `SORT BY` ; ce script organise les fichiers ORC, il ne cree pas un index secondaire autonome. |
| Performance/Justification_partitionnement_indexation.docx | Raisons des partitions annuelles, 16 buckets et tris ORC. Les effets et la taille des references en memoire restent a mesurer ; aucun gain n'est garanti par leur seule declaration. |

## Corrections indispensables avant Gold

Un patch **non applique** est fourni dans `sql/correctifs_gold.patch`. Il concerne les fichiers existants, pas les donnees :

1. `id_patient INT` devient STRING dans la dimension et les deux faits. Le HMAC complet choisi par le groupe ne rentre pas dans INT ; les tables partitionnees sont deja en STRING.
2. Les GROUP BY des dimensions patient/diagnostic/professionnel incluent toutes les colonnes selectionnees, afin de rendre les requetes valides sous Hive 1.1.
3. Le texte non commente apres `WHERE numerotes.rang = 1` devient un commentaire SQL.
4. La region des deces est propagee dans `dim_lieu_deces`, afin de couvrir le besoin du sujet pour 2019. Les lieux non resolus restent presents avec region NULL.
5. Le fait deces controle l'existence du defunt, pas uniquement une cle non NULL.

Application depuis la racine du depot, apres relecture par le responsable Gold :

```bash
git apply --ignore-space-change --check "Scripts SQL/silver/sql/correctifs_gold.patch"
git apply --ignore-space-change "Scripts SQL/silver/sql/correctifs_gold.patch"
```

Le patch modifie les scripts. Il ne migre **aucune table deja creee**, ni aucun fichier ORC existant. `CREATE TABLE IF NOT EXISTS` ne change pas un schema existant : pour un Gold deja charge, preparer une nouvelle version physique avec le bon schema et la recharger depuis Silver avant bascule. Ne pas utiliser un simple changement de metadonnees sur des ORC contenant des entiers pour les faire passer pour des HMAC.

Les DML lisent `silver.*`. Apres generation d'un lot Silver, les HQL de publication creent d'abord une base Hive propre au lot puis les vues `silver.*` et leurs alias. Une activation de plusieurs vues n'est pas une transaction atomique : arreter les lecteurs Gold pendant cette etape et conserver l'ancien script d'activation pour retour.

## Points rencontres dans les sources

- Le COG communes contient 37 544 lignes mais seulement 36 971 codes COM distincts : 573 variantes de TYPECOM. Une jointure brute augmenterait certains nombres de deces. La correspondance adopte COM, puis ARM, COMA et COMD ; les variantes ecartees sont tracees. Un conflit au meme TYPECOM bloque le traitement.
- Des FINESS corses e-Satis commencent par `2A` ou `2B`. Ils sont acceptes en texte ; un controle exclusivement numerique les aurait perdus.
- La source des professionnels contient aussi 44 887 identifiants ADELI alphanumeriques a conserver, et deux valeurs en notation scientifique impossibles a restaurer de facon fiable. Les premiers sont conserves comme chaines opaques ; les deux valeurs irrecuperables sont isolees, sans reconstruire un numero invente.
- `Ocean Indien` n'est pas attribue arbitrairement a une seule region COG. Son libelle reste disponible pour la satisfaction, avec code INSEE NULL et avertissement.
- Hospitalisations : dates `jj/mm/aaaa`. Deces : dates `aaaa-mm-jj`. Les conversions sont strictes, les valeurs impossibles ne sont pas normalisees silencieusement.
- XLSX 2020 : lecteur XML standard, borne en taille, feuille Resultats ; pas d'installation pandas/openpyxl requise.
- Le numero d'acte de deces n'est pas une cle. Le registre HDFS conserve une cle INT par occurrence source (offset), y compris si plusieurs occurrences ont les memes valeurs metier.

## Validation et limites d'execution

Les 18 tests Python passent sur le PC et sous Python 2.6 de la VM. Le test d'integration Spark sur la VM a valide les jointures, les doublons et l'aller-retour ORC avec une date historique. Un second test fictif a valide les cles deces sur deux relances, les occurrences identiques, les references et le HQL de publication. Les resultats detailles, les tentatives reelles et les limites sont consignes dans VALIDATION.md. Aucun script Gold n'a ete execute ni modifie automatiquement.

La VM confirmee par le groupe utilise Spark 1.6.0, Python 2.6.6, Java 1.7.0_67 et Hive 1.1.0-cdh5.12.0. Le test utilisateur PySpark/HMAC en mode local a reussi. Les parametres generaux de securite sont reportes a la fin a la demande du groupe ; la pseudonymisation et la minimisation restent implementees dans les transformations.

## Format corrige apres test Hive reel

La premiere tentative en Parquet a reussi cote Spark mais Hive 1.1 a refuse les colonnes DATE (HIVE-6384). Le stockage Silver est donc ORC, avec HiveContext dans Spark 1.6, comme le format des tables Gold. Les essais Parquet initiaux ne sont pas des lots publiables. Les anciennes tentatives sont conservees pour diagnostic ; le code courant produit exclusivement ORC.
