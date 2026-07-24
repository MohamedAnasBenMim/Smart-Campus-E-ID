
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


_cwd_before = os.getcwd()
os.chdir(SILENT_FACE_REPO_PATH)
_model_test = AntiSpoofPredict(device_id=0)
os.chdir(_cwd_before)

_image_cropper = CropImage()


def is_real_face(image_bgr: np.ndarray, bbox: list) -> bool:

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