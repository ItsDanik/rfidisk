<img width="1794" height="973" alt="3D" src="https://github.com/user-attachments/assets/7a0db381-44d1-4340-8a02-d670594e7833" />

# 💾 RFIDisk — Physical App Launcher for Linux PC

**RFIDisk** turns RFID tags into *physical shortcuts* that launch games, apps, or scripts when inserted on a retro-styled "floppy drive" reader.  
Think of it as a cross between an RFID scanner and a USB floppy disk drive.

---

### How It Works
- Each RFID tag inside the disk corresponds to a command (e.g. `steam steam://rungameid/12345`).
1. When a disk is inserted on the reader, the Arduino firmware identifies it and notifies the host.
2. The Python service looks up the tag’s command in `rfidisk_config.json` and launches it.
3. A notification is shown on the host machine.
4. The OLED display updates in real time.
5. When the disk is removed from the reader, the application is terminated.

---

<img src="https://github.com/user-attachments/assets/9dd670ca-56e6-4e30-9336-dc6832b9829a" width="240">

<img src="https://github.com/user-attachments/assets/92fac60e-d8e5-4bd7-88b9-1fdff2cd14ef" width="240">

<img src="https://github.com/user-attachments/assets/b9502485-c848-4b90-ae61-77a5aa62d406" width="240">

<img src="https://github.com/user-attachments/assets/eeecc4b2-6a04-49ed-a520-2e8493fd4019" width="240">

---

### Coming Soon (?)
- Gamescope support
- Decky Loader plugin for Steam Deck integration  
- GUI configurator for easy tag management  
- Custom icons loaded dynamically from the host  

---

## WARNING!
> [!CAUTION]
Use this **at your own risk!!** This project contains a script that can pretty much execute whatever command the user wants.  
Do not import other people's configurations, except if you really know what you're doing.  
**Always** manually check the configuration file for malicious commands!

> [!IMPORTANT]
This project, including this README, are work in progress. There may be bugs, errors, omissions etc.

---

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

---

## Hardware Assembly  

### Arduino Pinout  

Connect the devices to the arduino as shown below. Note: You will have to cut solder on the RC522 board because of space restrictions, it won't fit the case otherwise. You can use connectors on all other connections (Arduino & OLED module).


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

---

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

If everything was succesful, the OLED Display should now show a logo (RFIDisk).  

---

### Configuring rfidisk
Open the rfidisk_config.json file (use any editor you like), and tweak the topmost setting:  

```"serial_port": "/dev/rfidisk",```  

Replace "dev/rfidisk" with your Arduino's actual path (likely /dev/ttyACM0).  
To set up a udev rule with a static custom path like /dev/rfidisk, keep reading.  

You can also change any of the other settings in rfidisk_config.json, according to your preferences.  
Everything now should be set to go.  

---

## Using RFIDisk

To start RFIDisk go to the directory of the project and type:  

```python3 rfidisk.py```  

The app should initialize, and on the OLED screen of the device you should be able to see a "Ready/Insert Disk" message.  
Insert a floppy into the drive. A new entry should automatically be created in rfidisk_config.json.  
Remove the disk, open the file and edit the last entry:  

```
"a1b2c3d4": {
"command": "",  
"line1": "new entry",  
"line2": "configure me",  
"line3": "edit rfidisk_config.json",  
"line4": "a1b2c3d4",  
"terminate": ""
}
```

The "a1b2c3d4" at the top will be different and is the unique ID of the NFC tag. Don't touch this value.  
"command": Type here the command you want to execute when this disk is inserted.  
"line1": This is the first line that will be drawn on the OLED screen. Usually the first two rows should be used for the title of the application.  
"line2": This is the second line that will be drawn on the OLED screen.  
"line3": Third line, you can use it for whatever you want, for example year of release.  
"line4": Fourth line, you can use it for developer or publisher etc.  

Here is an example of an entry, properly configured and formatted:  

```
"1d0dc0070d1080": {
      "command": "/usr/bin/gzdoom -iwad /home/user/DOOM.WAD",
      "line1": "DOOM",
      "line2": "GZDoom Engine",
      "line3": "1993",
      "line4": "id Software",
      "terminate": ""
    },
```
> [!TIP]
> It is recommended that can use an editor like code, which constantly updates on the file.
> That way you don't have to reload every time you insert a new disk, you can leave it open
> and prepare multiple disks in one go that way. Also the usage of such an editor ensures
> proper json formatting.

Save the file, and insert the disk. The application should now launch! Remove the disk and the application closes.  
Repeat the configuration proccess for as many disks as you need.

---

## Post-Installation optimizations

### Create udev rules for static device path
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

### Make the python script executable
We can make the script directly executable.  
To do this, go to the project directory and type: 
```
chmod +x rfidisk.py
```
Now, you can directly execute the script without having to specify "python":  
```
./rfidisk.py
```

---

### Make the script run automatically upon login
We can make the script run silently in the background eveytime we login, by  
creating a systemd user service:  

```
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/rfidisk.service
```

Paste this into the empty file:  

```
[Unit]
Description=RFIDisk Arduino Monitor Script
After=default.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/path/to/rfidisk/rfidisk.py
WorkingDirectory=/home/path/to/rfidisk
Restart=on-failure
ExecStartPre=/bin/sleep 1

[Install]
WantedBy=default.target
```
And replace the /home/path/to/rfidisk/ with your actual path where rfidisk resides.  
Be sure to replace both instances (ExecStart and WorkingDirectory).  
Save the file (Ctrl+X, y)  

To apply the changes:  
```
systemctl --user daemon-reload
systemctl --user enable rfidisk.service
systemctl --user start rfidisk.service
```
Check if it's running:
```
systemctl --user status rfidisk.service
```  

Reboot to test!  

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
where "1234567" is the gameid of the game you want to play.  
To find the gameid, just look at the url address of the Store  
page of the game. For example, Cyberpunk 2077's store page URL is  
```https://store.steampowered.com/app/1091500/Cyberpunk_2077/```  
This means, that the gameid of Cyberpunk 2077 is 1091500.  
But also, terminating games that were launched cannot be automated. We have to manually specify a  
"terminate" command, that's what this field is reserved for in rfid_config.json entries.  
To determine the command:  
- Run the game manually
- Open a proccess monitor (htop, btop etc)
- Find the name of the process
- The terminate command is "killall (name of the process)"
In the example of Cyberpunk 2077, the proccess name is "GameThread".

After all this work, now we can build a Steam game entry:
```
"1d0abf070d1080": {
      "command": "steam steam://rungameid/1091500",
      "line1": "Cyberpunk 2077",
      "line2": "Phantom Liberty",
      "line3": "2020-2023",
      "line4": "CDProjectRed",
      "terminate": "killall GameThread"
    },
```

---

### TODO/Ideas List
- Find a solution for the known issue with Proton (USB Momentarily Disconnects and Arduino reboots)  
- Explore GameScope support (test game launching and make use of GameScope notification system)  
- Potentially package it as a DeckyLoader plugin?  
- Migrate icons from the arduino memory to the host PC. This way we can transmit any number of icons
  to a fixed 32x32 buffer using serial, not worry about Arduino RAM, and also allow for custom icons.
