# Colonnes des sources — DATA 2024

Inventaire des colonnes réellement lues dans `DATA 2024`. Les lexiques servent au sens. Les PDF n'ont pas de colonnes. `BDD PostgreSQL/DATA2023` est une copie du dump `DATA2023`.

Les huit besoins du sujet sont : consultations dans un établissement sur une période, consultations par diagnostic, hospitalisations sur une période, hospitalisations par diagnostic, hospitalisations par sexe et par âge, consultations par professionnel, décès par région en 2019, satisfaction par région en 2020. `utile` vaut oui si la colonne sert un de ces besoins, ou une clé pour le calculer. Sinon non. Doute : oui.

| Besoin | Colonnes qui le portent |
|---|---|
| Consultations dans l'établissement X sur Y | `Consultation.Date`, `Id_patient`, `Id_prof_sante` ; `activite_professionnel_sante` ; `etablissement_sante` |
| Consultations pour un diagnostic X sur Y | `Consultation.Code_diag`, `Date` ; `Diagnostic` |
| Hospitalisations sur Y | `Hospitalisations.Date_Entree`, `Id_patient` |
| Hospitalisations par diagnostic | `Hospitalisations.Code_diagnostic`, `Date_Entree` |
| Hospitalisations par sexe et par âge | `Hospitalisations.Id_patient` ; `Patient.Sexe`, `Patient.Date` |
| Consultations par professionnel | `Consultation.Id_prof_sante`, `Date` ; `Professionnel_de_sante` ; `professionnel_sante.csv` |
| Décès par région en 2019 | `deces.date_deces`, `deces.code_lieu_deces` |
| Satisfaction par région en 2020 | e-Satis 2020 : `region`, `score_all_rea_ajust` ou `score_all_ajust`, `nb_rep_score_all_*`, `finess` |

Les campagnes IQSS, DPA, DAN, RCP, ETE et IDM sont dans le dossier Satisfaction. Leurs mesures ne sont aucun des huit besoins : toutes leurs colonnes sont en non.

## PostgreSQL — `DATA2023`

Dump custom PostgreSQL 14.4. Colonnes lues dans les `CREATE TABLE`.

### Consultation

un acte de consultation.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Num_consultation | identifiant de la consultation | oui | grain du taux de consultation |
| Id_patient | patient | oui | rapproche le taux au patient, au sexe et à l'âge |
| Id_prof_sante | professionnel | oui | taux de consultation par professionnel, et rattachement à un établissement via l'activité |
| Code_diag | diagnostic | oui | taux de consultation pour un diagnostic |
| Date | date de l'acte | oui | période Y |
| Motif | motif de la consultation | oui | précise l'acte ; le taux par diagnostic s'appuie sur Code_diag |
| Heure_debut | heure de début | oui | durée de l'acte, citée dans le sujet |
| Heure_fin | heure de fin | oui | durée de l'acte, avec l'heure de début |
| Id_mut | mutuelle | non | aucun des huit besoins ne porte sur la mutuelle |

### Patient

identité et caractéristiques du patient.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Id_patient | identifiant du patient | oui | clé de jointure des consultations et des séjours |
| Sexe | sexe | oui | taux d'hospitalisation par sexe |
| Date | date de naissance, texte | oui | l'âge à la date de l'acte se calcule à partir d'elle |
| Age | âge à l'extraction | oui | âge figé dans le dump ; l'âge à la date de l'acte se calcule avec Date |
| Code_postal | code postal de résidence | oui | seul ancrage géographique du patient |
| Nom | nom | non | le sujet demande un patient anonymisé |
| Prenom | prénom | non | le sujet demande un patient anonymisé |
| Adresse | adresse | non | identité, hors des taux |
| Ville | ville | non | identité, hors des taux |
| Pays | pays | non | une seule valeur observée, pas un axe |
| EMail | courriel | non | identité, hors des taux |
| Tel | téléphone | non | identité, hors des taux |
| Num_Secu | numéro de sécurité sociale | non | identité, hors des taux |
| Groupe_sanguin | groupe sanguin | non | aucun des huit besoins |
| Poid | poids | non | aucun des huit besoins |
| Taille | taille | non | aucun des huit besoins |

### Diagnostic

référentiel des diagnostics.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Code_diag | code diagnostic | oui | axe des taux par diagnostic |
| Diagnostic | libellé | oui | libellé de cet axe |

### Professionnel_de_sante

annuaire des professionnels, base opérationnelle.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Identifiant | identifiant du professionnel | oui | axe du taux de consultation par professionnel |
| Nom | nom d'exercice | oui | libellé de cet axe |
| Prenom | prénom d'exercice | oui | libellé de cet axe |
| Profession | profession | oui | regroupement du taux par professionnel |
| Code_specialite | code spécialité | oui | relie le professionnel au référentiel des spécialités |
| Type_identifiant | ADELI, RPPS ou autre | oui | aligne la clé avec l'annuaire CSV |
| Civilite | civilité | oui | attribut du professionnel |
| Categorie_professionnelle | catégorie | oui | attribut du professionnel |

### Specialites

référentiel des spécialités.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Code_specialite | code spécialité | oui | clé vers le professionnel |
| Specialite | libellé de la spécialité | oui | libellé de l'axe professionnel |
| Fonction | fonction | oui | regroupe les spécialités |

### Mutuelle

référentiel des mutuelles.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Id_Mut | identifiant mutuelle | non | aucun des huit besoins |
| Nom | nom | non | aucun des huit besoins |
| Adresse | adresse | non | aucun des huit besoins |

### Adher

association patient-mutuelle.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Id_patient | patient | non | sert uniquement la mutuelle, hors besoin |
| Id_mut | mutuelle | non | sert uniquement la mutuelle, hors besoin |

### Prescription

association consultation-médicament.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Num_consultation | consultation | non | aucun besoin sur les prescriptions |
| Code_CIS | médicament | non | aucun besoin sur les médicaments |

### Medicaments

référentiel des médicaments.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Code_CIS | code CIS | non | aucun des huit besoins |
| Denomination | dénomination | non | aucun des huit besoins |
| Forme_pharmaceutique | forme | non | aucun des huit besoins |
| Voies_d_administration | voie | non | aucun des huit besoins |
| Statut_administratif | statut AMM | non | aucun des huit besoins |
| Type_de_procedure | type de procédure | non | aucun des huit besoins |
| Etat_de_commercialisation | commercialisation | non | aucun des huit besoins |
| Date_AMM | date d'AMM | non | aucun des huit besoins |
| StatutBdm | statut dans la base des médicaments | non | aucun des huit besoins |
| Num_autorisation_europeenne | autorisation européenne | non | aucun des huit besoins |
| Titulaire | titulaire | non | aucun des huit besoins |
| Surveillance_renforcee | surveillance renforcée | non | aucun des huit besoins |

### Laboratoire

référentiel des laboratoires, sans lien vers les médicaments.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Id_labo | identifiant | non | table isolée, aucun des huit besoins |
| Laboratoire | nom | non | table isolée, aucun des huit besoins |
| Pays | pays | non | table isolée, aucun des huit besoins |

### Salle

salle d'une consultation.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Id_salle | identifiant de salle | non | aucun des huit besoins |
| Num_consultation | consultation | non | aucun des huit besoins |
| Code_bloc | bloc | non | aucun des huit besoins |
| Num_etage | étage | non | aucun des huit besoins |
| Num_salle | numéro de salle | non | aucun des huit besoins |

### AAAA

brouillon, sans lien avec les actes.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Id | identifiant | non | brouillon |
| Num | numéro | non | brouillon |
| Code | code | non | brouillon |
| Nom | nom | non | brouillon |
| Prenom | prénom | non | brouillon |
| Adresse | adresse | non | brouillon |
| Code_diag | code diagnostic | non | brouillon, pas le référentiel Diagnostic |

### date

brouillon de dates, ce n'est pas le calendrier.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| date1 | date texte | non | brouillon |
| date2 | date texte | non | brouillon |

## Hospitalisation — `Hospitalisation/Hospitalisations.csv`

Séjours. Séparateur `;`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Num_Hospitalisation | identifiant du séjour | oui | grain du taux d'hospitalisation |
| Id_patient | patient | oui | rapproche le séjour au sexe et à l'âge |
| identifiant_organisation | site | oui | établissement du séjour, et sa région |
| Code_diagnostic | code diagnostic | oui | taux d'hospitalisation par diagnostic |
| Suite_diagnostic_consultation | libellé du diagnostic | oui | libellé de cet axe |
| Date_Entree | date d'entrée | oui | période Y |
| Jour_Hospitalisation | durée du séjour en jours | oui | le sujet cite les durées ; le taux compte les séjours |

## Établissements — `Etablissement de SANTE/etablissement_sante.csv`

Référentiel des sites. Séparateur `;`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| adresse | adresse | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| cedex | cedex | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| code_commune | code commune INSEE | oui | département et région du site |
| code_postal | code postal | oui | département et région quand le code commune manque |
| commune | commune | oui | libellé du lieu |
| complement_destinataire | complement destinataire | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| complement_point_geographique | complement point geographique | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| email | email | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| enseigne_commerciale_site | enseigne commerciale site | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| finess_etablissement_juridique | FINESS juridique | oui | jointure avec le FINESS des enquêtes de satisfaction |
| finess_site | FINESS du site | oui | jointure avec le FINESS géographique |
| identifiant_organisation | identifiant du site | oui | clé de l'établissement X et jointure des séjours |
| indice_repetition_voie | indice repetition voie | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| mention_distribution | mention distribution | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| numero_voie | numero voie | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| pays | pays du site | non | pas un axe des taux |
| raison_sociale_site | raison sociale | oui | libellé de l'établissement X |
| siren_site | siren site | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| siret_site | siret site | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| telecopie | telecopie | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| telephone | telephone | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| telephone_2 | telephone 2 | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| type_voie | type voie | non | adresse, contact ou identifiant administratif, hors des huit besoins |
| voie | voie | non | adresse, contact ou identifiant administratif, hors des huit besoins |

## Activité — `Etablissement de SANTE/activite_professionnel_sante.csv`

Lien professionnel-site. Séparateur `;`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| identifiant | professionnel | oui | relie le professionnel à un site |
| identifiant_organisation | site | oui | la consultation n'a pas d'établissement : c'est ce lien qui le lui donne |
| mode_exercice | salarié, libéral ou bénévole | oui | précise l'exercice pour le taux par professionnel |

## Professionnels — `Etablissement de SANTE/professionnel_sante.csv`

Annuaire. Séparateur `;`, ISO-8859-1. 1 048 575 lignes, plafond d'une feuille Excel.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| identifiant | identifiant | oui | clé du taux de consultation par professionnel |
| nom | nom | oui | libellé de cet axe |
| prenom | prénom | oui | libellé de cet axe |
| profession | profession | oui | regroupement de l'axe |
| specialite | spécialité | oui | regroupement de l'axe |
| type_identifiant | type d'identifiant | oui | aligne la clé avec la base et avec l'activité |
| civilite | civilité | oui | attribut du professionnel |
| categorie_professionnelle | catégorie | oui | attribut du professionnel |
| commune | commune d'exercice | oui | ancrage géographique du professionnel |

## Décès — `DECES EN FRANCE/deces.csv`

Répertoire INSEE. Séparateur `,`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| date_deces | date du décès | oui | filtre de l'année 2019 |
| code_lieu_deces | code commune du lieu de décès | oui | la région se déduit de ce code |
| sexe | sexe INSEE | non | le besoin est le nombre par région, pas par sexe |
| nom | nom | non | identité, le décompte par région n'en a pas besoin |
| prenom | prénom | non | identité, le décompte par région n'en a pas besoin |
| numero_acte_deces | numéro d'acte | non | identité administrative |
| date_naissance | date de naissance | non | le besoin ne découpe pas les décès par âge |
| code_lieu_naissance | code du lieu de naissance | non | le lieu demandé est celui du décès |
| lieu_naissance | lieu de naissance | non | le lieu demandé est celui du décès |
| pays_naissance | pays de naissance | non | le lieu demandé est celui du décès |

## Satisfaction — notes e-Satis

Notes patient agrégées par établissement. Le taux demandé est la note globale par région en 2020. Les millésimes 2017 et 2019 portent la même note : ils restent utiles comme historique. `Depot` non.

### `Satisfaction/2019/resultats-esatis48h-mco-open-data-2019.csv`

Millésime 2019.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| finess | FINESS juridique | oui | clé vers l'établissement |
| rs_finess | raison sociale du FINESS juridique | oui | libellé de l'établissement |
| finess_geo | FINESS géographique | oui | clé du site |
| rs_finess_geo | raison sociale du FINESS géographique | oui | libellé du site |
| region | région | oui | axe du taux de satisfaction par région. Millésime 2019, le taux chiffré demandé est 2020 |
| participation | participation obligatoire ou facultative | oui | filtre pour comparer les taux. Millésime 2019, le taux chiffré demandé est 2020 |
| Depot | au moins une adresse mail déposée | non | dépôt de mail, ni taux ni axe |
| nb_rep_score_all_rea_ajust | nombre de réponses, satisfaction globale | oui | poids pour agréger la note à la région. Millésime 2019, le taux chiffré demandé est 2020 |
| score_all_rea_ajust | note ajustée, satisfaction globale | oui | mesure du taux de satisfaction. Millésime 2019, le taux chiffré demandé est 2020 |
| classement | classe A à D, ou effectif insuffisant | oui | classe de la note globale. Millésime 2019, le taux chiffré demandé est 2020 |
| evolution | changement de classe d'une année sur l'autre | oui | écart dans le temps, le sujet couvre plusieurs années. Millésime 2019, le taux chiffré demandé est 2020 |
| nb_rep_score_accueil_rea_ajust | nombre de réponses, accueil | oui | poids d'un détail de la note patient. Millésime 2019, le taux chiffré demandé est 2020 |
| score_accueil_rea_ajust | note ajustée, accueil | oui | détail de la satisfaction patient. Millésime 2019, le taux chiffré demandé est 2020 |
| nb_rep_score_PECinf_rea_ajust | nombre de réponses, prise en charge infirmiers | oui | poids d'un détail de la note patient. Millésime 2019, le taux chiffré demandé est 2020 |
| score_PECinf_rea_ajust | note ajustée, prise en charge infirmiers | oui | détail de la satisfaction patient. Millésime 2019, le taux chiffré demandé est 2020 |
| nb_rep_score_PECmed_rea_ajust | nombre de réponses, prise en charge médecins | oui | poids d'un détail de la note patient. Millésime 2019, le taux chiffré demandé est 2020 |
| score_PECmed_rea_ajust | note ajustée, prise en charge médecins | oui | détail de la satisfaction patient. Millésime 2019, le taux chiffré demandé est 2020 |
| nb_rep_score_chambre_rea_ajust | nombre de réponses, chambre | oui | poids d'un détail de la note patient. Millésime 2019, le taux chiffré demandé est 2020 |
| score_chambre_rea_ajust | note ajustée, chambre | oui | détail de la satisfaction patient. Millésime 2019, le taux chiffré demandé est 2020 |
| nb_rep_score_repas_rea_ajust | nombre de réponses, repas | oui | poids d'un détail de la note patient. Millésime 2019, le taux chiffré demandé est 2020 |
| score_repas_rea_ajust | note ajustée, repas | oui | détail de la satisfaction patient. Millésime 2019, le taux chiffré demandé est 2020 |
| nb_rep_score_sortie_rea_ajust | nombre de réponses, sortie | oui | poids d'un détail de la note patient. Millésime 2019, le taux chiffré demandé est 2020 |
| score_sortie_rea_ajust | note ajustée, sortie | oui | détail de la satisfaction patient. Millésime 2019, le taux chiffré demandé est 2020 |
| taux_reco_brut | part des patients qui recommandent l'établissement | oui | autre note patient, proche du taux de satisfaction. Millésime 2019, le taux chiffré demandé est 2020 |
| nb_reco_brut | nombre de patients qui recommandent l'établissement | oui | effectif de la recommandation. Millésime 2019, le taux chiffré demandé est 2020 |

### `Satisfaction/2019/resultats-esatisca-mco-open-data-2019.csv`

Millésime 2019.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| finess | FINESS juridique | oui | clé vers l'établissement |
| rs_finess | raison sociale du FINESS juridique | oui | libellé de l'établissement |
| finess_geo | FINESS géographique | oui | clé du site |
| rs_finess_geo | raison sociale du FINESS géographique | oui | libellé du site |
| region | région | oui | axe du taux de satisfaction par région. Millésime 2019, le taux chiffré demandé est 2020 |
| participation | participation obligatoire ou facultative | oui | filtre pour comparer les taux. Millésime 2019, le taux chiffré demandé est 2020 |
| Depot | au moins une adresse mail déposée | non | dépôt de mail, ni taux ni axe |
| nb_rep_score_all_ajust | nombre de réponses, satisfaction globale | oui | poids pour agréger la note à la région. Millésime 2019, le taux chiffré demandé est 2020 |
| score_all_ajust | note ajustée, satisfaction globale | oui | mesure du taux de satisfaction. Millésime 2019, le taux chiffré demandé est 2020 |
| classement | classe A à D, ou effectif insuffisant | oui | classe de la note globale. Millésime 2019, le taux chiffré demandé est 2020 |
| evolution | changement de classe d'une année sur l'autre | oui | écart dans le temps, le sujet couvre plusieurs années. Millésime 2019, le taux chiffré demandé est 2020 |
| score_AVH_ajust | note ajustée, avant l'hospitalisation | oui | détail de la satisfaction patient. Millésime 2019, le taux chiffré demandé est 2020 |
| nb_rep_score_AVH_ajust | nombre de réponses, avant l'hospitalisation | oui | poids d'un détail de la note patient. Millésime 2019, le taux chiffré demandé est 2020 |
| score_ACC_ajust | note ajustée, accueil le jour de l'hospitalisation | oui | détail de la satisfaction patient. Millésime 2019, le taux chiffré demandé est 2020 |
| nb_rep_score_ACC_ajust | nombre de réponses, accueil le jour de l'hospitalisation | oui | poids d'un détail de la note patient. Millésime 2019, le taux chiffré demandé est 2020 |
| score_PEC_ajust | note ajustée, prise en charge | oui | détail de la satisfaction patient. Millésime 2019, le taux chiffré demandé est 2020 |
| nb_rep_score_PEC_ajust | nombre de réponses, prise en charge | oui | poids d'un détail de la note patient. Millésime 2019, le taux chiffré demandé est 2020 |
| score_CER_ajust | note ajustée, chambre et repas | oui | détail de la satisfaction patient. Millésime 2019, le taux chiffré demandé est 2020 |
| nb_rep_score_CER_ajust | nombre de réponses, chambre et repas | oui | poids d'un détail de la note patient. Millésime 2019, le taux chiffré demandé est 2020 |
| score_OVS_ajust | note ajustée, sortie et retour à domicile | oui | détail de la satisfaction patient. Millésime 2019, le taux chiffré demandé est 2020 |
| nb_rep_score_OVS_ajust | nombre de réponses, sortie et retour à domicile | oui | poids d'un détail de la note patient. Millésime 2019, le taux chiffré demandé est 2020 |
| taux_reco_brut | part des patients qui recommandent l'établissement | oui | autre note patient, proche du taux de satisfaction. Millésime 2019, le taux chiffré demandé est 2020 |
| nb_reco_brut | nombre de patients qui recommandent l'établissement | oui | effectif de la recommandation. Millésime 2019, le taux chiffré demandé est 2020 |

### `Satisfaction/2020/resultats-esatis48h-mco-open-data-2020.xlsx`

Millésime 2020.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| finess | FINESS juridique | oui | clé vers l'établissement |
| rs_finess | raison sociale du FINESS juridique | oui | libellé de l'établissement |
| finess_geo | FINESS géographique | oui | clé du site |
| rs_finess_geo | raison sociale du FINESS géographique | oui | libellé du site |
| region | région | oui | axe du taux de satisfaction par région |
| participation | participation obligatoire ou facultative | oui | filtre pour comparer les taux |
| Depot | au moins une adresse mail déposée | non | dépôt de mail, ni taux ni axe |
| nb_rep_score_all_rea_ajust | nombre de réponses, satisfaction globale | oui | poids pour agréger la note à la région |
| score_all_rea_ajust | note ajustée, satisfaction globale | oui | mesure du taux de satisfaction |
| classement | classe A à D, ou effectif insuffisant | oui | classe de la note globale |
| evolution | changement de classe d'une année sur l'autre | oui | écart dans le temps, le sujet couvre plusieurs années |
| nb_rep_score_accueil_rea_ajust | nombre de réponses, accueil | oui | poids d'un détail de la note patient |
| score_accueil_rea_ajust | note ajustée, accueil | oui | détail de la satisfaction patient |
| nb_rep_score_PECinf_rea_ajust | nombre de réponses, prise en charge infirmiers | oui | poids d'un détail de la note patient |
| score_PECinf_rea_ajust | note ajustée, prise en charge infirmiers | oui | détail de la satisfaction patient |
| nb_rep_score_PECmed_rea_ajust | nombre de réponses, prise en charge médecins | oui | poids d'un détail de la note patient |
| score_PECmed_rea_ajust | note ajustée, prise en charge médecins | oui | détail de la satisfaction patient |
| nb_rep_score_chambre_rea_ajust | nombre de réponses, chambre | oui | poids d'un détail de la note patient |
| score_chambre_rea_ajust | note ajustée, chambre | oui | détail de la satisfaction patient |
| nb_rep_score_repas_rea_ajust | nombre de réponses, repas | oui | poids d'un détail de la note patient |
| score_repas_rea_ajust | note ajustée, repas | oui | détail de la satisfaction patient |
| nb_rep_score_sortie_rea_ajust | nombre de réponses, sortie | oui | poids d'un détail de la note patient |
| score_sortie_rea_ajust | note ajustée, sortie | oui | détail de la satisfaction patient |
| taux_reco_brut | part des patients qui recommandent l'établissement | oui | autre note patient, proche du taux de satisfaction |
| nb_reco_brut | nombre de patients qui recommandent l'établissement | oui | effectif de la recommandation |

### `Satisfaction/2020/resultats-esatisca-mco-open-data-2020.xlsx`

Millésime 2020.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| finess | FINESS juridique | oui | clé vers l'établissement |
| rs_finess | raison sociale du FINESS juridique | oui | libellé de l'établissement |
| finess_geo | FINESS géographique | oui | clé du site |
| rs_finess_geo | raison sociale du FINESS géographique | oui | libellé du site |
| region | région | oui | axe du taux de satisfaction par région |
| participation | participation obligatoire ou facultative | oui | filtre pour comparer les taux |
| Depot | au moins une adresse mail déposée | non | dépôt de mail, ni taux ni axe |
| nb_rep_score_all_ajust | nombre de réponses, satisfaction globale | oui | poids pour agréger la note à la région |
| score_all_ajust | note ajustée, satisfaction globale | oui | mesure du taux de satisfaction |
| classement | classe A à D, ou effectif insuffisant | oui | classe de la note globale |
| evolution | changement de classe d'une année sur l'autre | oui | écart dans le temps, le sujet couvre plusieurs années |
| score_AVH_ajust | note ajustée, avant l'hospitalisation | oui | détail de la satisfaction patient |
| nb_rep_score_AVH_ajust | nombre de réponses, avant l'hospitalisation | oui | poids d'un détail de la note patient |
| score_ACC_ajust | note ajustée, accueil le jour de l'hospitalisation | oui | détail de la satisfaction patient |
| nb_rep_score_ACC_ajust | nombre de réponses, accueil le jour de l'hospitalisation | oui | poids d'un détail de la note patient |
| score_PEC_ajust | note ajustée, prise en charge | oui | détail de la satisfaction patient |
| nb_rep_score_PEC_ajust | nombre de réponses, prise en charge | oui | poids d'un détail de la note patient |
| score_CER_ajust | note ajustée, chambre et repas | oui | détail de la satisfaction patient |
| nb_rep_score_CER_ajust | nombre de réponses, chambre et repas | oui | poids d'un détail de la note patient |
| score_OVS_ajust | note ajustée, sortie et retour à domicile | oui | détail de la satisfaction patient |
| nb_rep_score_OVS_ajust | nombre de réponses, sortie et retour à domicile | oui | poids d'un détail de la note patient |
| taux_reco_brut | part des patients qui recommandent l'établissement | oui | autre note patient, proche du taux de satisfaction |
| nb_reco_brut | nombre de patients qui recommandent l'établissement | oui | effectif de la recommandation |

### `Satisfaction/ESATIS48H_MCO_recueil2017_donnees.csv`

Millésime 2017.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| finess | FINESS juridique | oui | clé vers l'établissement |
| rs_finess | raison sociale du FINESS juridique | oui | libellé de l'établissement |
| finess_geo | FINESS géographique | oui | clé du site |
| rs_finess_geo | raison sociale du FINESS géographique | oui | libellé du site |
| region | région | oui | axe du taux de satisfaction par région. Millésime 2017, le taux chiffré demandé est 2020 |
| participation | participation obligatoire ou facultative | oui | filtre pour comparer les taux. Millésime 2017, le taux chiffré demandé est 2020 |
| Depot | au moins une adresse mail déposée | non | dépôt de mail, ni taux ni axe |
| nb_rep_score_all_rea_ajust | nombre de réponses, satisfaction globale | oui | poids pour agréger la note à la région. Millésime 2017, le taux chiffré demandé est 2020 |
| score_all_rea_ajust | note ajustée, satisfaction globale | oui | mesure du taux de satisfaction. Millésime 2017, le taux chiffré demandé est 2020 |
| classement | classe A à D, ou effectif insuffisant | oui | classe de la note globale. Millésime 2017, le taux chiffré demandé est 2020 |
| evolution | changement de classe d'une année sur l'autre | oui | écart dans le temps, le sujet couvre plusieurs années. Millésime 2017, le taux chiffré demandé est 2020 |
| nb_rep_score_accueil_rea_ajust | nombre de réponses, accueil | oui | poids d'un détail de la note patient. Millésime 2017, le taux chiffré demandé est 2020 |
| score_accueil_rea_ajust | note ajustée, accueil | oui | détail de la satisfaction patient. Millésime 2017, le taux chiffré demandé est 2020 |
| nb_rep_score_PECinf_rea_ajust | nombre de réponses, prise en charge infirmiers | oui | poids d'un détail de la note patient. Millésime 2017, le taux chiffré demandé est 2020 |
| score_PECinf_rea_ajust | note ajustée, prise en charge infirmiers | oui | détail de la satisfaction patient. Millésime 2017, le taux chiffré demandé est 2020 |
| nb_rep_score_PECmed_rea_ajust | nombre de réponses, prise en charge médecins | oui | poids d'un détail de la note patient. Millésime 2017, le taux chiffré demandé est 2020 |
| score_PECmed_rea_ajust | note ajustée, prise en charge médecins | oui | détail de la satisfaction patient. Millésime 2017, le taux chiffré demandé est 2020 |
| nb_rep_score_chambre_rea_ajust | nombre de réponses, chambre | oui | poids d'un détail de la note patient. Millésime 2017, le taux chiffré demandé est 2020 |
| score_chambre_rea_ajust | note ajustée, chambre | oui | détail de la satisfaction patient. Millésime 2017, le taux chiffré demandé est 2020 |
| nb_rep_score_repas_rea_ajust | nombre de réponses, repas | oui | poids d'un détail de la note patient. Millésime 2017, le taux chiffré demandé est 2020 |
| score_repas_rea_ajust | note ajustée, repas | oui | détail de la satisfaction patient. Millésime 2017, le taux chiffré demandé est 2020 |
| nb_rep_score_sortie_rea_ajust | nombre de réponses, sortie | oui | poids d'un détail de la note patient. Millésime 2017, le taux chiffré demandé est 2020 |
| score_sortie_rea_ajust | note ajustée, sortie | oui | détail de la satisfaction patient. Millésime 2017, le taux chiffré demandé est 2020 |

## Satisfaction — autres campagnes

Indicateurs de qualité du dossier ou indicateurs cliniques. Aucun n'est un des huit besoins. Le classeur DPA HAD 2016 a les mêmes colonnes que le CSV du même nom.

### `Satisfaction/2014/DPA_SSR_recueil2014_donnee2013_table_es.csv`

Sens repris de `Satisfaction/2014/DPA_SSR_recueil2014_donnee2013_table_lexique.csv`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| raison_sociale | raison sociale | non | clé ou libellé déjà portés par le référentiel établissements |
| libelle_region | région | non | clé ou libellé déjà portés par le référentiel établissements |
| cat | Catégorie | non | clé ou libellé déjà portés par le référentiel établissements |
| finess | Finess du TAS | non | clé ou libellé déjà portés par le référentiel établissements |
| Sources | Année des données | non | année d'une campagne qui n'est pas un des huit besoins |
| tdp_c_den_etbt | Dénominateur Tenue du dossier patient | non | effectif d'un score déjà calculé, hors besoin |
| tdp_c_etbt | Valeur Tenue du dossier patient | non | indicateur de qualité des soins, pas un des huit taux |
| tdp_c_icbas_etbt | Intervalle de confiance bas Tenue du dossier patient | non | précision statistique, aucun des huit besoins |
| tdp_c_ichaut_etbt | Intervalle de confiance haut Tenue du dossier patient | non | précision statistique, aucun des huit besoins |
| dec_c_den_etbt | Dénominateur Délai d'envoi du courrier | non | effectif d'un score déjà calculé, hors besoin |
| dec_c_etbt | Valeur Délai d'envoi du courrier | non | indicateur de qualité des soins, pas un des huit taux |
| dec_c_icbas_etbt | Intervalle de confiance bas Délai d'envoi du courrier | non | précision statistique, aucun des huit besoins |
| dec_c_ichaut_etbt | Intervalle de confiance haut Délai d'envoi du courrier | non | précision statistique, aucun des huit besoins |
| trd_c_den_etbt | Dénominateur Evaluation de la douleur | non | effectif d'un score déjà calculé, hors besoin |
| trd_c_etbt | Valeur Evaluation de la douleur | non | indicateur de qualité des soins, pas un des huit taux |
| trd_c_icbas_etbt | Intervalle de confiance bas Evaluation de la douleur | non | précision statistique, aucun des huit besoins |
| trd_c_ichaut_etbt | Intervalle de confiance haut Evaluation de la douleur | non | précision statistique, aucun des huit besoins |
| dtn1_c1_den_etbt | Dénominateur Dépistage de troubles nutritionnels (2 niveaux) | non | effectif d'un score déjà calculé, hors besoin |
| dtn1_c1_etbt | Valeur Dépistage de troubles nutritionnels (2 niveaux) | non | indicateur de qualité des soins, pas un des huit taux |
| dtn1_c1_icbas_etbt | Intervalle de confiance bas Dépistage de troubles nutritionnels (2 niveaux) | non | précision statistique, aucun des huit besoins |
| dtn1_c1_ichaut_etbt | Intervalle de confiance haut Dépistage de troubles nutritionnels (2 niveaux) | non | précision statistique, aucun des huit besoins |

### `Satisfaction/2014/DPA_SSR_recueil2014_donnee2013_table_participant.csv`

Sens repris de `Satisfaction/2014/DPA_SSR_recueil2014_donnee2013_table_lexique.csv`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| sources | Année des données | non | année d'une campagne qui n'est pas un des huit besoins |
| finess | Finess du TAS | non | clé ou libellé déjà portés par le référentiel établissements |
| raison_sociale | raison sociale | non | clé ou libellé déjà portés par le référentiel établissements |
| libelle_region | région | non | clé ou libellé déjà portés par le référentiel établissements |
| cat | Catégorie | non | clé ou libellé déjà portés par le référentiel établissements |
| repondant | établissement répondant | non | participation à une campagne hors besoin |

### `Satisfaction/2014/RCP_MCO_recueil2014_donnee2013_table_es.csv`

Le lexique du dossier ne couvre que l'identité de l'établissement. Le sens des scores suit le nom de colonne.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Raison_sociale | raison sociale | non | clé ou libellé déjà portés par le référentiel établissements |
| Libelle_region | région | non | clé ou libellé déjà portés par le référentiel établissements |
| cat | catégorie de l'établissement | non | clé ou libellé déjà portés par le référentiel établissements |
| finess | FINESS de l'établissement | non | clé ou libellé déjà portés par le référentiel établissements |
| Sources | année des données | non | année d'une campagne qui n'est pas un des huit besoins |
| rcp2_c2_den_etbt | dénominateur, réunion de concertation pluridisciplinaire | non | effectif d'un score déjà calculé, hors besoin |
| rcp2_c2_etbt | valeur, réunion de concertation pluridisciplinaire | non | indicateur de qualité des soins, pas un des huit taux |
| rcp2_c2_icbas_etbt | borne basse de l'intervalle de confiance, réunion de concertation pluridisciplinaire | non | précision statistique, aucun des huit besoins |
| rcp2_c2_ichaut_etbt | borne haute de l'intervalle de confiance, réunion de concertation pluridisciplinaire | non | précision statistique, aucun des huit besoins |

### `Satisfaction/2014/RCP_MCO_recueil2014_donnee2013_table_participant.csv`

Sens repris de `Satisfaction/2014/DPA_SSR_recueil2014_donnee2013_table_lexique.csv`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Sources | Année des données | non | année d'une campagne qui n'est pas un des huit besoins |
| Finess | Finess du TAS | non | clé ou libellé déjà portés par le référentiel établissements |
| Raison_sociale | raison sociale | non | clé ou libellé déjà portés par le référentiel établissements |
| Libelle_region | région | non | clé ou libellé déjà portés par le référentiel établissements |
| cat | Catégorie | non | clé ou libellé déjà portés par le référentiel établissements |
| repondant | établissement répondant | non | participation à une campagne hors besoin |

### `Satisfaction/2015/hpp_mco_recueil2015_donnee2014_tables_es.csv`

Sens repris de `Satisfaction/2015/hpp_mco_recueil2015_donnee2014_lexique.csv`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Sources | Année des données | non | année d'une campagne qui n'est pas un des huit besoins |
| finess | Finess du TAS | non | clé ou libellé déjà portés par le référentiel établissements |
| raison_sociale | Raison sociale | non | clé ou libellé déjà portés par le référentiel établissements |
| lib_reg | Nom de la région | non | clé ou libellé déjà portés par le référentiel établissements |
| code_reg | Code de la région | non | clé ou libellé déjà portés par le référentiel établissements |
| cat | Catégorie | non | clé ou libellé déjà portés par le référentiel établissements |
| del1_c1_den_etbt | del1_c1 Dénominateur | non | effectif d'un score déjà calculé, hors besoin |
| del1_c1_etbt | Délivrance niveau 1 | non | indicateur de qualité des soins, pas un des huit taux |
| del1_c1_icbas_etbt | del1_c1 Intervalle de confiance bas | non | précision statistique, aucun des huit besoins |
| del1_c1_ichaut_etbt | del1_c1 Intervalle de confiance haut | non | précision statistique, aucun des huit besoins |
| peci_hppi_c_den_etbt | peci_hppi_c Dénominateur | non | effectif d'un score déjà calculé, hors besoin |
| peci_hppi_c_etbt | Prise en charge initiale de l’ HPPI | non | indicateur de qualité des soins, pas un des huit taux |
| peci_hppi_c_icbas_etbt | peci_hppi_c Intervalle de confiance bas | non | précision statistique, aucun des huit besoins |
| peci_hppi_c_ichaut_etbt | peci_hppi_c Intervalle de confiance haut | non | précision statistique, aucun des huit besoins |
| surmin_c_den_etbt | surmin_c Dénominateur | non | effectif d'un score déjà calculé, hors besoin |
| surmin_c_etbt | Surveillance clinique minimale | non | indicateur de qualité des soins, pas un des huit taux |
| surmin_c_icbas_etbt | surmin_c Intervalle de confiance bas | non | précision statistique, aucun des huit besoins |
| surmin_c_ichaut_etbt | surmin_c Intervalle de confiance haut | non | précision statistique, aucun des huit besoins |

### `Satisfaction/2015/idm_mco_recueil2015_donnee2014_tables_es.csv`

Pas de lexique IDM dans le dossier. Le sens suit le nom de colonne.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| Sources | année des données | non | année d'une campagne qui n'est pas un des huit besoins |
| finess | FINESS de l'établissement | non | clé ou libellé déjà portés par le référentiel établissements |
| raison_sociale | raison sociale | non | clé ou libellé déjà portés par le référentiel établissements |
| lib_reg | région | non | clé ou libellé déjà portés par le référentiel établissements |
| code_reg | code de la région | non | clé ou libellé déjà portés par le référentiel établissements |
| cat | catégorie de l'établissement | non | clé ou libellé déjà portés par le référentiel établissements |
| basi_c_den_etbt | dénominateur, indicateur IDM code basi, lexique absent | non | effectif d'un score déjà calculé, hors besoin |
| basi_c_etbt | valeur, indicateur IDM code basi, lexique absent | non | indicateur de qualité des soins, pas un des huit taux |
| basi_c_icbas_etbt | borne basse de l'intervalle de confiance, indicateur IDM code basi, lexique absent | non | précision statistique, aucun des huit besoins |
| basi_c_ichaut_etbt | borne haute de l'intervalle de confiance, indicateur IDM code basi, lexique absent | non | précision statistique, aucun des huit besoins |
| hyg_c_den_etbt | dénominateur, indicateur IDM code hyg, lexique absent | non | effectif d'un score déjà calculé, hors besoin |
| hyg_c_etbt | valeur, indicateur IDM code hyg, lexique absent | non | indicateur de qualité des soins, pas un des huit taux |
| hyg_c_icbas_etbt | borne basse de l'intervalle de confiance, indicateur IDM code hyg, lexique absent | non | précision statistique, aucun des huit besoins |
| hyg_c_ichaut_etbt | borne haute de l'intervalle de confiance, indicateur IDM code hyg, lexique absent | non | précision statistique, aucun des huit besoins |

### `Satisfaction/2016/dan_mco_recueil2016_donnee2015_donnees.csv`

Sens repris de `Satisfaction/2016/dan_mco_recueil2016_donnee2015_lexique.csv`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| finess | finess de l'établissement | non | clé ou libellé déjà portés par le référentiel établissements |
| Sources | année des données | non | année d'une campagne qui n'est pas un des huit besoins |
| lib_reg | libelle_region | non | clé ou libellé déjà portés par le référentiel établissements |
| code_reg | Code de la région | non | clé ou libellé déjà portés par le référentiel établissements |
| raison_sociale | raison sociale | non | clé ou libellé déjà portés par le référentiel établissements |
| lib_cat | catégorie | non | clé ou libellé déjà portés par le référentiel établissements |
| repondant | établissement répondant | non | participation à une campagne hors besoin |
| resultat_tda | classe ou résultat, tenue du dossier anesthésique | non | indicateur de qualité des soins, pas un des huit taux |
| resultat_trd | classe ou résultat, traçabilité de l'évaluation de la douleur | non | indicateur de qualité des soins, pas un des huit taux |
| tda_c_etbt | Tenue du dossier anesthésique | non | indicateur de qualité des soins, pas un des huit taux |
| tda_c_ichaut_etbt | tda_c Intervalle de confiance haut | non | précision statistique, aucun des huit besoins |
| tda_c_icbas_etbt | tda_c Intervalle de confiance bas | non | précision statistique, aucun des huit besoins |
| tda_c_den_etbt | tda_c Dénominateur | non | effectif d'un score déjà calculé, hors besoin |
| trd_c_etbt | Tracabilité de l évaluation de la douleur | non | indicateur de qualité des soins, pas un des huit taux |
| trd_c_ichaut_etbt | trd_c Intervalle de confiance haut | non | précision statistique, aucun des huit besoins |
| trd_c_icbas_etbt | trd_c Intervalle de confiance bas | non | précision statistique, aucun des huit besoins |
| trd_c_den_etbt | trd_c Dénominateur | non | effectif d'un score déjà calculé, hors besoin |

### `Satisfaction/2016/dpa_had_recueil2016_donnee2015_donnees.csv`

Sens repris de `Satisfaction/2016/dpa_had_recueil2016_donnee2015_lexique.csv`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| finess | finess de l'établissement | non | clé ou libellé déjà portés par le référentiel établissements |
| Sources | année des données | non | année d'une campagne qui n'est pas un des huit besoins |
| lib_reg | libelle_region | non | clé ou libellé déjà portés par le référentiel établissements |
| code_reg | Code de la région | non | clé ou libellé déjà portés par le référentiel établissements |
| raison_sociale | raison sociale | non | clé ou libellé déjà portés par le référentiel établissements |
| lib_cat | catégorie | non | clé ou libellé déjà portés par le référentiel établissements |
| repondant | établissement répondant | non | participation à une campagne hors besoin |
| resultat_dec | classe ou résultat, délai d'envoi du courrier de fin d'hospitalisation | non | indicateur de qualité des soins, pas un des huit taux |
| resultat_dtn | classe ou résultat, dépistage des troubles nutritionnels | non | indicateur de qualité des soins, pas un des huit taux |
| resultat_tdp | classe ou résultat, tenue du dossier patient | non | indicateur de qualité des soins, pas un des huit taux |
| resultat_trd | classe ou résultat, traçabilité de l'évaluation de la douleur | non | indicateur de qualité des soins, pas un des huit taux |
| resultat_tre | classe ou résultat, traçabilité du risque d'escarre | non | indicateur de qualité des soins, pas un des huit taux |
| dec_c_etbt | Délai d envoi du courrier de fin d hospitalisation | non | indicateur de qualité des soins, pas un des huit taux |
| dec_c_ichaut_etbt | dec_c Intervalle de confiance haut | non | précision statistique, aucun des huit besoins |
| dec_c_icbas_etbt | dec_c Intervalle de confiance bas | non | précision statistique, aucun des huit besoins |
| dec_c_den_etbt | dec_c Dénominateur | non | effectif d'un score déjà calculé, hors besoin |
| dtn_c_etbt | Dépistage des troubles nutritionnels (Suivi du poids en HAD - Pas de niveau) | non | indicateur de qualité des soins, pas un des huit taux |
| dtn_c_ichaut_etbt | dtn_c Intervalle de confiance haut | non | précision statistique, aucun des huit besoins |
| dtn_c_icbas_etbt | dtn_c Intervalle de confiance bas | non | précision statistique, aucun des huit besoins |
| dtn_c_den_etbt | dtn_c Dénominateur | non | effectif d'un score déjà calculé, hors besoin |
| tdp_c_etbt | Tenue du dossier patient | non | indicateur de qualité des soins, pas un des huit taux |
| tdp_c_ichaut_etbt | tdp_c Intervalle de confiance haut | non | précision statistique, aucun des huit besoins |
| tdp_c_icbas_etbt | tdp_c Intervalle de confiance bas | non | précision statistique, aucun des huit besoins |
| tdp_c_den_etbt | tdp_c Dénominateur | non | effectif d'un score déjà calculé, hors besoin |
| trd_c_etbt | Tracabilité de l évaluation de la douleur | non | indicateur de qualité des soins, pas un des huit taux |
| trd_c_ichaut_etbt | trd_c Intervalle de confiance haut | non | précision statistique, aucun des huit besoins |
| trd_c_icbas_etbt | trd_c Intervalle de confiance bas | non | précision statistique, aucun des huit besoins |
| trd_c_den_etbt | trd_c Dénominateur | non | effectif d'un score déjà calculé, hors besoin |
| tre_c_etbt | Tracabilité de l évaluation du risque d escarre | non | indicateur de qualité des soins, pas un des huit taux |
| tre_c_ichaut_etbt | tre_c Intervalle de confiance haut | non | précision statistique, aucun des huit besoins |
| tre_c_icbas_etbt | tre_c Intervalle de confiance bas | non | précision statistique, aucun des huit besoins |
| tre_c_den_etbt | tre_c Dénominateur | non | effectif d'un score déjà calculé, hors besoin |

### `Satisfaction/2016/dpa_had_recueil2016_donnee2015_donnees.xlsx`

Mêmes 32 colonnes, dans le même ordre, que `Satisfaction/2016/dpa_had_recueil2016_donnee2015_donnees.csv`. Même jugement.

### `Satisfaction/2017-2018/dpa-ssr-recueil2018-donnee2017-donnees.csv`

Sens repris de `Satisfaction/2017-2018/dpa-ssr-recueil2018-donnee2017-lexique.csv`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| finess | Finess du TAS | non | clé ou libellé déjà portés par le référentiel établissements |
| Raison_sociale | raison sociale | non | clé ou libellé déjà portés par le référentiel établissements |
| Enquete_obligatoire | caractère obligatoire du recueil | non | participation à une campagne hors besoin |
| Participation | participation à l'enquête | non | participation à une campagne hors besoin |
| Resultat_doc | DOC Résultat du contrôle | non | indicateur de qualité des soins, pas un des huit taux |
| doc_c_den_etbt | DOC_C Dénominateur | non | effectif d'un score déjà calculé, hors besoin |
| doc_c_etbt | Document de sortie de SSR | non | indicateur de qualité des soins, pas un des huit taux |
| doc_c_icbas_etbt | DOC_C Intervalle de confiance bas | non | précision statistique, aucun des huit besoins |
| doc_c_ichaut_etbt | DOC_C Intervalle de confiance haut | non | précision statistique, aucun des huit besoins |
| doc_c_pos_seuil_etbt | DOC_C Positionnement par rapport à l'objectif de performance | non | indicateur de qualité des soins, pas un des huit taux |
| doc_c_pos_evol_etbt | évolution, document de sortie | non | indicateur de qualité des soins, pas un des huit taux |
| Resultat_dtn | DTN Résultat du contrôle | non | indicateur de qualité des soins, pas un des huit taux |
| dtn2_c2_den_etbt | DTN2_C2 Dénominateur | non | effectif d'un score déjà calculé, hors besoin |
| dtn2_c2_etbt | Dépistage des troubles nutritionnels en SSR | non | indicateur de qualité des soins, pas un des huit taux |
| dtn2_c2_icbas_etbt | DTN2_C2 Intervalle de confiance bas | non | précision statistique, aucun des huit besoins |
| dtn2_c2_ichaut_etbt | DTN2_C2 Intervalle de confiance haut | non | précision statistique, aucun des huit besoins |
| dtn2_c2_pos_seuil_etbt | DTN2_C2 Positionnement par rapport à l'objectif de performance | non | indicateur de qualité des soins, pas un des huit taux |
| dtn2_c2_pos_evol_etbt | DTN2_C2 Evolution par rapport au recueil précédent | non | indicateur de qualité des soins, pas un des huit taux |
| Lib_reg | région | non | clé ou libellé déjà portés par le référentiel établissements |

### `Satisfaction/2017-2018/ete-ortho-ipaqss-2017-2018-donnees.csv`

Sens repris de `Satisfaction/2017-2018/ete-ortho-ipaqss-2017-2018-lexique.csv`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| finess | finess juridique | non | clé ou libellé déjà portés par le référentiel établissements |
| rs | finess juridique - raison sociale | non | clé ou libellé déjà portés par le référentiel établissements |
| region | Région | non | clé ou libellé déjà portés par le référentiel établissements |
| ete_ortho_cible_etbt | Nombre de séjours concernés | non | indicateur de qualité des soins, pas un des huit taux |
| ete_ortho_obs_etbt | Nombre d'ETE observé | non | indicateur de qualité des soins, pas un des huit taux |
| ete_ortho_att_etbt | Nombre d'ETE attendu | non | indicateur de qualité des soins, pas un des huit taux |
| ete_ortho_etbt | Ratio observé / attendu | non | indicateur de qualité des soins, pas un des huit taux |
| ete_ortho_pos_seuil_etbt | Position dans le funel plot (3ds) <3ds --> A / >3ds -> C / sinon B | non | indicateur de qualité des soins, pas un des huit taux |

### `Satisfaction/2017-2018/rcp-mco-recueil2018-donnee2017-donnees.csv`

Sens repris de `Satisfaction/2017-2018/rcp-mco-recueil2018-donnee2017-lexique.csv`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| finess | Finess du TAS | non | clé ou libellé déjà portés par le référentiel établissements |
| Raison_sociale | raison sociale | non | clé ou libellé déjà portés par le référentiel établissements |
| Enquete_obligatoire | caractère obligatoire du recueil | non | participation à une campagne hors besoin |
| Participation | participation à l'enquête | non | participation à une campagne hors besoin |
| Resultat_rcp2 | RCP2 Résultat du contrôle | non | indicateur de qualité des soins, pas un des huit taux |
| rcp2_c2_den_etbt | RCP2_C2 Dénominateur | non | effectif d'un score déjà calculé, hors besoin |
| rcp2_c2_etbt | RCP niveau 2 : plurisdisciplinarité de la concertation | non | indicateur de qualité des soins, pas un des huit taux |
| rcp2_c2_icbas_etbt | RCP2_C2 Intervalle de confiance bas | non | précision statistique, aucun des huit besoins |
| rcp2_c2_ichaut_etbt | RCP2_C2 Intervalle de confiance haut | non | précision statistique, aucun des huit besoins |
| rcp2_c2_pos_seuil_etbt | RCP2_C2 Positionnement par rapport à l'objectif de performance | non | indicateur de qualité des soins, pas un des huit taux |
| rcp2_c2_pos_evol_etbt | RCP2_C2 Evolution par rapport au recueil précédent | non | indicateur de qualité des soins, pas un des huit taux |
| Lib_reg | région | non | clé ou libellé déjà portés par le référentiel établissements |

### `Satisfaction/2019/resultats-iqss-open-data-2019.csv`

Sens repris de `Satisfaction/2019/lexique-iqss-open-data-2019.csv`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| finess | FINESS de l’établissement enquêté | non | clé ou libellé déjà portés par le référentiel établissements |
| finess_pmsi | FINESS PMSI de l’établissement | non | clé ou libellé déjà portés par le référentiel établissements |
| nom_ES | Nom de l'ES de l’établissement | non | clé ou libellé déjà portés par le référentiel établissements |
| region | Libellé de la région administrative de l’établissement enquêté | non | clé ou libellé déjà portés par le référentiel établissements |
| type | Libellé de la catégorie de l’établissement enquêté | non | clé ou libellé déjà portés par le référentiel établissements |
| obligatoire_icsha_v3_mhs | Recueil obligatoire pour ICSHA (Secteur : MCO/HAD/SSR) | non | participation à une campagne hors besoin |
| classe_ias_icsha_v3_mhs | Classe (Indicateur de consommation de solutions hydro-alcooliques : secteurs MCO/HAD/SSR - IAS) | non | indicateur de qualité des soins, pas un des huit taux |
| res_ias_icsha_v3_mhs | Résultat (Indicateur de consommation de solutions hydro-alcooliques : secteurs MCO/HAD/SSR - IAS) | non | indicateur de qualité des soins, pas un des huit taux |
| evol_ias_icsha_v3_mhs | Evolution par rapport au recueil précédent (Indicateur de consommation de solutions hydro-alcooliques : secteurs MCO/HAD/SSR - IAS) | non | indicateur de qualité des soins, pas un des huit taux |
| obligatoire_icsha_v3_psy | Recueil obligatoire pour ICSHA (Secteur : Psychiatrie) | non | participation à une campagne hors besoin |
| classe_ias_icsha_v3_psy | Classe (Indicateur de consommation de solutions hydro-alcooliques : secteur PSY - IAS) | non | indicateur de qualité des soins, pas un des huit taux |
| res_ias_icsha_v3_psy | Résultat (Indicateur de consommation de solutions hydro-alcooliques : secteur PSY - IAS) | non | indicateur de qualité des soins, pas un des huit taux |
| evol_ias_icsha_v3_psy | Evolution par rapport au recueil précédent (Indicateur de consommation de solutions hydro-alcooliques : secteur PSY - IAS) | non | indicateur de qualité des soins, pas un des huit taux |
| obligatoire_dpa_had | Recueil obligatoire en HAD | non | participation à une campagne hors besoin |
| classe_DPA_dtn_HAD | Classe (Suivi du poids - DPA HAD ) | non | indicateur de qualité des soins, pas un des huit taux |
| res_dpa_dtn_had | Résultat (Suivi du poids - DPA HAD) | non | indicateur de qualité des soins, pas un des huit taux |
| evol_dpa_dtn_had | Evolution par rapport au recueil précédent (Suivi du poids - DPA HAD) | non | indicateur de qualité des soins, pas un des huit taux |
| classe_DPA_tre_HAD | Classe (Traçabilité de l'évaluation du risque d'escarre - DPA HAD ) | non | indicateur de qualité des soins, pas un des huit taux |
| res_dpa_tre_had | Résultat (Traçabilité de l'évaluation du risque d'escarre - DPA HAD) | non | indicateur de qualité des soins, pas un des huit taux |
| evol_dpa_tre_had | Evolution par rapport au recueil précédent (Traçabilité de l'évaluation du risque d'escarre - DPA HAD) | non | indicateur de qualité des soins, pas un des huit taux |
| classe_DPA_coord_HAD | Classe (Coordination de la prise en charge - DPA HAD ) | non | indicateur de qualité des soins, pas un des huit taux |
| res_dpa_coord_had | Résultat (Coordination de la prise en charge - DPA HAD) | non | indicateur de qualité des soins, pas un des huit taux |
| evol_dpa_coord_had | Evolution par rapport au recueil précédent (Coordination de la prise en charge - DPA HAD) | non | indicateur de qualité des soins, pas un des huit taux |
| classe_DPA_tdp_v3_HAD | Classe (Tenue du dossier patient - DPA HAD ) | non | indicateur de qualité des soins, pas un des huit taux |
| res_dpa_tdp_v3_had | Résultat (Tenue du dossier patient - DPA HAD) | non | indicateur de qualité des soins, pas un des huit taux |
| evol_dpa_tdp_v3_had | Evolution par rapport au recueil précédent (Tenue du dossier patient - DPA HAD) | non | indicateur de qualité des soins, pas un des huit taux |
| obligatoire_dpa_mco | Recueil obligatoire en MCO | non | participation à une campagne hors besoin |
| classe_DPA_qls_v2_MCO | Classe (Qualité de la lettre de liaison à la sortie - DPA MCO ) | non | indicateur de qualité des soins, pas un des huit taux |
| res_dpa_qls_v2_mco | Résultat (Qualité de la lettre de liaison à la sortie - DPA MCO) | non | indicateur de qualité des soins, pas un des huit taux |
| evol_dpa_qls_v2_mco | Evolution par rapport au recueil précédent (Qualité de la lettre de liaison à la sortie - DPA MCO) | non | indicateur de qualité des soins, pas un des huit taux |
| classe_DPA_pcd_MCO | Classe (Evaluation et prise en charge de la douleur - DPA MCO ) | non | indicateur de qualité des soins, pas un des huit taux |
| res_dpa_pcd_mco | Résultat (Evaluation et prise en charge de la douleur - DPA MCO) | non | indicateur de qualité des soins, pas un des huit taux |
| evol_dpa_pcd_mco | Evolution par rapport au recueil précédent (Evaluation et prise en charge de la douleur - DPA MCO) | non | indicateur de qualité des soins, pas un des huit taux |
| obligatoire_dpa_ssr | Recueil obligatoire en SSR | non | participation à une campagne hors besoin |
| classe_DPA_qls_SSR | Classe (Qualité de la lettre de liaison à la sortie - DPA SSR ) | non | indicateur de qualité des soins, pas un des huit taux |
| res_dpa_qls_ssr | Résultat (Qualité de la lettre de liaison à la sortie - DPA SSR) | non | indicateur de qualité des soins, pas un des huit taux |
| evol_dpa_qls_ssr | Evolution par rapport au recueil précédent (Qualité de la lettre de liaison à la sortie - DPA SSR) | non | indicateur de qualité des soins, pas un des huit taux |
| classe_DPA_pcd_SSR | Classe (Evaluation et prise en charge de la douleur - DPA SSR ) | non | indicateur de qualité des soins, pas un des huit taux |
| res_dpa_pcd_ssr | Résultat (Evaluation et prise en charge de la douleur - DPA SSR) | non | indicateur de qualité des soins, pas un des huit taux |
| evol_dpa_pcd_ssr | Evolution par rapport au recueil précédent (Evaluation et prise en charge de la douleur - DPA SSR) | non | indicateur de qualité des soins, pas un des huit taux |
| classe_DPA_pspv_SSR | Classe (Projets de soins, projet de vie - DPA SSR ) | non | indicateur de qualité des soins, pas un des huit taux |
| res_dpa_pspv_ssr | Résultat (Projets de soins, projet de vie - DPA SSR) | non | indicateur de qualité des soins, pas un des huit taux |
| evol_dpa_pspv_ssr | Evolution par rapport au recueil précédent (Projets de soins, projet de vie - DPA SSR) | non | indicateur de qualité des soins, pas un des huit taux |
| obligatoire_ca_mco | Recueil obligatoire en chirurgie-ambulatoire | non | participation à une campagne hors besoin |
| classe_CA_qls_v2_MCO | Classe (Qualité de la lettre de liaison à la sortie - CA MCO ) | non | indicateur de qualité des soins, pas un des huit taux |
| res_ca_qls_v2_mco | Résultat (Qualité de la lettre de liaison à la sortie - CA MCO) | non | indicateur de qualité des soins, pas un des huit taux |
| evol_ca_qls_v2_mco | Evolution par rapport au recueil précédent (Qualité de la lettre de liaison à la sortie - CA MCO) | non | indicateur de qualité des soins, pas un des huit taux |
| ete_ortho_ratio_oe | Score de l'indicateur (Evènement thrombo-embolique après prothèse de hanche/genou) | non | indicateur de qualité des soins, pas un des huit taux |
| ete_ortho_alerte_supe | Position de l'établissement par rapport à la borne d'alerte (Evènement thrombo-embolique après prothèse de hanche/genou) | non | indicateur de qualité des soins, pas un des huit taux |

### `Satisfaction/2020/resultats-iqss-open-data-2020.xlsx`

Sens repris de `Satisfaction/2020/lexique-iqss-open-data-2020.xlsx`.

| Nom | Sens | utile | pourquoi c'est utile |
|---|---|---|---|
| finess | FINESS de l’établissement enquêté | non | clé ou libellé déjà portés par le référentiel établissements |
| nom_ES | Nom de l’établissement | non | clé ou libellé déjà portés par le référentiel établissements |
| region | Libellé de la région administrative de l’établissement enquêté | non | clé ou libellé déjà portés par le référentiel établissements |
| type | Libellé de la catégorie de l’établissement enquêté | non | clé ou libellé déjà portés par le référentiel établissements |
| ete_ortho_ratio_oe | Score de l'indicateur (Evènement thrombo-embolique après prothèse de hanche/genou) | non | indicateur de qualité des soins, pas un des huit taux |
| ete_ortho_alerte_sup | Position de l'établissement par rapport à la borne d'alerte (Evènement thrombo-embolique après prothèse de hanche/genou) | non | indicateur de qualité des soins, pas un des huit taux |
| ete_ortho_evol | Evolution du statut des établissements évalués - Données 2018 et 2019 | non | indicateur de qualité des soins, pas un des huit taux |
| iso_ortho_ratio_oe | Score de l'indicateur (Infections du site opératoire après prothèse de hanche/genou) | non | indicateur de qualité des soins, pas un des huit taux |
| iso_ortho_alerte_sup | Position de l'établissement par rapport à la borne d'alerte (Infections du site opératoire après prothèse de hanche/genou) | non | indicateur de qualité des soins, pas un des huit taux |
