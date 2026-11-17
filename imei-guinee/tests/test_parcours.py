"""Scénario complet et règles métier, à travers l'interface web."""

import re
from datetime import date, timedelta

from app import seed
from tests.conftest import connecter, csrf_de, deconnecter


def verifier(client, imei):
    return client.post("/verifier", data={"imei": imei})


def resultat(reponse) -> str:
    """Extrait le libellé du résultat affiché (« Signalé » / « Non signalé »)."""
    trouve = re.search(r'text-3xl font-extrabold[^"]*">([^<]+)<', reponse.text)
    return trouve.group(1) if trouve else ""


def formulaire(**surcharges):
    donnees = {
        "imei": seed.IMEI_LIBRE, "type_evenement": "VOL", "marque": "Tecno", "modele": "Spark 10",
        "couleur": "Noir", "commune_id": "1", "date_evenement": (date.today() - timedelta(days=1)).isoformat(),
        "numero_recepisse": "PV-KAL-2026-9999", "attestation": "1",
    }
    donnees.update(surcharges)
    return donnees


def declarer(client, **surcharges):
    jeton = csrf_de(client.get("/espace/declarer").text)
    return client.post("/espace/declarer", data={**formulaire(**surcharges), "csrf": jeton}, follow_redirects=False)


def test_donnees_de_demo_coherentes(client):
    assert resultat(verifier(client, seed.IMEI_SIGNALE)) == "Signalé"
    assert resultat(verifier(client, seed.IMEI_EN_ATTENTE)) == "Non signalé"
    assert resultat(verifier(client, seed.IMEI_REJETE)) == "Non signalé"
    assert resultat(verifier(client, seed.IMEI_LIBRE)) == "Non signalé"
    r = verifier(client, seed.IMEI_CLE_FAUSSE)
    assert r.status_code == 422 and "Luhn" in r.text


def test_scenario_declarer_valider_verifier(client):
    # 1. La victime déclare un appareil.
    assert connecter(client, "victime1", "demo1234").headers["location"] == "/espace"
    r = declarer(client)
    assert r.status_code == 303
    reference = r.headers["location"].rsplit("/", 1)[-1]
    assert reference.startswith("DEC-")
    page = client.get(f"/espace/declarations/{reference}").text
    assert "Soumis" in page and "Aïssatou Diallo" in page

    # 2. Tant qu'elle n'est pas validée, l'IMEI reste « Non signalé ».
    assert resultat(verifier(client, seed.IMEI_LIBRE)) == "Non signalé"
    deconnecter(client)

    # 3. L'agent valide.
    assert connecter(client, "agent", "police1234").headers["location"] == "/agent"
    assert reference in client.get("/agent").text
    jeton = csrf_de(client.get(f"/agent/declarations/{reference}").text)
    r = client.post(f"/agent/declarations/{reference}/valider", data={"csrf": jeton, "controle": "1"}, follow_redirects=False)
    assert r.status_code == 303
    deconnecter(client)

    # 4. L'IMEI est désormais « Signalé » ; la victime voit le statut et l'historique.
    assert resultat(verifier(client, seed.IMEI_LIBRE)) == "Signalé"
    connecter(client, "victime1", "demo1234")
    page = client.get(f"/espace/declarations/{reference}").text
    assert "Validé" in page and "Brigadier-chef Fatoumata Bah" in page


def test_rejet_avec_motif_obligatoire(client):
    connecter(client, "agent", "police1234")
    page = client.get("/agent").text
    reference = re.search(r"(DEC-\d{4}-000002)", page).group(1)
    jeton = csrf_de(client.get(f"/agent/declarations/{reference}").text)

    r = client.post(f"/agent/declarations/{reference}/rejeter", data={"csrf": jeton, "motif": ""})
    assert r.status_code == 422 and "motif" in r.text
    r = client.post(f"/agent/declarations/{reference}/rejeter", data={"csrf": jeton, "motif": "Autre motif"})
    assert r.status_code == 422

    r = client.post(
        f"/agent/declarations/{reference}/rejeter",
        data={"csrf": jeton, "motif": "Autre motif", "precisions": "Plainte retirée par le déclarant"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    page = client.get(f"/agent/declarations/{reference}").text
    assert "Rejeté" in page and "Plainte retirée par le déclarant" in page

    # Une déclaration traitée ne peut plus changer de statut.
    r = client.post(f"/agent/declarations/{reference}/valider", data={"csrf": jeton, "controle": "1"})
    assert r.status_code == 409 and "déjà été traitée" in r.text
    assert resultat(verifier(client, seed.IMEI_EN_ATTENTE)) == "Non signalé"


def test_doublon_refuse_puis_possible_apres_rejet(client):
    connecter(client, "victime1", "demo1234")
    r = declarer(client, imei=seed.IMEI_EN_ATTENTE)  # déjà déclaré par victime2, en attente
    assert r.status_code == 409 and "déjà l&#39;objet" in r.text
    r = declarer(client, imei=seed.IMEI_SIGNALE)  # déjà déclaré par victime1, validé
    assert r.status_code == 409 and "Vous avez déjà déclaré cet appareil" in r.text
    r = declarer(client, imei=seed.IMEI_REJETE)  # rejeté : une nouvelle déclaration est admise
    assert r.status_code == 303


def test_validation_du_formulaire(client):
    connecter(client, "victime1", "demo1234")
    r = declarer(client, imei=seed.IMEI_CLE_FAUSSE, marque="", commune_id="999",
                 date_evenement=(date.today() + timedelta(days=3)).isoformat(), attestation="")
    assert r.status_code == 422
    for message in ("Luhn", "la marque", "commune", "dans le futur", "attester"):
        assert message in r.text


def test_reponse_publique_sans_donnee_personnelle(client):
    html = verifier(client, seed.IMEI_SIGNALE).text
    for donnee in ("Aïssatou", "Diallo", "Galaxy", "Kaloum", "PV-KAL"):
        assert donnee not in html.split('id="resultat"')[1].split("</form>")[0]
    json = client.get(f"/api/v1/verification/{seed.IMEI_SIGNALE}").json()
    assert json == {"imei": seed.IMEI_SIGNALE, "resultat": "SIGNALE", "libelle": "Signalé"}


def test_limitation_du_debit(client):
    for _ in range(10):
        assert verifier(client, seed.IMEI_LIBRE).status_code == 200
    r = verifier(client, seed.IMEI_LIBRE)
    assert r.status_code == 429 and "Trop de vérifications" in r.text
    assert int(r.headers["Retry-After"]) >= 1
    assert client.get(f"/api/v1/verification/{seed.IMEI_LIBRE}").status_code == 429


def test_controle_des_roles(client):
    assert client.get("/agent", follow_redirects=False).headers["location"] == "/connexion?suivant=/agent"
    connecter(client, "victime1", "demo1234")
    assert client.get("/agent").status_code == 403
    # Une victime ne voit pas la déclaration d'une autre victime.
    connecter(client, "victime2", "demo1234")
    page = client.get("/espace").text
    autre = re.search(r"/espace/declarations/(DEC-\d{4}-\d{6})", page).group(1)
    deconnecter(client)
    connecter(client, "victime1", "demo1234")
    assert client.get(f"/espace/declarations/{autre}").status_code == 404
    deconnecter(client)
    connecter(client, "agent", "police1234")
    assert client.get("/espace").status_code == 403


def test_csrf_et_identifiants(client):
    r = client.post("/connexion", data={"identifiant": "agent", "mot_de_passe": "police1234", "csrf": "faux"})
    assert r.status_code == 400
    r = connecter(client, "agent", "mauvais")
    assert r.status_code == 401 and "incorrect" in r.text


def test_redirection_ouverte_impossible(client):
    jeton = csrf_de(client.get("/connexion").text)
    r = client.post("/connexion", data={"identifiant": "victime1", "mot_de_passe": "demo1234",
                                        "csrf": jeton, "suivant": "//exemple.org"}, follow_redirects=False)
    assert r.headers["location"] == "/espace"


def test_tableau_de_bord(client):
    page = client.get("/tableau-de-bord").text
    assert "Déclarations par commune" in page and "Ratoma" in page
    assert "Aïssatou" not in page
