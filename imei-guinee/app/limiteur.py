"""Limitation simple du débit, en mémoire (fenêtre glissante).

Suffisant pour un démonstrateur mono-processus. En production, ce rôle
reviendrait à une passerelle d'API ou à un stockage partagé (Redis, etc.).
"""

import threading
import time
from collections import defaultdict, deque


class LimiteurDebit:
    def __init__(self, limite: int, fenetre_secondes: int):
        self.limite = limite
        self.fenetre = fenetre_secondes
        self._appels: dict[str, deque[float]] = defaultdict(deque)
        self._verrou = threading.Lock()

    def autoriser(self, cle: str) -> tuple[bool, int]:
        """Enregistre un appel pour ``cle``.

        Retourne ``(autorise, secondes_avant_nouvel_essai)``.
        """
        maintenant = time.monotonic()
        with self._verrou:
            appels = self._appels[cle]
            while appels and appels[0] <= maintenant - self.fenetre:
                appels.popleft()
            if len(appels) >= self.limite:
                attente = int(appels[0] + self.fenetre - maintenant) + 1
                return False, max(attente, 1)
            appels.append(maintenant)
            return True, 0

    def reinitialiser(self) -> None:
        with self._verrou:
            self._appels.clear()


def _instance_par_defaut() -> LimiteurDebit:
    from app import config

    return LimiteurDebit(config.LIMITE_VERIFICATIONS, config.FENETRE_LIMITE_SECONDES)


# Instance partagée par la page de vérification et l'API.
limiteur_verification = _instance_par_defaut()
