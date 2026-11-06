USE gold;

-- Ressources de session : noeud YARN de 4096 Mio, conteneur maximal de 3072 Mio.
-- Aucun changement de la configuration globale du cluster.
SET hive.execution.engine=mr;
-- Evite la preparation locale des map joins, forcee a 50 Mio par cet environnement.
-- Les jointures distribuees conservent les memes lignes et les memes controles.
SET hive.auto.convert.join=false;
SET mapreduce.map.memory.mb=1024;
SET mapreduce.map.java.opts=-Xmx768m -Djava.net.preferIPv4Stack=true;
SET mapreduce.reduce.memory.mb=1536;
SET mapreduce.reduce.java.opts=-Xmx1024m -Djava.net.preferIPv4Stack=true;
SET mapreduce.job.reduce.slowstart.completedmaps=1.0;
SET hive.exec.reducers.max=8;


-- Les couples de Silver sont deja uniques et sans reference orpheline.
-- Pas de MAX(mode_exercice) : les conflits ont ete isoles en Silver.
-- La ponderation 1 / nombre de sites est calculee dans Power BI.
INSERT OVERWRITE TABLE pont_activite_pro
SELECT pont.id_prof_sante, pont.identifiant_organisation, pont.mode_exercice
FROM (
SELECT a.id_prof_sante, a.identifiant_organisation, a.mode_exercice
FROM silver.activite a
JOIN dim_professionnel p ON p.id_prof_sante = a.id_prof_sante
JOIN dim_etablissement e ON e.identifiant_organisation = a.identifiant_organisation
WHERE a.identifiant_organisation <> 'inconnu'
UNION ALL
-- Les professionnels sans site valide restent presents dans les analyses.
SELECT p.id_prof_sante, 'inconnu' AS identifiant_organisation, 'inconnu' AS mode_exercice
FROM dim_professionnel p
LEFT JOIN (
    SELECT DISTINCT a.id_prof_sante
    FROM silver.activite a
    JOIN dim_etablissement e ON e.identifiant_organisation = a.identifiant_organisation
    WHERE a.identifiant_organisation <> 'inconnu'
) connus ON connus.id_prof_sante = p.id_prof_sante
WHERE connus.id_prof_sante IS NULL
) pont;
