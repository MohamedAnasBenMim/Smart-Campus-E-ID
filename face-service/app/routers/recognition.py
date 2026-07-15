from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.schemas import EnrollResponse, RecognizeResponse, LoadEmbeddingsRequest, HealthResponse
from app.services import face_engine

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok", "personnes_en_cache": len(face_engine.EMBEDDINGS_STORE)}


@router.post("/enroll", response_model=EnrollResponse)
async def enroll(subject_id: str = Form(...), images: list[UploadFile] = File(...)):
    images_bytes = [await f.read() for f in images]
    embedding = face_engine.compute_average_embedding(images_bytes)
    if embedding is None:
        raise HTTPException(status_code=422, detail="Aucun visage exploitable dans les photos fournies")
    face_engine.EMBEDDINGS_STORE[subject_id] = embedding
    return {"subject_id": subject_id, "embedding": embedding}


@router.post("/load-embeddings")
async def load_embeddings(payload: LoadEmbeddingsRequest):
    face_engine.EMBEDDINGS_STORE.clear()
    face_engine.EMBEDDINGS_STORE.update(payload.embeddings)
    return {"loaded": len(face_engine.EMBEDDINGS_STORE)}


@router.post("/recognize", response_model=RecognizeResponse)
async def recognize(image: UploadFile = File(...)):
    file_bytes = await image.read()
    return face_engine.recognize_face(file_bytes)