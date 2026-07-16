FROM python:3.11-slim

# InsightFace/onnxruntime n'ont plus besoin de compiler du C++ comme dlib
# (vrai depuis InsightFace 1.0) — juste 2 librairies système pour OpenCV.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Télécharge le modèle buffalo_l PENDANT le build, pour qu'il soit intégré
# à l'image Docker — sinon il serait retéléchargé (~326 Mo) à chaque
# redémarrage du conteneur, ce qui serait lent et gênant hors ligne.
RUN python -c "from insightface.app import FaceAnalysis; FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']).prepare(ctx_id=-1)"

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]