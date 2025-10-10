# rfidisk
A complete RFID based app launcher for Linux.
<img width="1794" height="973" alt="3D" src="https://github.com/user-attachments/assets/7a0db381-44d1-4340-8a02-d670594e7833" />

<img src="https://github.com/user-attachments/assets/9dd670ca-56e6-4e30-9336-dc6832b9829a" width="240">

<img src="https://github.com/user-attachments/assets/92fac60e-d8e5-4bd7-88b9-1fdff2cd14ef" width="240">

<img src="https://github.com/user-attachments/assets/b9502485-c848-4b90-ae61-77a5aa62d406" width="240">

<img src="https://github.com/user-attachments/assets/eeecc4b2-6a04-49ed-a520-2e8493fd4019" width="240">

## Project Description:
An 3D-printed external disk drive, that connects to a host Linux machine via USB, and uses 3D-printed RFID-Enabled 3.5" floppy disks.
The user inserts disks into the drive, and the host machine launches an application. The application stays open as long as the disk is in the drive.
When the user removes the disk, the application is terminated. Also, there is an monochrome OLED 128x64 screen on the hardware that provides info
about the disk that is currently in the drive.

This project includes everything you're going to need, including BOM, schematics (pinout, basically), code for both the microcontroller and the host machine, and even models for 3D printing the harware required.

## WARNING!
> [!CAUTION]
Use this **at your own risk!!** This project contains a script that can pretty much execute whatever command the user wants.  
Do not import other people's configurations, except if you really know what you're doing.  
**Always** manually check the configuration file for malicious commands!

## What you'll need
### Bill of Materials:
1x Arduino UNO (or compatible)  
1x 1.3" OLED 128x64 Display (**SH1106 controller**)  
1x RFID Reader Module (**MFRC522**)  
11x Jumper Wires ~15cm (Female to Male)  
1x USB Cable (type B to type A)
16x 4mm self-tapping M2 Screws  
4x 6mm self-tapping M2 Screws  
NFC NTAG213 25mm 13.56MHz (as many as you need, one per floppy)

### Tools:
Soldering iron  
3D Printer  
A PC running Linux  

## Hardware Assembly  

### Arduino Pinout  

Connect the devices to the arduino as shown below. Note: You will have to cut solder on the RC522 board because of space restrictions, it won't fit the case otherwise. You can use connectors on all other connections (Arduino & OLED module).


> [!CAUTION]  
> Connecting the RC522 board to 5V **WILL fry it!** Don't ask me how I know :)  
> Always double-check that 3.3V goes to RC522 and 5V goes to OLED module.  

RC522 VCC ----- 3.3V  
RC522 GND ---- GND  
RC522 RST ----- 9  
RC522 MISO --- 12  
RC522 MOSI --- 11  
RC522 SCK ----- 13  
RC522 SDA ----- 10  
OLED VCC ------ 5V  
OLED GND ----- GND  
OLED SCL ------ A5  
OLED SDA ------ A4  

###  Case

- Go to **(PlaceHolder MakerWorld URL)** and 3D print the project.  
- Screw the OLED module on the 3D Printed Shell using 4x 4mm screws.  
- Screw the two boards on the 3D Printed PCB Support Piece using 8x 4mm screws.  
- Screw the whole PCB Support to the roof of the case using 4x 4mm screws.  
- Screw the bottom 3D Printed part to the bottom of the shell using 4x 6mm screws.
- Connect the device to the PC, using a USB type-B to type-A cable.

### RFIDisk Floppies

- Use the corresponding plate on the MakerWorld Project.
- Plate 4 is for single disk, plate 5 is for printing 4 disks in one go.
- The printing pauses on layer 7, that's when you go and stick the NFC tags on the designated area. Be careful to center the sticker. The sticker should not touch the walls of the area. Feel free to manually lower the bed using your printer's controls to get a better view/fit your hand.
- When you have placed the sticker(s) press resume. The printer will seal the NFC tags at the next layer.

> [!NOTE]
> You can also use real 3.5" floppy disks and stick the sticker at the center at the bottom (hub).
> If you experience weak signal and/or inconsistencies in reading, the metal surface of the disk is at fault.
> You can try to open carefully the disk and remove the whole disk, and stick the sticker through the hole on the inside.


## Software Installation / Configuration

### Prerequisites
The python script requires psutil and serial modules. Make sure to install them:  

```pip install pyserial psutil```  

Also, you're going to need an Arduino dev environment.  
The arduino sketch requires MFRC522, Adafruit GFX, and Adafruit SH110X libraries.  
Make sure to install them. If using arduino-cli:  

```arduino-cli lib install "Adafruit SH110X" "Adafruit GFX" MFRC522```  

The user should be able to get control of the serial port.  
This means that the user must be in the uucp or dialout group.  

```sudo usermod -a -G dialout $(whoami)```  
```sudo usermod -a -G uucp $(whoami)```  


### Compiling and Uploading the arduino sketch  
If using arduino-cli:  

```arduino-cli compile rfidisk.ino -p /dev/ttyACM0 -b arduino:avr:uno```  
```arduino-cli upload rfidisk.ino -p /dev/ttyACM0 -b arduino:avr:uno```  

> [!WARNING]
> If your setup has another device path for the arduino, replace /dev/ttyACM0 with yours.  

If everything was succesful, the OLED Display should now show a logo (RFIDisk).  


### Configuring rfidisk
Open the rfidisk_config.json file (use any editor you like), and tweak the topmost setting:  

```"serial_port": "/dev/rfidisk",```  

Replace "dev/rfidisk" with your Arduino's actual path (likely /dev/ttyACM0).  
To set up a symlink and use a static custom path like /dev/rfidisk, continue reading.  
You can also change any of the other settings in rfidisk_config.json, according to your preferences.
