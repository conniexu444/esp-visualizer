#include <TFT_eSPI.h>
#include <Wire.h>

TFT_eSPI screen;
struct BackgroundColor {
  uint16_t value;
  const char *name;
};
const BackgroundColor colors[] = {
  {TFT_BLACK, "black"}, {TFT_NAVY, "navy"}, {TFT_PURPLE, "purple"},
  {TFT_DARKGREEN, "dark green"}, {TFT_RED, "red"}
};
const int colorCount = sizeof(colors) / sizeof(colors[0]);
int colorIndex = 0;
unsigned long tapCount = 0;
bool wasTouched = false;

void drawGreeting() {
  screen.fillScreen(colors[colorIndex].value);
  screen.setTextColor(TFT_WHITE);
  screen.setTextSize(2);
  screen.setCursor(42, 112);
  screen.print("Hello, world!");
}

// Read the CST816S finger-count register. A failed read leaves the last state intact.
int fingerCount() {
  Wire.beginTransmission(0x15);
  Wire.write(0x02);
  if (Wire.endTransmission(false) != 0 || Wire.requestFrom(0x15, 1) != 1) {
    return -1;
  }
  return Wire.read();
}

void setup() {
  Serial.begin(115200);
  Wire.begin(6, 7);
  pinMode(2, OUTPUT);
  digitalWrite(2, HIGH);
  screen.init();
  drawGreeting();
}

void loop() {
  int fingers = fingerCount();
  if (fingers >= 0) {
    bool touched = fingers > 0;
    if (touched && !wasTouched) {
      colorIndex = (colorIndex + 1) % colorCount;
      drawGreeting();
      ++tapCount;
      Serial.printf("Tap %lu - background changed to %s\n", tapCount, colors[colorIndex].name);
    }
    wasTouched = touched;
  }
  delay(10);
}
