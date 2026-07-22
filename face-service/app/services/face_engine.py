import io
import logging

import cv2
import face_recognition
import numpy as np

from app.services import liveness

logger = logging.getLogger(__name__)

EMBEDDINGS_STORE: dict[str, list[float]] = {}
MATCH_THRESHOLD = 0.6


def bytes_to_image(file_bytes: bytes) -> np.ndarray:
    return face_recognition.load_image_file(io.BytesIO(file_bytes))


def compute_average_embedding(images_bytes: list[bytes]) -> list[float] | None:
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


def check_liveness(image_bgr: np.ndarray, bbox: list) -> bool:
    """
    BF-06 — Vérifie la vivacité d'UN visage précis (bbox), via
    Silent-Face-Anti-Spoofing.

    Choix de sécurité assumé : en cas d'erreur technique (modèle non
    chargé, bbox invalide...), on considère le visage comme NON vivant
    plutôt que de laisser passer par défaut — mieux vaut une fausse
    alerte à vérifier qu'une fraude non détectée à cause d'un bug.
    """
    try:
        return liveness.is_real_face(image_bgr, bbox)
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de vivacité : {e}")
        return False


def recognize_face(file_bytes: bytes) -> dict:
    """
    BF-05 à BF-08 — Détecte, vérifie la vivacité et identifie TOUS les
    visages présents dans l'image (pas seulement le premier), pour gérer
    le cas de plusieurs personnes passant ensemble devant une caméra.
    """
    image_rgb = bytes_to_image(file_bytes)
    face_locations = face_recognition.face_locations(image_rgb)

    if not face_locations:
        return {"visages_detectes": 0, "resultats": []}

    # face_recognition travaille en RGB, Silent-Face-Anti-Spoofing attend du BGR
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    encodings = face_recognition.face_encodings(image_rgb, known_face_locations=face_locations)

    known_ids = list(EMBEDDINGS_STORE.keys())
    known_encodings = [np.array(EMBEDDINGS_STORE[sid]) for sid in known_ids] if known_ids else []

    resultats = []
    for (top, right, bottom, left), encoding in zip(face_locations, encodings):
        # dlib renvoie (top, right, bottom, left) ; Silent-Face attend [left, top, width, height]
        bbox = [left, top, right - left, bottom - top]

        if not check_liveness(image_bgr, bbox):
            resultats.append({"vivant": False, "resultat": "spoof_detecte"})
            continue

        if not known_encodings:
            resultats.append({"vivant": True, "resultat": "inconnu", "raison": "aucune personne enrôlée"})
            continue

        distances = face_recognition.face_distance(known_encodings, encoding)
        best_index = int(np.argmin(distances))
        best_distance = float(distances[best_index])

        if best_distance <= MATCH_THRESHOLD:
            resultats.append({
                "vivant": True, "resultat": "reconnu",
                "subject_id": known_ids[best_index], "confiance": round(1 - best_distance, 3),
            })
        else:
            resultats.append({"vivant": True, "resultat": "inconnu", "distance_min": round(best_distance, 3)})

    return {"visages_detectes": len(face_locations), "resultats": resultats}