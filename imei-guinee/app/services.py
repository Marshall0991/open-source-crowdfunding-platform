"""Règles métier : déclaration, cycle de vie, vérification publique, statistiques."""

import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import date

from app.db import maintenant
from app.imei import valider_imei

STATUTS = ("SOUMIS", "VALIDE", "REJETE")
TYPES_EVENEMENT = {"VOL": "Vol", "PERTE": "Perte"}

MARQUES_COURANTES = [
    "Tecno", "Itel", "Infinix", "Samsung", "Apple", "Xiaomi", "Huawei",
    "Oppo", "Realme", "Nokia", "Vivo", "Motorola",
]
COULEURS_COURANTES = ["Noir", "Blanc", "Gris", "Bleu", "Vert", "Rouge", "Doré", "Argent", "Violet"]

MOTIFS_REJET = [
    "Récépissé de plainte introuvable ou non concordant",
    "Informations incohérentes avec la plainte enregistrée",
    "Déclaration erronée ou effectuée par erreur",
    "Appareil retrouvé et restitué",
    "Autre motif",
]


class ErreurMetier(Exception):
    """Erreur fonctionnelle à présenter telle quelle à l'utilisateur."""


@dataclass
class ResultatValidation:
    donnees: dict
    erreurs: dict = field(default_factory=dict)

    @property
    def valide(self) -> bool:
        return not self.erreurs


# --- Déclaration -------------------------------------------------------------

def _texte(valeur: str | None, longueur_max: int) -> str:
    return " ".join((valeur or "").split())[:longueur_max]


def valider_formulaire_declaration(db: sqlite3.Connection, saisie: dict) -> ResultatValidation:
    """Contrôle les champs du formulaire et renvoie les données nettoyées."""
    erreurs: dict[str, str] = {}

    imei, erreur_imei = valider_imei(saisie.get("imei"))
    if erreur_imei:
        erreurs["imei"] = erreur_imei

    type_evenement = (saisie.get("type_evenement") or "").upper()
    if type_evenement not in TYPES_EVENEMENT:
        erreurs["type_evenement"] = "Veuillez préciser s'il s'agit d'un vol ou d'une perte."

    donnees = {
        "imei": imei,
        "type_evenement": type_evenement,
        "marque": _texte(saisie.get("marque"), 40),
        "modele": _texte(saisie.get("modele"), 60),
        "couleur": _texte(saisie.get("couleur"), 30),
        "numero_recepisse": _texte(saisie.get("numero_recepisse"), 40),
        "commune_id": None,
        "date_evenement": "",
    }

    for champ, libelle in (("marque", "la marque"), ("modele", "le modèle"), ("couleur", "la couleur")):
        if not donnees[champ]:
            erreurs[champ] = f"Veuillez indiquer {libelle} de l'appareil."

    if len(donnees["numero_recepisse"]) < 3:
        erreurs["numero_recepisse"] = (
            "Veuillez indiquer le numéro du récépissé de plainte ou de déclaration de perte."
        )

    try:
        commune_id = int(saisie.get("commune_id") or 0)
    except ValueError:
        commune_id = 0
    if not db.execute("SELECT 1 FROM commune WHERE id = ?", (commune_id,)).fetchone():
        erreurs["commune_id"] = "Veuillez sélectionner la commune où l'événement s'est produit."
    else:
        donnees["commune_id"] = commune_id

    brute = (saisie.get("date_evenement") or "").strip()
    try:
        jour = date.fromisoformat(brute)
        if jour > date.today():
            erreurs["date_evenement"] = "La date de l'événement ne peut pas être dans le futur."
        elif jour < date(2000, 1, 1):
            erreurs["date_evenement"] = "La date de l'événement n'est pas plausible."
        donnees["date_evenement"] = jour.isoformat()
    except ValueError:
        erreurs["date_evenement"] = "Veuillez indiquer la date de l'événement (jj/mm/aaaa)."
        donnees["date_evenement"] = brute

    if not saisie.get("attestation"):
        erreurs["attestation"] = "Vous devez attester de l'exactitude des informations fournies."

    return ResultatValidation(donnees=donnees, erreurs=erreurs)


def declaration_active_pour_imei(db: sqlite3.Connection, imei: str) -> sqlite3.Row | None:
    return db.execute(
        "SELECT * FROM declaration WHERE imei = ? AND statut IN ('SOUMIS', 'VALIDE')", (imei,)
    ).fetchone()


def creer_declaration(
    db: sqlite3.Connection, declarant_id: int, donnees: dict, horodatage: str | None = None
) -> str:
    """Enregistre une déclaration au statut SOUMIS et retourne sa référence."""
    existante = declaration_active_pour_imei(db, donnees["imei"])
    if existante:
        if existante["declarant_id"] == declarant_id:
            raise ErreurMetier(
                f"Vous avez déjà déclaré cet appareil (référence {existante['reference']}). "
                "Vous pouvez suivre son traitement dans « Mes déclarations »."
            )
        raise ErreurMetier(
            "Cet IMEI fait déjà l'objet d'une déclaration en cours de traitement ou validée. "
            "Si vous pensez qu'il s'agit d'une erreur, présentez-vous au commissariat le plus "
            "proche muni de votre récépissé de plainte."
        )

    horodatage = horodatage or maintenant()
    try:
        with db:
            curseur = db.execute(
                """INSERT INTO declaration (reference, imei, type_evenement, marque, modele, couleur,
                       commune_id, date_evenement, numero_recepisse, statut, declarant_id, soumis_le)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'SOUMIS', ?, ?)""",
                (
                    f"tmp-{uuid.uuid4()}", donnees["imei"], donnees["type_evenement"],
                    donnees["marque"], donnees["modele"], donnees["couleur"], donnees["commune_id"],
                    donnees["date_evenement"], donnees["numero_recepisse"], declarant_id, horodatage,
                ),
            )
            identifiant = curseur.lastrowid
            reference = f"DEC-{horodatage[:4]}-{identifiant:06d}"
            db.execute("UPDATE declaration SET reference = ? WHERE id = ?", (reference, identifiant))
            db.execute(
                """INSERT INTO historique_statut
                       (declaration_id, statut_avant, statut_apres, auteur_id, horodatage, commentaire)
                   VALUES (?, NULL, 'SOUMIS', ?, ?, 'Déclaration déposée en ligne')""",
                (identifiant, declarant_id, horodatage),
            )
    except sqlite3.IntegrityError as exc:
        # Filet de sécurité si deux déclarations du même IMEI arrivent simultanément.
        raise ErreurMetier(
            "Cet IMEI fait déjà l'objet d'une déclaration en cours de traitement ou validée."
        ) from exc
    return reference


# --- Cycle de vie : SOUMIS -> VALIDE | REJETE ---------------------------------

def _changer_statut(
    db: sqlite3.Connection, reference: str, agent_id: int, nouveau: str,
    motif: str | None, commentaire: str, horodatage: str | None,
) -> None:
    horodatage = horodatage or maintenant()
    with db:
        ligne = db.execute("SELECT id, statut FROM declaration WHERE reference = ?", (reference,)).fetchone()
        if ligne is None:
            raise ErreurMetier("Déclaration introuvable.")
        # La condition « statut = 'SOUMIS' » garantit qu'une déclaration n'est traitée qu'une fois.
        curseur = db.execute(
            """UPDATE declaration
                  SET statut = ?, traite_par_id = ?, traite_le = ?, motif_rejet = ?
                WHERE id = ? AND statut = 'SOUMIS'""",
            (nouveau, agent_id, horodatage, motif, ligne["id"]),
        )
        if curseur.rowcount != 1:
            raise ErreurMetier("Cette déclaration a déjà été traitée ; son statut ne peut plus être modifié.")
        db.execute(
            """INSERT INTO historique_statut
                   (declaration_id, statut_avant, statut_apres, auteur_id, horodatage, commentaire)
               VALUES (?, 'SOUMIS', ?, ?, ?, ?)""",
            (ligne["id"], nouveau, agent_id, horodatage, commentaire),
        )


def valider_declaration(
    db: sqlite3.Connection, reference: str, agent_id: int, horodatage: str | None = None
) -> None:
    _changer_statut(
        db, reference, agent_id, "VALIDE", None,
        "Déclaration validée après contrôle du récépissé de plainte", horodatage,
    )


def rejeter_declaration(
    db: sqlite3.Connection, reference: str, agent_id: int, motif: str, horodatage: str | None = None
) -> None:
    motif = " ".join((motif or "").split())
    if len(motif) < 5:
        raise ErreurMetier("Le motif du rejet est obligatoire (5 caractères au minimum).")
    _changer_statut(db, reference, agent_id, "REJETE", motif[:500], motif[:500], horodatage)


# --- Vérification publique ---------------------------------------------------

def imei_signale(db: sqlite3.Connection, imei: str) -> bool:
    """Un IMEI n'est « Signalé » que s'il existe une déclaration VALIDÉE."""
    return db.execute(
        "SELECT 1 FROM declaration WHERE imei = ? AND statut = 'VALIDE' LIMIT 1", (imei,)
    ).fetchone() is not None


def journaliser_verification(db: sqlite3.Connection, resultat: str) -> None:
    with db:
        db.execute(
            "INSERT INTO journal_verification (horodatage, resultat) VALUES (?, ?)",
            (maintenant(), resultat),
        )


# --- Lectures ----------------------------------------------------------------

_SELECT_DECLARATION = """
    SELECT d.*, c.nom AS commune, c.region AS region,
           u.nom_complet AS declarant_nom, u.identifiant AS declarant_identifiant,
           a.nom_complet AS agent_nom, a.unite AS agent_unite
      FROM declaration d
      JOIN commune c          ON c.id = d.commune_id
      JOIN utilisateur u      ON u.id = d.declarant_id
      LEFT JOIN utilisateur a ON a.id = d.traite_par_id
"""


def obtenir_declaration(db: sqlite3.Connection, reference: str) -> sqlite3.Row | None:
    return db.execute(_SELECT_DECLARATION + " WHERE d.reference = ?", (reference,)).fetchone()


def declarations_de(db: sqlite3.Connection, declarant_id: int) -> list[sqlite3.Row]:
    return db.execute(
        _SELECT_DECLARATION + " WHERE d.declarant_id = ? ORDER BY d.soumis_le DESC", (declarant_id,)
    ).fetchall()


def declarations_en_attente(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute(
        _SELECT_DECLARATION + " WHERE d.statut = 'SOUMIS' ORDER BY d.soumis_le ASC"
    ).fetchall()


def declarations_traitees(db: sqlite3.Connection, limite: int = 50) -> list[sqlite3.Row]:
    return db.execute(
        _SELECT_DECLARATION + " WHERE d.statut != 'SOUMIS' ORDER BY d.traite_le DESC LIMIT ?", (limite,)
    ).fetchall()


def historique(db: sqlite3.Connection, declaration_id: int) -> list[sqlite3.Row]:
    return db.execute(
        """SELECT h.*, u.nom_complet AS auteur_nom, u.role AS auteur_role, u.unite AS auteur_unite
             FROM historique_statut h JOIN utilisateur u ON u.id = h.auteur_id
            WHERE h.declaration_id = ? ORDER BY h.horodatage, h.id""",
        (declaration_id,),
    ).fetchall()


def antecedents_imei(db: sqlite3.Connection, imei: str, sauf_id: int) -> list[sqlite3.Row]:
    """Autres déclarations portant sur le même IMEI (utile à l'agent)."""
    return db.execute(
        "SELECT reference, statut, soumis_le, motif_rejet FROM declaration "
        "WHERE imei = ? AND id != ? ORDER BY soumis_le DESC",
        (imei, sauf_id),
    ).fetchall()


def communes(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute("SELECT id, nom, region FROM commune ORDER BY region, nom").fetchall()


def compter_en_attente(db: sqlite3.Connection) -> int:
    return db.execute("SELECT COUNT(*) FROM declaration WHERE statut = 'SOUMIS'").fetchone()[0]


# --- Statistiques (agrégats, sans donnée personnelle) ------------------------

def statistiques(db: sqlite3.Connection) -> dict:
    par_statut = {statut: 0 for statut in STATUTS}
    for ligne in db.execute("SELECT statut, COUNT(*) AS n FROM declaration GROUP BY statut"):
        par_statut[ligne["statut"]] = ligne["n"]

    par_type = {cle: 0 for cle in TYPES_EVENEMENT}
    for ligne in db.execute("SELECT type_evenement, COUNT(*) AS n FROM declaration GROUP BY type_evenement"):
        par_type[ligne["type_evenement"]] = ligne["n"]

    par_commune = [
        dict(ligne)
        for ligne in db.execute(
            """SELECT c.nom AS commune, c.region AS region,
                      SUM(d.statut = 'SOUMIS') AS soumis,
                      SUM(d.statut = 'VALIDE') AS valide,
                      SUM(d.statut = 'REJETE') AS rejete,
                      COUNT(*) AS total
                 FROM declaration d JOIN commune c ON c.id = d.commune_id
                GROUP BY c.id
                ORDER BY total DESC, c.nom"""
        )
    ]

    verifications = {"SIGNALE": 0, "NON_SIGNALE": 0, "INVALIDE": 0}
    for ligne in db.execute("SELECT resultat, COUNT(*) AS n FROM journal_verification GROUP BY resultat"):
        verifications[ligne["resultat"]] = ligne["n"]

    return {
        "total": sum(par_statut.values()),
        "par_statut": par_statut,
        "par_type": par_type,
        "par_commune": par_commune,
        "max_commune": max((c["total"] for c in par_commune), default=0),
        "verifications": verifications,
        "total_verifications": sum(verifications.values()),
    }
