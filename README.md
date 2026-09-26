# I Built a Robot Dog from Scratch — Here's Everything That Went Wrong

**By Sreyas**  
**Project:** NovaSM3 Quadruped Robot Dog  
**Based on:** SpotMicro/NovaSM3 by Chris Locke

---

## Why I Did This

I've always been obsessed with Boston Dynamics' Spot. That fluid, almost biological movement, the way it navigates terrain, the sheer engineering behind it. When I found out there was an open source clone called the NovaSM3 that I could actually build myself, I jumped on it immediately.

The NovaSM3 is a 12-servo quadruped robot dog — a Spot-Mini Micro clone designed by Chris Locke. It uses a Teensy 4.0 as the brain, an Arduino Nano for sensor management, a PCA9685 PWM driver to control all 12 DS3218 servos, and an NRF24L01 for wireless control. It's not a beginner project. I found that out pretty quickly.

This is the complete story of my build — every mistake, every fix, every moment of "why is this not working" at 2am. I'm writing this so other people building this robot don't have to suffer through the same things I did.

---

## The Parts

Before I even touched a wire, I had to source everything. The full parts list:

| Component | Details |
|---|---|
| Main Controller | Teensy 4.0 |
| Slave Controller | Arduino Nano (CH340 variant) |
| Servo Driver | PCA9685 16-channel PWM |
| Servos | 12x DS3218 (270°, 15kg/cm) |
| IMU | GY-521 / MPU6050 |
| Wireless Modules | 2x NRF24L01 |
| Battery | OVONIC 3S LiPo 2200mAh 25C with T/Dean connector |
| Battery Charger | HTRC 80W 6A balance charger |
| Servo Buck Converter | XY-160D adjustable (set to 6.8V) |
| Logic Buck Converter | XL6009 adjustable (set to 5.4V) |
| MP3 Player | DFPlayer Pro (USB-C, DF1201S chip) |
| Speaker | Small 4-8 ohm |
| Ultrasonic Sensors | 2x HC-SR04 |
| PIR Sensors | 3x PIR |
| OLED Display | SPI 128x64 |
| RGB LEDs | 4x WS2812B 5050 addressable modules |
| 3D Printer | Bambu Lab A1 |

The 3D printing alone took days. Watching parts come off the bed one by one, checking tolerances, reprinting when something didn't fit right — it's a whole project within the project.

---

## Wiring: Where Everything Started Going Wrong

### The Wire Gauge Problem

The first thing I had to figure out was what wire to use where. I had 18 AWG and 22 AWG on hand and genuinely didn't know if it mattered. It does. A lot.

The rule I settled on: **18 AWG for anything carrying power, 22 AWG for anything carrying signal.** The DS3218 servos can pull 1-2 amps each under load, and with 12 of them running simultaneously you do not want thin wire on that power rail. 22 AWG on a servo power line would get warm at best, melt at worst.

My battery leads were actually 14 AWG — thicker than the 18 AWG I was routing to the buck converters. That's fine, thicker is always better on the power side. Splicing 14 to 18 AWG just meant twisting all three wires together (the 14 AWG battery wire plus the two 18 AWG runs going to the buck and the PCB), soldering the bundle solid, and heat shrinking it.

### The Power Architecture

Getting the power system right took longer than I expected. The full chain:

```
LiPo (11.1V 3S)
    → ON/OFF Rocker Switch
    → 6.8V Buck Converter
        → Distribution Block
            → PCA9685 Servo Power (green terminal)
        → 5.4V Buck Converter
            → Teensy VIN
            → Nano VIN
            → All sensors and peripherals
```

Setting the buck converter voltages required a multimeter set to **20V DC** — the range just above what I was measuring. Red probe to output positive, black to negative, adjust the tiny potentiometer screw until the display reads what you want. The 6.8V buck landed at 6.81V and I left it there. The 5.4V buck read 5.42V. Both perfectly fine.

### The PCA9685 Has TWO Power Inputs (I Didn't Know This)

This tripped me up badly. The PCA9685 servo driver board has two completely separate power connections:

1. **VCC on the side header pins** — this is logic power, needs 5V
2. **The green screw terminal** — this is servo power, needs 6.8V from the distribution block

I wired logic power through the rocker switch to VCC and called it done. The green terminal had GND connected but no V+. When I powered everything on, servos got zero power. I spent way too long debugging before I realized the servo power rail was completely disconnected.

Both inputs must be connected. VCC feeds the chip. The green terminal feeds the servos. Two different voltages, two different purposes.

---

## The Buck Converter Massacre

This was the most painful moment of the entire build.

I was wiring up the 6.8V buck converter — the one that would power all 12 servos. I had the battery wired up, everything connected, and flipped the switch to do a voltage test before connecting anything else.

It started smoking immediately.

I cut power as fast as I could. The buck converter was dead. I had plugged the battery wires in reversed — positive to the negative terminal, negative to positive. Reverse polarity on a buck converter kills it instantly. I could smell the burned component. The smoke left no doubt.

The lesson hurt: **always check polarity with a multimeter before powering on for the first time.** Red to +IN, black to −IN. It takes ten seconds and it costs nothing. Replacing a blown buck converter costs time and money and is entirely avoidable.

I ordered a replacement and waited. When it arrived I triple-checked polarity before touching anything. Landed at 6.81V on the first try.

---

## The PCA9685 Smoking Incident

A few days later, after getting the replacement buck converter wired up, I powered everything on and saw smoke again — this time coming from under the PCB somewhere near the PCA9685.

I cut power. My heart sank. Another dead component?

I started inspecting everything. No visible burn marks. No discoloration. Nothing obviously wrong. I powered on again carefully — no smoke. The PCA9685 power LED lit up red, solid and normal.

What happened? Almost certainly **flux burning off solder joints**. When you solder wires onto boards, rosin core flux residue is left behind. The first time those joints get warm, the flux burns off — it smokes, it smells a little, and it looks alarming. But it's completely harmless and only happens once. Every electronics builder eventually experiences this and panics unnecessarily.

The board was fine. I continued.

---

## Servos Going Crazy on Power-On

Once I had power sorted, I connected the servos and powered everything on together. All 12 servos immediately started spinning wildly in random directions, twisting their wires, fighting against the leg structure.

I cut power immediately.

The problem was timing. The servos were getting power before the Teensy had fully booted and sent any PWM signal to the PCA9685. With no valid signal, the servos just spin to random positions. The fix is a specific power-on order:

1. Plug Teensy into laptop USB first
2. Wait 5 full seconds for complete boot
3. Only then apply battery power to servos

When the Teensy is already running and sending valid PWM signals before servo power arrives, the servos snap directly to their commanded position instead of spinning randomly.

I also had another problem layered on top of this — some of my servos had been physically installed at the wrong angle during assembly. One servo had been rotated about 200 degrees from where it should have been before I attached the horn. When that servo tried to reach its home position it had to travel more than 360 degrees — which meant it just kept spinning, because it could never actually reach the target.

The software fix for this is adjusting the home position values in `NovaServos.h` to match the physical installation angle of each servo.

---

## Gluing the Servo Horns: A Terrible Idea

I'll be honest about this one. I glued the servo horns on because I was worried about them coming loose. This was a mistake.

Servo horns are supposed to come off. You need to be able to remove them to reposition them if a servo is installed at the wrong angle. The correct attachment method is the included screw — tight enough to hold but removable when needed.

With glued horns I had no way to manually reposition servos. The only option was adjusting home values in software to compensate, which works but is harder and less precise than just pulling the horn off and reattaching it at the correct angle.

**Never glue servo horns. Use only the screw.**

---

## The Teensy Serial Monitor Mystery

Getting the Teensy's Serial Monitor to work was a multi-day struggle.

First problem: the Teensy shows up in Arduino IDE 2.x as `usb:80003/0/0/1` instead of a standard COM port. Windows Device Manager shows nothing in the Ports section. There's no baud rate dropdown in Serial Monitor. This looks wrong but it's actually completely normal for Teensy on newer Arduino IDE versions. You just select that USB path as the port and it works.

Second problem: even after selecting the right port, Serial Monitor was completely blank. No output at all. I stared at an empty black box for longer than I'd like to admit.

The reason: every single debug flag in the NovaSM3 Teensy code defaults to 0. And `Serial.begin()` is only called inside an `if (debug)` block. With debug set to 0, the Teensy literally never initializes the serial port. It's not broken — it's intentionally silent for normal operation to avoid the Teensy hanging when not connected to a computer.

Fix: set `const byte debug = 1;` at the top of the code. Immediately Serial Monitor came alive with startup messages.

Third problem: even with debug enabled, I was missing the startup messages because they printed before I could open Serial Monitor. The `while (!Serial)` wait is commented out in the code because of Teensy quirks with USB initialization. Fix: add `delay(3000);` before the first serial print to give myself time to open the monitor.

---

## The 9-Blink Crash Loop

At one point the Teensy started doing a strange thing: the LED would blink exactly 9 times, pause for a few seconds, then blink 9 times again. Over and over. Nothing else worked. Serial Monitor was empty.

This turned out to be the Teensy's watchdog timer resetting it because it was stuck in an infinite loop. The culprit:

```cpp
if (!nrf_radio.begin()) {
  if (debug8) Serial.println(F("radio hardware is not responding!!"));
  while (1) {}  // infinite loop if NRF not found
}
```

The NRF24L01 module on the robot side wasn't being detected by the Teensy. Every time the Teensy booted it hit this line, got stuck in `while(1){}`, the watchdog timer fired after a few seconds and reset the board, and the whole cycle repeated.

The fix was changing `while (1) {}` to `nrf_active = 0;` so the robot would boot normally even if the NRF wasn't found, just without wireless control. This let me at least get the robot running and debug the NRF issue separately.

---

## Arduino Nano Upload Failures

When I tried to upload the slave code to the Arduino Nano, I kept getting:

```
Warning: attempt 1 of 10: not in sync: resp=0x1c
Warning: attempt 2 of 10: not in sync: resp=0x1c
...
Error: unable to open port COM9
Failed uploading: uploading error: exit status 1
```

The fix was simple once I knew it: go to **Tools → Processor → ATmega328P (Old Bootloader)**. The cheap CH340-based Arduino Nanos that are widely available use an older bootloader, and Arduino IDE defaults to the newer one. Switching to Old Bootloader fixed the upload immediately.

---

## Building the Wireless Controller

The original NovaSM3 remote control code was designed for an Arduino Mega. It uses analog pins A8 through A11 for potentiometers — pins that don't exist on an Arduino Nano. Trying to compile it on a Nano throws errors immediately.

Since I wanted to control the robot wirelessly from my laptop, I built a simple custom serial transmitter instead. The setup: an Arduino Nano on a breadboard with an NRF24L01 module, plugged into my laptop via USB. I open Serial Monitor, type a command, hit send, and the command gets transmitted wirelessly to the robot.

The NRF24L01 wiring on the breadboard:

| NRF24L01 | Arduino Nano |
|---|---|
| VCC | 3.3V (NEVER 5V) |
| GND | GND |
| CE | D7 |
| CSN | D8 |
| SCK | D13 |
| MOSI | D11 |
| MISO | D12 |

A 22uF capacitor across VCC and GND of the NRF is essential. Without it the module can be unstable — the NRF24L01 draws sudden current spikes and the capacitor smooths those out. Positive leg to VCC, negative (shorter) leg to GND.

One critical thing I got wrong initially: the `radioNumber` setting. The Teensy code has `radioNumber = 1` and opens a reading pipe on `address[!radioNumber]` which works out to `address[0]` ("1Node"). My transmitter needs `radioNumber = 0` to write to `address[0]`. Getting this backward means the two modules are talking to the wrong addresses and communication never happens.

---

## Servo Calibration

The calibration process requires the PCA9685 to be initialized with very specific settings. The original builder burned multiple servos by accidentally changing these:

```cpp
pwm1.setOscillatorFrequency(25000000);  // 25 MHz — do not change
pwm1.setPWMFreq(60);                    // 60 Hz — do not change
```

Adafruit suggests 50 Hz for analog servos but the DS3218 is a digital servo and 60 Hz works correctly. Changing either of these values completely invalidates all calibration and can cause servos to behave erratically or get damaged.

I ran the calibration sketch one leg at a time to start, to avoid any leg-to-leg collisions during sweeping. Connecting three servos, powering up, watching where they homed, then adjusting the values in `NovaServos.h` and repeating.

My measured home values ended up different from the defaults because my servos were installed at slightly different angles:

```cpp
// Default values in the original code:
float servoHome[TOTAL_SERVOS] = {
  328, 280, 520,   // RFx
  370, 472, 280,   // LFx
  375, 331, 370,   // RRx
  374, 451, 213,   // LRx
};

// My actual measured values:
float servoHome[TOTAL_SERVOS] = {
  352, 280, 510,   // RFx
  364, 442, 225,   // LFx
  367, 331, 423,   // RRx
  364, 351, 213,   // LRx
};
```

The front tibia servos (RFT and LFT) were physically installed 180 degrees flipped compared to the correct orientation. Because I had glued the horns, I couldn't just reposition them. Instead I had to invert the values in software.

For an inverted servo the formula is: `inverted_home = min + max - current_home`

For RFT: 375 + 617 − 510 = **482**  
For LFT: 425 + 183 − 225 = **383**

The min/max limits for those servos also need to be swapped since the direction of movement is reversed.

---

## What I Learned

Building this robot taught me more about electronics in a few months than years of casual tinkering. A few things I'll carry into every future build:

**Check polarity before powering on.** Every time. No exceptions. Ten seconds with a multimeter is worth more than a replacement component and the time it takes to arrive.

**Never glue servo horns.** The screw is there for a reason.

**Home servos before assembly.** Use a servo tester to put all 12 servos in their home position first. Then assemble each leg around them. Doing it in reverse order causes exactly the kinds of calibration problems I ran into.

**Power on order matters.** Controller first, then servos. Always.

**Read the code before assuming hardware is broken.** The 9-blink crash loop looked like a hardware failure. It was a single line of code. The blank Serial Monitor looked like a driver issue. It was a debug flag set to 0. Most of my "hardware problems" were actually software problems in disguise.

**Libraries have versions for a reason.** The NovaSM3 code was written in 2021. Updating libraries to the latest version can and does break things. When something stops working after a library update, downgrade it.

---

## Current Status

At the time of writing this, here's where the build stands:

- ✅ Power system fully wired and verified
- ✅ Teensy 4.0 running NovaSM3 firmware
- ✅ Arduino Nano running slave firmware  
- ✅ PCA9685 communicating with Teensy via I2C
- ✅ Serial Monitor working on both boards
- ✅ Servo calibration code running, home positions measured
- ✅ NRF24L01 transmitter built on breadboard and detecting radio hardware
- 🔧 Front tibia servo orientations being corrected in software
- 🔧 NRF24L01 wireless communication between transmitter and robot being debugged
- ⬜ Full walking gait testing
- ⬜ Wireless control from laptop end-to-end

There's still work to do. But the robot is taking shape, the servos are moving, and every problem I've fixed has taught me something I couldn't have learned any other way. That's what this kind of project is really about.

---

## Resources

- NovaSM3 GitHub: https://github.com/cguweb-com/Arduino-Projects/tree/main/Nova-SM3
- Nova's Website: https://novaspotmicro.com
- Discord: https://discord.gg/kwYCufegRr
- YouTube Build Series: https://www.youtube.com/watch?v=00PkTcGWPvo&list=PLcOZNHwM_I2a3YZKf8FtUjJneKGXCfduk
- RF24 Library: https://github.com/nRF24/RF24
- Teensyduino: https://www.pjrc.com/teensy/td_download.html
