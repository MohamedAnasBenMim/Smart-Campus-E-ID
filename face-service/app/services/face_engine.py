import logging
from typing import Optional

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from app.services import liveness

logger = logging.getLogger(__name__)

# Taille de la grille interne utilisée pour la détection — compromis vitesse/précision :
# - Plus grand (ex. 1024x1024) : meilleure détection des visages petits/éloignés, plus lent.
# - Plus petit (ex. 480x480) : plus rapide, rate les visages éloignés de la caméra.
DET_SIZE = (640, 640)

_face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
_face_app.prepare(ctx_id=-1, det_size=DET_SIZE)

# Détecteur de SILHOUETTE (pas de visage) — HOG, intégré nativement à OpenCV,
# licence Apache/BSD (aucune question de licence, contrairement à YOLO/AGPL).
# Sert à détecter une présence humaine même quand aucun visage n'est visible
# (personne de dos, visage masqué par un obstacle...).
_hog = cv2.HOGDescriptor()
_hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())


def detect_persons(image_bgr: np.ndarray) -> list:
    """
    Détecte les silhouettes humaines dans l'image, indépendamment de la
    visibilité du visage. Renvoie une liste de bbox [left, top, width, height].

    NB : HOG est une technique plus ancienne (2005) que les détecteurs de
    visage modernes utilisés ailleurs dans ce service — moins précise, mais
    suffisante pour la question qu'on lui pose ("y a-t-il quelqu'un ici ?"),
    pas pour identifier qui que ce soit.
    """
    rects, _weights = _hog.detectMultiScale(image_bgr, winStride=(8, 8), padding=(8, 8), scale=1.05)
    return [[int(x), int(y), int(w), int(h)] for (x, y, w, h) in rects]

EMBEDDINGS_STORE: dict[str, list[float]] = {}

MATCH_THRESHOLD = 0.4

DET_SCORE_THRESHOLD = 0.5

FRONTAL_RATIO_THRESHOLD = 0.35

# Largeur minimale (en pixels) en dessous de laquelle un visage est considéré
# "à risque" (fiabilité réduite, cf. étude citée : ~78% de précision à 15px
# contre ~98% à 45px). MODIFIÉ : le système TENTE quand même la reconnaissance
# en dessous de ce seuil (à la demande explicite du projet), mais ajoute un
# avertissement dans la réponse plutôt que de rester silencieux sur ce risque —
# pour que l'information "ce résultat est moins fiable" ne soit jamais perdue.
MIN_FACE_WIDTH_PX = 60


def estimate_frontal_ratio(kps: np.ndarray) -> float:
    eye_left, eye_right, nose = kps[0], kps[1], kps[2]
    dist_left = np.linalg.norm(nose - eye_left)
    dist_right = np.linalg.norm(nose - eye_right)
    if max(dist_left, dist_right) == 0:
        return 0.0
    return float(min(dist_left, dist_right) / max(dist_left, dist_right))


def bytes_to_image(file_bytes: bytes) -> np.ndarray:
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
    try:
        return liveness.is_real_face(image_bgr, bbox)
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de vivacité : {e}")
        return False


def recognize_face(file_bytes: bytes) -> dict:
    """
    Détecte, vérifie la vivacité et identifie TOUS les visages présents
    dans l'image.

    CHANGEMENT IMPORTANT : contrairement à la version précédente, un visage
    sous MIN_FACE_WIDTH_PX n'est PLUS automatiquement écarté — le système
    tente quand même la reconnaissance. Un champ "avertissement" est ajouté
    au résultat pour signaler que la fiabilité est réduite (rappel : études
    citées ~78% de précision à 15px contre ~98% à 45px). Cette information
    doit être prise en compte par le backend/dashboard avant de faire
    confiance aveuglément à ce résultat pour une décision d'accès.
    """
    image_bgr = bytes_to_image(file_bytes)
    faces = _face_app.get(image_bgr)
    personnes = detect_persons(image_bgr)  # tourne TOUJOURS, même si aucun visage détecté

    known_ids = list(EMBEDDINGS_STORE.keys())
    known_embeddings = [np.array(EMBEDDINGS_STORE[sid]) for sid in known_ids] if known_ids else []

    resultats = []
    for face in faces:
        x1, y1, x2, y2 = face.bbox.astype(int)
        bbox = [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]  # [left, top, width, height]

        if face.det_score < DET_SCORE_THRESHOLD:
            resultats.append({
                "bbox": bbox,
                "vivant": None, "resultat": "detection_incertaine",
                "raison": f"score de détection {round(float(face.det_score), 3)} sous le seuil {DET_SCORE_THRESHOLD}",
            })
            continue

        face_width_px = bbox[2]
        visage_petit = face_width_px < MIN_FACE_WIDTH_PX  # on continue quand même, juste on retient l'info

        frontal_ratio = estimate_frontal_ratio(face.kps)
        if frontal_ratio < FRONTAL_RATIO_THRESHOLD:
            resultats.append({
                "bbox": bbox,
                "vivant": None, "resultat": "angle_trop_marque",
                "raison": f"ratio de frontalité {round(frontal_ratio, 3)} sous le seuil {FRONTAL_RATIO_THRESHOLD}",
            })
            continue

        if not check_liveness(image_bgr, bbox):
            resultats.append({"bbox": bbox, "vivant": False, "resultat": "spoof_detecte"})
            continue

        if not known_embeddings:
            resultat = {"vivant": True, "resultat": "inconnu", "raison": "aucune personne enrôlée"}
        else:
            similarities = [cosine_similarity(emb, face.embedding) for emb in known_embeddings]
            best_index = int(np.argmax(similarities))
            best_similarity = similarities[best_index]

            if best_similarity >= MATCH_THRESHOLD:
                resultat = {
                    "vivant": True, "resultat": "reconnu",
                    "subject_id": known_ids[best_index], "confiance": round(best_similarity, 3),
                }
            else:
                resultat = {"vivant": True, "resultat": "inconnu", "similarite_max": round(best_similarity, 3)}

        resultat["bbox"] = bbox

        # On tente la reconnaissance même sur petit visage (demande explicite),
        # mais on garde toujours une trace du risque plutôt que de le taire.
        if visage_petit:
            resultat["avertissement"] = f"visage petit ({face_width_px}px, sous {MIN_FACE_WIDTH_PX}px) — fiabilité réduite, résultat à confirmer"

        resultats.append(resultat)

    # Signal clé : quelqu'un est physiquement présent (silhouette détectée),
    # mais aucun visage n'a pu être exploité pour confirmer qui — le cas
    # exact d'une personne de dos, ou dont le visage est masqué/hors cadre.
    # SANS ce signal, ce scénario ne générait auparavant AUCUNE alerte.
    #
    # CORRIGÉ : on compare au nombre de visages ayant réellement mené à une
    # identité (reconnu/inconnu/spoof_detecte) — PAS au nombre brut détecté
    # par InsightFace. Un visage détecté puis écarté en amont (detection_incertaine,
    # angle_trop_marque) n'a jamais permis de déterminer une identité, donc
    # ne doit pas compter comme "visage traité" dans cette comparaison —
    # sinon ce cas précis échappait au signal qu'il est censé déclencher.
    visages_avec_identite = sum(
        1 for r in resultats if r.get("resultat") in ("reconnu", "inconnu", "spoof_detecte")
    )
    presence_non_identifiee = len(personnes) > visages_avec_identite

    return {
        "visages_detectes": len(faces),
        "personnes_detectees": len(personnes),
        "presence_non_identifiee": presence_non_identifiee,
        "resultats": resultats,
    }