"""Pages publiques : vérification d'un IMEI, tableau de bord, à propos."""

import sqlite3

from fastapi import APIRouter, Depends, Form, Request

from app import services
from app.db import maintenant, obtenir_db
from app.imei import valider_imei
from app.limiteur import limiteur_verification
from app.securite import utilisateur_optionnel
from app.vues import rendre

router = APIRouter()


def adresse_client(request: Request) -> str:
    # En production derrière un mandataire inverse, l'adresse proviendrait d'un en-tête de confiance.
    return request.client.host if request.client else "inconnue"


def verifier(db: sqlite3.Connection, request: Request, saisie: str) -> dict:
    """Logique commune à la page web et à l'API.

    Retourne un dictionnaire ``{"etat": ..., ...}`` où ``etat`` vaut
    ``LIMITE``, ``INVALIDE``, ``SIGNALE`` ou ``NON_SIGNALE``.
    """
    autorise, attente = limiteur_verification.autoriser(adresse_client(request))
    if not autorise:
        return {"etat": "LIMITE", "attente": attente}
    imei, erreur = valider_imei(saisie)
    if erreur:
        services.journaliser_verification(db, "INVALIDE")
        return {"etat": "INVALIDE", "imei": imei, "erreur": erreur}
    resultat = "SIGNALE" if services.imei_signale(db, imei) else "NON_SIGNALE"
    services.journaliser_verification(db, resultat)
    return {"etat": resultat, "imei": imei}


@router.get("/")
def accueil(request: Request, utilisateur=Depends(utilisateur_optionnel)):
    return rendre(request, "accueil.html", utilisateur)


@router.post("/verifier")
def verifier_formulaire(
    request: Request,
    imei: str = Form(""),
    db: sqlite3.Connection = Depends(obtenir_db),
    utilisateur=Depends(utilisateur_optionnel),
):
    resultat = verifier(db, request, imei)
    statut_http = {"LIMITE": 429, "INVALIDE": 422}.get(resultat["etat"], 200)
    reponse = rendre(
        request, "accueil.html", utilisateur, status_code=statut_http,
        resultat=resultat, saisie=imei[:40], verifie_le=maintenant(),
    )
    if resultat["etat"] == "LIMITE":
        reponse.headers["Retry-After"] = str(resultat["attente"])
    return reponse


@router.get("/tableau-de-bord")
def tableau_de_bord(
    request: Request,
    db: sqlite3.Connection = Depends(obtenir_db),
    utilisateur=Depends(utilisateur_optionnel),
):
    return rendre(request, "tableau_de_bord.html", utilisateur, stats=services.statistiques(db))


@router.get("/a-propos")
def a_propos(request: Request, utilisateur=Depends(utilisateur_optionnel)):
    return rendre(request, "a_propos.html", utilisateur)
