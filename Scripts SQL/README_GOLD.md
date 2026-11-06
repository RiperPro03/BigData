# Gold : scripts finaux et lancement manuel

Les tables lisent le Silver publie dans `silver.*` et utilisent :

```text
/user/cloudera/chu/gold/
  tables/   dimensions, pont, faits et variantes de performance
  rejets/   faits refuses avec motif et horodatage
```

## Decisions appliquees

- Identifiants patients et professionnels pseudonymises en STRING, HMAC integral.
- Deces minimaux : aucune date/lieu de naissance, aucun numero d'acte et aucun age au deces.
- Sexe et age des hospitalisations fournis par `dim_patient` ; age de la source, pas age recalcule au sejour.
- Deces : departement, code region, libelle regional et categorie de localisation dans `dim_lieu_deces`.
- Les lieux sans region restent dans les dimensions et les faits. `code_region` reste NULL, le libelle devient `Region non resolue`.
- `categorie_localisation` distingue REGION_FRANCAISE, CODE_PAYS, OUTRE_MER_HORS_REGIONS et NON_RESOLU. Ces categories ne sont pas des regions INSEE inventees.
- Les regions proviennent du COG 2024 utilise dans Silver : ce n'est pas une reconstitution des limites historiques de 2019.
- Pas de nouveau choix arbitraire de doublons dans Gold : Silver fournit les cles uniques et isole les conflits.
- Verification des dimensions de chaque fait, y compris `dim_defunt`, avec sorties de rejets.
- Rejets d'activite Silver conserves. Les professionnels sans site valide rejoignent le site `inconnu` dans le pont.
- Ponderation des consultations par etablissement et satisfaction calculees dans Power BI.

## Ressources de session

Les DML, controles et variantes utilisent MapReduce avec des conteneurs map de
1024 Mio (heap Java 768 Mio), reduce de 1536 Mio (heap 1024 Mio), au plus huit
reducers et leur demarrage apres la fin des maps. Ces parametres sont adaptes
au noeud YARN de 4096 Mio ; les valeurs par defaut de la VM etaient de 128 Mio
par conteneur avec un heap de 50 Mio. Chaque script definit sa propre session.
La conversion automatique en map join est desactivee : le processus local de
preparation des tables de hachage restait force a 50 Mio dans cette VM, meme avec
hive.mapred.local.mem=768. Les jointures distribuees utilisent les ressources
MapReduce definies ci-dessus. Cela change le plan d'execution, pas les resultats.
Aucun parametre global du cluster n'est modifie. Conserver ces valeurs dans les
mesures de performance pour comparer des configurations identiques.

## Ordre manuel

Une seule alimentation a la fois. Le Silver doit etre publie et rester stable
pendant le chargement. Suspendre l'actualisation BI jusqu'a validation finale :
les INSERT OVERWRITE de plusieurs tables ne sont pas une transaction commune.
Aucun lancement automatique n'est fourni.

Executer les fichiers dans cet ordre, en s'arretant a la premiere erreur :

1. `Database/Create_Database.sql`
2. `DDL/01_DDL_dimensions.sql`
3. `DDL/02_DDL_pont.sql`
4. `DDL/03_DDL_faits.sql`
5. `DDL/04_DDL_rejets.sql`
6. `DML/11_DML_dimensions.sql`
7. `DML/12_DML_pont.sql`
8. `DML/13_DML_faits.sql`
9. `Controles/30_controles_gold.sql`

Exemple pour chaque fichier, depuis SSH :

```bash
beeline -u 'jdbc:hive2://localhost:10000/default' -n cloudera --force=false \
  -f '/home/cloudera/Scripts SQL/DDL/01_DDL_dimensions.sql'
```

Les blocs de controle peuvent aussi etre lances individuellement apres l'etape
concernee. Les doublons, orphelins et ecarts de reconciliation doivent valoir 0.
Un rejet non nul doit etre explique avant de valider le chargement. Conserver le
journal du lancement et les resultats des controles pour le livrable 2.

Les faits et dimensions sont recharges avec INSERT OVERWRITE. Rejouer seulement
les DDL ne recharge pas les donnees. CREATE IF NOT EXISTS ne modifie pas une table
existante : verifier les schemas et emplacements si un ancien Gold existe deja.
`Database/Drop_Database.sql` est une action destructive sur les objets Hive,
pas une etape de chargement ; ne pas l'executer en routine.

## Couverture des besoins utilisateurs

| Besoin | Tables et mesure a construire dans Power BI |
| --- | --- |
| Consultations / etablissement / periode | Consultation, temps, professionnel, pont et etablissement. Part de chaque site : 1 / nombre de sites valides du professionnel ; inconnu si aucun site. |
| Consultations / diagnostic / periode | Consultation, temps et diagnostic. |
| Hospitalisations globales / periode | Hospitalisation et temps, filtrage sur date_entree. |
| Hospitalisations / diagnostic | Hospitalisation, temps et diagnostic. |
| Hospitalisations / sexe et age | Hospitalisation et patient ; tranches derivees de patient.age. |
| Consultations / professionnel | Consultation et professionnel, affichage du pseudonyme. |
| Deces / region / 2019 | Fait deces, temps deces et lieu deces. Compter les lignes, afficher aussi les categories sans region. |
| Satisfaction / region / 2020 | Fait satisfaction, temps satisfaction et region. Moyenne du score ajustee ponderee par le nombre de repondants. |

Les taux de soins suivent la definition du livrable 1 : evenements / patients
distincts dans le meme filtre. Ils peuvent depasser 1 et ne sont pas une
proportion populationnelle. Pour les consultations par etablissement, ponderer
le numerateur et conserver un compte distinct des patients dans le filtre.
Le rattachement par professionnel est une attribution analytique, pas une preuve
du site reel de chaque consultation.

Satisfaction : inclure dans le numerateur et le denominateur les memes lignes,
avec score non NULL et nombre de repondants strictement positif. Un score NULL
n'est jamais remplace par zero.

## Performance, apres la reference

1. `Performance/20_statistiques_reference.sql` : recalculer les statistiques des tables de reference sans changer les lignes.
2. Executer la phase `reference` des benchmarks : elle constitue une premiere mesure avant creation des variantes.
3. `Performance/21_partitionnement.sql` : variantes par annee.
4. `Performance/22_buckets.sql` : deces et defunts, 16 buckets sur `defunt_key`.
5. `Performance/23_tri_intra_partition.sql` : variantes triees distinctes ; aucun index n'est cree par ce tri.
6. `Performance/24_creer_index_compact.sql`, puis `25_reconstruire_index_compact.sql` : creation et construction d'un index compact sur le diagnostic de consultation.
7. `Performance/26_verifier_index_compact.sql` : inspecter le metastore et le plan pour la requete selective.
8. Executer la phase `comparaison`, verifier l'egalite des resultats, puis mesurer et documenter les variantes.

L'index est experimental sur cette version Hive 1.1. Son activation est limitee
aux sessions de benchmark (`hive.optimize.index.filter=true` et seuil minimal de
0). Elle n'est pas activee globalement. La construction et le stockage ont un
cout ; un gain n'est pas garanti. Apres chaque INSERT OVERWRITE sur
`fait_consultation`, reconstruire l'index avec le script 25 avant de l'utiliser.
Le script 24 est reserve a la premiere creation : verifier `SHOW INDEX ON
fait_consultation` avant de le rejouer.

Pour chaque comparaison, partir de variantes partitionnees vides : un INSERT
OVERWRITE avec partitions dynamiques ne remplace que les partitions presentes
dans le flux. Une ancienne partition absente du nouveau flux doit etre retiree
avant de reconstruire une variante existante.

Les requetes de `Performance/Benchmarks/` couvrent les besoins du projet et comprennent
une jointure complementaire pour les buckets. Elles utilisent des fenetres
identiques dans les deux versions et conservent la meme definition de mesure.
Pour executer depuis SSH apres avoir prepare le repertoire de journalisation :

```bash
mkdir -p /home/cloudera/.chu/gold_perf
cd '/home/cloudera/Scripts SQL/Performance/Benchmarks'
python executer_benchmarks.py --phase reference --output /home/cloudera/.chu/gold_perf/resultats.json
# Executer ensuite les scripts 21 a 26 dans l'ordre, avec leurs controles.
python executer_benchmarks.py --phase comparaison --output /home/cloudera/.chu/gold_perf/resultats.json
```

Le programme reprend les mesures terminees, compare une empreinte des resultats
et interrompt la campagne en cas de difference ou de modification des tables.
Il ne conserve pas les lignes de resultats dans le journal. Le temps rapporte
inclut le lancement du client Beeline et la lecture des resultats. Le cache du
systeme n'est pas vide ; l'ordre et les horaires sont conserves. Les mesures
sont repetees trois fois, avec des comparaisons alternees ; comparer les medianes
et ne pas presenter la satisfaction, qui utilise la meme table, comme une
optimisation. Les buckets ne garantissent pas un plan de jointure specifique :
examiner le plan avant de leur attribuer un gain.

Avant de conclure, verifier la concordance sur l'ensemble des tables, pas
seulement sur les requetes echantillons, puis produire les graphiques. Si un
chargement est relance, verifier et nettoyer explicitement les anciennes
partitions absentes du nouveau lot avant toute nouvelle comparaison.
