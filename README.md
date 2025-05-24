# 3DScanner Project

A modular, open-source 3D scanning system combining web-based control, ESP8266/ESP32 hardware, and phone camera integration. This project enables remote-controlled scanning, image capture, and 3D reconstruction, all managed from a browser interface.

## Repository Structure

```
FlaskApp/
    app.py
    config.py
    README.md
    modules/
        esp32_controller.py
        image_processor.py
        point_cloud.py
        storage.py
        utils.py
    templates/
        index.html
        phone.html
        processing.html
NodeMCU8266/
    sketch_may16a/
        README.md
        sketch_may16a.ino
```

- **[FlaskApp/](FlaskApp/README.md):** Python web application for scan management, hardware control, image processing, and 3D reconstruction. See [FlaskApp/README.md](FlaskApp/README.md) for setup, features, and usage.
- **[NodeMCU8266/sketch_may16a/](NodeMCU8266/sketch_may16a/README.md):** ESP8266 firmware for stepper motor and laser control via HTTP API. See [NodeMCU8266/sketch_may16a/README.md](NodeMCU8266/sketch_may16a/README.md) for wiring, endpoints, and deployment.

## Quick Start

1. **Flash the ESP8266**  
   - Upload the firmware in [`NodeMCU8266/sketch_may16a/sketch_may16a.ino`](NodeMCU8266/sketch_may16a/sketch_may16a.ino) to your NodeMCU8266 after editing WiFi credentials.
2. **Set up the FlaskApp**  
   - Follow [FlaskApp/README.md](FlaskApp/README.md) for Python dependencies and running the server.
3. **Connect your phone**  
   - Scan the QR code on the web dashboard or open `/phone` to use your phone as a wireless camera.
4. **Scan and Process**  
   - Use the web UI to start a scan, crop images, and reconstruct a 3D model.

## Integration

- The FlaskApp communicates with the ESP8266 firmware for hardware control and with the phone client for image capture.
- All scan data and results are managed and processed by the FlaskApp.

## More Information

- For detailed usage, configuration, and troubleshooting, see the respective READMEs:
  - [FlaskApp/README.md](FlaskApp/README.md)
  - [NodeMCU8266/sketch_may16a/README.md](NodeMCU8266/sketch_may16a/README.md)

---

**Contributions and issues are welcome!**