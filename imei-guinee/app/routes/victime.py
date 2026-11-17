"""Espace victime : déclarer un appareil, suivre ses déclarations."""

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import services
from app.db import obtenir_db
from app.securite import exiger_victime, flash, verifier_csrf
from app.vues import rendre

router = APIRouter(prefix="/espace")


@router.get("")
def mes_declarations(
    request: Request,
    utilisateur=Depends(exiger_victime),
    db: sqlite3.Connection = Depends(obtenir_db),
):
    return rendre(
        request, "victime/mes_declarations.html", utilisateur,
        declarations=services.declarations_de(db, utilisateur["id"]),
    )


def _rendre_formulaire(request, utilisateur, db, valeurs=None, erreurs=None, erreur_generale=None, status_code=200):
    return rendre(
        request, "victime/declarer.html", utilisateur, status_code=status_code,
        valeurs=valeurs or {}, erreurs=erreurs or {}, erreur_generale=erreur_generale,
        communes=services.communes(db), marques=services.MARQUES_COURANTES,
        couleurs=services.COULEURS_COURANTES, aujourd_hui=date.today().isoformat(),
    )


@router.get("/declarer")
def formulaire_declaration(
    request: Request,
    utilisateur=Depends(exiger_victime),
    db: sqlite3.Connection = Depends(obtenir_db),
):
    return _rendre_formulaire(request, utilisateur, db, valeurs={"type_evenement": "VOL"})


@router.post("/declarer")
async def deposer_declaration(
    request: Request,
    utilisateur=Depends(exiger_victime),
    db: sqlite3.Connection = Depends(obtenir_db),
):
    formulaire = await request.form()
    verifier_csrf(request, formulaire.get("csrf"))
    saisie = {cle: str(valeur) for cle, valeur in formulaire.items()}

    validation = services.valider_formulaire_declaration(db, saisie)
    valeurs = {**saisie, **{k: v for k, v in validation.donnees.items() if v}}
    if not validation.valide:
        return _rendre_formulaire(
            request, utilisateur, db, valeurs, validation.erreurs,
            "Le formulaire comporte des erreurs. Veuillez corriger les champs signalés.", 422,
        )
    try:
        reference = services.creer_declaration(db, utilisateur["id"], validation.donnees)
    except services.ErreurMetier as exc:
        return _rendre_formulaire(
            request, utilisateur, db, valeurs, {"imei": str(exc)},
            "La déclaration n'a pas pu être enregistrée : cet IMEI est déjà déclaré.", 409,
        )

    flash(request, f"Votre déclaration a bien été enregistrée sous la référence {reference}. "
                   "Elle sera examinée par la Police nationale.")
    return RedirectResponse(f"/espace/declarations/{reference}", status_code=303)


@router.get("/declarations/{reference}")
def detail_declaration(
    reference: str,
    request: Request,
    utilisateur=Depends(exiger_victime),
    db: sqlite3.Connection = Depends(obtenir_db),
):
    declaration = services.obtenir_declaration(db, reference)
    # Une victime ne peut consulter que ses propres déclarations.
    if declaration is None or declaration["declarant_id"] != utilisateur["id"]:
        raise HTTPException(status_code=404)
    return rendre(
        request, "victime/detail.html", utilisateur,
        d=declaration, historique=services.historique(db, declaration["id"]),
    )
