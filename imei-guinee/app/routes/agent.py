"""Espace agent de police : examen et validation des déclarations."""

import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import services
from app.db import obtenir_db
from app.securite import exiger_agent, flash, verifier_csrf
from app.vues import rendre

router = APIRouter(prefix="/agent")


@router.get("")
def file_attente(
    request: Request,
    utilisateur=Depends(exiger_agent),
    db: sqlite3.Connection = Depends(obtenir_db),
):
    return rendre(
        request, "agent/file.html", utilisateur, onglet="attente",
        declarations=services.declarations_en_attente(db),
        nb_attente=services.compter_en_attente(db),
    )


@router.get("/traitees")
def declarations_traitees(
    request: Request,
    utilisateur=Depends(exiger_agent),
    db: sqlite3.Connection = Depends(obtenir_db),
):
    return rendre(
        request, "agent/file.html", utilisateur, onglet="traitees",
        declarations=services.declarations_traitees(db),
        nb_attente=services.compter_en_attente(db),
    )


def _rendre_detail(request, utilisateur, db, reference, erreur=None, valeurs=None, status_code=200):
    declaration = services.obtenir_declaration(db, reference)
    if declaration is None:
        raise HTTPException(status_code=404)
    return rendre(
        request, "agent/detail.html", utilisateur, status_code=status_code,
        d=declaration, historique=services.historique(db, declaration["id"]),
        antecedents=services.antecedents_imei(db, declaration["imei"], declaration["id"]),
        motifs=services.MOTIFS_REJET, erreur=erreur, valeurs=valeurs or {},
    )


@router.get("/declarations/{reference}")
def detail(
    reference: str,
    request: Request,
    utilisateur=Depends(exiger_agent),
    db: sqlite3.Connection = Depends(obtenir_db),
):
    return _rendre_detail(request, utilisateur, db, reference)


@router.post("/declarations/{reference}/valider")
def valider(
    reference: str,
    request: Request,
    csrf: str = Form(""),
    controle: str = Form(""),
    utilisateur=Depends(exiger_agent),
    db: sqlite3.Connection = Depends(obtenir_db),
):
    verifier_csrf(request, csrf)
    if not controle:
        return _rendre_detail(
            request, utilisateur, db, reference, status_code=422,
            erreur="Veuillez confirmer avoir contrôlé le récépissé de plainte avant de valider.",
        )
    try:
        services.valider_declaration(db, reference, utilisateur["id"])
    except services.ErreurMetier as exc:
        return _rendre_detail(request, utilisateur, db, reference, erreur=str(exc), status_code=409)
    flash(request, f"La déclaration {reference} a été validée. L'IMEI apparaît désormais comme "
                   "« Signalé » lors des vérifications publiques.")
    return RedirectResponse("/agent", status_code=303)


@router.post("/declarations/{reference}/rejeter")
def rejeter(
    reference: str,
    request: Request,
    csrf: str = Form(""),
    motif: str = Form(""),
    precisions: str = Form(""),
    utilisateur=Depends(exiger_agent),
    db: sqlite3.Connection = Depends(obtenir_db),
):
    verifier_csrf(request, csrf)
    motif = motif if motif in services.MOTIFS_REJET else ""
    precisions = " ".join(precisions.split())
    valeurs = {"motif": motif, "precisions": precisions}

    if not motif:
        erreur = "Veuillez sélectionner le motif du rejet."
    elif motif == "Autre motif" and len(precisions) < 5:
        erreur = "Veuillez préciser le motif du rejet."
    else:
        erreur = None
    if erreur:
        return _rendre_detail(request, utilisateur, db, reference, erreur=erreur, valeurs=valeurs, status_code=422)

    texte = precisions if motif == "Autre motif" else (f"{motif} : {precisions}" if precisions else motif)
    try:
        services.rejeter_declaration(db, reference, utilisateur["id"], texte)
    except services.ErreurMetier as exc:
        return _rendre_detail(request, utilisateur, db, reference, erreur=str(exc), valeurs=valeurs, status_code=409)
    flash(request, f"La déclaration {reference} a été rejetée. Le déclarant en est informé dans son espace.", "info")
    return RedirectResponse("/agent", status_code=303)
