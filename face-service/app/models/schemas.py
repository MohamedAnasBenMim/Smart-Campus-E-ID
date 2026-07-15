from pydantic import BaseModel
from typing import Optional, Dict, List


class EnrollResponse(BaseModel):
    subject_id: str
    embedding: List[float]


class RecognizeResponse(BaseModel):
    visage_detecte: bool
    vivant: Optional[bool] = None
    resultat: Optional[str] = None
    subject_id: Optional[str] = None
    confiance: Optional[float] = None
    distance_min: Optional[float] = None
    raison: Optional[str] = None


class LoadEmbeddingsRequest(BaseModel):
    embeddings: Dict[str, List[float]]


class HealthResponse(BaseModel):
    status: str
    personnes_en_cache: int