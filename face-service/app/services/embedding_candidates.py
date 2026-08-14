"""
Candidats d'embeddings — amélioration progressive et CONTRÔLÉE de la
reconnaissance faciale.

PRINCIPE CENTRAL, à ne jamais enfreindre :
Un embedding candidat n'est JAMAIS intégré automatiquement au profil
actif d'une personne. Il est stocké à part, en attente d'une
validation EXPLICITE (typiquement humaine, via l'endpoint dédié) —
ça évite la contamination progressive d'un profil par une
reconnaissance ponctuellement erronée (le risque qu'on avait identifié
dès le début : fausse reconnaissance → embedding contaminé →
davantage de fausses reconnaissances).
"""

import logging
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Stockage en mémoire, même logique que EMBEDDINGS_STORE (face_engine.py)
# — un dict simple, vidé au redémarrage. Suffisant pour cette phase.
CANDIDATES_STORE: dict[str, list[dict]] = {}

# Seuils DISTINCTS et plus stricts que ceux de la reconnaissance elle-même
# (rappel : le seuil de correspondance simple, MATCH_THRESHOLD, est 0.4 —
# ici on veut une marge de sécurité large avant de nourrir un profil).
CANDIDATE_CONFIDENCE_THRESHOLD = 0.6
CANDIDATE_COHERENCE_THRESHOLD = 0.55  # similarité minimale avec le profil déjà enrôlé


def _similarite_cosinus(a, b) -> float:
    a_np, b_np = np.array(a), np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))


def evaluer_candidat(
    subject_id: str,
    embedding: list,
    embedding_profil_actuel: list,
    confiance: float,
    face_size: int,
    vivant: bool,
) -> Optional[dict]:
    """
    Vérifie tous les critères ; enregistre un candidat SEULEMENT s'ils
    sont tous respectés. Ne modifie jamais le profil actif directement.

    Retourne le candidat créé, ou None si rejeté (raison journalisée
    dans les deux cas, pour pouvoir suivre le comportement réel).
    """

    if not vivant:
        logger.info(f"[CANDIDAT] {subject_id} rejeté : liveness négatif")
        return None

    if confiance < CANDIDATE_CONFIDENCE_THRESHOLD:
        logger.info(
            f"[CANDIDAT] {subject_id} rejeté : confiance {confiance:.3f} "
            f"< seuil {CANDIDATE_CONFIDENCE_THRESHOLD}"
        )
        return None

    if face_size < 60:
        logger.info(f"[CANDIDAT] {subject_id} rejeté : visage trop petit ({face_size}px)")
        return None

    similarite = _similarite_cosinus(embedding, embedding_profil_actuel)
    if similarite < CANDIDATE_COHERENCE_THRESHOLD:
        logger.info(
            f"[CANDIDAT] {subject_id} rejeté : incohérent avec le profil actuel "
            f"(similarité {similarite:.3f} < {CANDIDATE_COHERENCE_THRESHOLD}) — "
            f"probable erreur de reconnaissance, volontairement pas intégré"
        )
        return None

    candidat = {
        "subject_id": subject_id,
        "embedding": embedding,
        "confiance_reconnaissance": round(confiance, 3),
        "similarite_avec_profil": round(similarite, 3),
        "face_size": face_size,
        "timestamp": time.time(),
    }

    CANDIDATES_STORE.setdefault(subject_id, []).append(candidat)
    logger.info(
        f"[CANDIDAT] {subject_id} ACCEPTÉ (confiance={confiance:.3f}, similarite={similarite:.3f}) "
        f"— {len(CANDIDATES_STORE[subject_id])} candidat(s) en attente de validation"
    )
    return candidat


def lister_candidats() -> dict:
    """Résumé par personne — pour inspection AVANT toute validation."""
    resume = {}
    for subject_id, candidats in CANDIDATES_STORE.items():
        if not candidats:
            continue
        resume[subject_id] = {
            "nombre_candidats": len(candidats),
            "similarite_moyenne": round(
                sum(c["similarite_avec_profil"] for c in candidats) / len(candidats), 3
            ),
            "confiance_moyenne": round(
                sum(c["confiance_reconnaissance"] for c in candidats) / len(candidats), 3
            ),
        }
    return resume


def valider_candidats(subject_id: str, embedding_profil_actuel: list) -> Optional[list]:
    """
    Agrège tous les candidats en attente pour cette personne avec le
    profil actuel (moyenne), puis VIDE la liste.

    Ne fait RIEN automatiquement — appelé explicitement via l'endpoint
    dédié, après inspection humaine de lister_candidats().
    """
    candidats = CANDIDATES_STORE.get(subject_id, [])
    if not candidats:
        return None

    tous_les_embeddings = [embedding_profil_actuel] + [c["embedding"] for c in candidats]
    nouveau_profil = np.mean(np.array(tous_les_embeddings), axis=0).tolist()

    logger.info(f"[CANDIDAT] {subject_id} : {len(candidats)} candidat(s) agrégés au profil, liste vidée")
    CANDIDATES_STORE[subject_id] = []

    return nouveau_profil


def rejeter_candidats(subject_id: str) -> int:
    """Vide les candidats en attente SANS les appliquer."""
    nombre = len(CANDIDATES_STORE.get(subject_id, []))
    CANDIDATES_STORE[subject_id] = []
    logger.info(f"[CANDIDAT] {subject_id} : {nombre} candidat(s) rejetés manuellement")
    return nombre