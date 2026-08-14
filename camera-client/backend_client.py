"""
Client caméra — teste le PIPELINE COMPLET, via le backend.

Différent de video_client.py (qui teste face-service ISOLÉMENT, en le
contournant) : ce script envoie les frames au BACKEND, avec
authentification — c'est le vrai chemin de bout en bout :
    authentification → décision d'accès → journalisation MongoDB → alertes

Exemple :
    python backend_client.py video.mp4 --zone-id 66f1a2b3c4d5e6f7a8b9c0d1

Pour trouver un zone-id valide : créez une zone dans le dashboard, puis
ouvrez MongoDB Compass -> smartcampus -> zones -> copiez le champ "_id"
du document.

Installation : pip install opencv-python requests
"""

import argparse
import time

import cv2
import requests


def se_connecter(base_url: str, email: str, mot_de_passe: str) -> str:
    """Authentifie et retourne le token JWT."""
    reponse = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "motDePasse": mot_de_passe},
        timeout=10,
    )
    reponse.raise_for_status()
    return reponse.json()["token"]


def envoyer_frame(frame, frame_num: int, fps: float, base_url: str, token: str, zone_id: str):
    timestamp_s = frame_num / fps

    success, buffer = cv2.imencode(".jpg", frame)
    if not success:
        print(f"[Frame {frame_num}] Erreur encodage JPEG")
        return None

    start = time.perf_counter()

    try:
        reponse = requests.post(
            f"{base_url}/api/access-events",
            files={"image": (f"frame_{frame_num}.jpg", buffer.tobytes(), "image/jpeg")},
            data={"zoneId": zone_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        reponse.raise_for_status()
        decisions = reponse.json()

    except requests.RequestException as e:
        print(f"[Frame {frame_num}] Erreur backend : {e}")
        return None

    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"[Frame {frame_num:6d}] [{timestamp_s:6.2f}s] [{elapsed_ms:7.1f} ms] — {len(decisions)} décision(s)")
    for d in decisions:
        nom = d.get("nom") or "Inconnu"
        print(f"    {nom} -> {d.get('resultat')} ({d.get('raison')})")

    return decisions


def main():
    parser = argparse.ArgumentParser(description="Test du pipeline complet, via le backend.")
    parser.add_argument("video_path")
    parser.add_argument("--base-url", default="http://localhost:8080", help="URL du backend")
    parser.add_argument("--email", default="admin@smartcampus.local")
    parser.add_argument("--password", default="ChangeMoi123!")
    parser.add_argument("--zone-id", required=True, help="ID MongoDB de la zone (voir Compass ou le dashboard)")
    parser.add_argument(
        "--every-n-frames", type=int, default=25,
        help="Analyse une frame toutes les N (défaut 25 = environ 1x/seconde à 25fps)",
    )
    args = parser.parse_args()

    print("Connexion au backend...")
    try:
        token = se_connecter(args.base_url, args.email, args.password)
    except requests.RequestException as e:
        print(f"Échec de la connexion : {e}")
        print("Vérifiez que le backend tourne bien, et que l'email/mot de passe sont corrects.")
        return
    print("Connecté avec succès.\n")

    cap = cv2.VideoCapture(args.video_path)
    if not cap.isOpened():
        print(f"Impossible d'ouvrir la vidéo : {args.video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_num = 0
    frames_envoyees = 0

    print("=" * 70)
    print("SMART CAMPUS E-ID — TEST DU PIPELINE COMPLET (via le backend)")
    print("=" * 70)
    print(f"Zone ciblée : {args.zone_id}")
    print(f"Backend     : {args.base_url}")
    print("=" * 70)
    print()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_num += 1

        if frame_num % args.every_n_frames == 0:
            frames_envoyees += 1
            envoyer_frame(frame, frame_num, fps, args.base_url, token, args.zone_id)

    cap.release()

    print()
    print("=" * 70)
    print(f"Terminé — {frames_envoyees} frame(s) envoyée(s) au backend")
    print("Consultez le dashboard (Alertes / Historique de présence) pour voir les résultats.")
    print("=" * 70)


if __name__ == "__main__":
    main()