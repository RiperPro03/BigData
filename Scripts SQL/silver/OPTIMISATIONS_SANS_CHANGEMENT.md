# Optimisations Silver : invariants et validation

Les optimisations ci-dessous ne changent ni les regles `rules.py`, ni les
contrats `contracts.py`, ni les clefs, les rejets, les categories de qualite,
la pseudonymisation ou le registre HDFS des deces. Les durees relevees dans
les rapports sont naturellement susceptibles de changer.

1. **Deces : suppression d'un calcul interne non utilise.** La colonne privee
   `_payload` sert a `unique()` pour d'autres sources. La branche deces conserve
   toutes les occurrences et n'appelle pas `unique()` ; elle ne calcule donc
   plus ce hash. La colonne reste presente dans le schema technique, a NULL,
   et n'est exposee ni dans les tables metier ni dans les rejets. Le HMAC n'est
   pas concerne.
2. **Une lecture ORC au lieu de plusieurs pour les bilans.** `save()` calcule
   le nombre de lignes et les valeurs NULL dans une seule aggregation. Pour
   `deces`, le nombre de rattachements regionaux non resolus en 2019 est aussi
   compte dans cette aggregation. Le resultat est identique a l'ancien
   `filter(...).count()` meme lorsque la table est vide.
3. **Aucun controle supprime.** Les verifications de registre, de cardinalite,
   de schema, les controles finaux et la gestion des rejets restent actifs.
   Les partitions et la methode d'attribution des cles ne sont pas modifiees.

L'execution anterieure a subi 16 arrets d'executeurs pour depassement memoire ;
le reglage YARN a ete corrige separement. Reutiliser le registre deja termine
evite de le recreer, sans supprimer sa verification.

## Tests a executer avant de considerer cette version validee

```bash
python tests/test_rules.py
python tests/test_reprise.py
python tests/test_performance_semantique.py
spark-submit --master 'local[2]' \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.eventLog.enabled=false \
  --py-files chu_silver.zip tests/integration_performance_equivalence.py
```

La comparaison Spark cree uniquement des donnees fictives. Elle execute les
calculs anterieurs et optimises avec un meme registre et compare les lignes,
y compris doublons, les cles, les rejets/motifs, les bilans, les NULL et les
schemas ; elle couvre les dates invalides, les rattachements non resolus,
la cardinalite attendue et une table vide. Elle cree un dossier HDFS de test
isole et affiche son chemin ; les tests ne modifient pas les donnees du projet.
Le resultat attendu est `CHU_PERFORMANCE_EQUIVALENCE_OK`.

Le 5 novembre 2026, la comparaison a reussi en Spark local et sur YARN, sur
7 000 lignes fictives pour le dernier passage YARN. Les 19 tests des regles,
5 tests de reprise et le test unitaire de l'empreinte ont reussi sous Python
2.6 sur la VM. Le test de checkpoint a aussi reussi avec les optimisations.

Sur la VM, `python tests/benchmark_empreinte_deces.py` a mesure en moyenne
1,706 s avec empreinte contre 0,863 s sans empreinte, pour deux passages sur
100 000 lignes fictives. Il s'agit d'une micro-mesure CPU de la seule
normalisation, pas d'un gain mesure sur le traitement complet Spark.

Les checkpoints recents incluent une empreinte du code : ils refusent de
melanger les anciennes et nouvelles versions sans validation. La reprise de la
tentative historique documentee reste explicite avec `--legacy-attempt` ; elle
conserve l'avertissement sur les identifiants professionnels. Il faut utiliser
la meme livraison de code entre les nouvelles phases 01, 02 et 03.

Le test fictif ne prouve ni le temps sur 25 millions de lignes ni la capacite
de la VM a traiter le volume complet. L'execution reelle, sa consommation et
son temps doivent etre mesures apres remise en service de la VM.
