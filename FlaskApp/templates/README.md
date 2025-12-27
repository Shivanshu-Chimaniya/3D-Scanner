# FlaskApp — 3DScanner Web Backend

This is the Flask-based web application for the 3DScanner project. It provides the web UI (desktop and phone views), coordinates scans by talking to the ESP8266 firmware, receives images from the phone client, processes images to extract laser points, and produces a reconstructed 3D model (PLY).

---

## Contents
- `app.py` — Main application, routes and Socket.IO events.
- `config.py` — Configuration (HOST, PORT, ESP32_IP, TIME_DELAY, IMAGES_FOLDER, etc.).
- `modules/` — Core modules:
  - `esp32_controller.py` — HTTP calls to the NodeMCU/ESP32 (laser on/off, step motor, status)
  - `image_processor.py` — Image preprocessing, laser line extraction, cropping helpers
  - `point_cloud.py` — Conversion from 2D image points to 3D and saving PLY
  - `storage.py` — Scan folder management and utility helpers
  - `utils.py` — Misc helpers (e.g., QR code generation)
- `templates/` — UI templates (`index.html`, `phone.html`, `processing.html`).
- `scan_images/` — Automatically created storage for scans. Each scan directory contains `laser_on/`, `laser_off/`, `processed/`, `cropped/`.

---

## Features
- Web dashboard to manage and monitor scans (desktop UI).
- Phone client (mobile UI) to capture images during a scan (connect via QR code or `/phone`).
- Socket.IO communication for real-time control and capture requests.
- Endpoints to start/stop scans, control laser and stepper, upload images, crop scans, run processing, stream processing status, and download/view PLY results.

---

## Quick Start (development)
1. Create a virtual environment and activate it:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1  # Windows Powershell
```

2. Install dependencies (examples — adapt as needed):

```powershell
pip install flask flask-socketio eventlet opencv-python numpy
```

3. Configure `FlaskApp/config.py`:
- Set `ESP32_IP` to your NodeMCU/ESP8266 IP address (device must be accessible on the same network).
- Edit `HOST`, `PORT`, `DEBUG`, and `TIME_DELAY` to suit your environment.

4. Run the app:

```powershell
python app.py
```

The UI will be available at `http://<HOST>:<PORT>/` (by default `http://0.0.0.0:5000/`).

---

## Important Routes & APIs
(Short summary — for full device firmware endpoints, see `NodeMCU8266/sketch_may16a/README.md`)

- GET `/` — Desktop dashboard (shows scan list, QR code for phone client).
- GET `/phone` — Phone UI for capturing images.
- POST `/start-scan` — Start a full scan (server will call the ESP32 and request image capture via Socket.IO).
- POST `/stop-scan` — Stop an ongoing scan.
- POST `/laser-on` and `/laser-off` — Toggle laser via ESP32.
- POST `/step-motor` — Trigger single motor step on ESP32.
- POST `/upload-image` — Phone client uploads an image (form fields: `image`, `step`, `mode`).
- POST `/process_scan/<scan_id>` — Start image processing for a given scan (runs in a background thread).
- GET `/api/status/<scan_id>` — Server-Sent Events (SSE) stream for processing progress (used by UI during processing).
- GET `/download_processed/<scan_id>` — Download `reconstructed_model.ply` (if it exists).
- GET `/preview_first_image/<scan_id>` — Return the first `laser_on` image for previewing.
- GET `/get_scans` and GET `/delete_scan/<scan_id>` — Manage scan directories.

---

## Typical Scan Workflow
1. Ensure ESP8266 firmware is flashed and reachable (see `NodeMCU8266` README).
2. Start the Flask server.
3. Open the dashboard and scan the QR code with a phone or open `/phone`.
4. Press "Start scan" — the server will command the ESP to step & toggle laser and will request the phone to capture images (200 laser_on + 200 laser_off by default).
5. After capture, select a scan and run processing to generate a 3D PLY model.

---

## Processing Details
- Pairing: processing expects matching `laser_on` / `laser_off` image pairs with the same step index.
- Output: processed images and `reconstructed_model.ply` are placed in the scan's `processed/` directory.
- Cropping: you can crop a scan before processing via `POST /crop_scan/<scan_id>` with `crop_coords` (json: `x`, `y`, `width`, `height`). If a cropped set exists, processing will use cropped images.
- Streaming status: use `/api/status/<scan_id>` SSE to monitor progress programmatically.

---

## Development & Debugging Tips
- Check `config.py` and make sure the `IMAGES_FOLDER` points where you expect; scans are created under that folder.
- If images are not being saved, ensure the phone client is connected via Socket.IO and that `/upload-image` is being called with the correct form fields.
- Adjust `TIME_DELAY` in `config.py` if captures or motor steps need more time between them.
- Use the Web UI logs (Socket.IO `log_message` events) to get step-by-step messages while scanning.

---

## Contributing
Contributions are welcome. Please open issues for bugs or feature requests, and PRs for fixes or new features.

---

## See also
- NodeMCU firmware: `NodeMCU8266/sketch_may16a/README.md` (device endpoints and wiring) 🔧

---

© 2025 3DScanner Project — License: MIT (or add your project's license)
