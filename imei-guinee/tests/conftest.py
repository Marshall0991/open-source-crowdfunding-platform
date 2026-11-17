import re

import pytest
from fastapi.testclient import TestClient

from app import config
from app.limiteur import limiteur_verification


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    limiteur_verification.reinitialiser()
    from app.main import app

    with TestClient(app) as c:
        yield c
    limiteur_verification.reinitialiser()


def csrf_de(html: str) -> str:
    trouve = re.search(r'name="csrf" value="([^"]+)"', html)
    assert trouve, "jeton CSRF absent de la page"
    return trouve.group(1)


def connecter(client: TestClient, identifiant: str, mot_de_passe: str):
    jeton = csrf_de(client.get("/connexion").text)
    return client.post(
        "/connexion",
        data={"identifiant": identifiant, "mot_de_passe": mot_de_passe, "csrf": jeton},
        follow_redirects=False,
    )


def deconnecter(client: TestClient):
    jeton = csrf_de(client.get("/").text)
    client.post("/deconnexion", data={"csrf": jeton})
