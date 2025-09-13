/*
 * ESP8266 MPU6050 Gyroscope Data Sender
 * This code uses I2C communication with MPU6050 sensor
 * 
 * Expected JSON format: {"x": float, "y": float, "z": float}
 * Send to: <PC_IP>:12345
 * 
 * Hardware Connections:
 * - VCC -> 3.3V
 * - GND -> GND
 * - SCL -> D1 (GPIO5)
 * - SDA -> D2 (GPIO4)
 */

#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>
#include <Wire.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Server details
const char* server_ip = "192.168.1.100";  // Replace with your PC's IP
const int server_port = 12345;

// MPU6050 I2C address
const int MPU6050_ADDR = 0x68;

// MPU6050 registers
const int MPU6050_WHO_AM_I = 0x75;
const int MPU6050_PWR_MGMT_1 = 0x6B;
const int MPU6050_GYRO_XOUT_H = 0x43;

// Gyroscope sensitivity (LSB/°/s)
const float GYRO_SENSITIVITY = 131.0;  // For ±250°/s range

WiFiClient client;

// Connection state tracking
unsigned long lastWiFiCheck = 0;
unsigned long lastServerCheck = 0;
const unsigned long wifiCheckInterval = 30000;  // Check WiFi every 30 seconds
const unsigned long serverCheckInterval = 5000; // Check server every 5 seconds

void setup() {
  Serial.begin(115200);
  delay(1000);  // Give serial time to initialize
  
  Serial.println("ESP8266 MPU6050 Gyroscope Mouse Controller");
  Serial.println("==========================================");
  
  // Initialize I2C communication
  Wire.begin();
  Wire.setClock(400000);  // 400kHz I2C clock
  
  // Initialize MPU6050
  if (initializeMPU6050()) {
    Serial.println("MPU6050 initialized successfully!");
  } else {
    Serial.println("MPU6050 initialization failed!");
    Serial.println("Check your wiring and I2C connections.");
  }
  
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
  
  // Read gyroscope data from MPU6050
  float gyro_x, gyro_y, gyro_z;
  readMPU6050Gyro(gyro_x, gyro_y, gyro_z);
  
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

bool initializeMPU6050() {
  // Wake up MPU6050
  writeRegister(MPU6050_PWR_MGMT_1, 0x00);
  delay(100);
  
  // Check if MPU6050 is responding
  if (readRegister(MPU6050_WHO_AM_I) == 0x68) {
    return true;
  }
  return false;
}

void writeRegister(int reg, int value) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission();
}

int readRegister(int reg) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(reg);
  Wire.endTransmission();
  Wire.requestFrom(MPU6050_ADDR, 1);
  return Wire.read();
}

void readMPU6050Gyro(float &x, float &y, float &z) {
  // Request gyroscope data from MPU6050
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(MPU6050_GYRO_XOUT_H);
  Wire.endTransmission();
  Wire.requestFrom(MPU6050_ADDR, 6);  // Request 6 bytes (2 bytes per axis)
  
  // Read raw gyroscope data
  int16_t raw_x = (Wire.read() << 8) | Wire.read();
  int16_t raw_y = (Wire.read() << 8) | Wire.read();
  int16_t raw_z = (Wire.read() << 8) | Wire.read();
  
  // Convert to degrees per second
  x = raw_x / GYRO_SENSITIVITY;
  y = raw_y / GYRO_SENSITIVITY;
  z = raw_z / GYRO_SENSITIVITY;
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
