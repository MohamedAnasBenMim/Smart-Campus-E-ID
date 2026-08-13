"""
Encapsule le tracker multi-objets — ByteTrack, via le paquet `trackers`
(Roboflow, licence Apache 2.0).

IMPORTANT — ce que ce module NE fait PAS :
- Aucune reconnaissance faciale ici (Phase 2 uniquement).
- Aucune notion de zone, d'événement ou de caméra globale.

============================================================
MODE DIAGNOSTIC (temporaire) — track_id qui change à tort
============================================================
Objectif : répondre à UNE question précise — "le track_id change
parce que MediaPipe perd la détection, ou parce que ByteTrack échoue
à réassocier une détection pourtant présente ?"

AUCUNE logique de décision n'est modifiée : la confiance transmise à
ByteTrack reste fixée à 0.9 comme avant (voir commentaire plus bas).
Seule la JOURNALISATION est enrichie.

Pour DÉSACTIVER ce diagnostic une fois l'analyse terminée : mettre
DIAGNOSTIC_LOGGING = False ci-dessous (ou ne pas définir la variable
d'environnement TRACK_DIAGNOSTIC), sans toucher au reste du fichier.
"""

import logging
import os

import numpy as np
import supervision as sv
from trackers import ByteTrackTracker

logger = logging.getLogger(__name__)

# Activable/désactivable sans toucher au code : variable d'environnement
# TRACK_DIAGNOSTIC=true dans docker-compose.yml, ou directement ici.
DIAGNOSTIC_LOGGING = os.environ.get("TRACK_DIAGNOSTIC", "false").lower() == "true"

# Valeur inchangée depuis la Phase 1 — voir diagnostic en cours pour
# savoir si elle doit évoluer. NE PAS modifier avant la fin du diagnostic.
_CONFIANCE_FIXE_TRANSMISE_AU_TRACKER = 0.9


class PersonTracker:
    """Un tracker dédié à UNE seule caméra — voir TrackManager."""

    def __init__(self):
        self._tracker = ByteTrackTracker()

        # État interne, UNIQUEMENT pour le diagnostic — ne participe à
        # aucune décision de tracking, juste à la détection de
        # NEW TRACK / TRACK LOST d'une frame à l'autre.
        self._track_ids_precedents: set[int] = set()
        self._derniere_apparition: dict[int, int] = {}  # track_id -> dernier frame_num vu
        self._dernier_bbox: dict[int, list] = {}  # track_id -> dernière bbox connue
        self._compteur_frames_internes = 0  # utilisé si frame_num n'est pas fourni

    def update(
        self,
        detections: list,
        confidences_reelles: list | None = None,
        frame_num: int | None = None,
    ) -> list[dict]:
        """
        Fait avancer le tracker d'une frame.

        Entrée :
            detections : liste de [x, y, w, h]
            confidences_reelles : NOUVEAU, uniquement pour le diagnostic
                — la vraie confiance MediaPipe par détection, dans le
                même ordre que `detections`. N'influence AUCUNE décision
                du tracker, sert uniquement à être journalisée.
            frame_num : NOUVEAU, uniquement pour le diagnostic — permet
                de dater les logs et calculer "depuis combien de frames
                un track est perdu".

        Sortie : liste de dicts (INCHANGÉE)
            {"track_id": int|None, "bbox": [...], "confiance": float, "etat": str}
        """
        self._compteur_frames_internes += 1
        frame_actuelle = frame_num if frame_num is not None else self._compteur_frames_internes

        if DIAGNOSTIC_LOGGING:
            logger.info(f"[TRACK-DIAG] ===== frame={frame_actuelle} =====")
            logger.info(f"[TRACK-DIAG] MediaPipe a détecté {len(detections)} personne(s)")
            for i, bbox in enumerate(detections):
                conf_reelle = confidences_reelles[i] if confidences_reelles else None
                logger.info(
                    f"[TRACK-DIAG]   detection[{i}] bbox={bbox} "
                    f"confidence_reelle_mediapipe={round(conf_reelle, 3) if conf_reelle is not None else 'N/A'}"
                )

        if not detections:
            self._tracker.update(sv.Detections.empty())
            sorties = []
        else:
            xyxy = np.array(
                [[x, y, x + w, y + h] for x, y, w, h in detections],
                dtype=np.float32,
            )

            # INCHANGÉ — décision de tracking toujours basée sur une
            # confiance fixe, PAS la confiance réelle MediaPipe. Ne pas
            # modifier avant la fin du diagnostic (voir docstring du module).
            confidence_tracker = np.array(
                [_CONFIANCE_FIXE_TRANSMISE_AU_TRACKER] * len(detections),
                dtype=np.float32,
            )
            sv_detections = sv.Detections(xyxy=xyxy, confidence=confidence_tracker)

            resultat = self._tracker.update(sv_detections)

            sorties = []
            for i in range(len(resultat.xyxy)):
                track_id_brut = int(resultat.tracker_id[i])
                x1, y1, x2, y2 = resultat.xyxy[i]
                confiance = float(resultat.confidence[i]) if resultat.confidence is not None else None

                sorties.append({
                    "track_id": track_id_brut if track_id_brut >= 0 else None,
                    "bbox": [int(x1), int(y1), int(x2 - x1), int(y2 - y1)],
                    "confiance": confiance,
                    "etat": "confirme" if track_id_brut >= 0 else "tentative",
                })

        if DIAGNOSTIC_LOGGING:
            self._log_diagnostic_tracks(sorties, frame_actuelle)

        return sorties

    def _log_diagnostic_tracks(self, sorties: list[dict], frame_actuelle: int):
        """Compare les track_id de cette frame à ceux de la frame précédente,
        journalise NEW TRACK / TRACK LOST avec le contexte utile au diagnostic."""

        track_ids_actuels = {t["track_id"] for t in sorties if t["track_id"] is not None}

        logger.info(
            f"[TRACK-DIAG] ByteTrack renvoie {len(sorties)} track(s) : "
            f"{[t['track_id'] for t in sorties]}"
        )

        for t in sorties:
            if t["track_id"] is None:
                continue
            tid = t["track_id"]
            bbox_precedente = self._dernier_bbox.get(tid, "N/A (premiere apparition)")
            logger.info(
                f"[TRACK-DIAG]   track_id={tid} bbox_precedente={bbox_precedente} "
                f"bbox_actuelle={t['bbox']} etat={t['etat']}"
            )

        nouveaux = track_ids_actuels - self._track_ids_precedents
        perdus = self._track_ids_precedents - track_ids_actuels

        for tid in nouveaux:
            bbox_du_nouveau = next((t["bbox"] for t in sorties if t["track_id"] == tid), None)
            logger.info(f"[TRACK-DIAG] *** NEW TRACK *** track_id={tid} bbox={bbox_du_nouveau}")

        for tid in perdus:
            derniere_frame_vue = self._derniere_apparition.get(tid, frame_actuelle)
            frames_depuis = frame_actuelle - derniere_frame_vue
            # Déduction FAITE PAR NOTRE CODE, pas une info native de la
            # bibliothèque (maximum_frames_without_update = 30 par défaut,
            # non modifié — voir tracker._tracker.maximum_frames_without_update).
            seuil = self._tracker.maximum_frames_without_update
            if frames_depuis < seuil:
                statut = f"probablement recuperable (encore {seuil - frames_depuis} frames de tampon)"
            else:
                statut = "tampon depasse -> tres probablement supprime definitivement par ByteTrack"
            logger.info(
                f"[TRACK-DIAG] *** TRACK LOST *** track_id={tid} "
                f"disparu depuis {frames_depuis} frame(s) -> {statut}"
            )

        # Mise à jour de l'état pour la prochaine frame
        for t in sorties:
            if t["track_id"] is not None:
                self._derniere_apparition[t["track_id"]] = frame_actuelle
                self._dernier_bbox[t["track_id"]] = t["bbox"]

        self._track_ids_precedents = track_ids_actuels