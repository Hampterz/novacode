/*
 * NovaSM3 Serial Transmitter
 * Upload this to the Nano connected to your PC via USB
 * Open Serial Monitor at 19200 baud
 * Type commands and press Send
 * 
 * NRF24L01 wiring:
 * CE  -> D7
 * CSN -> D8
 * SCK -> D13
 * MOSI-> D11
 * MISO-> D12
 * VCC -> 3.3V
 * GND -> GND
 * 
 * COMMANDS:
 * 1 = march
 * 2 = walk
 * 3 = freestyle
 * 4 = trot
 * 5 = follow
 * s = stop / select mode
 * r = reset / start
 * b1 = button 1 (L1)
 * b2 = button 2 (R1)
 * b3 = button 3 (L2)
 * b4 = button 4 (R2)
 * w = left stick up
 * x = left stick down
 * a = left stick left
 * d = left stick right
 * i = right stick up
 * k = right stick down
 * j = right stick left
 * l = right stick right
 * 0 = stop all / center sticks
 */

#include <SPI.h>
#include <RF24.h>

RF24 radio(7, 8);  // CE=D7, CSN=D8

uint8_t address[][6] = {"1Node", "2Node"};
bool radioNumber = 0;

const int data_num = 14;
uint8_t tm_data[data_num] = {
  0, 0, 0, 0,   // btn1, btn2, btn3, btn4
  0, 0,         // sel1, sel2
  0, 0, 0, 0,   // p1, p2, p3, p4
  127, 127, 127, 127  // lx, ly, rx, ry (CENTERED by default)
};

uint8_t rc_data[data_num] = {0};

// Function prototypes
void print_help();
void send_data();
void parse_command(char* cmd);
void handle_command_legacy(char* cmd);

void setup() {
  Serial.begin(19200);
  while (!Serial) {}

  Serial.println("NovaSM3 Serial Controller");
  Serial.println("-------------------------");

  if (!radio.begin()) {
    Serial.println("NRF24L01 not found! Check wiring.");
    while (1) {}
  }

  radio.setPALevel(RF24_PA_LOW);
  radio.setPayloadSize(sizeof(tm_data));
  radio.setChannel(124);
  radio.openWritingPipe(address[radioNumber]);
  radio.enableAckPayload();
  radio.setRetries(5, 5);

  Serial.println("Radio ready!");
  print_help();
}

unsigned long last_serial_time = 0;

char serial_buf[64];
int buf_idx = 0;

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (buf_idx > 0) {
        serial_buf[buf_idx] = '\0'; // Null-terminate
        
        // Check if it's a binary packet format <...>
        if (serial_buf[0] == '<' && serial_buf[buf_idx - 1] == '>') {
          serial_buf[buf_idx - 1] = '\0'; // Remove trailing >
          parse_command(&serial_buf[1]);  // Skip leading <
          send_data();
          last_serial_time = millis();
        } 
        // Only accept short, non-packet strings as manual commands.
        // Fragments from corrupted binary packets are silently dropped.
        else if (buf_idx > 0 && buf_idx <= 4 && strchr(serial_buf, ',') == NULL) {
          // Convert to lowercase
          for(int i=0; i<buf_idx; i++){
            serial_buf[i] = tolower(serial_buf[i]);
          }
          handle_command_legacy(serial_buf);
          send_data();
          last_serial_time = millis();
        }
        buf_idx = 0; // Reset buffer for next line
      }
    } else {
      if (buf_idx < 63) {
        serial_buf[buf_idx++] = c;
      }
    }
  }

  // Safety failsafe: if no commands received for 500ms from the Python app, stop the robot
  if (millis() - last_serial_time > 500) {
    tm_data[10] = 127; tm_data[11] = 127; // lx, ly CENTER
    tm_data[12] = 127; tm_data[13] = 127; // rx, ry CENTER
    tm_data[0] = 0; tm_data[1] = 0;   // btn1, btn2
    tm_data[2] = 0; tm_data[3] = 0;   // btn3, btn4
    tm_data[4] = 0; tm_data[5] = 0;   // sel1, sel2
    tm_data[7] = 0;                    // p2 (no command)
    send_data();
    delay(50); // Prevent spamming radio when disconnected
  }
}

void parse_command(char* cmd) {
  // Validate packet integrity by counting commas
  int commaCount = 0;
  for (int i=0; cmd[i] != '\0'; i++) {
    if (cmd[i] == ',') commaCount++;
  }
  if (commaCount != 11) return; // Drop corrupted packets

  char* ptr = strtok(cmd, ",");
  int i = 0;
  while (ptr != NULL && i < 12) {
    int val = atoi(ptr);
    
    if (i == 0) tm_data[10] = val;      // lx
    else if (i == 1) tm_data[11] = val; // ly
    else if (i == 2) tm_data[12] = val; // rx
    else if (i == 3) tm_data[13] = val; // ry
    else if (i == 4) tm_data[0] = val;  // btn1
    else if (i == 5) tm_data[1] = val;  // btn2
    else if (i == 6) tm_data[2] = val;  // btn3
    else if (i == 7) tm_data[3] = val;  // btn4
    else if (i == 8) tm_data[4] = val;  // sel1
    else if (i == 9) tm_data[5] = val;  // sel2
    else if (i == 10) tm_data[6] = val; // p1 (mode)
    else if (i == 11) tm_data[7] = val; // p2 (special cmd)
    
    ptr = strtok(NULL, ",");
    i++;
  }
  
  // Clear unused slide pot values so random image pixels don't cause the robot to jitter
  tm_data[8] = 0; 
  tm_data[9] = 0;
}

void handle_command_legacy(char* cmd) {
  // reset sticks to CENTER and buttons to 0
  tm_data[10] = 127; tm_data[11] = 127;
  tm_data[12] = 127; tm_data[13] = 127;
  tm_data[0] = 0; tm_data[1] = 0;
  tm_data[2] = 0; tm_data[3] = 0;
  tm_data[4] = 0; tm_data[5] = 0;
  tm_data[7] = 0;

  if (strcmp(cmd, "1") == 0) {
    tm_data[7] = 11; // p2=11 -> march
    Serial.println("-> Mode: MARCH");
  } else if (strcmp(cmd, "2") == 0) {
    tm_data[7] = 12; // p2=12 -> walk
    Serial.println("-> Mode: WALK");
  } else if (strcmp(cmd, "3") == 0) {
    tm_data[7] = 13; // p2=13 -> freestyle
    Serial.println("-> Mode: FREESTYLE");
  } else if (strcmp(cmd, "4") == 0) {
    tm_data[7] = 14; // p2=14 -> trot
    Serial.println("-> Mode: TROT");
  } else if (strcmp(cmd, "5") == 0) {
    tm_data[7] = 15; // p2=15 -> follow
    Serial.println("-> Mode: FOLLOW");
  } else if (strcmp(cmd, "r") == 0) {
    tm_data[5] = 1;  // sel2 = 1 -> start
    Serial.println("-> Robot START");
  } else if (strcmp(cmd, "s") == 0) {
    tm_data[5] = 1;  // sel2 = 1 -> stop (toggle)
    Serial.println("-> Robot STOP");
  } else if (strcmp(cmd, "w") == 0) {
    tm_data[13] = 215; // right stick down (walk backward)
    Serial.println("-> Right stick DOWN");
  } else if (strcmp(cmd, "x") == 0) {
    tm_data[13] = 40;  // right stick up (walk forward)
    Serial.println("-> Right stick UP");
  } else if (strcmp(cmd, "a") == 0) {
    tm_data[10] = 40;  // left stick left
    Serial.println("-> Left stick LEFT");
  } else if (strcmp(cmd, "d") == 0) {
    tm_data[10] = 215; // left stick right
    Serial.println("-> Left stick RIGHT");
  } else if (strcmp(cmd, "i") == 0) {
    tm_data[13] = 40;  // right stick up
    Serial.println("-> Right stick UP");
  } else if (strcmp(cmd, "k") == 0) {
    tm_data[13] = 215; // right stick down
    Serial.println("-> Right stick DOWN");
  } else if (strcmp(cmd, "j") == 0) {
    tm_data[12] = 40;  // right stick left
    Serial.println("-> Right stick LEFT");
  } else if (strcmp(cmd, "l") == 0) {
    tm_data[12] = 215; // right stick right
    Serial.println("-> Right stick RIGHT");
  } else if (strcmp(cmd, "0") == 0) {
    Serial.println("-> All stop / center");
  } else if (strcmp(cmd, "?") == 0 || strcmp(cmd, "help") == 0) {
    print_help();
  } else {
    Serial.print("Unknown command: ");
    Serial.println(cmd);
  }
}

void send_data() {
  bool resp = radio.write(&tm_data, sizeof(tm_data));
  if (resp) {
    if (radio.isAckPayloadAvailable()) {
      radio.read(&rc_data, sizeof(rc_data));
      // Forward ACK data to Python: [ACK:remote_select,start_mode,mpu_active]
      Serial.print("[ACK:");
      Serial.print(rc_data[6]); Serial.print(",");  // remote_select
      Serial.print(rc_data[7]); Serial.print(",");  // start_mode
      Serial.print(rc_data[8]); Serial.print(",");  // mpu_active
      Serial.print(rc_data[9]); Serial.print(",");  // USS left (cm)
      Serial.print(rc_data[10]);                     // USS right (cm)
      Serial.println("]");
    }
  }
}

void print_help() {
  Serial.println("");
  Serial.println("=== COMMANDS ===");
  Serial.println("1-5  : select mode (march/walk/freestyle/trot/follow)");
  Serial.println("r    : start robot");
  Serial.println("s    : stop robot");
  Serial.println("w/x  : left stick up/down");
  Serial.println("a/d  : left stick left/right");
  Serial.println("i/k  : right stick up/down");
  Serial.println("j/l  : right stick left/right");
  Serial.println("b1-b4: buttons 1-4");
  Serial.println("0    : stop all movement");
  Serial.println("?    : show this help");
  Serial.println("================");
  Serial.println("");
}