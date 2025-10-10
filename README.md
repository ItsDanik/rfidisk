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
8x 4mm self-tapping M2 Screws  
4x 6mm self-tapping M2 Screws  
NFC NTAG213 25mm 13.56MHz (as many as you need, one per floppy)

### Tools:
Soldering iron  
3D Printer  
A PC running Linux  

## Hardware Assembly  
### Arduino Pinout

Connect the devices to the arduino as shown below. Note: You will have to cut solder on the RC522 board because of space restrictions, it won't fit the case otherwise. You can use connectors on all other connections (Arduino & OLED module).

>RC522 VCC ----- 3.3V  
>RC522 GND ----- GND  
>RC522 RST ----- 9  
>RC522 MISO ---- 12  
>RC522 MOSI ---- 11  
>RC522 SCK ----- 13  
>RC522 SDA ----- 10  
>OLED VCC ------ 5V  
>OLED GND ------ GND  
>OLED SCL ------ A5  
>OLED SDA ------ A4  

