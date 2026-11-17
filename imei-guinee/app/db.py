"""Accès à la base SQLite : connexion, schéma et horodatage."""

import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS utilisateur (
    id                INTEGER PRIMARY KEY,
    identifiant       TEXT    NOT NULL UNIQUE,
    nom_complet       TEXT    NOT NULL,
    role              TEXT    NOT NULL CHECK (role IN ('VICTIME', 'AGENT')),
    unite             TEXT,
    mot_de_passe_hash TEXT    NOT NULL,
    cree_le           TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS commune (
    id     INTEGER PRIMARY KEY,
    nom    TEXT NOT NULL UNIQUE,
    region TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS declaration (
    id               INTEGER PRIMARY KEY,
    reference        TEXT    NOT NULL UNIQUE,
    imei             TEXT    NOT NULL CHECK (length(imei) = 15),
    type_evenement   TEXT    NOT NULL CHECK (type_evenement IN ('VOL', 'PERTE')),
    marque           TEXT    NOT NULL,
    modele           TEXT    NOT NULL,
    couleur          TEXT    NOT NULL,
    commune_id       INTEGER NOT NULL REFERENCES commune(id),
    date_evenement   TEXT    NOT NULL,
    numero_recepisse TEXT    NOT NULL,
    statut           TEXT    NOT NULL DEFAULT 'SOUMIS'
                             CHECK (statut IN ('SOUMIS', 'VALIDE', 'REJETE')),
    declarant_id     INTEGER NOT NULL REFERENCES utilisateur(id),
    soumis_le        TEXT    NOT NULL,
    traite_par_id    INTEGER REFERENCES utilisateur(id),
    traite_le        TEXT,
    motif_rejet      TEXT
);

-- Un IMEI ne peut faire l'objet que d'une seule déclaration active à la fois.
CREATE UNIQUE INDEX IF NOT EXISTS ux_declaration_imei_active
    ON declaration(imei) WHERE statut IN ('SOUMIS', 'VALIDE');
CREATE INDEX IF NOT EXISTS ix_declaration_imei   ON declaration(imei);
CREATE INDEX IF NOT EXISTS ix_declaration_statut ON declaration(statut);

-- Piste d'audit : chaque changement d'état, avec son auteur et son horodatage.
CREATE TABLE IF NOT EXISTS historique_statut (
    id             INTEGER PRIMARY KEY,
    declaration_id INTEGER NOT NULL REFERENCES declaration(id),
    statut_avant   TEXT,
    statut_apres   TEXT    NOT NULL,
    auteur_id      INTEGER NOT NULL REFERENCES utilisateur(id),
    horodatage     TEXT    NOT NULL,
    commentaire    TEXT
);
CREATE INDEX IF NOT EXISTS ix_historique_declaration ON historique_statut(declaration_id);

-- Journal des vérifications publiques, à des fins statistiques uniquement.
-- Volontairement sans IMEI ni adresse IP (minimisation des données).
CREATE TABLE IF NOT EXISTS journal_verification (
    id         INTEGER PRIMARY KEY,
    horodatage TEXT NOT NULL,
    resultat   TEXT NOT NULL CHECK (resultat IN ('SIGNALE', 'NON_SIGNALE', 'INVALIDE'))
);
"""


def maintenant() -> str:
    """Horodatage ISO 8601 en UTC (la Guinée est à GMT+0, sans heure d'été)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connecter() -> sqlite3.Connection:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialiser_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def obtenir_db() -> Iterator[sqlite3.Connection]:
    """Dépendance FastAPI : une connexion par requête."""
    conn = connecter()
    try:
        yield conn
    finally:
        conn.close()
