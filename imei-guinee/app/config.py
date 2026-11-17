"""Paramètres du démonstrateur.

Toutes les valeurs ont un défaut adapté à une démonstration locale ; elles
peuvent être surchargées par des variables d'environnement.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"

# Base SQLite locale (créée automatiquement au premier lancement).
DB_PATH = Path(os.environ.get("IMEI_DB_PATH", BASE_DIR / "data" / "imei_guinee.db"))

# Clé de signature des cookies de session. À remplacer hors démonstration.
SECRET_KEY = os.environ.get("IMEI_SECRET_KEY", "cle-de-demonstration-a-remplacer")

# Durée de validité d'une session (secondes).
DUREE_SESSION = 8 * 3600

# Limitation de débit de la vérification publique : N requêtes par fenêtre et par adresse IP.
LIMITE_VERIFICATIONS = int(os.environ.get("IMEI_LIMITE_VERIFICATIONS", "10"))
FENETRE_LIMITE_SECONDES = int(os.environ.get("IMEI_FENETRE_LIMITE_SECONDES", "60"))

# Affiche l'encart des comptes de démonstration sur la page de connexion.
AFFICHER_COMPTES_DEMO = os.environ.get("IMEI_AFFICHER_COMPTES_DEMO", "1") == "1"
