"""Validation des numéros IMEI (15 chiffres, clé de contrôle de Luhn)."""

import re

_SEPARATEURS = re.compile(r"[\s\-./]")


def normaliser(saisie: str | None) -> str:
    """Retire les espaces, tirets, points et barres obliques d'une saisie."""
    return _SEPARATEURS.sub("", saisie or "")


def cle_luhn(quatorze_chiffres: str) -> str:
    """Calcule le 15e chiffre (clé de contrôle) à partir des 14 premiers."""
    total = 0
    for position, caractere in enumerate(quatorze_chiffres):
        chiffre = int(caractere)
        if position % 2 == 1:  # un chiffre sur deux, en partant de la gauche
            chiffre *= 2
            if chiffre > 9:
                chiffre -= 9
        total += chiffre
    return str((10 - total % 10) % 10)


def luhn_valide(imei: str) -> bool:
    """Vrai si l'IMEI à 15 chiffres porte une clé de Luhn correcte."""
    return len(imei) == 15 and imei.isdigit() and cle_luhn(imei[:14]) == imei[14]


def valider_imei(saisie: str | None) -> tuple[str, str | None]:
    """Normalise et valide une saisie.

    Retourne ``(imei_normalise, message_erreur)`` ; ``message_erreur`` vaut
    ``None`` si l'IMEI est valide.
    """
    imei = normaliser(saisie)
    if not imei:
        return imei, "Veuillez saisir un numéro IMEI."
    if not imei.isdigit():
        return imei, "Le numéro IMEI ne doit contenir que des chiffres."
    if len(imei) != 15:
        return imei, (
            "Le numéro IMEI doit comporter exactement 15 chiffres "
            f"(vous en avez saisi {len(imei)})."
        )
    if not luhn_valide(imei):
        return imei, (
            "Ce numéro IMEI n'est pas valide : son chiffre de contrôle (algorithme de Luhn) "
            "ne correspond pas. Vérifiez votre saisie en composant *#06# sur l'appareil."
        )
    return imei, None
