-- Construire l'index apres creation et le reconstruire apres chaque rechargement Gold.
-- Tant qu'il n'est pas reconstruit, ne pas activer son utilisation dans les requetes.
USE gold;
SET hive.execution.engine=mr;
SET hive.auto.convert.join=false;
SET mapreduce.map.memory.mb=1024;
SET mapreduce.map.java.opts=-Xmx768m -Djava.net.preferIPv4Stack=true;
SET mapreduce.reduce.memory.mb=1536;
SET mapreduce.reduce.java.opts=-Xmx1024m -Djava.net.preferIPv4Stack=true;
SET mapreduce.job.reduce.slowstart.completedmaps=1.0;
SET hive.exec.reducers.max=8;

ALTER INDEX idx_consultation_diag ON fait_consultation REBUILD;
