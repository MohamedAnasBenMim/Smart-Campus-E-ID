"""
Intégration de Silent-Face-Anti-Spoofing (MiniFASNet) — BF-06.
Licence Apache 2.0 (minivision-ai) — utilisation commerciale autorisée.

Version adaptée pour le multi-visages : leur fonction native get_bbox()
ne détecte qu'UN SEUL visage par image (pensée pour un usage type
smartphone/porte, une personne à la fois). Pour votre cas (plusieurs
élèves pouvant passer ensemble devant une caméra), on lui fournit
directement la zone de CHAQUE visage détecté en amont par dlib,
et on réutilise seulement leurs fonctions de découpage (CropImage)
et de prédiction (AntiSpoofPredict.predict), pas leur détecteur.
"""

import logging
import os
import sys

import numpy as np

logger = logging.getLogger(__name__)

SILENT_FACE_REPO_PATH = "/opt/silent_face"
MODEL_DIR = os.path.join(SILENT_FACE_REPO_PATH, "resources/anti_spoof_models")

sys.path.insert(0, SILENT_FACE_REPO_PATH)

from src.anti_spoof_predict import AntiSpoofPredict  # noqa: E402
from src.generate_patches import CropImage  # noqa: E402
from src.utility import parse_model_name  # noqa: E402

# ATTENTION : leur classe charge le détecteur de visage via un chemin
# RELATIF ("./resources/detection_model/..."), qui ne fonctionne que si
# on est positionné dans leur dossier au moment du chargement. On se
# déplace donc temporairement, puis on revient à notre dossier normal.
_cwd_before = os.getcwd()
os.chdir(SILENT_FACE_REPO_PATH)
_model_test = AntiSpoofPredict(device_id=0)
os.chdir(_cwd_before)

_image_cropper = CropImage()


def is_real_face(image_bgr: np.ndarray, bbox: list) -> bool:
    """
    Vérifie la vivacité d'UN visage précis, dont la zone (bbox) est fournie
    par l'appelant (détectée en amont par dlib), plutôt que par leur
    détecteur interne — nécessaire pour traiter plusieurs visages sur
    la même image.

    bbox attendu au format [left, top, width, height].

    ⚠️ POINT D'INCERTITUDE ASSUMÉ : ce format est déduit de l'usage de
    bbox dans leur test.py officiel (où il provient de get_bbox()), mais
    je n'ai pas pu vérifier ligne par ligne le code interne de
    CropImage.crop() pour confirmer ce format à 100%. Si les résultats
    semblent incohérents (toujours "spoof" ou toujours "vivant" peu
    importe l'image testée), c'est le premier point à vérifier ensemble —
    ça se corrigerait facilement en ajustant l'ordre des 4 valeurs.

    Convention du dépôt officiel pour le résultat :
    label == 1  →  vrai visage
    label == 0 ou 2  →  tentative de spoofing
    """
    prediction = np.zeros((1, 3))

    for model_name in os.listdir(MODEL_DIR):
        h_input, w_input, model_type, scale = parse_model_name(model_name)
        param = {
            "org_img": image_bgr,
            "bbox": bbox,
            "scale": scale,
            "out_w": w_input,
            "out_h": h_input,
            "crop": True,
        }
        if scale is None:
            param["crop"] = False
        img = _image_cropper.crop(**param)
        prediction += _model_test.predict(img, os.path.join(MODEL_DIR, model_name))

    label = int(np.argmax(prediction))
    return label == 1