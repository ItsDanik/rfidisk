#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>

#define RST_PIN 9
#define SS_PIN 10

Adafruit_SH1106G display(128, 64, &Wire, -1);
MFRC522 mfrc522(SS_PIN, RST_PIN);

bool tagPresent = false;
String lastTagUid = "";
const char version[] PROGMEM = "v0.82";

const unsigned char rfidisk_logo[] PROGMEM = {
0xfc, 0x7f, 0x77, 0xe1, 0xc0, 0x1c, 0x00, 0xe6, 0x70, 0x77, 0x31, 0xc0, 0x1c, 0x00, 0xe6, 0x70, 
	0x77, 0x18, 0x00, 0x1c, 0x00, 0xe7, 0x70, 0x77, 0x19, 0xc7, 0x1c, 0xc0, 0xe6, 0x70, 0x77, 0x19, 
	0xcd, 0x9d, 0x80, 0xe6, 0x7f, 0x77, 0x19, 0xdc, 0x1d, 0x80, 0xfc, 0x70, 0x77, 0x19, 0xcf, 0x1f, 
	0x00, 0xec, 0x70, 0x77, 0x19, 0xc7, 0x9f, 0x00, 0xe4, 0x70, 0x77, 0x19, 0xc1, 0x9f, 0x80, 0xe6, 
	0x70, 0x77, 0x31, 0xd9, 0x9d, 0x80, 0xe7, 0x70, 0x77, 0xe1, 0xcf, 0x1c, 0xc0
};

// 'icon_floppy', 24x24px
const unsigned char floppy_icon[] PROGMEM = {
	0x7f, 0xff, 0xfe, 0x40, 0x00, 0x02, 0x47, 0xff, 0xe2, 0x57, 0xff, 0xea, 0x47, 0xff, 0xe2, 0x47, 
	0xff, 0xe2, 0x47, 0xff, 0xe2, 0x47, 0xff, 0xe2, 0x47, 0xff, 0xe2, 0x47, 0xff, 0xe2, 0x47, 0xff, 
	0xe2, 0x47, 0xff, 0xe2, 0x43, 0xff, 0xc2, 0x40, 0x00, 0x02, 0x40, 0x00, 0x02, 0x41, 0xff, 0x82, 
	0x41, 0x1f, 0x82, 0x41, 0x1f, 0x82, 0x41, 0x1f, 0x82, 0x41, 0x1f, 0x82, 0x41, 0x1f, 0x82, 0x21, 
	0xff, 0x82, 0x10, 0x00, 0x02, 0x0f, 0xff, 0xfe
};

// 'icon_steam', 24x24px
const unsigned char steam_icon[] PROGMEM = {
	0x00, 0x7e, 0x00, 0x01, 0xff, 0x80, 0x07, 0xff, 0xe0, 0x0f, 0xff, 0xf0, 0x1f, 0xfc, 0x38, 0x3f, 
	0xf0, 0x0c, 0x3f, 0xf3, 0xcc, 0x7f, 0xe4, 0x26, 0x7f, 0xe4, 0x26, 0xff, 0xe4, 0x27, 0xff, 0xc4, 
	0x27, 0x7f, 0xc3, 0xcf, 0x0f, 0x80, 0x0f, 0x02, 0x00, 0x3f, 0x00, 0xc3, 0xff, 0x00, 0x27, 0xfe, 
	0x60, 0x2f, 0xfe, 0x38, 0x2f, 0xfc, 0x3d, 0xdf, 0xfc, 0x1e, 0x3f, 0xf8, 0x0f, 0xff, 0xf0, 0x07, 
	0xff, 0xe0, 0x01, 0xff, 0x80, 0x00, 0x7e, 0x00
};

void setup() {
  Serial.begin(9600);
  
  // Initialize display
  if (!display.begin(0x3C, false)) {
    // If display fails, continue anyway
  }

  // Show boot logo
  display.clearDisplay();
  display.drawBitmap(39, 28, rfidisk_logo, 50, 11, SH110X_WHITE);
  display.setTextColor(SH110X_WHITE);
  display.setCursor(98, 56);
  display.print((const __FlashStringHelper*)version);
  display.display();
  delay(800);
  
  // Initialize RFID
  SPI.begin();
  mfrc522.PCD_Init();

  Serial.println("OK");
}

void updateDisplay(const char* line1, const char* line2, const char* line3, const char* line4, byte iconType) {
  display.clearDisplay();
  display.setTextColor(SH110X_WHITE);
  display.setTextSize(1);

  // Top section (line1 and line2)
  display.setCursor(5, 8);
  display.print(line1);
  
  display.setCursor(5, 20);
  display.print(line2);

  // Horizontal divider line
  display.drawLine(0, 31, 128, 31, SH110X_WHITE);

  // Bottom section (line3 and line4)
  display.setCursor(5, 40);
  display.print(line3);
  
  display.setCursor(5, 52);
  display.print(line4);

  // Draw icon in bottom right based on iconType - UPDATED for 24x24
  if (iconType > 0) {
    // Position: 128-24=104 (right edge), 64-24=40 (bottom edge) - centered better
    switch(iconType) {
      case 1: // Floppy disk icon
        display.drawBitmap(100, 36, floppy_icon, 24, 24, SH110X_WHITE);
        break;
      case 2: // Steam icon
        display.drawBitmap(100, 36, steam_icon, 24, 24, SH110X_WHITE);
        break;
      // Add more cases for different icon types later
      default:
        break;
    }
  }

  display.display();
}

String getTagUid() {
  String uid = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    if (mfrc522.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(mfrc522.uid.uidByte[i], HEX);
  }
  return uid;
}

bool isTagPresent() {
  // Reset the reader
  mfrc522.PCD_Init();
  delay(10);
  
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return false;
  }
  
  if (!mfrc522.PICC_ReadCardSerial()) {
    return false;
  }
  
  return true;
}

void loop() {

  // Process serial commands immediately
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    if (cmd.startsWith("D|")) {
      // Parse display command: D|line1|line2|line3|line4|iconType
      int p1 = cmd.indexOf('|');
      int p2 = cmd.indexOf('|', p1 + 1);
      int p3 = cmd.indexOf('|', p2 + 1);
      int p4 = cmd.indexOf('|', p3 + 1);
      int p5 = cmd.indexOf('|', p4 + 1);
      
      if (p1 != -1 && p2 != -1 && p3 != -1 && p4 != -1 && p5 != -1) {
        String line1 = cmd.substring(p1 + 1, p2);
        String line2 = cmd.substring(p2 + 1, p3);
        String line3 = cmd.substring(p3 + 1, p4);
        String line4 = cmd.substring(p4 + 1, p5);
        byte iconType = cmd.substring(p5 + 1).toInt();
        
        updateDisplay(line1.c_str(), line2.c_str(), line3.c_str(), line4.c_str(), iconType);
      }
    }
  }

  // Check RFID
  bool currentTagPresent = isTagPresent();
  
  if (currentTagPresent && mfrc522.uid.size > 0) {
    String currentUid = getTagUid();
    
    if (!tagPresent) {
      // New tag detected
      Serial.print("ON:");
      Serial.println(currentUid);
      tagPresent = true;
      lastTagUid = currentUid;
    } else if (currentUid != lastTagUid) {
      // Different tag detected
      Serial.print("OF:");
      Serial.println(lastTagUid);
      Serial.print("ON:");
      Serial.println(currentUid);
      lastTagUid = currentUid;
    }
    mfrc522.PICC_HaltA();
  } else if (tagPresent && !currentTagPresent) {
    // Tag was present but now it's gone
    Serial.print("OF:");
    Serial.println(lastTagUid);
    tagPresent = false;
    lastTagUid = "";
  }

  delay(200);
}
