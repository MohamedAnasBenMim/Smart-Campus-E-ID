import cv2
import numpy as np


class FaceQuality:
    """
    Évalue la qualité d'un visage détecté.

    Le score global est compris entre 0 et 1.

    Plus il est proche de 1,
    meilleure est la qualité du visage.
    """

    @staticmethod
    def blur_score(face_crop: np.ndarray):
        """
        Mesure la netteté du visage avec la variance du Laplacien.
        Retourne :
            variance, score_normalisé
        """

        if face_crop.size == 0:
            return 0.0, 0.0

        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)

        variance = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Normalisation
        score = min(variance / 300.0, 1.0)

        return float(variance), float(score)

    @staticmethod
    def size_score(face_width: int):

        if face_width >= 150:
            return 1.0

        return max(face_width / 150.0, 0.0)

    @staticmethod
    def frontal_score(frontal_ratio):

        return min(max(frontal_ratio, 0.0), 1.0)

    @staticmethod
    def detection_score(det_score):

        return min(max(det_score, 0.0), 1.0)

    @staticmethod
    def compute(
        face_crop,
        face_width,
        frontal_ratio,
        det_score
    ):

        blur_value, blur = FaceQuality.blur_score(face_crop)

        size = FaceQuality.size_score(face_width)

        frontal = FaceQuality.frontal_score(frontal_ratio)

        detection = FaceQuality.detection_score(det_score)

        quality = (
            0.40 * size +
            0.30 * blur +
            0.20 * detection +
            0.10 * frontal
        )

        return {
            "quality": round(quality, 3),
            "blur_value": round(blur_value, 2),
            "blur_score": round(blur, 3),
            "size_score": round(size, 3),
            "frontal_score": round(frontal, 3),
            "detection_score": round(detection, 3),
        }