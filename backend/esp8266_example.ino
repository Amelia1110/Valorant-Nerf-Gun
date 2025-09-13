/*
 * ESP8266 Gyroscope Data Sender Example
 * This code shows how to send gyroscope data to the Python mouse controller
 * 
 * Expected JSON format: {"x": float, "y": float, "z": float}
 * Send to: <PC_IP>:12345
 * 
 * IMPORTANT: ESP8266 only has 1 ADC pin (A0), so this example uses
 * simulated gyroscope data. For real sensors, use I2C (see MPU6050 version below).
 */

#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Server details
const char* server_ip = "192.168.1.100";  // Replace with your PC's IP
const int server_port = 12345;

// ESP8266 only has 1 ADC pin (A0), so we'll simulate gyroscope data
// For real sensors, use I2C communication instead
const int gyro_pin = A0;  // Only available ADC pin

WiFiClient client;

// Connection state tracking
unsigned long lastWiFiCheck = 0;
unsigned long lastServerCheck = 0;
const unsigned long wifiCheckInterval = 30000;  // Check WiFi every 30 seconds
const unsigned long serverCheckInterval = 5000; // Check server every 5 seconds

void setup() {
  Serial.begin(115200);
  delay(1000);  // Give serial time to initialize
  
  Serial.println("ESP8266 Gyroscope Mouse Controller");
  Serial.println("==================================");
  
  // Initialize gyroscope pin (only A0 available on ESP8266)
  pinMode(gyro_pin, INPUT);
  
  // Connect to WiFi with proper error handling
  connectToWiFi();
  
  // Connect to Python server
  connectToServer();
}

void loop() {
  unsigned long currentTime = millis();
  
  // Check WiFi connection periodically
  if (currentTime - lastWiFiCheck > wifiCheckInterval) {
    checkWiFiConnection();
    lastWiFiCheck = currentTime;
  }
  
  // Check server connection
  if (!client.connected()) {
    if (currentTime - lastServerCheck > serverCheckInterval) {
      connectToServer();
      lastServerCheck = currentTime;
    }
    return;
  }
  
  // Read gyroscope data (simulated for demo - use I2C for real sensors)
  float gyro_x, gyro_y, gyro_z;
  readGyroscopeData(gyro_x, gyro_y, gyro_z);
  
  // Create JSON object
  DynamicJsonDocument doc(1024);
  doc["x"] = gyro_x;
  doc["y"] = gyro_y;
  doc["z"] = gyro_z;
  
  // Send JSON data with newline (CRITICAL for Python parsing)
  String jsonString;
  serializeJson(doc, jsonString);
  client.println(jsonString);  // println adds \n automatically
  
  // Small delay to prevent overwhelming the server
  delay(10);  // 100Hz update rate
}

void connectToWiFi() {
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("WiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println();
    Serial.println("WiFi connection failed!");
    Serial.println("Please check your credentials and try again.");
    // Continue anyway - will retry in loop()
  }
}

void checkWiFiConnection() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected! Attempting to reconnect...");
    WiFi.begin(ssid, password);
  }
}

void connectToServer() {
  Serial.println("Connecting to Python server...");
  if (client.connect(server_ip, server_port)) {
    Serial.println("Connected to Python server!");
    lastServerCheck = millis();
  } else {
    Serial.println("Server connection failed. Will retry...");
  }
}

void readGyroscopeData(float &x, float &y, float &z) {
  // SIMULATED GYROSCOPE DATA - Replace with real sensor code
  // ESP8266 only has 1 ADC pin (A0), so we simulate 3-axis data
  
  // Read the single ADC pin
  int raw_value = analogRead(gyro_pin);
  
  // Convert to voltage (0-3.3V for ESP8266)
  float voltage = (raw_value / 1023.0) * 3.3;
  
  // Simulate 3-axis gyroscope data based on single input
  // This is just for demonstration - use I2C for real sensors
  x = (voltage - 1.65) * 50.0;  // Simulate X-axis rotation
  y = sin(millis() * 0.001) * 10.0;  // Simulate Y-axis oscillation
  z = cos(millis() * 0.002) * 5.0;   // Simulate Z-axis oscillation
  
  // Add some noise to make it more realistic
  x += random(-5, 5) * 0.1;
  y += random(-5, 5) * 0.1;
  z += random(-5, 5) * 0.1;
}
