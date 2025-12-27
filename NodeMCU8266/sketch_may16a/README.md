# NodeMCU8266 Stepper & Laser Controller

This firmware runs on an ESP8266 (NodeMCU) board and provides HTTP endpoints to control a stepper motor and a laser module, as part of a 3D scanner system. It is designed to work with the FlaskApp in the parent directory.

## Features

- WiFi connection (edit SSID and password in the source)
- HTTP API for:
  - Laser ON/OFF
  - Stepper motor single step or 360° rotation (200 steps)
  - Status check
- PWM LED indicator for status feedback

## Pin Assignments

| Function      | Pin      |
|---------------|----------|
| Stepper STEP  | D6       |
| Stepper DIR   | D7       |
| Stepper EN    | D0       |
| Laser         | D3       |
| Status LED    | GPIO4    |

## HTTP Endpoints

- `/esp32/status` &mdash; Returns "OK" if running
- `/esp32/laser-on` &mdash; Turns laser ON
- `/esp32/laser-off` &mdash; Turns laser OFF
- `/esp32/step` &mdash; Single step pulse
- `/esp32/step360` &mdash; 200 steps (full rotation for 1.8°/step motors)

## Usage

1. Edit WiFi credentials in `sketch_may16a.ino`.
2. Upload to your NodeMCU8266 board.
3. Connect hardware as per pin assignments.
4. On boot, the device connects to WiFi and starts the HTTP server.
5. Use the FlaskApp or direct HTTP requests to control the hardware.

## Integration

This firmware is intended to be used with the FlaskApp for a complete 3D scanning workflow.

---
