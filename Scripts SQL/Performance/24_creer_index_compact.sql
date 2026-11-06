-- Creation initiale : ne pas relancer si l'index existe deja.
-- Les ecritures ulterieures sur fait_consultation exigent une reconstruction.
USE gold;
SET hive.execution.engine=mr;
SET hive.auto.convert.join=false;
SET mapreduce.map.memory.mb=1024;
SET mapreduce.map.java.opts=-Xmx768m -Djava.net.preferIPv4Stack=true;
SET mapreduce.reduce.memory.mb=1536;
SET mapreduce.reduce.java.opts=-Xmx1024m -Djava.net.preferIPv4Stack=true;
SET mapreduce.job.reduce.slowstart.completedmaps=1.0;
SET hive.exec.reducers.max=8;

CREATE INDEX idx_consultation_diag ON TABLE fait_consultation (code_diag)
AS 'COMPACT' WITH DEFERRED REBUILD
IN TABLE index_consultation_diag
LOCATION '/user/cloudera/chu/gold/index/index_consultation_diag';
