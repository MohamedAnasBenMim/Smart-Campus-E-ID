import io
import logging
from typing import Optional

import face_recognition
import numpy as np

logger = logging.getLogger(__name__)

# Cache mémoire : { subject_id: embedding }
EMBEDDINGS_STORE: dict[str, list[float]] = {}
MATCH_THRESHOLD = 0.6


def bytes_to_image(file_bytes: bytes) -> np.ndarray:
    return face_recognition.load_image_file(io.BytesIO(file_bytes))


def compute_average_embedding(images_bytes: list[bytes]) -> Optional[list[float]]:
    encodings = []
    for file_bytes in images_bytes:
        image = bytes_to_image(file_bytes)
        faces = face_recognition.face_encodings(image)
        if faces:
            encodings.append(faces[0])
        else:
            logger.warning("Aucun visage détecté sur une photo, ignorée.")
    if not encodings:
        return None
    return np.mean(encodings, axis=0).tolist()


def check_liveness(image: np.ndarray) -> bool:
    logger.warning("check_liveness: stub actif.")
    return True


def recognize_face(file_bytes: bytes) -> dict:
    image = bytes_to_image(file_bytes)
    face_locations = face_recognition.face_locations(image)

    if not face_locations:
        return {"visage_detecte": False}

    if not check_liveness(image):
        return {"visage_detecte": True, "vivant": False, "resultat": "spoof_detecte"}

    unknown_encoding = face_recognition.face_encodings(image, known_face_locations=face_locations)[0]

    if not EMBEDDINGS_STORE:
        return {"visage_detecte": True, "vivant": True, "resultat": "inconnu", "raison": "aucune personne enrôlée"}

    known_ids = list(EMBEDDINGS_STORE.keys())
    known_encodings = [np.array(EMBEDDINGS_STORE[sid]) for sid in known_ids]
    distances = face_recognition.face_distance(known_encodings, unknown_encoding)
    best_index = int(np.argmin(distances))
    best_distance = float(distances[best_index])

    if best_distance <= MATCH_THRESHOLD:
        return {
            "visage_detecte": True, "vivant": True, "resultat": "reconnu",
            "subject_id": known_ids[best_index], "confiance": round(1 - best_distance, 3),
        }

    return {"visage_detecte": True, "vivant": True, "resultat": "inconnu", "distance_min": round(best_distance, 3)}
