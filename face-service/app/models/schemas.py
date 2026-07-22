from typing import Optional

from pydantic import BaseModel


class EnrollResponse(BaseModel):
    subject_id: str
    embedding: list[float]


class FaceResult(BaseModel):
    """Résultat pour UN visage détecté sur l'image envoyée."""
    vivant: Optional[bool] = None
    resultat: Optional[str] = None
    subject_id: Optional[str] = None
    confiance: Optional[float] = None
    distance_min: Optional[float] = None
    raison: Optional[str] = None


class RecognizeResponse(BaseModel):
    """
    ⚠️ Changement de contrat par rapport à avant : la réponse contient
    maintenant une LISTE de résultats (un par visage détecté), plutôt
    qu'un seul résultat — nécessaire pour gérer plusieurs personnes
    présentes en même temps devant une caméra.
    """
    visages_detectes: int
    resultats: list[FaceResult]


class LoadEmbeddingsRequest(BaseModel):
    embeddings: dict[str, list[float]]


class HealthResponse(BaseModel):
    status: str
    personnes_en_cache: int