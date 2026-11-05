# Validation de la premiere livraison Silver

Date : 5 novembre 2026. Base SQL analysee : `main`, commit `7ed0f68`. Les essais de developpement ne modifient ni Bronze, ni Gold, ni les vues communes `silver.*`.

## Tests passes

| Controle | Environnement / resultat |
|---|---|
| Regles unitaires | 18 tests, passes sur Python 3.13 du poste et Python 2.6.6 de la VM. HMAC, normalisation commune aux trois flux, exclusions, dates, FINESS corses, ADELI alphanumeriques, NULL et domaines de mesure, CSV cite, XLSX, priorites COG, contrats DML. |
| Integration Spark | Spark 1.6.0 / Java 7, mode local a deux coeurs. Categories de doublon/conflit/rejet attendues, cardinalite apres jointure, lecture CSV par offset, ecriture/relecture ORC et date du 1er janvier 1882. Marqueur `CHU_SILVER_INTEGRATION_OK`. |
| Registre deces HDFS | Quatre occurrences fictives, trois acceptees et une date de deces refusee. Deux occurrences identiques conservent deux cles distinctes. Deux executions retrouvent les memes cles. Une naissance invalide reste NULL ; un lieu non resolu reste present. Marqueur `CHU_DECES_REGISTRE_OK`. |
| Finalisation 08 fictive | 14 tables coherentes, cles uniques, dix relations referentielles, format des HMAC et rapprochement des compteurs verifies ; generation des HQL de publication. Aucun alias commun active. |
| Lecture Hive 1.1 ORC | Creation de 14 tables externes et six alias dans une base de test propre. Trois deces retrouves via `s4_deces`, jointure deces/defunt = 3, naissance NULL = 1, patient avec HMAC de longueur 64 = 1. |
| Patch Gold | `git apply --ignore-space-change --check` passe contre les scripts du groupe ; le patch n'est pas applique. |

Le test Hive a du desactiver `hive.auto.convert.join` **pour cette session**, car la conversion en MapJoin local echouait sur la VM. Le meme resultat a ete verifie en jointure MapReduce. Aucun parametre global n'a ete change. Ce point doit etre diagnostique et documente avant les comparaisons de performance du livrable 2.

## Controles sur les fichiers du projet

Verification de structure effectuee sur les copies sources locales deja rapprochees de Bronze par l'audit du 4 novembre :

| Source | Enregistrements | Nombre de colonnes incorrect | Enregistrements multilignes |
|---|---:|---:|---:|
| Etablissements | 416 665 | 0 | 0 |
| Activites professionnelles | 1 823 588 | 0 | 0 |
| Hospitalisations | 2 479 | 0 | 0 |
| Deces | 25 088 208 | 0 | 0 |

Le lecteur distribue ligne/offset est donc adapte au lot fourni. Une future source CSV multiligne provoque un echec explicite et necessite une adaptation du lecteur ; elle n'est pas silencieusement decoupee en plusieurs personnes.

Les conversions metier locales passent pour 2 479 hospitalisations et pour les 1 157, 1 152 et 1 150 lignes des campagnes e-Satis 2017/2019/2020, avant leurs jointures et controles d'unicite Spark. Le lecteur XML a ete teste sur le vrai XLSX 2020 sans dependance externe.

Le COG contient 37 544 lignes et 36 971 codes COM distincts. Les 573 variantes de TYPECOM sont tracees et n'augmentent pas les faits. Le referentiel postal produit 35 007 communes a partir de 39 192 occurrences, avec repartition explicite entre repetitions et alternatives non retenues.

## Choix corriges par les tests reels

- Le separateur issu de JSON est Unicode ; Python 2.6 exige un separateur byte-string pour son module CSV. Le lecteur effectue cette conversion et le test de regression utilise un separateur charge depuis JSON.
- Spark 1.6 ne retrouvait pas ses scripts dans un chemin contenant `Scripts%20SQL`. Le preparateur exporte une liste fermee de code dans un dossier sans espaces.
- Les identifiants ADELI alphanumeriques et les FINESS corses sont conserves en texte. Seuls les vrais formats irrecuperables restent en rejet ; aucune lettre n'est supprimee pour forcer une conversion numerique.
- Parquet a ete refuse par Hive 1.1 pour les colonnes DATE (HIVE-6384). La livraison utilise ORC et HiveContext, valides dans Spark puis Hive. Les tentatives Parquet precedentes ne sont pas activables comme lots Silver courants.
- YARN expose 3 072 Mio et 3 vcores : un executeur avec deux coeurs permet d'utiliser la capacite observee, alors que le second executeur demande lors du premier essai restait sans allocation memoire.

## Execution reelle ORC des etapes 01 a 06

Execution YARN terminee avec code de sortie **0**, sur la version corrigee ORC/ADELI, avec un executeur a deux coeurs. Audit HDFS :

`/user/cloudera/chu/silver_runs/initial_20261105/a202611051528577fcb78/audit/`

| Table | Lignes acceptees / relues |
|---|---:|
| activite | 868 844 |
| codes_postaux | 35 007 |
| commune | 36 971 |
| consultation | 1 027 157 |
| diagnostic | 15 490 |
| etablissement | 416 665 |
| hospitalisation | 2 479 |
| patient | 100 000 |
| professionnel | 1 048 573 |
| region | 20 |
| satisfaction | 3 459 |
| specialite | 93 |

Toutes les 1 027 157 consultations, les 2 479 hospitalisations et les 3 459 lignes de satisfaction des trois campagnes sont conservees. Les 100 000 patients sont pseudonymises.

Points de qualite a presenter au groupe avant activation :

- Professionnels : deux identifiants en notation scientifique sont rejetes ; les 44 887 ADELI alphanumeriques sont conserves. Une specialite non resolue devient `inconnu`.
- Activite : 358 814 lignes sans organisation, 595 476 relations vers un professionnel absent de la reference et 454 lignes de couples a modes contradictoires sont isolees. Leurs references et motifs restent disponibles dans les rejets. Ces chiffres concernent des relations, pas autant de personnes distinctes. La couverture de la reference professionnelle doit etre expliquee dans le rapport ; la possible troncature a 1 048 575 lignes etait deja relevee dans le livrable 1.
- Satisfaction : 11, 12 et 13 lignes des campagnes 2017, 2019 et 2020 gardent un libelle regional non rattache au COG (notamment Ocean Indien), sans perdre leur score ni inventer de code regional. La reference region contient donc 20 libelles, dont les 18 regions COG, `inconnu` et le regroupement non resolu.
- Ce resultat est marque `PARTIAL_NOT_PUBLISHED` : la branche deces complete et la finalisation 08 sur le lot reel restent a executer avant activation commune.

## Perimetre restant

Le traitement deces est valide sur donnees fictives, y compris son registre et la lecture Hive. Le passage complet des 25 millions de lignes, ses temps, ses rejets reels et sa consommation disque restent a mesurer. Le controle de structure de 25 millions de lignes ne constitue pas ce traitement Silver.

Le pipeline genere des scripts de publication, mais la bascule de plusieurs vues Hive demande une fenetre sans lecture Gold et une procedure de retour ; elle n'a pas ete executee sur les donnees reelles. Les migrations Gold et les benchmarks avant/apres restent des travaux distincts. Les reglages generaux de securite sont reportes par decision du groupe ; la pseudonymisation et la minimisation sont dans les scripts.
