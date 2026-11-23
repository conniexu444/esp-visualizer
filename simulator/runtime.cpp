#include <TFT_eSPI.h>
void setup();
void loop();
extern "C" void sketch_setup() { setup(); }
extern "C" void sketch_loop() { loop(); }
extern "C" const uint16_t* pixels() { return backlightOn ? activePixels : nullptr; }
