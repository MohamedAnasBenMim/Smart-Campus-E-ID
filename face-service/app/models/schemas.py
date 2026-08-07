from typing import Optional

from pydantic import BaseModel


class EnrollResponse(BaseModel):
    subject_id: str
    embedding: list[float]


class FaceResult(BaseModel):
    """Résultat pour UN visage détecté sur l'image envoyée."""
    bbox: Optional[list[int]] = None  # [left, top, width, height] en pixels
    vivant: Optional[bool] = None
    resultat: Optional[str] = None
    subject_id: Optional[str] = None
    confiance: Optional[float] = None
    similarite_max: Optional[float] = None
    raison: Optional[str] = None
    avertissement: Optional[str] = None


class RecognizeResponse(BaseModel):
    visages_detectes: int
    personnes_detectees: int
    presence_non_identifiee: bool
    resultats: list[FaceResult]


class LoadEmbeddingsRequest(BaseModel):
    embeddings: dict[str, list[float]]


class HealthResponse(BaseModel):
    status: str
    personnes_en_cache: int