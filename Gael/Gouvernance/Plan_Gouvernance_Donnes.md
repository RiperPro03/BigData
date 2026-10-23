# Plan de gouvernance des données

## Conformité RPGD

Le traitement de données de santé à caractère personnel impose un respect strict du principe de minimisation et de protection de la vie privée dès la conception.

1. Cadre Juridique et Fondement du Traitement (Recommandation CNIL)
    - Exception de traitement pour motif de santé publique : Le traitement de données sensibles (santé) dans le projet CHU s'appuie sur les exceptions légales prévues par le RGPD et le code de la santé publique, à savoir la gestion des systèmes de soins, les diagnostics médicaux et l'intérêt public dans le domaine de la santé (recherche et pilotage sanitaire).
    - Documentation des traitements : Tenue rigoureuse d'un registre des activités de traitement, décrivant précisément les flux, les finalités et les mesures de mise en conformité.

2. Désignation d'un Délégué à la Protection des Données (DPO / DPD)
    - S'agissant d'un groupement hospitalier (groupe CHU), l'établissement a l'obligation de désigner un Délégué à la Protection des Données (DPO) chargé de piloter la mise en conformité, de faire le lien avec les autorités et d'animer la politique de protection des données en interne.

3. Analyse d'Impact sur la Protection des Données (AIPD / DPIA)
    - Compte tenu du traitement de données de santé à grande échelle (données patients, séjours, consultations, mortalité), la réalisation d'une AIPD préalable est obligatoire. Cette analyse évalue les risques sur les droits et libertés des personnes et valide les mesures correctives techniques (pseudonymisation, cloisonnement des couches Bronze/Silver/Gold) avant toute mise en production.

4. Encadrement Contractuel des Prestataires (Sous-traitance)
    - Conformément à l'article 28 du RGPD, l'ensemble des prestataires, éditeurs de logiciels (SaaS), ou intégrateurs intervenant sur la plateforme Big Data doivent signer un acte de sous-traitance spécifique intégrant des clauses strictes sur la sécurité, l'interdiction d'utiliser les données à d'autres fins et l'obligation de restitution ou de suppression en fin de contrat.

5. Droits des Personnes et Procédures d'Exercice
    - Mise en place de procédures opérationnelles pour garantir l'exercice effectif des droits renforcés des patients (droit d'accès, de rectification, d'opposition pour motif légitime, et droit à la portabilité), en coordination avec les services médicaux et administratifs gestionnaires des dossiers patients.

6. Notification des Violations de Données
    - En cas d'incident de sécurité (fuite, altération ou accès non autorisé aux données de santé), application d'une double procédure de signalement : la notification obligatoire auprès de la CNIL (dans les 72h) et le signalement des incidents de sécurité des systèmes d'information de santé (conformément aux exigences sectorielles).

## Conformité HDS (Hébergement de Données de Santé)

Conformément à la législation française (Article L.1111-8 du Code de la santé publique), toute organisation qui héberge des données de santé personnelles doit s'assurer de la fiabilité et de la sécurité de l'infrastructure.

- Certification de l'infrastructure : L'environnement virtuel utilisé pour déployer l'architecture Big Data (Hadoop/Cloudera) doit reposer sur un hébergeur certifié HDS (ou une architecture cloud conforme aux exigences de sécurité équivalentes).
- Chiffrement des données :
    - En transit : Utilisation systématique de protocoles sécurisés (HTTPS, TLS 1.3) pour les flux FTP et les connexions aux bases de données.
    - Au repos : Chiffrement des volumes de stockage pour empêcher toute lecture en cas de vol de support physique.
- Isolation des environnements : Séparation stricte entre les environnements de développement, de test et de production.

## Rôles et droits d'accès

L'accès aux données au sein de la plateforme Lakehouse est régi par le principe du moindre privilège (chaque utilisateur n'accède qu'à ce qui lui est strictement nécessaire pour ses missions).

- Administrateurs de la Plateforme et Data Engineers :
    - Droits complets (écriture et lecture) sur les couches Bronze, Silver et Gold pour la maintenance des pipelines ETL, la gestion des flux et la supervision technique.
- Analystes de données et Data scientist :
    - Accès restreint (lecture) à la couche Gold et aux rapports Power BI. Pas d'accès aux tables brutes ou aux informations identifiantes.
- Opérateurs :
    - Accès restreint (lecture) aux rapports Power BI.

## Traçabilité des flux

Pour garantir la transparence et l'intégrité des analyses présentées au groupe CHU, la traçabilité est assurée de bout en bout par l'enregistrement automatique des connexions, des tentatives d'accès aux données sensibles et des modifications de structure. Ces journaux (logs) sont conservés de manière inaltérable pour répondre aux contrôles de la CNIL ou des auditeurs internes.