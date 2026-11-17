"""Authentification simplifiée (comptes de démonstration), sessions et CSRF."""

import hashlib
import hmac
import secrets
import sqlite3

from fastapi import Depends, Request

from app.db import obtenir_db

_ITERATIONS = 200_000


# --- Mots de passe -----------------------------------------------------------

def hacher_mot_de_passe(mot_de_passe: str) -> str:
    sel = secrets.token_hex(16)
    empreinte = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode(), bytes.fromhex(sel), _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${sel}${empreinte.hex()}"


def verifier_mot_de_passe(mot_de_passe: str, stocke: str) -> bool:
    try:
        algo, iterations, sel, attendu = stocke.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    calcule = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode(), bytes.fromhex(sel), int(iterations))
    return hmac.compare_digest(calcule.hex(), attendu)


def authentifier(db: sqlite3.Connection, identifiant: str, mot_de_passe: str) -> sqlite3.Row | None:
    utilisateur = db.execute(
        "SELECT * FROM utilisateur WHERE identifiant = ?", (identifiant.strip().lower(),)
    ).fetchone()
    if utilisateur and verifier_mot_de_passe(mot_de_passe, utilisateur["mot_de_passe_hash"]):
        return utilisateur
    return None


# --- Session -----------------------------------------------------------------

def ouvrir_session(request: Request, utilisateur: sqlite3.Row) -> None:
    request.session.clear()  # évite la fixation de session
    request.session["uid"] = utilisateur["id"]


def fermer_session(request: Request) -> None:
    request.session.clear()


def utilisateur_optionnel(request: Request, db: sqlite3.Connection = Depends(obtenir_db)) -> sqlite3.Row | None:
    uid = request.session.get("uid")
    if uid is None:
        return None
    return db.execute(
        "SELECT id, identifiant, nom_complet, role, unite FROM utilisateur WHERE id = ?", (uid,)
    ).fetchone()


class ConnexionRequise(Exception):
    """Levée lorsqu'une page protégée est demandée sans session."""

    def __init__(self, suivant: str):
        self.suivant = suivant


class AccesRefuse(Exception):
    """Levée lorsqu'un utilisateur connecté n'a pas le rôle requis."""


def exiger_role(role: str):
    def dependance(
        request: Request, utilisateur: sqlite3.Row | None = Depends(utilisateur_optionnel)
    ) -> sqlite3.Row:
        if utilisateur is None:
            raise ConnexionRequise(request.url.path)
        if utilisateur["role"] != role:
            raise AccesRefuse()
        return utilisateur

    return dependance


exiger_victime = exiger_role("VICTIME")
exiger_agent = exiger_role("AGENT")


def chemin_retour_sur(suivant: str | None) -> str | None:
    """N'accepte qu'un chemin interne (protection contre les redirections ouvertes)."""
    if suivant and suivant.startswith("/") and not suivant.startswith("//") and "\\" not in suivant:
        return suivant
    return None


# --- CSRF --------------------------------------------------------------------

def jeton_csrf(request: Request) -> str:
    jeton = request.session.get("csrf")
    if not jeton:
        jeton = secrets.token_urlsafe(32)
        request.session["csrf"] = jeton
    return jeton


class JetonCsrfInvalide(Exception):
    pass


def verifier_csrf(request: Request, jeton: str | None) -> None:
    attendu = request.session.get("csrf")
    if not attendu or not jeton or not hmac.compare_digest(attendu, jeton):
        raise JetonCsrfInvalide()


# --- Messages flash ----------------------------------------------------------

def flash(request: Request, message: str, categorie: str = "succes") -> None:
    messages = request.session.get("flash", [])
    messages.append({"message": message, "categorie": categorie})
    request.session["flash"] = messages


def recuperer_flashes(request: Request) -> list[dict]:
    return request.session.pop("flash", [])
