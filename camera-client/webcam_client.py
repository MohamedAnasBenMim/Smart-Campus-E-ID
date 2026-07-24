

import time
import cv2
import requests

RECOGNIZE_URL = "http://localhost:8000/recognize"
SEND_INTERVAL_SECONDS = 1.0


def format_lines(result: dict) -> list[str]:
    """Une ligne de texte par visage détecté, plutôt qu'une seule ligne globale."""
    n = result.get("visages_detectes", 0)
    if n == 0:
        return ["Aucun visage détecté"]

    lines = []
    for i, r in enumerate(result.get("resultats", []), start=1):
        if not r.get("vivant", True):
            lines.append(f"Visage {i} : ALERTE spoofing")
        elif r.get("resultat") == "reconnu":
            lines.append(f"Visage {i} : {r['subject_id']} ({r['confiance']})")
        elif r.get("resultat") == "inconnu":
            lines.append(f"Visage {i} : Inconnu")
        else:
            lines.append(f"Visage {i} : {r}")
    return lines


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Impossible d'ouvrir la webcam.")
        return

    last_sent = 0.0
    last_lines = ["En attente de la première capture..."]

    print("Webcam ouverte. Appuyez sur 'q' pour quitter.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        now = time.time()
        if now - last_sent >= SEND_INTERVAL_SECONDS:
            last_sent = now
            _, buffer = cv2.imencode(".jpg", frame)
            try:
                response = requests.post(
                    RECOGNIZE_URL,
                    files={"image": ("frame.jpg", buffer.tobytes(), "image/jpeg")},
                    timeout=5,
                )
                response.raise_for_status()
                last_lines = format_lines(response.json())
            except requests.RequestException as e:
                last_lines = [f"Erreur service IA : {e}"]

        # Une ligne de texte par visage, empilées verticalement
        for idx, line in enumerate(last_lines):
            y = 40 + idx * 35
            cv2.putText(frame, line, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Smart Campus E-ID - Test temps reel", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()