-- Verification du metastore et du plan ; activation limitee a cette session.
-- Le seuil par defaut (5 Gio) depasse la taille de cette maquette.
USE gold;
SET hive.execution.engine=mr;
SET hive.auto.convert.join=false;
SET mapreduce.map.memory.mb=1024;
SET mapreduce.map.java.opts=-Xmx768m -Djava.net.preferIPv4Stack=true;
SET mapreduce.reduce.memory.mb=1536;
SET mapreduce.reduce.java.opts=-Xmx1024m -Djava.net.preferIPv4Stack=true;
SET mapreduce.job.reduce.slowstart.completedmaps=1.0;
SET hive.exec.reducers.max=8;

SHOW FORMATTED INDEX ON fait_consultation;
SET hive.optimize.index.filter=true;
SET hive.optimize.index.filter.compact.minsize=0;
EXPLAIN SELECT COUNT(*) FROM fait_consultation
WHERE code_diag='M4157' AND date_consultation >= '2021-01-01'
  AND date_consultation < '2022-01-01';
