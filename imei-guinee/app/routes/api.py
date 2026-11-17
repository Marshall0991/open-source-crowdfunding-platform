"""API JSON de vérification : illustre l'interface qui serait proposée aux opérateurs.

Même règle que la page publique : réponse binaire, aucune donnée personnelle.
"""

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db import obtenir_db
from app.routes.public import verifier

router = APIRouter(prefix="/api/v1", tags=["Vérification"])


class ReponseVerification(BaseModel):
    imei: str
    resultat: Literal["SIGNALE", "NON_SIGNALE"]
    libelle: str


class ReponseErreur(BaseModel):
    detail: str


@router.get(
    "/verification/{imei}",
    response_model=ReponseVerification,
    summary="Vérifier si un IMEI est signalé",
    responses={422: {"model": ReponseErreur}, 429: {"model": ReponseErreur}},
)
def verification(imei: str, request: Request, db: sqlite3.Connection = Depends(obtenir_db)):
    """Retourne « SIGNALE » si l'IMEI fait l'objet d'une déclaration **validée** par la
    Police nationale, « NON_SIGNALE » sinon. Limité à quelques appels par minute et par adresse IP."""
    resultat = verifier(db, request, imei)
    if resultat["etat"] == "LIMITE":
        return JSONResponse(
            {"detail": "Trop de vérifications. Veuillez réessayer dans quelques instants."},
            status_code=429, headers={"Retry-After": str(resultat["attente"])},
        )
    if resultat["etat"] == "INVALIDE":
        return JSONResponse({"detail": resultat["erreur"]}, status_code=422)
    libelle = "Signalé" if resultat["etat"] == "SIGNALE" else "Non signalé"
    return ReponseVerification(imei=resultat["imei"], resultat=resultat["etat"], libelle=libelle)
