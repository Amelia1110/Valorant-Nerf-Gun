#include <Arduino.h>
#include <Wire.h>

#define LED D5

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

  Serial.begin(115200);
  Serial.println("ESP8266 MPU6050 Raw Data");
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

  Serial.print("Accel: ");
  Serial.print(a_cX);
  Serial.print(",");
  Serial.print(a_cY);
  Serial.print(",");
  Serial.print(a_cZ);

  Serial.print(" | Gyro: ");
  Serial.print(g_yX);
  Serial.print(",");
  Serial.print(g_yY);
  Serial.print(",");
  Serial.print(g_yZ);

  Serial.print(" | Temp: ");
  Serial.println(tmp);

  digitalWrite(LED, !digitalRead(LED));

  delay(10);
}