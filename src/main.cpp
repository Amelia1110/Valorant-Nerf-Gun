#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiUdp.h>

// Joystick
#define FWD 39  // ADC CH0
#define SIDE 36 // ADC CH3
#define JUMP 4
// Buttons
#define BUTTON_PIN_R 14
#define BUTTON_PIN_LEFT_MOUSE 33
#define BUTTON_PIN_SWITCH 19

// Wifi
const char *ssid = "HackTheNorth";

const char *password = "HTN2025!";
const char *PC_IP = "10.37.126.245"; // TODO: IP of your PC running Python CHANGE THIS
const int PC_PORT = 5005;

WiFiUDP udp;

const int MPU_addr = 0x68; // I2C address
int16_t a_cX, a_cY, a_cZ, tmp, g_yX, g_yY, g_yZ;

// Global variables for gyro bias
float gyroBiasX = 0, gyroBiasY = 0, gyroBiasZ = 0;
const float gyroDeadzone = 0.2; // tune this experimentally

void calibrateGyro(int samples = 500) {
  long sumX = 0, sumY = 0, sumZ = 0;
  for (int i = 0; i < samples; i++) {
    Wire.beginTransmission(MPU_addr);
    Wire.write(0x43); // GYRO_XOUT_H
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_addr, 6, true); // 3 axes * 2 bytes

    int16_t gx = Wire.read() << 8 | Wire.read();
    int16_t gy = Wire.read() << 8 | Wire.read();
    int16_t gz = Wire.read() << 8 | Wire.read();

    sumX += gx;
    sumY += gy;
    sumZ += gz;

    delay(2); // short delay between readings
  }

  gyroBiasX = sumX / (float)samples;
  gyroBiasY = sumY / (float)samples;
  gyroBiasZ = sumZ / (float)samples;

  Serial.println("Gyro calibrated:");
  Serial.println(gyroBiasX);
  Serial.println(gyroBiasY);
  Serial.println(gyroBiasZ);
}

void setup() {
  pinMode(BUTTON_PIN_R, INPUT_PULLUP);
  pinMode(BUTTON_PIN_LEFT_MOUSE, INPUT_PULLUP);
  pinMode(JUMP, INPUT_PULLUP);
  pinMode(FWD, INPUT);
  pinMode(SIDE, INPUT);

  Serial.begin(115200);

  Wire.begin();
  Wire.beginTransmission(MPU_addr);
  Wire.write(0x6B); // PWR_MGMT_1 register
  Wire.write(0);    // set to zero
  Wire.endTransmission(true);

  // Calibrate gyro at startup
  calibrateGyro();

  // WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  udp.begin(PC_PORT);
}

void loop() {
  Wire.beginTransmission(MPU_addr);
  Wire.write(0x3B); // ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_addr, 14, true);

  a_cX = Wire.read() << 8 | Wire.read();
  a_cY = Wire.read() << 8 | Wire.read();
  a_cZ = Wire.read() << 8 | Wire.read();
  tmp = Wire.read() << 8 | Wire.read();
  g_yX = Wire.read() << 8 | Wire.read();
  g_yY = Wire.read() << 8 | Wire.read();
  g_yZ = Wire.read() << 8 | Wire.read();

  float ax = a_cX / 16384.0f;
  float ay = a_cY / 16384.0f;
  float az = a_cZ / 16384.0f;

  // Subtract bias and apply deadzone
  float gx = (g_yX - gyroBiasX) / 131.0f;
  float gy = (g_yY - gyroBiasY) / 131.0f;
  float gz = (g_yZ - gyroBiasZ) / 131.0f;

  if (abs(gx) < gyroDeadzone) gx = 0;
  if (abs(gy) < gyroDeadzone) gy = 0;
  if (abs(gz) < gyroDeadzone) gz = 0;

  // Buttons
  uint8_t buttons = 0;
  if (digitalRead(BUTTON_PIN_R) == HIGH) buttons |= 1 << 0;
  if (digitalRead(BUTTON_PIN_LEFT_MOUSE) == HIGH) buttons |= 1 << 1;
  if (digitalRead(JUMP) == HIGH) buttons |= 1 << 2;
  if (digitalRead(BUTTON_PIN_SWITCH) == HIGH) buttons |= 1 << 3;

  // Joystick normalization (ESP32 12-bit ADC)
  int rawY = analogRead(FWD);
  int rawX = analogRead(SIDE);

  float joystickFwd = (rawY - 2048.0f) / 2048.0f;
  float joystickSide = (rawX - 2048.0f) / 2048.0f;

  if (joystickFwd > 1) joystickFwd = 1;
  if (joystickFwd < -1) joystickFwd = -1;
  if (joystickSide > 1) joystickSide = 1;
  if (joystickSide < -1) joystickSide = -1;

  // Pack and send
  uint8_t buf[33];
  memcpy(buf, &ax, 4);
  memcpy(buf + 4, &ay, 4);
  memcpy(buf + 8, &az, 4);
  memcpy(buf + 12, &gx, 4);
  memcpy(buf + 16, &gy, 4);
  memcpy(buf + 20, &gz, 4);
  buf[24] = buttons;
  memcpy(buf + 25, &joystickFwd, 4);
  memcpy(buf + 29, &joystickSide, 4);

  udp.beginPacket(PC_IP, PC_PORT);
  udp.write(buf, sizeof(buf));
  udp.endPacket();

  delay(10);
}
