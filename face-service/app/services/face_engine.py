import logging
from typing import Optional

import cv2
import numpy as np
from insightface.app import FaceAnalysis

logger = logging.getLogger(__name__)

# Chargé UNE SEULE FOIS au démarrage du service, pas à chaque requête (coûteux).
# ctx_id=-1 = CPU uniquement (pas de GPU dans votre conteneur actuel).
_face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
_face_app.prepare(ctx_id=-1, det_size=(640, 640))

EMBEDDINGS_STORE: dict[str, list[float]] = {}

# ATTENTION : avec InsightFace/ArcFace, on utilise la similarité cosinus (0 à 1),
# PLUS HAUT = PLUS proche — c'est l'INVERSE de la distance euclidienne de dlib,
# où plus BAS = plus proche. Ne pas mélanger les deux logiques.
# 0.4 est un point de départ raisonnable documenté pour ce modèle ; à ajuster
# après vos propres tests, comme on l'avait fait pour le seuil dlib.
MATCH_THRESHOLD = 0.4


def bytes_to_image(file_bytes: bytes) -> np.ndarray:
    """
    IMPORTANT : InsightFace attend des images en BGR (comme cv2.imread),
    PAS en RGB comme le faisait face_recognition.load_image_file().
    cv2.imdecode respecte déjà cette convention BGR par défaut.
    """
    array = np.frombuffer(file_bytes, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Similarité cosinus entre deux embeddings, normalisés au préalable."""
    a_norm = a / np.linalg.norm(a)
    b_norm = b / np.linalg.norm(b)
    return float(np.dot(a_norm, b_norm))


def compute_average_embedding(images_bytes: list[bytes]) -> Optional[list[float]]:
    embeddings = []
    for file_bytes in images_bytes:
        image = bytes_to_image(file_bytes)
        faces = _face_app.get(image)
        if faces:
            embeddings.append(faces[0].embedding)
        else:
            logger.warning("Aucun visage détecté sur une photo, ignorée.")
    if not embeddings:
        return None
    return np.mean(embeddings, axis=0).tolist()


def check_liveness(image: np.ndarray) -> bool:
    """TODO : brancher Silent-Face-Anti-Spoofing ici (BF-06). Inchangé par rapport à avant."""
    logger.warning("check_liveness: stub actif.")
    return True


def recognize_face(file_bytes: bytes) -> dict:
    image = bytes_to_image(file_bytes)
    faces = _face_app.get(image)

    if not faces:
        return {"visage_detecte": False}

    if not check_liveness(image):
        return {"visage_detecte": True, "vivant": False, "resultat": "spoof_detecte"}

    # InsightFace peut renvoyer un score de détection (face.det_score) — pas utilisé
    # ici pour rester simple, mais exploitable plus tard pour filtrer les détections peu fiables.
    unknown_embedding = faces[0].embedding

    if not EMBEDDINGS_STORE:
        return {"visage_detecte": True, "vivant": True, "resultat": "inconnu", "raison": "aucune personne enrôlée"}

    known_ids = list(EMBEDDINGS_STORE.keys())
    similarities = [
        cosine_similarity(np.array(EMBEDDINGS_STORE[sid]), unknown_embedding)
        for sid in known_ids
    ]

    # argMAX, pas argmin : on cherche la plus GRANDE similarité, pas la plus petite distance.
    best_index = int(np.argmax(similarities))
    best_similarity = similarities[best_index]

    # >=, pas <= : logique inversée par rapport à MATCH_THRESHOLD avec dlib.
    if best_similarity >= MATCH_THRESHOLD:
        return {
            "visage_detecte": True, "vivant": True, "resultat": "reconnu",
            "subject_id": known_ids[best_index], "confiance": round(best_similarity, 3),
        }

    return {"visage_detecte": True, "vivant": True, "resultat": "inconnu", "similarite_max": round(best_similarity, 3)}