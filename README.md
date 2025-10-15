<img width="1794" height="973" alt="3D" src="https://github.com/user-attachments/assets/7a0db381-44d1-4340-8a02-d670594e7833" />

# 💾 RFIDisk — Physical App Launcher for Linux PC

**RFIDisk** turns RFID tags into *physical shortcuts* that launch games, apps, or scripts when inserted on a retro-styled "floppy drive" reader. Think of it as a cross between an RFID scanner and a USB floppy disk drive.  



https://github.com/user-attachments/assets/157f7cc6-f476-471f-b4b7-5301d1c28b9b


---

## What it is
This project is a combination of hardware and software:  

### Hardware
- An microcontroller device (Arduino), attached to an RFID reader module and an OLED display module, connected to the host machine via USB. It has its own 3D printed case design, resembling an external floppy disk drive.
- 3D Printed "Floppies" (they're not really floppy), with the RFID tag embedded in the print (invisible). Real floppies can be used instead, if you have an abundance of faulty ones.  

### Software
- The software is again a combination of two pieces of software:  
- One running on the arduino (we'll call it firmware).  
- The other one running on the host machine (Linux PC).  
- The two applications talk between them via Serial USB.
- Configuration and Tag Management is done via RFIDisk Manager (GUI App).

---

## How It Works
- Each RFID tag inside the disk corresponds to a command (e.g. `steam steam://rungameid/12345`).
1. When a disk is inserted in the drive, the Arduino firmware identifies it and notifies the host.
2. The Python service looks up the tag’s command in `rfidisk_config.json` and launches it.
3. A notification is shown on the host machine.
4. The OLED display updates in real time, showing metadata of the disk (user-configurable).
5. When the disk is removed from the reader, the application is automatically terminated.

This mode of operation closely resembles a cartridge-based game console system, only you don't have to reboot :)

---

<img src="https://github.com/user-attachments/assets/9dd670ca-56e6-4e30-9336-dc6832b9829a" width="240">

<img src="https://github.com/user-attachments/assets/92fac60e-d8e5-4bd7-88b9-1fdff2cd14ef" width="240">

<img src="https://github.com/user-attachments/assets/b9502485-c848-4b90-ae61-77a5aa62d406" width="240">

<img src="https://github.com/user-attachments/assets/eeecc4b2-6a04-49ed-a520-2e8493fd4019" width="240">

---

### Coming Soon (?)
- Gamescope support
- Decky Loader plugin for Steam Deck integration  
  
---

## WARNING!
> [!CAUTION]
Use this **at your own risk!!** This project contains a script that can pretty much execute whatever command the user wants. Do not import other people's configurations, except if you really know what you're doing. **Always** manually check the configuration file for malicious commands!

> [!IMPORTANT]
This project, including this README, are work in progress. There may be bugs, typos, errors, omissions etc.

---

## What you'll need
### Bill of Materials:

- 1x Arduino UNO (or compatible)  
- 1x 1.3" OLED 128x64 Display (**SH1106 controller**)  
- 1x RFID Reader Module (**MFRC522**)  
- 11x Jumper Wires ~15cm (Female to Male)  
- 1x USB Cable (type B to type A)
- 16x 4mm self-tapping M2 Screws  
- 4x 6mm self-tapping M2 Screws  
- 4x Rubber Feet  
- NFC NTAG213 25mm 13.56MHz (as many as you need, one per floppy)


### Tools:
- Soldering iron  
- 3D Printer  
- A PC running Linux  

---

## Hardware Assembly  

### Arduino Pinout  

Connect the devices to the arduino as shown below. 

> [!WARNING]  
> You will have to cut and solder on the RC522 board because of space restrictions, it won't fit the case otherwise.
> You can use connectors on all other connections (Arduino & OLED module).  

> [!CAUTION]  
> Connecting the RC522 board to 5V **WILL fry it!** Don't ask me how I know :)  
> Always double-check that 3.3V goes to RC522 and 5V goes to OLED module.  

```
RC522 VCC --- 3.3V  Arduino  
RC522 GND ---- GND  Arduino  
RC522 RST ------ 9  Arduino  
RC522 MISO ---- 12  Arduino  
RC522 MOSI ---- 11  Arduino  
RC522 SCK ----- 13  Arduino  
RC522 SDA ----- 10  Arduino  
 OLED VCC ----- 5V  Arduino  
 OLED GND ---- GND  Arduino  
 OLED SCL ----- A5  Arduino  
 OLED SDA ----- A4  Arduino  
```

###  Case

- Go to [https://makerworld.com/en/models/1875124-rfidisk-drive-disk](https://makerworld.com/en/models/1875124-rfidisk-drive-disk) and 3D print the project.  
- Screw the OLED module on the 3D Printed Shell using 4x 4mm screws.  
- Screw the two boards on the 3D Printed PCB Support Piece using 8x 4mm screws.  
- Screw the whole PCB Support to the roof of the case using 4x 4mm screws.  
- Screw the bottom 3D Printed part to the bottom of the shell using 4x 6mm screws.
- Stick the four rubber feet to the bottom of the case.
- Connect the device to the PC, using a USB type-B to type-A cable.

### RFIDisk Floppies

- Use the corresponding plate on the MakerWorld Project.
- Plate 4 is for single disk, plate 5 is for printing 4 disks in one go.
- The printing pauses on layer 7, that's when you go and stick the NFC tags on the designated area.
  Be careful to center the sticker. The sticker should not touch the walls of the area. Feel free
  to manually lower the bed using your printer's controls to get a better view/fit your hand.
- When you have placed the sticker(s) press resume. The printer will seal the NFC tags at the next layer.

> [!NOTE]
> You can also use real 3.5" floppy disks and stick the sticker at the center at the bottom (hub).
> If you experience weak signal and/or inconsistencies in reading, the metal surface of the disk is at fault.
> You can try to open carefully the disk and remove the whole disk, and stick the sticker through the hole on the inside.

---

## Software Installation / Configuration

### Project File Structure
This project consists of 6 files:  
```
- License             | Standard GNU GPL3.0 License  
- README.md           | What you're reading now.  
- floppy.png          | The icon that is being displayed in the desktop notifications.  
- install.sh          | Automatic installation script. You need to chmod +x it before you run it.  
- rfidisk.ino         | The arduino firmware. Written in C++. We will compile and upload this to the Arduino.  
- rfidisk.py          | The host software, running on our host machine. Wtieen in Python. This does the talking with the Arduino.  
- rfidisk_config.json | This is the configuration file for the Python script. It also stores the RFID Tag database.  
- rfidisk_tags.json   | This is the RFID Tag database. Edit this file to configure RFID Tag behaviour.  
- rfidisk-manager.py  | A simple GUI manager that simplifies new tag entry and editing/removal of existing Tags.  
```

---

## Download rfidisk
From ~/ or any subdirectory, type:  
```
git clone https://github.com/ItsDanik/rfidisk.git
cd rfidisk
```
>[!WARNING]
>It is suggested that you choose your home directory or any subdirectory in that folder!
>This is to ensure correct file permissions and save a lot of trouble.

---

## Installation using install script  
As of version 0.85 and later, there is an install script that can (hopefully) install everything with minimal user input.  
WARNING! Everything is beta, USE AT YOUR OWN RISK!!!  

```
chmod +x ./install.sh
./install.sh
```

## Updating RFIDisk
- From the install directory: 
```
git pull https://github.com/ItsDanik/rfidisk.git
chmod +x ./install.sh
./install.sh
```
  
Log out and back in, or reboot. If everything went smoothly and you see "Ready/Insert Disk" on the device's OLED screen, congratulations!  

> [!NOTE]
> There is a 10 second delay in launching the app during boot. This is on purpose to ensure serial bus has settled and environment is set.  
> However, on some setups, there may be some instability (a couple of resets of the arduino) as the system enumerates the buses during boot.
> Give it a minute after a fresh boot/reboot and try again once the OLED screen consistently reads "Insert Disk".  

Skip to the "Configuring RFIDisk" section.  

## Uninstalling RFIDisk
- From the install directory:
```
./install.sh --uninstall
```

The app now will not launch on next login, and the RFID Manager is removed from the start menu. Your settings and Tag Database remains saved.  
To remove everything (you will lose all your config!):  

```
cd ..
rm -rf rfidisk
```

---
## Manual Installation
If the install scripts fails, or you don't trust it, here are step by step instructions for manual installation of RFIDisk.  

### Prerequisites
The python script requires psutil and serial modules. Make sure to install them:  

```pip install pyserial psutil```  

Also, you're going to need an Arduino dev environment. In this example we will use code-oss & arduino-cli.  
The arduino sketch requires MFRC522, Adafruit GFX, and Adafruit SH110X libraries.  
Make sure to install them. If using arduino-cli:  

```arduino-cli lib install "Adafruit SH110X" "Adafruit GFX" MFRC522```  

The user should be able to get control of the serial port.  
This means that the user must be in the uucp or dialout group.  

```
sudo usermod -a -G dialout $(whoami)
sudo usermod -a -G uucp $(whoami)
```  

---

### Compiling and Uploading the arduino sketch  
If using arduino-cli, go into the directory of the project and type:  

```
arduino-cli compile rfidisk.ino -p /dev/ttyACM0 -b arduino:avr:uno
arduino-cli upload rfidisk.ino -p /dev/ttyACM0 -b arduino:avr:uno
```  

> [!WARNING]
> If your setup has another device path for the arduino, replace /dev/ttyACM0 with yours.  

If everything was succesful, the OLED Display should now show a logo (RFIDisk) and firmware version.  
To start RFIDisk manually, type:  
```
python3 ./rfidisk.py
```

---

## RFIDisk Manager
This is the app that you interacti with to configure and manage RFIDisk.  
Open RFIDisk Manager via start menu.  

<img width="739" height="721" alt="RFIDisk Manager" src="https://github.com/user-attachments/assets/9cfbc301-d578-4767-be6c-4864a9980690" />


### Configuring rfidisk
Open RFIDisk Manager (via start menu) and click on the Configuration Tab:  

<img width="444" height="328" alt="RFIDisk Manager Settings" src="https://github.com/user-attachments/assets/b68884b3-0da5-42a6-baf0-b7ca180318ca" />


```Serial Port: /dev/ttyACM0```  

This is likely already correct. In case your device has a different path, enter it here.  
If have have more serial devices and want to set up a udev rule with a static custom path like /dev/rfidisk, to avoid mixups, keep reading.  

```Removal Delay (seconds): 0.0```  

This ensures that a disk is not ejected by mistake. If you reinsert the disk during that time, the removal is not registered, and the app is not terminated.  
```Desktop Notifications```  

This enabled desktop notifications when a disk is inserted. Disable it if you want to disable desktop notifications.   

```Notification Timeout (ms): 8000```  

This works only when desktop_notifications is true. Determines the amount of time (in ms) that the notification will be displayed for.  

```"Auto Launch Manager```

When this is enabled, RFIDisk Manager automatically gets launched when the user inserts a new (or unconfigured) Tag.  

### Tag Management  
You can manage your Tag entries in this tab (add, remove, edit).  
Changes take effect immediately. Keep reading for details.  

---

## Using RFIDisk

RFIDisk should start automatically upon login if you installed it using the script.  

- The app should initialize, and on the OLED screen of the device you should be able to see a "Ready/Insert Disk" message. Insert a floppy into the drive.
- RFIDisk Manager should automatically pop open with a new entry already created and the Tag ID field automatically completed. Remove the disk now and edit the followind fields:  

<img width="378" height="262" alt="RFIDisk Manager New Tag" src="https://github.com/user-attachments/assets/38867cf5-7aa0-497f-9bf9-6268a00593ee" />

The Tag ID ("a1b2c3d4") at the top will be different and is the unique ID of the NFC tag. Don't touch this value.  
Launch command: Type here the command you want to execute when this disk is inserted. You can also browse for the executable.  
Display Line 1-4: These are the four lines of text that will be displayed on the OLED screen when this disk gets inserted.  
Usually the first two lines are used for the title of the application, Line 3 for release year and Line 4 for Developer/Publisher.  
Terminate command: Useful when launching Steam games (keep reading).  

> [!NOTE]
> - "Display Line 1" and "Display Line 2" get truncated at 20 characters.  
> - "Display Line 3" and "Display Line 4" get truncated at 14 characters (to make room for the icon).

Here is an example of an entry, properly configured and formatted:  

<img width="458" height="215" alt="RFIDisk Manager Full Tag" src="https://github.com/user-attachments/assets/12a1846b-84c0-450a-9090-86f507bb3483" />

>[!TIP]
>We can leave the "Terminate Command" blank for all native linux titles. The script is aware of the whole process tree and can sucessfully track and terminate most applications.  

Click on "Save Changes", quit the manager and insert the disk. The application should now launch!  
Remove the disk and the application closes.  
Repeat the configuration proccess for as many disks as you need.  

---

## Post-Installation optimizations

### Create udev rules for static device path
If you have more than one serial devices, they might get mixed up if you rely on /dev/ttyACM0 path.  
We need to create a unique device path for the arduino.  
We'll create two udev rules, let's start with one that ensures USB serial ownership:  
```
sudo nano /etc/udev/rules.d/90-tty-acm.rules  
```
Paste this into the empty new file:  
```
SUBSYSTEM=="tty", KERNEL=="ttyACM[0-9]*", GROUP="uucp", MODE="0660", TAG+="uaccess"
```
Save the file (Ctrl-X, y)  

Now, another to set the symlink:  
```
sudo nano /etc/udev/rules.d/99-custom-serial.rules
```
Paste this into the empty new file:  
```
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0043", \
  SYMLINK+="rfidisk", GROUP="uucp", MODE="0660", TAG+="uaccess"
```
Save the file (Ctrl-X, y)

To apply:  
```
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo udevadm settle
```
Unplug the RFIDisk drive and plug it back in. You should now see:  
```
ls -l /dev/rifidisk
```

If successful, remember to update the rfidisk_config.json file:  
```
"serial_port": "/dev/rfidisk",
```


---

## Bugs / Quirks:
### Proton Quirks
When an application is launched via proton (ie most Steam games), for some reason the USB ports  
on the host machine get reset. That means that the arduino resets. This is a known issue with  
Proton, you can check it out [here](https://github.com/ValveSoftware/Proton/issues/6927).  
To combat this, as a workaround, an overly-complex connection recovery routine has been implemented,  
to avoid double launching of an app, and double notifications etc. It seems to be working ok, but  
it is a hack. If anyone finds a better way to handle this, like prevent the USB device from disconnecting  
when Proton initializes, please let me know.  

---

### Steam Games
To launch steam games, in the "command" field of the entry, use:  

```steam steam://rungameid/1234567```

where "1234567" is the gameid of the game you want to play. To find the gameid, just look at the url address of the Store page of the game. For example, Cyberpunk 2077's store page URL is  

```https://store.steampowered.com/app/1091500/Cyberpunk_2077/```  

This means, that the gameid of Cyberpunk 2077 is 1091500. But also, terminating games that were launched cannot be automated. We have to manually specify a "terminate" command, that's what this field is reserved for in rfid_config.json entries. To determine the command:  

- Run the game manually
- Open a proccess monitor (htop, btop etc)
- Find the name of the process
- The terminate command is "killall (name of the process)"
In the example of Cyberpunk 2077, the proccess name is "GameThread".

After all this work, now we can build a Steam game entry:

<img width="380" height="217" alt="2025-10-14T18:30:53,591035808+03:00" src="https://github.com/user-attachments/assets/3febd89b-1f19-4c17-a427-bbf8b1351b25" />


---

### TODO/Ideas List
- Find a solution for the known issue with Proton (USB Momentarily Disconnects and Arduino reboots)  
- Explore GameScope support (test game launching and make use of GameScope notification system)  
- Potentially package it as a DeckyLoader plugin?
- Make RFIDisk manager themable (colors) with pre-installed light theme, dark theme, catppuccin mocha theme:  
  A simple dropdown menu in RFIDisk manager selects theme. Themes should be located in rfidisk-manager-themes.json  

