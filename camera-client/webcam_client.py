import time
import cv2
import requests

RECOGNIZE_URL = "http://localhost:8000/recognize"
SEND_INTERVAL_SECONDS = 1.0  


def format_label(result: dict) -> str:
    """Traduit la réponse JSON du service en texte affichable à l'écran."""
    if not result.get("visage_detecte"):
        return "Aucun visage détecté"
    if not result.get("vivant", True):
        return "ALERTE : tentative de spoofing détectée"
    if result.get("resultat") == "reconnu":
        return f"Reconnu : {result['subject_id']} (confiance {result['confiance']})"
    if result.get("resultat") == "inconnu":
        return "Inconnu"
    return str(result)


def main():
    cap = cv2.VideoCapture(0)  # 0 = webcam par défaut
    if not cap.isOpened():
        print("Impossible d'ouvrir la webcam. Vérifiez qu'aucune autre application ne l'utilise.")
        return

    last_sent = 0.0
    last_label = "En attente de la première capture..."

    print("Webcam ouverte. Appuyez sur 'q' dans la fenêtre vidéo pour quitter.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Erreur de lecture webcam, arrêt.")
            break

        now = time.time()
        if now - last_sent >= SEND_INTERVAL_SECONDS:
            last_sent = now
            _, buffer = cv2.imencode(".jpg", frame)
            try:
                response = requests.post(
                    RECOGNIZE_URL,
                    files={"image": ("frame.jpg", buffer.tobytes(), "image/jpeg")},
                    timeout=3,
                )
                response.raise_for_status()
                last_label = format_label(response.json())
            except requests.RequestException as e:
                last_label = f"Erreur service IA (est-il bien lancé ?) : {e}"

        # Affiche le résultat directement sur l'image vidéo, en haut à gauche
        cv2.putText(
            frame, last_label, (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2,
        )
        cv2.imshow("Smart Campus E-ID - Test temps reel", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
