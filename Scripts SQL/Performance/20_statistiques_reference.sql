-- Recalcul des statistiques des tables de reference, sans changer leurs lignes.
USE gold;
SET hive.execution.engine=mr;
SET hive.auto.convert.join=false;
SET mapreduce.map.memory.mb=1024;
SET mapreduce.map.java.opts=-Xmx768m -Djava.net.preferIPv4Stack=true;
SET mapreduce.reduce.memory.mb=1536;
SET mapreduce.reduce.java.opts=-Xmx1024m -Djava.net.preferIPv4Stack=true;
SET mapreduce.job.reduce.slowstart.completedmaps=1.0;
SET hive.exec.reducers.max=8;

ANALYZE TABLE fait_consultation COMPUTE STATISTICS;
ANALYZE TABLE fait_hospitalisation COMPUTE STATISTICS;
ANALYZE TABLE fait_deces COMPUTE STATISTICS;
ANALYZE TABLE fait_satisfaction COMPUTE STATISTICS;
ANALYZE TABLE dim_patient COMPUTE STATISTICS;
ANALYZE TABLE dim_professionnel COMPUTE STATISTICS;
ANALYZE TABLE dim_etablissement COMPUTE STATISTICS;
ANALYZE TABLE pont_activite_pro COMPUTE STATISTICS;
ANALYZE TABLE dim_defunt COMPUTE STATISTICS;
ANALYZE TABLE dim_lieu_deces COMPUTE STATISTICS;
