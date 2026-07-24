import logging
from typing import Optional

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from app.services import liveness

logger = logging.getLogger(__name__)

_face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
_face_app.prepare(ctx_id=-1, det_size=(640, 640))

EMBEDDINGS_STORE: dict[str, list[float]] = {}


MATCH_THRESHOLD = 0.4


def bytes_to_image(file_bytes: bytes) -> np.ndarray:
    """cv2.imdecode renvoie déjà du BGR — pas de conversion nécessaire pour
    Silent-Face-Anti-Spoofing, contrairement à la branche dlib (qui travaille
    en RGB via face_recognition et doit convertir avant d'appeler liveness)."""
    array = np.frombuffer(file_bytes, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
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


def check_liveness(image_bgr: np.ndarray, bbox: list) -> bool:
    """BF-06 — même logique de sécurité que la branche dlib : erreur = rejeté."""
    try:
        return liveness.is_real_face(image_bgr, bbox)
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de vivacité : {e}")
        return False


def recognize_face(file_bytes: bytes) -> dict:

    image_bgr = bytes_to_image(file_bytes)
    faces = _face_app.get(image_bgr)

    if not faces:
        return {"visages_detectes": 0, "resultats": []}

    known_ids = list(EMBEDDINGS_STORE.keys())
    known_embeddings = [np.array(EMBEDDINGS_STORE[sid]) for sid in known_ids] if known_ids else []

    resultats = []
    for face in faces:
      
        x1, y1, x2, y2 = face.bbox.astype(int)
        bbox = [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]

        if not check_liveness(image_bgr, bbox):
            resultats.append({"vivant": False, "resultat": "spoof_detecte"})
            continue

        if not known_embeddings:
            resultats.append({"vivant": True, "resultat": "inconnu", "raison": "aucune personne enrôlée"})
            continue

        similarities = [cosine_similarity(emb, face.embedding) for emb in known_embeddings]
        best_index = int(np.argmax(similarities))
        best_similarity = similarities[best_index]

        if best_similarity >= MATCH_THRESHOLD:
            resultats.append({
                "vivant": True, "resultat": "reconnu",
                "subject_id": known_ids[best_index], "confiance": round(best_similarity, 3),
            })
        else:
            resultats.append({"vivant": True, "resultat": "inconnu", "similarite_max": round(best_similarity, 3)})

    return {"visages_detectes": len(faces), "resultats": resultats}