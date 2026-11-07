# Requetes metier Hive

Huit requetes HiveQL lisent les tables Gold du projet. Elles sont destinees a
l'exploration et a la verification des indicateurs ; leur resultat peut etre
reproduit ou presente dans Power BI. Elles ne modifient aucune donnee.

| Fichier | Besoin |
| --- | --- |
| `01_consultations_etablissement.hql` | Consultations par site, avec attribution estimee |
| `02_consultations_diagnostic.hql` | Consultations par diagnostic |
| `03_hospitalisations_globales.hql` | Hospitalisations sur une periode |
| `04_hospitalisations_diagnostic.hql` | Hospitalisations par diagnostic |
| `05_hospitalisations_sexe_age.hql` | Hospitalisations par sexe et tranche d'age |
| `06_consultations_professionnel.hql` | Consultations par professionnel pseudonymise |
| `07_deces_region_2019.hql` | Deces par localisation en 2019 (optionnel) |
| `08_satisfaction_region_2020.hql` | Satisfaction ponderee par region en 2020 (optionnel) |

## Utilisation

Dans l'editeur Hive de Hue, copier une requete puis l'executer. Avant de la
lancer sur la VM, executer `00_session_vm.hql` dans la meme session : il ajuste
les ressources Hive/MapReduce pour la VM sans changer le cluster globalement.
Les dates des requetes 01 a 06 sont des exemples a modifier dans chaque fichier.
Les intervalles sont de la forme `[debut, fin[` : la date de fin est exclue.
Les requetes 07 et 08 portent sur les annees 2019 et 2020 demandees par le sujet.

## Definitions et limites

Le livrable 1 definit les taux de soins comme le nombre d'evenements divise par
le nombre de patients distincts du meme groupe et de la meme periode. Les
colonnes `..._par_patient` expriment donc un nombre moyen d'evenements par
patient concerne. Ce n'est pas un pourcentage de la population et il peut etre
superieur a 1. Quand le denominateur est nul, le resultat est NULL.

Les consultations ne portent pas directement la cle de leur etablissement.
La requete 01 repartit chaque consultation sur les sites du professionnel, a
hauteur de 1 / nombre de sites. Il s'agit d'une estimation, non du site reel ;
un patient peut etre compte dans plusieurs sites. La categorie `inconnu` est
conservee. Pour les hospitalisations par age, `dim_patient.age` est l'age issu
de la source patient, pas un age calcule a la date du sejour.

Les deces sans region sont conserves par categorie. La satisfaction est une
moyenne ponderee du score par le nombre de reponses : seules les lignes avec
un score non NULL et un nombre de reponses positif sont retenues dans le
numerateur comme dans le denominateur. Ce score n'est pas un pourcentage de
patients satisfaits individuellement recalcule.

Ces requetes utilisent les tables Gold de reference, toujours distinctes des
variantes d'optimisation. La comparaison avant/apres, ses mesures et ses plans
se trouvent dans `../Performance/Benchmarks/` : ces requetes metier seules ne
constituent pas une preuve de gain ou de respect de la limite de deux minutes.
Si Gold est recharge, reconstruire les variantes et l'index avant de refaire
une comparaison de performance.
