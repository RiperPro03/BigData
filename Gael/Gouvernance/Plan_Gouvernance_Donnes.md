# Plan de gouvernance des données

## Conformité RPGD

Le traitement de données de santé à caractère personnel impose un respect strict du principe de minimisation et de protection de la vie privée dès la conception.

1. **Cadre Juridique et Fondement du Traitement (Recommandation CNIL)**
    - **Exception de traitement pour motif de santé publique** : Le traitement de données sensibles (santé) dans le projet CHU s'appuie sur les exceptions légales prévues par le RGPD et le code de la santé publique, à savoir la gestion des systèmes de soins, les diagnostics médicaux et l'intérêt public dans le domaine de la santé (recherche et pilotage sanitaire).
    - **Documentation des traitements** : Tenue rigoureuse d'un registre des activités de traitement, décrivant précisément les flux, les finalités et les mesures de mise en conformité.

2. **Désignation d'un Délégué à la Protection des Données (DPO / DPD)**
    - S'agissant d'un groupement hospitalier (groupe CHU), l'établissement a l'obligation de désigner un Délégué à la Protection des Données (DPO) chargé de piloter la mise en conformité, de faire le lien avec les autorités et d'animer la politique de protection des données en interne.

3. **Analyse d'Impact sur la Protection des Données (AIPD / DPIA)**
    - Compte tenu du traitement de données de santé à grande échelle (données patients, séjours, consultations, mortalité), la réalisation d'une AIPD préalable est obligatoire. Cette analyse évalue les risques sur les droits et libertés des personnes et valide les mesures correctives techniques (pseudonymisation, cloisonnement des couches Bronze/Silver/Gold) avant toute mise en production.

4. **Encadrement Contractuel des Prestataires (Sous-traitance)**
    - Conformément à l'article 28 du RGPD, l'ensemble des prestataires, éditeurs de logiciels (SaaS), ou intégrateurs intervenant sur la plateforme Big Data doivent signer un acte de sous-traitance spécifique intégrant des clauses strictes sur la sécurité, l'interdiction d'utiliser les données à d'autres fins et l'obligation de restitution ou de suppression en fin de contrat.

5. **Droits des Personnes et Procédures d'Exercice**
    - Mise en place de procédures opérationnelles pour garantir l'exercice effectif des droits renforcés des patients (droit d'accès, de rectification, d'opposition pour motif légitime, et droit à la portabilité), en coordination avec les services médicaux et administratifs gestionnaires des dossiers patients.

6. **Notification des Violations de Données**
    - En cas d'incident de sécurité (fuite, altération ou accès non autorisé aux données de santé), application d'une double procédure de signalement : la notification obligatoire auprès de la CNIL (dans les 72h) et le signalement des incidents de sécurité des systèmes d'information de santé (conformément aux exigences sectorielles).

## Conformité HDS (Hébergement de Données de Santé)

Conformément à la législation française (Article L.1111-8 du Code de la santé publique), toute organisation qui héberge des données de santé personnelles doit s'assurer de la fiabilité et de la sécurité de l'infrastructure, en respectant le cadre de la PGSSI-S :
- **Certification de l'infrastructure (HDS)** : L'environnement virtuel utilisé pour déployer l'architecture Big Data (Hadoop/Cloudera) doit reposer sur un hébergeur certifié HDS (les 6 activités de certification), garantissant la sécurité physique des data centers, la souveraineté des données (stockage sur le territoire de l'UE) et la réversibilité des prestations.
- **Chiffrement des données** :
    - *En transit* : Utilisation systématique de protocoles sécurisés (HTTPS, TLS 1.3) pour les flux FTP, les API et les connexions aux bases de données.
    - *Au repos* : Chiffrement des volumes de stockage (chiffrement AES-256 sur les couches HDFS/stockage objet) pour empêcher toute lecture en cas de compromission physique des supports.
- **Isolation et cloisonnement des environnements** : Séparation stricte et étanche entre les environnements de développement, de test et de production, interdisant l'utilisation de données de santé réelles dans les environnements de test (obligation d'utiliser des jeux de données synthétiques ou entièrement anonymisés).
- **Continuité d'activité et résilience (PRA / PCA)** : Mise en place d'un Plan de Reprise d'Activité (PRA) et d'un Plan de Continuité d'Activité (PCA) incluant des sauvegardes incrémentales et régulières, chiffrées et stockées de manière isolée (hors-ligne ou sur un site secondaire certifié HDS).
- **Gestion des vulnérabilités** : Audits de sécurité réguliers, tests d'intrusion (pentests) et application automatisée des correctifs de sécurité sur les briques logicielles de la plateforme Big Data.

## Rôles et droits d'accès

L'accès aux données au sein de la plateforme Lakehouse est régi par le principe du moindre privilège (chaque utilisateur n'accède qu'à ce qui lui est strictement nécessaire pour ses missions).

- Administrateurs de la Plateforme et Data Engineers :
    - Droits complets (écriture et lecture) sur les couches Bronze, Silver et Gold pour la maintenance des pipelines ETL, la gestion des flux et la supervision technique.
- Analystes de données et Data scientist :
    - Accès restreint (lecture) à la couche Gold et aux rapports Power BI. Pas d'accès aux tables brutes ou aux informations identifiantes.
- Opérateurs :
    - Accès restreint (lecture) aux rapports Power BI.

## Traçabilité des flux

Pour garantir la transparence, la conformité réglementaire et l'intégrité des analyses présentées au groupe CHU, la traçabilité est assurée de bout en bout selon deux axes majeurs :
- **Traçabilité technique et de sécurité (Journaux d'audit / Audit Logs)** :
    - Enregistrement automatique et centralisé de toutes les connexions, des tentatives d'accès aux données sensibles, des modifications de structure des bases et des élévations de privilèges.
    - Ces journaux sont conservés de manière inaltérable et sécurisée pendant une durée réglementaire définie (ex: 6 mois à 1 an minimum) pour répondre aux contrôles de la CNIL, des auditeurs internes ou des organismes de certification HDS.
- **Lignage des données (Data Lineage)** :
    - Traçabilité algorithmique et fonctionnelle permettant de remonter à tout moment de n'importe quel indicateur ou chiffre affiché dans un rapport Power BI (couche Gold) jusqu'à sa source d'origine exacte (PostgreSQL, fichier CSV ou flux FTP), en passant par l'historique complet des transformations appliquées dans les jobs ETL (couches Bronze et Silver). Cela garantit la reproductibilité et la fiabilité totale des analyses.