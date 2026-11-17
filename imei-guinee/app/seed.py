"""Jeu de données de démonstration (personnes et IMEI entièrement fictifs).

Usage :
    python -m app.seed            # charge les données si la base est vide
    python -m app.seed --reset    # efface la base et recharge les données

Les IMEI utilisent le préfixe « 00 », réservé aux essais : ils ne
correspondent à aucun appareil réel. Les dates sont calculées par rapport au
jour du chargement, pour que la démonstration reste actuelle.
"""

import argparse
import sqlite3
from datetime import datetime, time, timedelta, timezone

from app import config
from app.db import connecter, initialiser_schema
from app.imei import cle_luhn
from app.securite import hacher_mot_de_passe


def imei_demo(quatorze: str) -> str:
    return quatorze + cle_luhn(quatorze)


# IMEI de référence pour le scénario de démonstration (voir README).
IMEI_SIGNALE = imei_demo("00123456000010")      # déclaration VALIDÉE -> « Signalé »
IMEI_EN_ATTENTE = imei_demo("00123456000020")   # déclaration SOUMISE -> « Non signalé »
IMEI_REJETE = imei_demo("00123456000030")       # déclaration REJETÉE -> « Non signalé »
IMEI_LIBRE = imei_demo("00123456000990")        # aucune déclaration : à déclarer en direct
IMEI_CLE_FAUSSE = IMEI_LIBRE[:14] + str((int(IMEI_LIBRE[14]) + 1) % 10)  # échoue au contrôle de Luhn

COMMUNES = [
    ("Kaloum", "Conakry"), ("Dixinn", "Conakry"), ("Matam", "Conakry"),
    ("Ratoma", "Conakry"), ("Matoto", "Conakry"),
    ("Kindia", "Kindia"), ("Coyah", "Kindia"), ("Dubréka", "Kindia"),
    ("Boké", "Boké"), ("Kamsar", "Boké"),
    ("Mamou", "Mamou"), ("Labé", "Labé"),
    ("Kankan", "Kankan"), ("Siguiri", "Kankan"),
    ("Faranah", "Faranah"), ("Kissidougou", "Faranah"),
    ("N'Zérékoré", "N'Zérékoré"),
]

# (identifiant, nom complet, rôle, unité, mot de passe)
UTILISATEURS = [
    ("victime1", "Aïssatou Diallo", "VICTIME", None, "demo1234"),
    ("victime2", "Ibrahima Camara", "VICTIME", None, "demo1234"),
    ("victime3", "Mariama Sow", "VICTIME", None, "demo1234"),
    ("victime4", "Ousmane Barry", "VICTIME", None, "demo1234"),
    ("victime5", "Fanta Kourouma", "VICTIME", None, "demo1234"),
    ("agent", "Brigadier-chef Fatoumata Bah", "AGENT", "Commissariat central de Kaloum", "police1234"),
    ("agent2", "Inspecteur Moussa Kaba", "AGENT", "Commissariat central de Ratoma", "police1234"),
]

# (imei, déclarant, type, marque, modèle, couleur, commune, jours avant aujourd'hui,
#  récépissé, statut, agent, motif de rejet)
DECLARATIONS = [
    (IMEI_SIGNALE, "victime1", "VOL", "Samsung", "Galaxy A15", "Noir", "Kaloum", 24,
     "PV-KAL-2026-0412", "VALIDE", "agent", None),
    (IMEI_EN_ATTENTE, "victime2", "VOL", "Tecno", "Spark 20", "Bleu", "Ratoma", 2,
     "PV-RAT-2026-1187", "SOUMIS", None, None),
    (IMEI_REJETE, "victime3", "PERTE", "Itel", "A70", "Doré", "Matam", 15,
     "DP-MAT-2026-0093", "REJETE", "agent2",
     "Récépissé de plainte introuvable ou non concordant : le numéro indiqué ne figure pas au registre."),
    (imei_demo("00123456000040"), "victime4", "VOL", "Infinix", "Hot 40i", "Vert", "Matoto", 40,
     "PV-MTT-2026-0301", "VALIDE", "agent2", None),
    (imei_demo("00123456000050"), "victime5", "VOL", "Apple", "iPhone 12", "Blanc", "Dixinn", 33,
     "PV-DIX-2026-0277", "VALIDE", "agent", None),
    (imei_demo("00123456000060"), "victime2", "VOL", "Xiaomi", "Redmi Note 13", "Gris", "Ratoma", 19,
     "PV-RAT-2026-1022", "VALIDE", "agent2", None),
    (imei_demo("00123456000070"), "victime3", "PERTE", "Samsung", "Galaxy A05", "Argent", "Kindia", 12,
     "DP-KIN-2026-0058", "VALIDE", "agent", None),
    (imei_demo("00123456000080"), "victime4", "VOL", "Tecno", "Camon 30", "Noir", "Kankan", 9,
     "PV-KAN-2026-0144", "VALIDE", "agent", None),
    (imei_demo("00123456000090"), "victime5", "VOL", "Itel", "S23", "Bleu", "Ratoma", 6,
     "PV-RAT-2026-1201", "VALIDE", "agent2", None),
    (imei_demo("00123456000100"), "victime1", "VOL", "Huawei", "Nova Y70", "Violet", "Matoto", 5,
     "PV-MTT-2026-0388", "REJETE", "agent2",
     "Informations incohérentes avec la plainte enregistrée (marque et modèle différents)."),
    (imei_demo("00123456000110"), "victime3", "VOL", "Infinix", "Smart 8", "Noir", "Labé", 4,
     "PV-LAB-2026-0071", "SOUMIS", None, None),
    (imei_demo("00123456000120"), "victime4", "PERTE", "Oppo", "A38", "Doré", "N'Zérékoré", 3,
     "DP-NZE-2026-0036", "SOUMIS", None, None),
    (imei_demo("00123456000130"), "victime5", "VOL", "Samsung", "Galaxy A25", "Bleu", "Kaloum", 1,
     "PV-KAL-2026-0459", "SOUMIS", None, None),
    (imei_demo("00123456000140"), "victime2", "VOL", "Tecno", "Pop 8", "Noir", "Boké", 28,
     "PV-BOK-2026-0119", "VALIDE", "agent", None),
]


def _iso(moment: datetime) -> str:
    return moment.replace(microsecond=0).isoformat()


def base_vide(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT COUNT(*) FROM utilisateur").fetchone()[0] == 0


def charger(conn: sqlite3.Connection) -> None:
    """Insère communes, comptes et déclarations de démonstration."""
    with conn:
        conn.executemany("INSERT INTO commune (nom, region) VALUES (?, ?)", COMMUNES)
        commune_id = {nom: i for i, nom in conn.execute("SELECT id, nom FROM commune")}

        cree_le = _iso(datetime.now(timezone.utc) - timedelta(days=60))
        for identifiant, nom, role, unite, mot_de_passe in UTILISATEURS:
            conn.execute(
                "INSERT INTO utilisateur (identifiant, nom_complet, role, unite, mot_de_passe_hash, cree_le) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (identifiant, nom, role, unite, hacher_mot_de_passe(mot_de_passe), cree_le),
            )
        uid = {ident: i for i, ident in conn.execute("SELECT id, identifiant FROM utilisateur")}

        aujourd_hui = datetime.now(timezone.utc).date()
        for numero, (imei, declarant, type_ev, marque, modele, couleur, commune, jours,
                     recepisse, statut, agent, motif) in enumerate(DECLARATIONS, start=1):
            jour_evenement = aujourd_hui - timedelta(days=jours)
            # Dépôt le lendemain de l'événement (ou le jour même s'il est récent), en fin de matinée.
            jour_depot = min(jour_evenement + timedelta(days=1), aujourd_hui)
            soumis = datetime.combine(jour_depot, time(9 + numero % 4, 10 + numero * 3 % 50), timezone.utc)
            soumis = min(soumis, datetime.now(timezone.utc) - timedelta(minutes=30))
            traite = soumis + timedelta(hours=3 + numero % 5) if statut != "SOUMIS" else None

            curseur = conn.execute(
                """INSERT INTO declaration (reference, imei, type_evenement, marque, modele, couleur,
                       commune_id, date_evenement, numero_recepisse, statut, declarant_id, soumis_le,
                       traite_par_id, traite_le, motif_rejet)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"DEC-{soumis.year}-{numero:06d}", imei, type_ev, marque, modele, couleur,
                    commune_id[commune], jour_evenement.isoformat(), recepisse, statut, uid[declarant],
                    _iso(soumis), uid[agent] if agent else None, _iso(traite) if traite else None, motif,
                ),
            )
            declaration_id = curseur.lastrowid
            conn.execute(
                "INSERT INTO historique_statut (declaration_id, statut_avant, statut_apres, auteur_id, "
                "horodatage, commentaire) VALUES (?, NULL, 'SOUMIS', ?, ?, 'Déclaration déposée en ligne')",
                (declaration_id, uid[declarant], _iso(soumis)),
            )
            if statut != "SOUMIS":
                commentaire = motif or "Déclaration validée après contrôle du récépissé de plainte"
                conn.execute(
                    "INSERT INTO historique_statut (declaration_id, statut_avant, statut_apres, auteur_id, "
                    "horodatage, commentaire) VALUES (?, 'SOUMIS', ?, ?, ?, ?)",
                    (declaration_id, statut, uid[agent], _iso(traite), commentaire),
                )

        # Quelques vérifications publiques passées, pour animer le tableau de bord.
        journal = [("NON_SIGNALE", 31), ("SIGNALE", 9), ("INVALIDE", 4)]
        maintenant = datetime.now(timezone.utc)
        for resultat, nombre in journal:
            conn.executemany(
                "INSERT INTO journal_verification (horodatage, resultat) VALUES (?, ?)",
                [(_iso(maintenant - timedelta(hours=7 * i + 1)), resultat) for i in range(nombre)],
            )


def initialiser(reinitialiser: bool = False) -> bool:
    """Crée le schéma et charge les données si nécessaire. Retourne vrai si chargées."""
    if reinitialiser and config.DB_PATH.exists():
        config.DB_PATH.unlink()
    conn = connecter()
    try:
        initialiser_schema(conn)
        if base_vide(conn):
            charger(conn)
            return True
        return False
    finally:
        conn.close()


def main() -> None:
    parseur = argparse.ArgumentParser(description="Charge le jeu de données de démonstration.")
    parseur.add_argument("--reset", action="store_true", help="efface la base avant de recharger")
    args = parseur.parse_args()
    charge = initialiser(reinitialiser=args.reset)
    print(f"Base : {config.DB_PATH}")
    print("Données de démonstration chargées." if charge else "La base contenait déjà des données.")
    print(f"  IMEI signalé (validé)        : {IMEI_SIGNALE}")
    print(f"  IMEI en attente (soumis)     : {IMEI_EN_ATTENTE}")
    print(f"  IMEI rejeté                  : {IMEI_REJETE}")
    print(f"  IMEI libre (à déclarer)      : {IMEI_LIBRE}")
    print(f"  IMEI à clé de contrôle fausse : {IMEI_CLE_FAUSSE}")


if __name__ == "__main__":
    main()
