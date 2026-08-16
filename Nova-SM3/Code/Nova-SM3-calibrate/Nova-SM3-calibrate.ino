//use copy of software calibration file for home & limits
#include "NovaServos.h"
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm1 = Adafruit_PWMServoDriver();

void setup() {
  Serial.begin(19200);
  Serial.println("Servo Calibration - Interactive Mode");

  pwm1.begin();
  pwm1.setOscillatorFrequency(25000000);
  pwm1.setPWMFreq(60);
  
  // Start with all servos OFF
  for (int i = 0; i < TOTAL_SERVOS; i++) {
    servoPos[i] = servoHome[i];
    pwm1.setPWM(servoSetup[i][1], 0, 0); 
  }

  Serial.println("-------------------------------------------------");
  Serial.println("Type 'leg1' for Right Front (Servos 0, 1, 2)");
  Serial.println("Type 'leg2' for Left Front (Servos 3, 4, 5)");
  Serial.println("Type 'leg3' for Right Rear (Servos 6, 7, 8)");
  Serial.println("Type 'leg4' for Left Rear (Servos 9, 10, 11)");
  Serial.println("-------------------------------------------------");
}

void loop() {
  static int activeLegBase = 0;
  
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.length() > 0) {
      if (input == "leg1" || input == "leg2" || input == "leg3" || input == "leg4") {
        if (input == "leg1") activeLegBase = 0;
        if (input == "leg2") activeLegBase = 3;
        if (input == "leg3") activeLegBase = 6;
        if (input == "leg4") activeLegBase = 9;
        
        Serial.print("\nActivating ");
        Serial.println(input);
        
        // Turn off all servos first
        for (int i = 0; i < TOTAL_SERVOS; i++) {
          pwm1.setPWM(servoSetup[i][1], 0, 0);
        }
        
        // Turn on the 3 servos for the selected leg to their current servoPos
        for (int i = activeLegBase; i < activeLegBase + 3; i++) {
          pwm1.setPWM(servoSetup[i][1], 0, servoPos[i]);
          Serial.print("Joint "); Serial.print(i - activeLegBase); Serial.print(" snapped to "); Serial.println(servoPos[i]);
        }
        Serial.println("Type '<joint> <pwm>' (e.g. '0 350' for Hip, '1 350' for Femur, '2 350' for Knee) to adjust.");
        Serial.println("Type '<joint> min' or '<joint> max' to test physical limits.");
        Serial.println("Type '<joint> home' to return to home.");
        
      } else if (input == "done") {
        Serial.println("\n--- FINAL CALIBRATION VALUES ---");
        for (int i = 0; i < TOTAL_SERVOS; i++) {
            Serial.print("Servo ");
            Serial.print(i);
            Serial.print(":\t");
            Serial.println(servoPos[i]);
        }
        Serial.println("--------------------------------\n");
      } else {
        int spaceIdx = input.indexOf(' ');
        if (spaceIdx > 0) {
          int localJoint = input.substring(0, spaceIdx).toInt();
          String valStr = input.substring(spaceIdx + 1);
          
          if (localJoint >= 0 && localJoint <= 2) {
            int servoNum = activeLegBase + localJoint;
            int targetPWM = -1;
            
            if (valStr == "min") {
              targetPWM = servoLimit[servoNum][0];
            } else if (valStr == "max") {
              targetPWM = servoLimit[servoNum][1];
            } else if (valStr == "home") {
              targetPWM = servoHome[servoNum];
            } else {
              targetPWM = valStr.toInt();
            }
            
            if (targetPWM > 0) {
              Serial.print("Moving Joint ");
              Serial.print(localJoint);
              Serial.print(" (Global Servo ");
              Serial.print(servoNum);
              Serial.print(") to ");
              Serial.print(targetPWM);
              if (valStr == "min") Serial.println(" (MIN limit)");
              else if (valStr == "max") Serial.println(" (MAX limit)");
              else if (valStr == "home") Serial.println(" (HOME position)");
              else Serial.println("");
              
              servoPos[servoNum] = targetPWM;  // Save the new value
              pwm1.setPWM(servoSetup[servoNum][1], 0, targetPWM);
            } else {
              Serial.println("Invalid PWM value");
            }
          } else {
            Serial.println("Invalid joint number (must be 0, 1, or 2)");
          }
        } else {
          Serial.println("Unknown Command.");
        }
      }
    }
  }
}