-- Meme perimetre pour numerateur et denominateur ; NULL n'est pas zero.
SELECT s.region, ROUND(SUM(s.score_all_rea_ajust*s.nb_rep_score_all_rea_ajust)
                         /SUM(s.nb_rep_score_all_rea_ajust), 6) AS score_pondere,
       COUNT(*) AS sites
FROM gold.fait_satisfaction s
WHERE s.annee=2020 AND s.score_all_rea_ajust IS NOT NULL AND s.nb_rep_score_all_rea_ajust>0
GROUP BY s.region ORDER BY s.region;
