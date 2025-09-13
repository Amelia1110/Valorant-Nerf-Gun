#include <Arduino.h>
#include <Wire.h>
#define s1 D4
#define s2 D3

const int en = 2, rw = 1, rs = 0, d4 = 4, d5 = 5, d6 = 6, d7 = 7, b1 = 3;

void setup() {
  pinMode(A0, INPUT);
  digitalWrite(D4, LOW);
  digitalWrite(D3, LOW);
}

int varX, varY;

void loop() {
  varX = analogRead(A0);
  Serial.print(varX);
  delay(10);

  varY = analogRead(A0);
  Serial.print(varY);
  delay(10);

  delay(100);
}