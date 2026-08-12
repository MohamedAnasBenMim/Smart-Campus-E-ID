FROM python:3.11-slim

# libgl1/libglib2.0-0 : déjà nécessaires pour OpenCV (InsightFace)
# git : pour cloner Silent-Face-Anti-Spoofing pendant le build
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 --retries 5 -r requirements.txt

# InsightFace installe parfois opencv-python en plus d'opencv-python-headless
# en dépendance transitive — les deux se marchent dessus et cassent certains
# sous-modules (dont cv2.dnn, nécessaire à Silent-Face-Anti-Spoofing).
# On force une réinstallation propre, ET on fige une version stable connue
# (plutôt que la toute dernière 5.x, potentiellement incompatible avec le
# vieux format Caffe utilisé par Silent-Face-Anti-Spoofing).
RUN pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless 2>/dev/null; \
    pip install --no-cache-dir "opencv-python-headless==4.10.0.84"

# PyTorch CPU uniquement, nécessaire pour Silent-Face-Anti-Spoofing
RUN pip install --no-cache-dir --default-timeout=120 --retries 5 torch --index-url https://download.pytorch.org/whl/cpu

# Télécharge le modèle buffalo_l pendant le build (pas à chaque redémarrage)
RUN python -c "from insightface.app import FaceAnalysis; FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']).prepare(ctx_id=-1)"

# Clone du dépôt officiel Silent-Face-Anti-Spoofing (Apache 2.0)
RUN git clone --depth 1 https://github.com/minivision-ai/Silent-Face-Anti-Spoofing.git /opt/silent_face

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]