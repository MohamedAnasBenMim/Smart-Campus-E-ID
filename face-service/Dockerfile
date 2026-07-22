FROM python:3.11-slim

# build-essential/cmake/etc. : pour compiler dlib (comme avant)
# git : pour cloner le dépôt Silent-Face-Anti-Spoofing pendant le build
# libgl1/libglib2.0-0 : dépendances système d'OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake libopenblas-dev liblapack-dev libx11-dev \
    git libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# PyTorch en version CPU uniquement — beaucoup plus léger que la version
# par défaut (qui inclut le support GPU/CUDA, inutile dans notre conteneur).
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Clone du dépôt officiel (Apache 2.0) — on réutilise leur code tel quel
# (voir app/services/liveness.py) plutôt que de le réimplémenter nous-mêmes.
RUN git clone --depth 1 https://github.com/minivision-ai/Silent-Face-Anti-Spoofing.git /opt/silent_face

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]