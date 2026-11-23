#include <TFT_eSPI.h>
#include <Wire.h>

TFT_eSPI lcd;
int level = 68;
const uint16_t ink = 0x0843, mint = 0x7FF6, muted = 0x8492;

void label(const char *text, int y, int size, uint16_t color) {
  lcd.setTextSize(size);
  lcd.setTextColor(color);
  lcd.setCursor(120 - strlen(text) * 3 * size, y);
  lcd.print(text);
}

void drawDial() {
  lcd.fillScreen(ink);
  for (int tick = 0; tick <= 60; tick++) {
    float a = (140 + tick * 260.0 / 60) * DEG_TO_RAD;
    int radius = tick % 5 == 0 ? 88 : 95;
    lcd.drawLine(120 + cos(a) * radius, 120 + sin(a) * radius,
                 120 + cos(a) * 104, 120 + sin(a) * 104,
                 tick * 100 <= level * 60 ? mint : 0x31A7);
  }
  label("TOUCH DIAL", 71, 1, muted);
  char value[4];
  snprintf(value, sizeof(value), "%d", level);
  label(value, 94, 6, TFT_WHITE);
  label("PERCENT", 151, 1, mint);
  lcd.fillRoundRect(99, 188, 42, 3, 1, muted);
}

// Read finger count and X from the CST816S touch controller.
int touchedX() {
  Wire.beginTransmission(0x15);
  Wire.write(0x02);
  if (Wire.endTransmission(false) != 0 ||
      Wire.requestFrom(0x15, 3) != 3) return -1;
  int fingers = Wire.read();
  int high = Wire.read(), low = Wire.read();
  return fingers ? ((high & 15) << 8) | low : -1;
}

void setup() {
  Serial.begin(115200);
  Wire.begin(6, 7);
  pinMode(2, OUTPUT);
  digitalWrite(2, HIGH);
  lcd.init();
  lcd.setRotation(0);
  drawDial();
  Serial.println("Touch dial ready. Drag across the display.");
}

void loop() {
  int x = touchedX();
  if (x >= 0) {
    int next = map(constrain(x, 0, 239), 0, 239, 0, 100);
    if (next != level) {
      level = next;
      drawDial();
      Serial.printf("Level = %d%%\n", level);
    }
  }
  delay(16);
}
