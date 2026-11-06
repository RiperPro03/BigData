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

Valider et mesurer d'abord les resultats des tables de reference. Ensuite :

- `Performance/21_partitionnement.sql` : variantes par annee.
- `Performance/22_buckets.sql` : variantes deces/defunts en 16 buckets.
- `Performance/23_tri_intra_partition.sql` : variantes partitionnees et triees distinctes, sans ecraser la variante seulement partitionnee.

Le dernier fichier remplace `23_indexation.sql`. Il ne cree pas d'index explicite.
Pour chaque comparaison, partir de variantes partitionnees vides : un INSERT
OVERWRITE avec partitions dynamiques ne remplace que les partitions presentes
dans le flux du lancement. Une ancienne partition absente du nouveau flux doit
etre retiree avant de reconstruire une variante existante.

Mesurer les memes requetes, sur les memes donnees, et verifier des resultats
identiques avant de conclure a un gain. L'egalite des seuls nombres de lignes
ne suffit pas. Les benchmarks restent a executer et a documenter.
