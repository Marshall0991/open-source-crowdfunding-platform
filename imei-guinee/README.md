# IMEI Guinée — Démonstrateur

Démonstrateur (MVP) d'un **registre national des téléphones déclarés volés ou perdus**, destiné à être
présenté à l'ARPT, aux opérateurs de téléphonie et à la Police nationale.

L'objectif est de montrer l'architecture et le parcours des usagers, **pas** de livrer le système de
production. Toutes les données sont fictives.

| Fonction | Acteur | Accès |
|---|---|---|
| Vérification publique d'un IMEI (« Signalé » / « Non signalé ») | Public | Sans compte |
| Déclaration d'un appareil volé ou perdu, suivi de l'état | Victime | Compte de démonstration |
| Validation ou rejet motivé des déclarations | Agent de police | Compte de démonstration |
| Tableau de bord (statistiques agrégées) | Tous | Sans compte |

**Hors périmètre, volontairement :** aucune géolocalisation, aucun suivi par numéro, aucune connexion
aux réseaux de télécommunications, aucun blocage réel d'IMEI. Le blocage réseau et les échanges avec
les opérateurs sont simulés : les boutons sont affichés mais désactivés, avec la mention
« nécessite l'autorisation du régulateur (ARPT) ».

---

## 1. Installation

Prérequis : **Python 3.12 ou supérieur**. Aucune base de données ni aucun service externe à installer.

```bash
cd imei-guinee
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Lancement

```bash
uvicorn app.main:app
```

Puis ouvrir **http://127.0.0.1:8000**.

Au premier lancement, la base SQLite `data/imei_guinee.db` est créée et le jeu de données de
démonstration est chargé automatiquement.

**Démonstration sur téléphone** (même réseau Wi-Fi que l'ordinateur) :

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

puis ouvrir `http://<adresse-IP-de-l-ordinateur>:8000` sur le téléphone.

**Remettre la démonstration à zéro** (entre deux présentations) :

```bash
python -m app.seed --reset
```

> Tailwind CSS est chargé depuis un CDN. Une copie locale est servie automatiquement si le réseau est
> indisponible : la démonstration fonctionne donc aussi hors connexion.

## 3. Comptes de démonstration

| Rôle | Identifiant | Mot de passe | Nom fictif |
|---|---|---|---|
| Victime | `victime1` | `demo1234` | Aïssatou Diallo |
| Victime | `victime2` | `demo1234` | Ibrahima Camara |
| Agent de police | `agent` | `police1234` | Brigadier-chef Fatoumata Bah (Commissariat central de Kaloum) |
| Agent de police | `agent2` | `police1234` | Inspecteur Moussa Kaba (Commissariat central de Ratoma) |

Les comptes `victime3` à `victime5` (mot de passe `demo1234`) portent le reste des déclarations
fictives. Sur la page de connexion, un encart permet de remplir le formulaire d'un simple toucher.

## 4. IMEI de test

Les IMEI fictifs utilisent le préfixe `00`, réservé aux essais. Ils sont aussi rappelés dans l'encart
« Aide à la démonstration » de la page d'accueil.

| IMEI | Situation | Réponse publique |
|---|---|---|
| `001234560000105` | Déclaration **validée** (victime1) | **Signalé** |
| `001234560000204` | Déclaration **soumise**, en attente (victime2) | Non signalé |
| `001234560000303` | Déclaration **rejetée** (victime3) | Non signalé |
| `001234560009908` | Aucune déclaration : **à déclarer pendant la démonstration** | Non signalé |
| `001234560009909` | Clé de contrôle (Luhn) fausse | Message d'erreur |

## 5. Scénario de démonstration pas à pas

Durée : 5 à 7 minutes. Il fonctionne aussi bien sur un téléphone que sur un vidéoprojecteur.

**Étape 1 : vérification publique (sans compte)**
1. Ouvrir la page d'accueil « Vérifier un téléphone ».
2. Saisir `001234560000105` puis cliquer sur **Vérifier** : la réponse est **Signalé** (en rouge).
   Souligner qu'aucune donnée personnelle n'est affichée : ni propriétaire, ni marque, ni lieu.
3. Saisir `001234560009908` : la réponse est **Non signalé** (en vert).
4. Saisir `001234560009909` : le message d'erreur explique que le chiffre de contrôle (algorithme de
   Luhn) ne correspond pas. Le système détecte les fautes de frappe.

**Étape 2 : déclaration par la victime**
1. **Se connecter** avec `victime1` / `demo1234`.
2. **Déclarer un appareil**. Pour illustrer les contrôles :
   - IMEI `001234560000204` → refusé : *« Cet IMEI fait déjà l'objet d'une déclaration… »*
     (détection des doublons) ;
   - puis IMEI `001234560009908`, marque *Tecno*, modèle *Spark 10*, couleur *Noir*, nature *Vol*,
     date d'hier, commune *Kaloum*, récépissé `PV-KAL-2026-0500`, cocher l'attestation.
3. **Envoyer la déclaration** : une référence `DEC-AAAA-NNNNNN` est attribuée et le statut est
   **Soumis**. L'historique indique l'auteur et l'horodatage.
4. Revenir sur « Vérifier un IMEI » et vérifier `001234560009908` : toujours **Non signalé**,
   car la déclaration n'est pas encore validée par la Police.
5. **Se déconnecter.**

**Étape 3 : validation par la Police nationale**
1. Se connecter avec `agent` / `police1234`. La file « En attente » s'affiche.
2. **Examiner** la nouvelle déclaration : identité du déclarant, appareil, récépissé, historique.
3. Montrer l'encart **« Transmission aux opérateurs et blocage réseau »** : les boutons sont désactivés.
   Au survol ou au toucher, l'infobulle indique que la fonction nécessite l'autorisation de l'ARPT.
4. Cocher « J'ai vérifié la concordance du récépissé… » puis **Valider**.
5. (Facultatif) Ouvrir une autre déclaration et la **Rejeter** avec un motif : le motif est obligatoire.
6. **Se déconnecter.**

**Étape 4 : l'IMEI est désormais signalé**
1. Vérifier de nouveau `001234560009908` : la réponse est **Signalé**.
2. (Facultatif) Se reconnecter en `victime1` : le statut est **Validé** et l'historique mentionne l'agent.

**Étape 5 : pilotage et cadre**
1. Ouvrir le **Tableau de bord** : déclarations par statut et par commune, nombre de vérifications.
2. Ouvrir **À propos** : rôle de chaque acteur, ce qui est simulé, mention relative à l'ARPT.
3. (Pour les opérateurs) Ouvrir **/docs** : l'API de vérification
   `GET /api/v1/verification/{imei}` illustre une intégration possible.

## 6. Architecture

```
Navigateur (mobile / vidéoprojecteur)
        │  pages HTML (Jinja2) + Tailwind CSS
        ▼
┌──────────────────────────────── FastAPI ──────────────────────────────────┐
│  Pages publiques     Espace victime     Espace agent      API JSON        │
│  /  /verifier        /espace/...        /agent/...        /api/v1/...     │
│  /tableau-de-bord  /a-propos  /connexion                                  │
│  ───────────────────────────────────────────────────────────────────────  │
│  services.py : règles métier · imei.py : Luhn · limiteur.py : débit       │
│  securite.py : sessions, rôles, CSRF, mots de passe hachés (PBKDF2)       │
│  ───────────────────────────────────────────────────────────────────────  │
│  db.py : sqlite3 (bibliothèque standard), requêtes paramétrées            │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    ▼
                         data/imei_guinee.db (SQLite)

   [Simulé]  Passerelle opérateurs / liste de blocage
             → boutons désactivés : « nécessite l'autorisation de l'ARPT »
```

### Arborescence

```
imei-guinee/
├── app/
│   ├── main.py            application, middlewares, gestion des erreurs
│   ├── config.py          paramètres (surchargeables par variables d'environnement)
│   ├── db.py              schéma SQL et connexion
│   ├── seed.py            jeu de données de démonstration (python -m app.seed [--reset])
│   ├── imei.py            validation IMEI (15 chiffres + Luhn)
│   ├── limiteur.py        limitation du débit (fenêtre glissante en mémoire)
│   ├── securite.py        authentification, sessions, rôles, CSRF
│   ├── services.py        déclaration, cycle de vie, vérification, statistiques
│   ├── vues.py            rendu des gabarits, filtres d'affichage en français
│   ├── routes/            public, auth, victime, agent, api
│   ├── templates/         pages HTML
│   └── static/            logo, styles, copie locale de Tailwind
├── data/                  base SQLite (générée)
├── tests/                 tests automatisés (pytest)
├── requirements.txt
└── README.md
```

### Schéma des tables

| Table | Rôle | Champs principaux |
|---|---|---|
| `utilisateur` | Comptes de démonstration | identifiant, nom_complet, role (`VICTIME`/`AGENT`), unite, mot_de_passe_hash |
| `commune` | Référentiel (liste indicative) | nom, region |
| `declaration` | Déclarations | reference, imei, type_evenement (`VOL`/`PERTE`), marque, modele, couleur, commune_id, date_evenement, numero_recepisse, statut, declarant_id, soumis_le, traite_par_id, traite_le, motif_rejet |
| `historique_statut` | Piste d'audit | declaration_id, statut_avant, statut_apres, auteur_id, horodatage, commentaire |
| `journal_verification` | Statistiques de vérification | horodatage, resultat. **Ni IMEI ni adresse IP.** |

Un index unique partiel (`imei` lorsque `statut IN ('SOUMIS','VALIDE')`) garantit en base qu'un IMEI
n'a jamais deux déclarations actives.

### Règles métier

- **IMEI** : les espaces et tirets sont acceptés puis retirés. L'IMEI doit compter exactement
  15 chiffres et sa clé de Luhn doit être correcte. Chaque erreur a son message.
- **Doublons** : la déclaration est refusée si l'IMEI fait déjà l'objet d'une déclaration soumise
  ou validée. Après un rejet, une nouvelle déclaration est possible.
- **Cycle de vie** : `SOUMIS → VALIDÉ` ou `SOUMIS → REJETÉ`, sans retour possible. Le motif est
  obligatoire en cas de rejet. Chaque transition est horodatée, attribuée à son auteur et enregistrée
  dans la même transaction que le changement de statut.
- **Vérification publique** : « Signalé » **uniquement** si une déclaration est validée.
  La réponse ne contient aucune autre information.
- **Limitation du débit** : 10 vérifications par minute et par adresse IP (page web et API
  confondues). Au-delà, le serveur renvoie le code HTTP 429 et un message en français.
- **Cloisonnement** : une victime ne voit que ses propres déclarations. Seuls les agents valident
  ou rejettent.

### API de vérification

```
GET /api/v1/verification/001234560000105
→ 200 {"imei": "001234560000105", "resultat": "SIGNALE", "libelle": "Signalé"}

GET /api/v1/verification/001234560009909
→ 422 {"detail": "Ce numéro IMEI n'est pas valide : son chiffre de contrôle …"}
```

La documentation interactive est disponible sur `/docs`.

## 7. Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Les tests couvrent :
- l'algorithme de Luhn et les messages d'erreur ;
- le scénario complet déclarer → valider → vérifier ;
- les doublons et la redéclaration possible après un rejet ;
- les transitions interdites et le motif de rejet obligatoire ;
- l'absence de données personnelles dans la réponse publique et dans l'API ;
- la limitation du débit ;
- le contrôle des rôles, le jeton CSRF et la protection contre les redirections ouvertes.

## 8. Configuration (facultatif)

| Variable | Défaut | Rôle |
|---|---|---|
| `IMEI_DB_PATH` | `data/imei_guinee.db` | Emplacement de la base |
| `IMEI_SECRET_KEY` | valeur de démonstration | Clé de signature des sessions, à changer hors démonstration |
| `IMEI_LIMITE_VERIFICATIONS` | `10` | Vérifications autorisées par fenêtre et par IP |
| `IMEI_FENETRE_LIMITE_SECONDES` | `60` | Durée de la fenêtre |
| `IMEI_AFFICHER_COMPTES_DEMO` | `1` | Affiche les comptes et les IMEI de test (`0` pour masquer) |

## 9. Limites du démonstrateur et pistes pour la suite

Les choix suivants suffisent pour une démonstration mais ne conviennent pas à une mise en production :
- **Authentification** : comptes de démonstration en dur. En production, il faudrait un annuaire des
  agents habilité, une authentification forte et, pour les victimes, une vérification d'identité.
- **Limitation du débit** : elle est gérée en mémoire, dans un seul processus. Il faudrait la confier
  à une passerelle d'API ou à un stockage partagé.
- **Base de données** : SQLite convient pour une démonstration. Une base serveur, des sauvegardes et
  la journalisation des accès seraient nécessaires.
- **Cookies de session** : passer `https_only=True` derrière HTTPS.
- **Téléphones double SIM** : un seul IMEI est saisi par déclaration. Un second IMEI facultatif
  pourrait être ajouté.
- **Liste des communes** : indicative, à remplacer par le référentiel administratif officiel.
- **Intégration aux opérateurs et blocage réseau** : à concevoir avec l'ARPT et les opérateurs, sous
  réserve de son autorisation et du cadre juridique applicable (protection des données personnelles,
  durée de conservation, habilitations).

---

*Démonstrateur réalisé à des fins de présentation. Il ne constitue pas un service officiel.
Personnes, plaintes et IMEI sont fictifs.*
