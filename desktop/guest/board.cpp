// UART1 carries the emulator's display address and packed touch reports.
// UART0 remains available to the sketch as the normal Arduino Serial console.
#include <Arduino.h>
#include "RoundbenchLCD.h"
#include <esp_heap_caps.h>
extern void deviceSketchSetup();
extern void deviceSketchLoop();
static uint32_t lastTouch;
uint32_t sim_touch() {
  while (Serial1.available() >= 4) {
    if (Serial1.read() != 0xfa) continue;
    int down = Serial1.read(), x = Serial1.read(), y = Serial1.read();
    lastTouch = ((down == 1) << 16) | (x << 8) | y;
  }
  return lastTouch;
}
void setup() {
  Serial1.begin(115200, SERIAL_8N1, 18, 17);
  deviceSketchSetup();
}
void loop() {
  static uint16_t *lastBuffer = nullptr;
  if (activePixels && activePixels != lastBuffer) {
    Serial1.printf("LCD %08lx\n", (unsigned long)activePixels);
    lastBuffer = activePixels;
  }
  deviceSketchLoop();
}
