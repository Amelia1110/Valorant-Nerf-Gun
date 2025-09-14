#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiUdp.h>

// Joystick
#define FWD 39 //ADC CH0
#define SIDE 36 //ADC CH3
#define JUMP 4
// Buttons
#define BUTTON_PIN_R 14
#define BUTTON_PIN_LEFT_MOUSE 13
#define BUTTON_PIN_SWITCH 16 //D2

// Wifi
const char* ssid = "HackTheNorth";

const char* password = "HTN2025!";
const char *PC_IP = "10.37.126.245"; // TODO: IP of your PC running Python CHANGE THIS
const int   PC_PORT  = 5005;

WiFiUDP udp;

const int MPU_addr = 0x68; // I2C address
int16_t a_cX, a_cY, a_cZ, tmp, g_yX, g_yY, g_yZ;

void setup()
{
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

  // wifi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  udp.begin(PC_PORT);
}

void loop()
{
  Wire.beginTransmission(MPU_addr);
  Wire.write(0x3B); // starting with register 0x3B ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_addr, 14); // request a total of 14 registers

  a_cX = Wire.read() << 8 | Wire.read(); // 0x3B ACCEL_XOUT_H 0x3C ACCEL_XOUT_L
  a_cY = Wire.read() << 8 | Wire.read(); // 0x3D ACCEL_YOUT_H 0x3E ACCEL_YOUT_L
  a_cZ = Wire.read() << 8 | Wire.read(); // 0x3F ACCEL_ZOUT_H 0x40 ACCEL_ZOUT_L
  tmp = Wire.read() << 8 | Wire.read(); // 0x41 TEMP_OUT_H 0x42 TEMP_OUT_L
  g_yX = Wire.read() << 8 | Wire.read(); // 0x43 GYRO_XOUT_H 0x44 GYRO_XOUT_L
  g_yY = Wire.read() << 8 | Wire.read(); // 0x45 GYRO_YOUT_H 0x46 GYRO_YOUT_L
  g_yZ = Wire.read() << 8 | Wire.read(); // 0x47 GYRO_ZOUT_H 0x48 GYRO_ZOUT_L

  float ax = a_cX / 16384.0f;
  float ay = a_cY / 16384.0f;
  float az = a_cZ / 16384.0f;

  float gx = g_yX / 131.0f;
  float gy = g_yY / 131.0f;
  float gz = g_yZ / 131.0f;

  // Build a byte of button states (bitmask)
  // Up to 8 buttons
  uint8_t buttons = 0;
  if (digitalRead(BUTTON_PIN_R) == HIGH) buttons |= 1 << 0; // bit 0 = 'R'
  if (digitalRead(BUTTON_PIN_LEFT_MOUSE) == HIGH)
    buttons |= 1 << 1; // bit 1 = 'Left Mouse Click'
  if (digitalRead(JUMP) == HIGH)
    buttons |= 1 << 2; // bit 2 = 'Space'
  if (digitalRead(BUTTON_PIN_SWITCH) == LOW)
    buttons |= 1 << 3; // bit 3 = 'Mouse Scroll Down' 

  // joystick analog normalized -1.0 to +1.0
  int rawY = analogRead(FWD); // 0-1023
  float joystickFwd = (rawY - 2048.0f) / 2048.0f;
  if (joystickFwd > 1) joystickFwd = 1;
  if (joystickFwd < -1) joystickFwd = -1;

  int rawX = analogRead(SIDE); // 0-1023
  float joystickSide = (rawX - 2048.0f) / 2048.0f;
  if (joystickSide > 1) joystickSide = 1;
  if (joystickSide < -1) joystickSide = -1;

  // pack into one buffer: 6 floats + 1 byte + 1 float = 24 +1 +4 = 29 bytes
  uint8_t buf[33];
  memcpy(buf,       &ax, 4);
  memcpy(buf + 4,   &ay, 4);
  memcpy(buf + 8,   &az, 4);
  memcpy(buf + 12,  &gx, 4);
  memcpy(buf + 16,  &gy, 4);
  memcpy(buf + 20,  &gz, 4);
  buf[24] = buttons;
  memcpy(buf + 25, &joystickFwd, 4);
  memcpy(buf + 29, &joystickSide, 4);

  udp.beginPacket(PC_IP, PC_PORT);
  udp.write(buf, sizeof(buf));
  udp.endPacket();

  // delay(5);
}