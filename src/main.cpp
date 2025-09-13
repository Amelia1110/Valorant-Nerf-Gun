#include <Arduino.h>
#include <Wire.h>
#define s1 D3

int fwd, jump;


void setup() {
  Serial.begin(9600);
  pinMode(A0, INPUT);
  pinMode(s1, INPUT);
}

void loop() {
  fwd = analogRead(A0);
  jump = digitalRead(s1);

  Serial.print(fwd);
  Serial.print(" || ");
  Serial.println(jump); //jump == 0 when pressed
  delay(10);
}