"""Connexion et déconnexion (comptes de démonstration)."""

import sqlite3

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.db import obtenir_db
from app.securite import (
    authentifier, chemin_retour_sur, fermer_session, flash, ouvrir_session,
    utilisateur_optionnel, verifier_csrf,
)
from app.vues import rendre

router = APIRouter()

ACCUEIL_PAR_ROLE = {"VICTIME": "/espace", "AGENT": "/agent"}

COMPTES_DEMO = [
    {"identifiant": "victime1", "mot_de_passe": "demo1234", "nom": "Aïssatou Diallo", "role": "Victime"},
    {"identifiant": "victime2", "mot_de_passe": "demo1234", "nom": "Ibrahima Camara", "role": "Victime"},
    {"identifiant": "agent", "mot_de_passe": "police1234", "nom": "Brigadier-chef Fatoumata Bah",
     "role": "Agent de police"},
]


@router.get("/connexion")
def page_connexion(request: Request, suivant: str | None = None, utilisateur=Depends(utilisateur_optionnel)):
    if utilisateur:
        return RedirectResponse(ACCUEIL_PAR_ROLE[utilisateur["role"]], status_code=303)
    return rendre(request, "connexion.html", None, suivant=chemin_retour_sur(suivant), comptes=COMPTES_DEMO)


@router.post("/connexion")
def connexion(
    request: Request,
    identifiant: str = Form(""),
    mot_de_passe: str = Form(""),
    suivant: str = Form(""),
    csrf: str = Form(""),
    db: sqlite3.Connection = Depends(obtenir_db),
):
    verifier_csrf(request, csrf)
    utilisateur = authentifier(db, identifiant, mot_de_passe)
    if utilisateur is None:
        return rendre(
            request, "connexion.html", None, status_code=401,
            erreur="Identifiant ou mot de passe incorrect.",
            identifiant=identifiant[:50], suivant=chemin_retour_sur(suivant), comptes=COMPTES_DEMO,
        )
    ouvrir_session(request, utilisateur)
    flash(request, f"Bienvenue, {utilisateur['nom_complet']}.")
    destination = chemin_retour_sur(suivant)
    prefixe = ACCUEIL_PAR_ROLE[utilisateur["role"]]
    if not destination or not destination.startswith(prefixe):
        destination = prefixe
    return RedirectResponse(destination, status_code=303)


@router.post("/deconnexion")
def deconnexion(request: Request, csrf: str = Form("")):
    verifier_csrf(request, csrf)
    fermer_session(request)
    flash(request, "Vous êtes déconnecté(e).", "info")
    return RedirectResponse("/", status_code=303)
