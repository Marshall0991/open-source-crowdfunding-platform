"""Point d'entrée de l'application : ``uvicorn app.main:app``."""

from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app import config, seed
from app.routes import agent, api, auth, public, victime
from app.db import connecter
from app.securite import AccesRefuse, ConnexionRequise, JetonCsrfInvalide, utilisateur_optionnel
from app.vues import rendre


@asynccontextmanager
async def cycle_de_vie(_: FastAPI):
    # Crée la base et charge les données de démonstration au premier lancement.
    seed.initialiser()
    yield


app = FastAPI(
    title="IMEI Guinée — Démonstrateur",
    description=(
        "Démonstrateur d'un registre national des téléphones déclarés volés ou perdus. "
        "Données fictives. Aucune connexion aux réseaux de télécommunications."
    ),
    version="0.1.0",
    lifespan=cycle_de_vie,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=config.SECRET_KEY,
    session_cookie="imei_session",
    max_age=config.DUREE_SESSION,
    same_site="lax",
    https_only=False,  # à passer à True derrière HTTPS
)


@app.middleware("http")
async def entetes_securite(request: Request, appel_suivant):
    reponse = await appel_suivant(request)
    reponse.headers.setdefault("X-Content-Type-Options", "nosniff")
    reponse.headers.setdefault("X-Frame-Options", "DENY")
    reponse.headers.setdefault("Referrer-Policy", "same-origin")
    return reponse


app.mount("/static", StaticFiles(directory=str(config.APP_DIR / "static")), name="static")

app.include_router(public.router)
app.include_router(auth.router)
app.include_router(victime.router)
app.include_router(agent.router)
app.include_router(api.router)


# --- Gestion des erreurs -----------------------------------------------------

def _utilisateur(request: Request):
    conn = connecter()
    try:
        return utilisateur_optionnel(request, conn)
    finally:
        conn.close()


@app.exception_handler(ConnexionRequise)
async def connexion_requise(request: Request, exc: ConnexionRequise):
    return RedirectResponse(f"/connexion?suivant={quote(exc.suivant)}", status_code=303)


@app.exception_handler(AccesRefuse)
async def acces_refuse(request: Request, _exc: AccesRefuse):
    return rendre(
        request, "erreur.html", _utilisateur(request), status_code=403,
        titre="Accès non autorisé",
        message="Votre profil ne permet pas d'accéder à cette page.",
    )


@app.exception_handler(JetonCsrfInvalide)
async def csrf_invalide(request: Request, _exc: JetonCsrfInvalide):
    return rendre(
        request, "erreur.html", _utilisateur(request), status_code=400,
        titre="Formulaire expiré",
        message="Le formulaire a expiré ou n'est plus valide. Veuillez recharger la page et recommencer.",
    )


@app.exception_handler(StarletteHTTPException)
async def erreur_http(request: Request, exc: StarletteHTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    titres = {404: "Page introuvable", 405: "Méthode non autorisée"}
    messages = {404: "La page ou la déclaration demandée n'existe pas, ou vous n'y avez pas accès."}
    return rendre(
        request, "erreur.html", _utilisateur(request), status_code=exc.status_code,
        titre=titres.get(exc.status_code, "Erreur"),
        message=messages.get(exc.status_code, "Une erreur est survenue. Veuillez réessayer."),
    )
