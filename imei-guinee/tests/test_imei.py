from app.imei import cle_luhn, luhn_valide, normaliser, valider_imei


def test_imei_de_reference_valide():
    # Exemple classique de la documentation GSMA / 3GPP.
    assert luhn_valide("490154203237518")
    assert cle_luhn("49015420323751") == "8"


def test_cle_fausse_refusee():
    assert not luhn_valide("490154203237519")
    imei, erreur = valider_imei("490154203237519")
    assert "Luhn" in erreur


def test_normalisation_des_separateurs():
    assert normaliser(" 49-015420 323751.8 ") == "490154203237518"
    assert valider_imei("49 015420 323751 8") == ("490154203237518", None)


def test_messages_d_erreur_explicites():
    assert valider_imei("")[1] == "Veuillez saisir un numéro IMEI."
    assert "que des chiffres" in valider_imei("49015420323751A")[1]
    assert "(vous en avez saisi 14)" in valider_imei("49015420323751")[1]
    assert "(vous en avez saisi 16)" in valider_imei("4901542032375180")[1]
