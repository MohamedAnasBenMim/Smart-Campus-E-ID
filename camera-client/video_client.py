"""
Client de test vidéo pour Smart Campus E-ID.

Objectif :
    Tester correctement le service de reconnaissance faciale ET,
    depuis la Phase 1, le service de tracking sur une vidéo de caméra
    de surveillance.

Exemples :

    # Mode reconnaissance (comportement historique, inchangé)
    python video_client.py video.mp4 --interval 1.0

    # NOUVEAU — Mode tracking (Phase 1)
    python video_client.py video.mp4 --mode track --camera-id CAM_01 --every-frame

    # Analyse toutes les 10 frames
    python video_client.py video.mp4 --every-n-frames 10

    # Sauvegarder les frames envoyées au serveur
    python video_client.py video.mp4 --every-n-frames 10 --save-frames

Installation :
    pip install opencv-python requests
"""

import argparse
import colorsys
import os
import time

import cv2
import requests


COULEURS = {
    "reconnu": (0, 200, 0),
    "inconnu": (0, 165, 255),
    "spoof_detecte": (0, 0, 255),
    "detection_incertaine": (128, 128, 128),
    "angle_trop_marque": (128, 128, 128),
}

COULEUR_DEFAUT = (255, 255, 0)


# ================================================================
# MODE RECOGNIZE — inchangé, toutes les fonctions ci-dessous sont
# identiques au fichier d'origine.
# ================================================================

def libelle_court(resultat: dict) -> str:
    resultat_type = resultat.get("resultat")

    if resultat_type == "reconnu":
        return (
            f"{resultat.get('subject_id')} "
            f"({resultat.get('confiance')})"
        )

    if resultat_type == "spoof_detecte":
        return "ALERTE spoofing"

    if resultat_type == "inconnu":
        similarity = resultat.get("similarite_max")
        if similarity is not None:
            return f"Inconnu ({similarity})"
        return "Inconnu"

    if resultat_type == "visage_trop_petit":
        return "Trop loin"

    if resultat_type == "angle_trop_marque":
        return "Angle défavorable"

    if resultat_type == "detection_incertaine":
        return "Détection incertaine"

    return str(resultat_type)


def dessiner_resultats(frame, result: dict):
    """
    Dessine les résultats sur LA frame qui vient d'être analysée.
    """

    n = result.get("visages_detectes", 0)

    if n == 0:
        cv2.putText(
            frame,
            "Aucun visage detecte",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
        return

    for r in result.get("resultats", []):

        bbox = r.get("bbox")

        if not bbox:
            continue

        x, y, w, h = bbox

        resultat_type = r.get("resultat")
        couleur = COULEURS.get(
            resultat_type,
            COULEUR_DEFAUT
        )

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            couleur,
            2,
        )

        texte = libelle_court(r)

        if r.get("avertissement"):
            texte += " !"

        (tw, th), _ = cv2.getTextSize(
            texte,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            2,
        )

        label_y1 = max(0, y - th - 8)
        label_y2 = max(0, y)

        cv2.rectangle(
            frame,
            (x, label_y1),
            (x + tw + 6, label_y2),
            couleur,
            -1,
        )

        cv2.putText(
            frame,
            texte,
            (x + 3, max(15, y - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 0),
            2,
        )


def envoyer_frame(
    frame,
    frame_num: int,
    fps: float,
    url: str,
    save_frames: bool,
    output_dir: str,
):
    """
    Envoie UNE frame précise au serveur (mode /recognize).

    Le résultat retourné correspond exactement à cette frame.
    """

    timestamp_s = frame_num / fps

    frame_path = None

    if save_frames:
        os.makedirs(output_dir, exist_ok=True)
        frame_path = os.path.join(output_dir, f"frame_{frame_num:06d}.jpg")
        cv2.imwrite(frame_path, frame)

    success, buffer = cv2.imencode(".jpg", frame)

    if not success:
        print(f"[Frame {frame_num}] Erreur encodage JPEG")
        return None

    start = time.perf_counter()

    try:
        response = requests.post(
            url,
            files={
                "image": (
                    f"frame_{frame_num}.jpg",
                    buffer.tobytes(),
                    "image/jpeg",
                )
            },
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()

    except requests.RequestException as e:
        print(f"[Frame {frame_num}] Erreur service IA : {e}")
        return None

    elapsed_ms = (time.perf_counter() - start) * 1000

    print(
        f"[Frame {frame_num:6d}] "
        f"[{timestamp_s:7.2f}s] "
        f"[{elapsed_ms:7.1f} ms] "
        f"visages={result.get('visages_detectes', 0)}"
    )

    for i, r in enumerate(result.get("resultats", []), start=1):
        bbox = r.get("bbox")
        face_width = bbox[2] if bbox else None
        print(
            f"    visage {i}: "
            f"{libelle_court(r)} "
            f"| largeur={face_width}px "
            f"| resultat={r.get('resultat')}"
        )

    result["_test"] = {
        "frame": frame_num,
        "timestamp_s": timestamp_s,
        "response_ms": elapsed_ms,
        "frame_path": frame_path,
    }

    return result


# ================================================================
# NOUVEAU — MODE TRACK (Phase 1)
# ================================================================

def couleur_pour_track(track_id) -> tuple:
    """
    Couleur STABLE et distincte pour un track_id donné — dérivée par
    un nombre d'or (golden ratio), pour que des track_id consécutifs
    (1, 2, 3...) reçoivent des couleurs bien différenciables à l'œil,
    plutôt que des teintes trop proches.

    Un track_id encore "tentative" (None) reçoit toujours le même gris
    neutre, pour bien le distinguer visuellement d'un track confirmé.
    """
    if track_id is None:
        return (128, 128, 128)

    teinte = (track_id * 0.618033988749895) % 1.0
    r, g, b = colorsys.hsv_to_rgb(teinte, 0.85, 0.95)
    return (int(b * 255), int(g * 255), int(r * 255))  # BGR pour OpenCV


def dessiner_tracks(frame, result: dict):
    """Dessine les tracks (mode /track) — équivalent de dessiner_resultats()
    pour le mode reconnaissance, mais sans aucune notion d'identité."""

    tracks = result.get("tracks", [])

    if not tracks:
        cv2.putText(
            frame,
            "Aucune personne suivie",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
        return

    for t in tracks:
        x, y, w, h = t["bbox"]
        track_id = t.get("track_id")
        couleur = couleur_pour_track(track_id)

        cv2.rectangle(frame, (x, y), (x + w, y + h), couleur, 2)

        if track_id is not None:
            texte = f"Track #{track_id}"
        else:
            texte = "..."  # tentative, pas encore confirme

        (tw, th), _ = cv2.getTextSize(texte, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        label_y1 = max(0, y - th - 8)

        cv2.rectangle(frame, (x, label_y1), (x + tw + 6, y), couleur, -1)
        cv2.putText(
            frame, texte, (x + 3, max(15, y - 5)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2,
        )


def envoyer_frame_track(
    frame,
    frame_num: int,
    fps: float,
    url: str,
    camera_id: str,
):
    """Envoie UNE frame au serveur, mode /track — équivalent de
    envoyer_frame() pour le mode reconnaissance."""

    timestamp_s = frame_num / fps

    success, buffer = cv2.imencode(".jpg", frame)
    if not success:
        print(f"[Frame {frame_num}] Erreur encodage JPEG")
        return None

    start = time.perf_counter()

    try:
        response = requests.post(
            url,
            files={"image": (f"frame_{frame_num}.jpg", buffer.tobytes(), "image/jpeg")},
            data={"camera_id": camera_id, "frame_num": frame_num},  # frame_num ajouté pour le diagnostic
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()

    except requests.RequestException as e:
        print(f"[Frame {frame_num}] Erreur service tracking : {e}")
        return None

    elapsed_ms = (time.perf_counter() - start) * 1000

    tracks = result.get("tracks", [])
    resume = " | ".join(
        f"#{t['track_id']}" if t["track_id"] is not None else "(tentative)"
        for t in tracks
    ) or "aucune"

    print(
        f"[{camera_id}] [Frame {frame_num:6d}] "
        f"[{timestamp_s:7.2f}s] [{elapsed_ms:6.1f} ms] "
        f"tracks: {resume}"
    )

    return result


# ================================================================
# Logique commune de sélection des frames — inchangée
# ================================================================

def doit_analyser_frame(
    frame_num: int,
    fps: float,
    mode: str,
    every_n_frames: int,
    interval: float,
    next_interval_time: float,
):
    """
    Détermine si la frame actuelle doit être envoyée.

    NB : ce "mode" est celui de l'ÉCHANTILLONNAGE (every_frame /
    every_n_frames / interval) — sans rapport avec le nouveau
    --mode {recognize,track}, qui détermine QUEL endpoint est appelé.
    """

    if mode == "every_frame":
        return True, next_interval_time

    if mode == "every_n_frames":
        if frame_num % every_n_frames == 0:
            return True, next_interval_time
        return False, next_interval_time

    current_video_time = frame_num / fps

    if current_video_time >= next_interval_time:
        next_interval_time += interval
        return True, next_interval_time

    return False, next_interval_time


def main():

    parser = argparse.ArgumentParser(
        description="Test du service Smart Campus E-ID sur une vidéo de surveillance."
    )

    parser.add_argument("video_path", help="Chemin de la vidéo")

    parser.add_argument(
        "--url",
        default=None,
        help=(
            "URL du service. Par défaut : http://localhost:8000/recognize "
            "ou http://localhost:8000/track selon --mode."
        ),
    )

    # NOUVEAU — quel service appeler (indépendant de l'échantillonnage ci-dessous)
    parser.add_argument(
        "--mode",
        choices=["recognize", "track"],
        default="recognize",
        help="recognize (comportement historique) ou track (Phase 1, nouveau)",
    )

    parser.add_argument(
        "--camera-id",
        default="CAM_01",
        help="Identifiant de la caméra — requis en pratique pour --mode track",
    )

    # Modes d'échantillonnage temporel — inchangés
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--every-frame", action="store_true", help="Analyse toutes les frames")
    group.add_argument("--every-n-frames", type=int, help="Analyse une frame toutes les N frames")
    group.add_argument(
        "--interval", type=float, default=1.0,
        help="Analyse une frame toutes les N secondes de la vidéo",
    )

    parser.add_argument("--no-display", action="store_true", help="Ne pas afficher la vidéo")
    parser.add_argument("--save-frames", action="store_true", help="Sauvegarder chaque frame envoyée (mode recognize uniquement)")
    parser.add_argument("--output-dir", default="test_frames", help="Dossier des frames sauvegardées")

    args = parser.parse_args()

    # URL par défaut, dépendante du mode si non précisée explicitement
    if args.url is None:
        args.url = (
            "http://localhost:8000/track"
            if args.mode == "track"
            else "http://localhost:8000/recognize"
        )

    if args.mode == "track" and args.every_n_frames is None and not args.every_frame:
        print(
            "ATTENTION : en mode track, un échantillonnage trop espacé "
            "(--interval) fait souvent ECHOUER la confirmation des tracks "
            "(déplacement trop grand entre deux frames analysées).\n"
            "Recommandé : --every-frame ou --every-n-frames 2-3.\n"
        )

    if args.every_frame:
        mode_echantillon = "every_frame"
    elif args.every_n_frames is not None:
        if args.every_n_frames <= 0:
            print("--every-n-frames doit être > 0")
            return
        mode_echantillon = "every_n_frames"
    else:
        if args.interval <= 0:
            print("--interval doit être > 0")
            return
        mode_echantillon = "interval"

    cap = cv2.VideoCapture(args.video_path)

    if not cap.isOpened():
        print(f"Impossible d'ouvrir la vidéo : {args.video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 30.0

    largeur = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    hauteur = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duree = total_frames / fps if total_frames > 0 else 0

    print()
    print("=" * 70)
    print("SMART CAMPUS E-ID — TEST VIDÉO")
    print("=" * 70)
    print(f"Vidéo       : {args.video_path}")
    print(f"Résolution  : {largeur}x{hauteur}")
    print(f"FPS         : {fps:.2f}")
    print(f"Frames      : {total_frames}")
    print(f"Durée       : {duree:.2f} secondes")
    print(f"Mode API    : {args.mode}" + (f" (camera_id={args.camera_id})" if args.mode == "track" else ""))
    print(f"Service     : {args.url}")
    print(f"Échantillon : {mode_echantillon}")
    print("=" * 70)
    print()

    frame_num = 0
    next_interval_time = 0.0
    analyzed_frames = 0
    results_history = []
    dernier_resultat = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_num += 1

        send, next_interval_time = doit_analyser_frame(
            frame_num=frame_num,
            fps=fps,
            mode=mode_echantillon,
            every_n_frames=(args.every_n_frames if args.every_n_frames else 1),
            interval=args.interval,
            next_interval_time=next_interval_time,
        )

        if send:
            analyzed_frames += 1

            if args.mode == "track":
                result = envoyer_frame_track(
                    frame=frame,
                    frame_num=frame_num,
                    fps=fps,
                    url=args.url,
                    camera_id=args.camera_id,
                )
            else:
                result = envoyer_frame(
                    frame=frame,
                    frame_num=frame_num,
                    fps=fps,
                    url=args.url,
                    save_frames=args.save_frames,
                    output_dir=args.output_dir,
                )

            if result is not None:
                results_history.append(result)
                dernier_resultat = result

        if not args.no_display:

            if dernier_resultat is not None:
                if args.mode == "track":
                    dessiner_tracks(frame, dernier_resultat)
                else:
                    dessiner_resultats(frame, dernier_resultat)

            texte = f"Frame {frame_num}/{total_frames} | {frame_num / fps:.2f}s"
            cv2.putText(frame, texte, (20, hauteur - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

            cv2.imshow("Smart Campus E-ID - Test video", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

    cap.release()
    if not args.no_display:
        cv2.destroyAllWindows()

    print()
    print("=" * 70)
    print("FIN DU TEST")
    print("=" * 70)
    print(f"Frames totales     : {frame_num}")
    print(f"Frames analysées   : {analyzed_frames}")

    if frame_num > 0:
        pourcentage = (analyzed_frames / frame_num) * 100
        print(f"Pourcentage analysé : {pourcentage:.2f}%")

    print(f"Résultats obtenus  : {len(results_history)}")

    if args.mode == "track" and results_history:
        # Nombre de track_id distincts CONFIRMÉS observés sur toute la vidéo
        tous_les_ids = {
            t["track_id"]
            for r in results_history
            for t in r.get("tracks", [])
            if t["track_id"] is not None
        }
        print(f"Track_id distincts confirmés : {len(tous_les_ids)} -> {sorted(tous_les_ids)}")

    if args.save_frames and args.mode == "recognize":
        print(f"Frames sauvegardées dans : {args.output_dir}")

    print("=" * 70)


if __name__ == "__main__":
    main()