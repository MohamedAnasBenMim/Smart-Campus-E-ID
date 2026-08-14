import logging
import time

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.schemas import (
    EnrollResponse,
    RecognizeResponse,
    LoadEmbeddingsRequest,
    HealthResponse,
    TrackResponse,
)
from app.services import face_engine
from app.services import embedding_candidates
from app.services.track_manager import track_manager

logger = logging.getLogger(__name__)
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


# ============================================================
# PHASE 1 : TRACKING (+ diagnostic temporaire, voir tracker.py)
#
# Endpoint séparé de /recognize. Ne fait AUCUNE reconnaissance
# faciale — uniquement détection de personnes (MediaPipe) + tracking.
# ============================================================

@router.post("/track", response_model=TrackResponse)
async def track(
    image: UploadFile = File(...),
    camera_id: str = Form(...),
    frame_num: int | None = Form(None),  # NOUVEAU — uniquement pour le diagnostic
):
    # ---- CHRONOMÉTRAGE TEMPORAIRE — pour diagnostiquer la lenteur (~2s/frame) ----
    t0 = time.perf_counter()

    file_bytes = await image.read()
    image_bgr = face_engine.bytes_to_image(file_bytes)
    t1 = time.perf_counter()

    if image_bgr is None:
        raise HTTPException(status_code=422, detail="Image impossible à décoder")

    detections_brutes = face_engine.detect_persons(image_bgr)
    t2 = time.perf_counter()

    bboxes = [d["bbox"] for d in detections_brutes]
    confidences_reelles = [d["confidence"] for d in detections_brutes]

    tracker = track_manager.get_tracker(camera_id)
    tracks = tracker.update(bboxes, confidences_reelles=confidences_reelles, frame_num=frame_num)
    t3 = time.perf_counter()

    logger.info(
        f"[TIMING] frame={frame_num} | "
        f"decode={round((t1 - t0) * 1000)}ms | "
        f"detect_persons(MediaPipe)={round((t2 - t1) * 1000)}ms | "
        f"tracker.update(ByteTrack)={round((t3 - t2) * 1000)}ms | "
        f"TOTAL={round((t3 - t0) * 1000)}ms"
    )
    # ---- FIN chronométrage temporaire ----

    return {"camera_id": camera_id, "tracks": tracks}


# ============================================================
# AMÉLIORATION PROGRESSIVE — candidats d'embeddings
#
# IMPORTANT : /candidates/{subject_id}/valider doit être appelé
# explicitement (typiquement par un administrateur, après avoir
# consulté GET /candidates) — RIEN ne s'applique automatiquement.
# ============================================================

@router.get("/candidates")
async def lister_candidats():
    """Résumé des candidats en attente, par personne — à consulter
    AVANT de valider ou rejeter quoi que ce soit."""
    return embedding_candidates.lister_candidats()


@router.post("/candidates/{subject_id}/valider")
async def valider_candidats(subject_id: str):
    if subject_id not in face_engine.EMBEDDINGS_STORE:
        raise HTTPException(status_code=404, detail="Personne inconnue")

    nouveau_profil = embedding_candidates.valider_candidats(
        subject_id=subject_id,
        embedding_profil_actuel=face_engine.EMBEDDINGS_STORE[subject_id],
    )

    if nouveau_profil is None:
        raise HTTPException(status_code=404, detail="Aucun candidat en attente pour cette personne")

    face_engine.EMBEDDINGS_STORE[subject_id] = nouveau_profil
    return {"subject_id": subject_id, "statut": "profil mis à jour"}


@router.delete("/candidates/{subject_id}")
async def rejeter_candidats(subject_id: str):
    nombre = embedding_candidates.rejeter_candidats(subject_id)
    return {"subject_id": subject_id, "candidats_rejetes": nombre}