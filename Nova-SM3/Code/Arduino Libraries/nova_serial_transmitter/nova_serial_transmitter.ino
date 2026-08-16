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
  0, 0, 0, 0    // lx, ly, rx, ry
};

uint8_t rc_data[data_num] = {0};

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

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    cmd.toLowerCase();
    handle_command(cmd);
    send_data();
  }
}

void handle_command(String cmd) {
  // reset sticks and buttons each command
  tm_data[10] = 0; tm_data[11] = 0;
  tm_data[12] = 0; tm_data[13] = 0;
  tm_data[0] = 0; tm_data[1] = 0;
  tm_data[2] = 0; tm_data[3] = 0;
  tm_data[4] = 0; tm_data[5] = 0;

  if (cmd == "1") {
    tm_data[4] = 1; // sel1 = mode select
    tm_data[6] = 0; // p1 = mode 0 (march)
    Serial.println("-> March mode");
  } else if (cmd == "2") {
    tm_data[4] = 1;
    tm_data[6] = 64;
    Serial.println("-> Walk mode");
  } else if (cmd == "3") {
    tm_data[4] = 1;
    tm_data[6] = 128;
    Serial.println("-> Freestyle mode");
  } else if (cmd == "4") {
    tm_data[4] = 1;
    tm_data[6] = 192;
    Serial.println("-> Trot mode");
  } else if (cmd == "5") {
    tm_data[4] = 1;
    tm_data[6] = 255;
    Serial.println("-> Follow mode");
  } else if (cmd == "s") {
    tm_data[5] = 1; // sel2 = stop
    Serial.println("-> Stop");
  } else if (cmd == "r") {
    tm_data[4] = 1; // sel1 = start
    Serial.println("-> Start");
  } else if (cmd == "b1") {
    tm_data[0] = 1;
    Serial.println("-> Button 1 (L1)");
  } else if (cmd == "b2") {
    tm_data[1] = 1;
    Serial.println("-> Button 2 (R1)");
  } else if (cmd == "b3") {
    tm_data[2] = 1;
    Serial.println("-> Button 3 (L2)");
  } else if (cmd == "b4") {
    tm_data[3] = 1;
    Serial.println("-> Button 4 (R2)");
  } else if (cmd == "w") {
    tm_data[11] = 127; // left stick up
    Serial.println("-> Left stick UP");
  } else if (cmd == "x") {
    tm_data[11] = -127; // left stick down
    Serial.println("-> Left stick DOWN");
  } else if (cmd == "a") {
    tm_data[10] = -127; // left stick left
    Serial.println("-> Left stick LEFT");
  } else if (cmd == "d") {
    tm_data[10] = 127; // left stick right
    Serial.println("-> Left stick RIGHT");
  } else if (cmd == "i") {
    tm_data[13] = 127; // right stick up
    Serial.println("-> Right stick UP");
  } else if (cmd == "k") {
    tm_data[13] = -127; // right stick down
    Serial.println("-> Right stick DOWN");
  } else if (cmd == "j") {
    tm_data[12] = -127; // right stick left
    Serial.println("-> Right stick LEFT");
  } else if (cmd == "l") {
    tm_data[12] = 127; // right stick right
    Serial.println("-> Right stick RIGHT");
  } else if (cmd == "0") {
    Serial.println("-> All stop / center");
  } else if (cmd == "?" || cmd == "help") {
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
    }
    Serial.println("Sent OK");
  } else {
    Serial.println("Send FAILED - is robot on?");
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