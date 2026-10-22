# Plan de gouvernance des données

## Conformité RPGD

Le traitement de données de santé à caractère personnel impose un respect strict du principe de minimisation et de protection de la vie privée dès la conception.

* Mécanisme de Pseudonymisation (Zone Silver) : Les identifiants patients sont remplacés par des hachages cryptographiques (SHA-256) ou des tokens aléatoires. Cela permet de suivre le parcours d'un patient sans jamais pouvoir l'identifier directement.

* Anonymisation pour l'analyse et l'Open Data (Zone Gold) : Pour les restitutions statistiques ou l'intégration des données démographiques (comme les décès INSEE).

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