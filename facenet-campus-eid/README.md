# FaceNet Campus E-ID Prototype

Local proof-of-concept face recognition for a Smart Campus E-ID system. The app enrolls users from webcam samples, detects and aligns faces with MTCNN, generates FaceNet embeddings with `InceptionResnetV1(pretrained="vggface2")`, stores local NPZ/JSON artifacts, and recognizes enrolled users from a webcam.

This is not a web app and does not run a database server.

## Architecture

- `app/face_detector.py`: MTCNN detection, OpenCV BGR to RGB conversion, face alignment.
- `app/quality_service.py`: face-count, confidence, size, blur, brightness, and border checks.
- `app/embedding_service.py`: FaceNet inference, CPU/CUDA selection, L2 normalization.
- `app/recognition_service.py`: Euclidean nearest-neighbor matching and simple temporal stabilization.
- `app/storage_service.py`: local metadata and embedding storage.
- `app/event_logger.py`: JSON Lines access events with cooldowns.
- `app/liveness_service.py`: future anti-spoofing boundary, currently `not_implemented`.

Face detection finds and aligns face crops. Face recognition compares embeddings to enrolled identities. Liveness checks whether a presented face is real; it is intentionally only a placeholder here. Authorization is a separate access-policy decision and is not mixed into identity matching.

FaceNet maps each aligned face image to a 512-dimensional embedding. Images of the same person should land closer together in this embedding space than images of different people, so this prototype recognizes a user by finding the enrolled embedding with the smallest Euclidean distance.

## Setup On Ubuntu

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

In VS Code, run `Python: Select Interpreter` and choose `.venv/bin/python` from this folder.

If CUDA-enabled PyTorch is needed, install the PyTorch build recommended for your driver from the official PyTorch instructions, then install the remaining requirements.

## Usage

Smoke-test model loading:

```bash
python scripts/test_model.py
```

Enroll a user:

```bash
python scripts/enroll_user.py \
  --user-id STU001 \
  --name "Mohamed Anas" \
  --role student
```

Enroll a user from existing image files:

```bash
python scripts/enroll_from_images.py \
  --user-id TEA001 \
  --name "Teacher Name" \
  --role teacher \
  --images enrollment_images/teacher
```

Run webcam recognition:

```bash
python scripts/recognize_webcam.py
```

Run face detection on recorded classroom videos:

```bash
python scripts/recognize_video.py --source videos --detect-only --min-face-size 40
```

Run full recognition on recorded classroom videos and save annotated MP4 files:

```bash
python scripts/recognize_video.py \
  --source videos \
  --output outputs \
  --min-face-size 40
```

Run recognition on still test images and save annotated images:

```bash
python scripts/recognize_images.py \
  --source test_images/teacher \
  --output outputs/image_tests \
  --min-face-size 40 \
  --threshold 1.05
```

Rebuild embeddings from saved enrollment images:

```bash
python scripts/rebuild_embeddings.py
```

## Enrollment Notes

Enrollment captures 10 valid samples by default. Press `SPACE` to capture only when the on-screen quality status is ready. Press `Q` to quit. The app asks for pose and expression variation, including straight, slight left, slight right, upward, downward, neutral expression, and slight smile.

Image-based enrollment accepts one or more image files or folders. Each accepted image must contain exactly one confident face. Use `--overwrite` to replace an existing user ID. If the images are from classroom videos and the face is small, try `--min-face-size 40`; use `--allow-low-quality` only for proof-of-concept testing.

Duplicate user IDs are blocked unless `--overwrite` is passed.

## Recognition Notes

Recognition supports multiple faces per frame. Unknown live faces are logged as `unknown_person`, not spoof attempts. The displayed score is Euclidean `distance`, not a confidence percentage.

Each enrollment NPZ stores both the averaged embedding and the individual sample embeddings. Recognition compares a live face against the closest stored sample for each user, which is more tolerant of pose, lighting, glasses, and other normal variation than comparing only against one averaged vector. Older NPZ files that contain only an averaged embedding still load, but re-enrolling or running `python scripts/rebuild_embeddings.py` upgrades them to multi-sample matching.

For classroom videos, start with `--detect-only` to confirm that faces are visible enough. If faces are far from the camera, lower `--min-face-size` to `40` or `30`. Full recognition can identify only people who were enrolled previously; everyone else should remain `Unknown`.

`RECOGNITION_DISTANCE_THRESHOLD` starts at a reasonable prototype value, but it must be calibrated with local validation data before any real access-control use.

## Folder Structure

```text
facenet-campus-eid/
├── app/
├── data/
│   ├── enrolled_faces/
│   ├── embeddings/
│   └── events/
├── scripts/
├── tests/
├── requirements.txt
├── .gitignore
├── README.md
└── main.py
```

Enrollment images are saved under `data/enrolled_faces/<user_id>/`. Embeddings are saved as compressed NPZ files under `data/embeddings/`, with metadata in adjacent JSON files. Events are appended to `data/events/access_events.jsonl`.

## CPU And CUDA

The app automatically uses CUDA when `torch.cuda.is_available()` is true; otherwise it runs on CPU. CPU works for the prototype but may feel slow on some machines.

## Webcam Troubleshooting

- Confirm the camera works in another app.
- Try `--camera-index 1` if the default camera is not the intended device.
- On Linux, verify the user can access `/dev/video*`.
- Close other apps that may already own the webcam.

## Privacy Warning

Face images and embeddings are biometric data. Keep the `data/` folder protected, do not commit real user data, and collect consent before enrollment. This prototype stores local files only and does not implement retention, encryption, or access-policy controls.

## Future Anti-Spoofing

`LivenessService` is the reserved integration point. The intended final pipeline is detection, quality verification, liveness, FaceNet recognition, then separate authorization. Do not treat unknown people as spoof attempts.

## Checks

```bash
python -m compileall app scripts
pytest
```
