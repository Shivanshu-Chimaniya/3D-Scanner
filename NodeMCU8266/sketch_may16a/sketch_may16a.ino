#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>

// WiFi credentials
const char *ssid = "ssid_here";
const char *password = "password_here";

// Pin Definitions
#define LED_GPIO_NUM 4
#define STEP_PIN D6
#define DIRE_PIN D7
#define EN_PIN D0
#define LASER_PIN D3

// Delay between step HIGH and LOW
int STEP_DELAY = 500;

ESP8266WebServer server(80);

// Set PWM intensity (0–255)
void set_led_intensity(int intensity)
{
  intensity = constrain(intensity, 0, 255);
  analogWrite(LED_GPIO_NUM, intensity);
}

// Initialize GPIOs
void init_control_pins()
{
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIRE_PIN, OUTPUT);
  pinMode(LASER_PIN, OUTPUT);
  pinMode(EN_PIN, OUTPUT);
  pinMode(LED_GPIO_NUM, OUTPUT);

  digitalWrite(EN_PIN, HIGH); // Disable motor driver initially
  digitalWrite(STEP_PIN, LOW);
  digitalWrite(DIRE_PIN, LOW);
  digitalWrite(LASER_PIN, LOW);
}

// Route: /esp32/status
void handle_status()
{
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/plain", "OK");
}

// Route: /esp32/laser-on
void handle_laser_on()
{
  digitalWrite(LASER_PIN, HIGH);
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/plain", "Laser ON");
}

// Route: /esp32/laser-off
void handle_laser_off()
{
  digitalWrite(LASER_PIN, LOW);
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/plain", "Laser OFF");
}

// Route: /esp32/step
void handle_step()
{
  digitalWrite(STEP_PIN, HIGH);
  delay(STEP_DELAY);
  digitalWrite(STEP_PIN, LOW);
  delay(STEP_DELAY);

  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/plain", "Step triggered");
}
// Route: /esp32/step360
void handle_step360()
{
  for (int i = 0; i < 200; i++)
  {
    digitalWrite(STEP_PIN, HIGH);
    delay(STEP_DELAY);
    Serial.println(i);
    digitalWrite(STEP_PIN, LOW);
    delay(STEP_DELAY);
  }

  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/plain", "Step triggered");
}

// Set routes
void setup_routes()
{
  server.on("/esp32/status", HTTP_GET, handle_status);
  server.on("/esp32/laser-on", HTTP_GET, handle_laser_on);
  server.on("/esp32/laser-off", HTTP_GET, handle_laser_off);
  server.on("/esp32/step", HTTP_GET, handle_step);
  server.on("/esp32/step360", HTTP_GET, handle_step360);
}

void setup()
{
  Serial.begin(115200);
  init_control_pins();

  set_led_intensity(50);
  delay(500);
  set_led_intensity(0);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi...");
  while (WiFi.status() != WL_CONNECTED)
  {
    set_led_intensity(10);
    delay(200);
    set_led_intensity(0);
    delay(800);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi!");
  Serial.println(WiFi.localIP());

  server.begin();
  setup_routes();

  digitalWrite(EN_PIN, LOW); // Enable stepper motor
  set_led_intensity(2);
  delay(500);
  set_led_intensity(0);
}

void loop()
{
  server.handleClient();
}
