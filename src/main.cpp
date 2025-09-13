#include <Arduino.h>
#include <Wire.h>
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

#define LED D5

// Wifi
const char* ssid     = "HackTheNorth";
const char* password = "HTN2025!";
const char* PC_IP    = "Placeholder"; // TODO: IP of your PC running Python CHANGE THIS
const int   PC_PORT  = 5005;

WiFiUDP udp;

const int MPU_addr = 0x68; // I2C address
int16_t a_cX, a_cY, a_cZ, tmp, g_yX, g_yY, g_yZ;

void setup()
{
  pinMode(LED, OUTPUT);

  Wire.begin();
  Wire.beginTransmission(MPU_addr);
  Wire.write(0x6B); // PWR_MGMT_1 register
  Wire.write(0);    // set to zero
  Wire.endTransmission(true);

  // Wi-Fi
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
  Wire.requestFrom(MPU_addr, 14, true); // request a total of 14 registers

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

  // Pack into 24 bytes (6 floats)
  uint8_t buf[24];
  memcpy(buf,       &ax, 4);
  memcpy(buf + 4,   &ay, 4);
  memcpy(buf + 8,   &az, 4);
  memcpy(buf + 12,  &gx, 4);
  memcpy(buf + 16,  &gy, 4);
  memcpy(buf + 20,  &gz, 4);

  udp.beginPacket(PC_IP, PC_PORT);
  udp.write(buf, sizeof(buf));
  udp.endPacket();

  digitalWrite(LED, !digitalRead(LED));

  delay(10);
}