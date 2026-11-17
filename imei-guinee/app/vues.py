"""Rendu des gabarits Jinja2 et filtres d'affichage en français."""

from datetime import date, datetime

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app import config, seed
from app.securite import jeton_csrf, recuperer_flashes

templates = Jinja2Templates(directory=str(config.APP_DIR / "templates"))

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]

LIBELLES_STATUT = {"SOUMIS": "Soumis", "VALIDE": "Validé", "REJETE": "Rejeté"}


def _date_heure(valeur: str | None) -> str:
    """« 2026-11-17T14:32:00+00:00 » -> « 17/11/2026 à 14 h 32 »."""
    if not valeur:
        return "—"
    moment = datetime.fromisoformat(valeur)
    return f"{moment:%d/%m/%Y} à {moment:%H} h {moment:%M}"


def _date_longue(valeur: str | None) -> str:
    """« 2026-11-17 » -> « 17 novembre 2026 »."""
    if not valeur:
        return "—"
    jour = date.fromisoformat(valeur[:10])
    premier = "1er" if jour.day == 1 else str(jour.day)
    return f"{premier} {MOIS[jour.month - 1]} {jour.year}"


def _imei_groupe(imei: str) -> str:
    """Présentation lisible : 00 123456 000010 4 (TAC / numéro de série / clé)."""
    if len(imei) != 15:
        return imei
    return f"{imei[:2]} {imei[2:8]} {imei[8:14]} {imei[14]}"


templates.env.filters["date_heure"] = _date_heure
templates.env.filters["date_longue"] = _date_longue
templates.env.filters["imei"] = _imei_groupe
templates.env.filters["statut"] = lambda s: LIBELLES_STATUT.get(s, s)
templates.env.globals["TYPES_EVENEMENT"] = {"VOL": "Vol", "PERTE": "Perte"}
templates.env.globals["imei_demo"] = {
    "signale": _imei_groupe(seed.IMEI_SIGNALE),
    "en_attente": _imei_groupe(seed.IMEI_EN_ATTENTE),
    "libre": _imei_groupe(seed.IMEI_LIBRE),
    "cle_fausse": _imei_groupe(seed.IMEI_CLE_FAUSSE),
}


def rendre(request: Request, gabarit: str, utilisateur=None, status_code: int = 200, **contexte):
    contexte.update(
        utilisateur=utilisateur,
        csrf=jeton_csrf(request),
        flashes=recuperer_flashes(request),
        chemin=request.url.path,
        afficher_comptes_demo=config.AFFICHER_COMPTES_DEMO,
    )
    return templates.TemplateResponse(request, gabarit, contexte, status_code=status_code)
