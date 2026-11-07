-- Indicateur optionnel : moyenne des scores ponderee par les reponses.
-- Les scores absents et les nombres de reponses non positifs sont exclus.
SELECT region, COUNT(*) AS etablissements_avec_score,
       SUM(nb_rep_score_all_rea_ajust) AS nombre_reponses,
       ROUND(SUM(score_all_rea_ajust * nb_rep_score_all_rea_ajust)
             / SUM(nb_rep_score_all_rea_ajust), 4) AS score_satisfaction_pondere
FROM gold.fait_satisfaction
WHERE annee = 2020
  AND score_all_rea_ajust IS NOT NULL
  AND nb_rep_score_all_rea_ajust > 0
GROUP BY region
ORDER BY region;
