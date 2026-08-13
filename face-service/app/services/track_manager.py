"""
Maintient un PersonTracker DISTINCT par caméra.

Prépare le terrain pour le multi-caméra (Phase 5) sans le construire
maintenant : chaque camera_id obtient automatiquement son propre
tracker, créé à la demande — ajouter une deuxième caméra plus tard ne
demandera aucune modification de ce fichier.
"""

import logging
import time

from app.services.tracker import PersonTracker

logger = logging.getLogger(__name__)

# Au-delà de cette inactivité, le tracker d'une caméra est supprimé —
# évite une fuite mémoire si des camera_id de test s'accumulent au fil
# des essais (ex. plusieurs noms différents testés dans la journée).
INACTIVITE_MAX_SECONDES = 600  # 10 minutes


class TrackManager:
    def __init__(self):
        self._trackers: dict[str, PersonTracker] = {}
        self._derniere_activite: dict[str, float] = {}

    def get_tracker(self, camera_id: str) -> PersonTracker:
        if camera_id not in self._trackers:
            logger.info(f"[TRACK] Nouveau tracker créé pour camera_id={camera_id}")
            self._trackers[camera_id] = PersonTracker()

        self._derniere_activite[camera_id] = time.time()
        self._nettoyer_inactifs()
        return self._trackers[camera_id]

    def cameras_actives(self) -> list[str]:
        return list(self._trackers.keys())

    def _nettoyer_inactifs(self):
        maintenant = time.time()
        inactifs = [
            cam for cam, derniere in self._derniere_activite.items()
            if maintenant - derniere > INACTIVITE_MAX_SECONDES
        ]
        for cam in inactifs:
            logger.info(f"[TRACK] Tracker inactif supprimé : camera_id={cam}")
            self._trackers.pop(cam, None)
            self._derniere_activite.pop(cam, None)


# Instance UNIQUE, partagée par toute l'application — même logique que
# EMBEDDINGS_STORE dans face_engine.py (un seul état global, par process).
track_manager = TrackManager()