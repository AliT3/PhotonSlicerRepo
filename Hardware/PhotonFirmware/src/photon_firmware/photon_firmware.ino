//General structure:
// On each loop:
// checkforinput, returns instruction once complete
// if there was an instruction returned then process that instruction

#include <Servo.h>

//PIN constants
int xservoPIN = 9;
int yservoPIN = 8;
int laserPIN = 13;

//Distance constants
float xMirrorToTarget = 14;
int xAngleOffset = -27;
float yMirrorToTarget = 3;
int yAngleOffset = 0;

//Hardware interface objects
Servo xServo;
Servo yServo;

//Global variable for holding the current instruction
int currentInstruction[3]; // Format: [command|arg1|arg2]

void setup() {

  // Initiate serial connection using 9600 Baud Rate
  Serial.begin(9600);
  
  // Send signal indicating that the printer is free
  Serial.println("Printer Free");

  // Attach pins
  xServo.attach(xservoPIN);
  yServo.attach(yservoPIN);
  pinMode(laserPIN, OUTPUT);

  // Set default idle instruction
  currentInstruction[0] = -1;
}

void loop() {

  //Check whether there is currently an instruction to complete
  if (currentInstruction[0] >= 0) {
    
    //Process instruction
    if (currentInstruction[0] == 1){ // SET POSITION COMMAND

      // Calculate servo angle for given coordinate
      int xAngle = xCoordToAngle(currentInstruction[1]);//0.5 map is temporary
      int yAngle = yCoordToAngle(currentInstruction[2]);
      
      // Move servo to destination position
      xServo.write(xAngle);
      yServo.write(yAngle);
      
      // Upon completion set instruction to idle
      currentInstruction[0] = -1;
    }
    else if (currentInstruction[0] == 2){ // SET LASER COMMAND

      // Set Laser to appropriate state
      if (currentInstruction[1]){
        digitalWrite(laserPIN, HIGH);
      }
      else{
        digitalWrite(laserPIN, LOW);
      }
      
      // Upon completion set instruction to idle
      currentInstruction[0] = -1;
    }
    
  }
  // Otherwise check for and process input
  else{
    processInput();
  }
}

char commandBuffer[5];
int commandPosition = 0;
void processInput(){
  
  // Check if there is a character to be read
  if (Serial.available() < 1){return;}

  // Read in the command
  char byteReceived = Serial.read();
  commandBuffer[commandPosition] = byteReceived;
  commandPosition++;

  // Check if command complete
  if (commandPosition >= 5){
    
    //Reset array index
    commandPosition = 0;

    //Process byte data into a command
    if(commandBuffer[0] == 1){ // SET POSITION COMMAND
      
      //Extract arguments x and y
      int x1 = commandBuffer[1]; if (x1 < 0) { x1 += 256;}
      int x2 = commandBuffer[2]; if (x2 < 0) { x2 += 256;}
      int y1 = commandBuffer[3]; if (y1 < 0) { y1 += 256;}
      int y2 = commandBuffer[4]; if (y2 < 0) { y2 += 256;}

      int x = (x1 << 8) + x2 - 10000;
      int y = (y1 << 8) + y2 - 10000;

      //Serial.println("Set");
      currentInstruction[0] = 1;
      currentInstruction[1] = x;
      currentInstruction[2] = y;
    }
    else if(commandBuffer[0] == 2){ // SET LASER COMMAND
      currentInstruction[0] = 2;
      currentInstruction[1] = commandBuffer[2];
    }
    else if(commandBuffer[0] == 3){ // RAISE LAYER COMMAND
      //Serial.println("Raise");
    }
    else if(commandBuffer[0] == 0){ // FINSIH COMMAND
      //Serial.println("FINISHED");
      //Serial.println(commandBuffer[1]);
      //Serial.println(commandBuffer[2]);
      //Serial.println(commandBuffer[3]);
      //Serial.println(commandBuffer[4]);
    }

    // Request next instruction
    Serial.println("NEXT");
  }
}

int xCoordToAngle(int xCoord){
  
  // Map coordinate onto range -1.0 -> +1.0
  float x = (float)xCoord / 10000;

  // Perform trig calculations
  float angle = tan(x/xMirrorToTarget);

  int angleDeg = (angle/PI)*180 + 90;
  //Serial.println(angleDeg);
  return angleDeg+xAngleOffset;
}

int yCoordToAngle(int yCoord){
  
  // Map coordinate onto range -1.0 -> +1.0
  float y = (float)yCoord / 10000;

  // Perform trig calculations
  float angle = tan(y/yMirrorToTarget);

  int angleDeg = (angle/PI)*180 + 90;
  //Serial.println(angleDeg);
  return angleDeg+yAngleOffset;
}
