#pragma once
#include "Adafruit_GFX.h"
constexpr uint16_t TFT_BLACK=0, TFT_WHITE=0xffff, TFT_RED=0xf800, TFT_GREEN=0x07e0,
 TFT_BLUE=0x001f, TFT_YELLOW=0xffe0, TFT_ORANGE=0xfda0, TFT_CYAN=0x07ff,
 TFT_MAGENTA=0xf81f, TFT_NAVY=0x000f, TFT_DARKGREY=0x7bef, TFT_LIGHTGREY=0xd69a,
 TFT_PURPLE=0x780f, TFT_PINK=0xfe19, TFT_DARKGREEN=0x03e0;
constexpr int TFT_WIDTH=240, TFT_HEIGHT=240;
inline uint16_t *activePixels=nullptr;
class TFT_eSPI : public GFXcanvas16 {
public:
  TFT_eSPI() : GFXcanvas16(240,240) { activePixels=getBuffer(); }
  void begin() { activePixels=getBuffer(); }
  void init() { begin(); }
  static uint16_t color565(uint8_t r,uint8_t g,uint8_t b) {
    return ((r&248)<<8) | ((g&252)<<3) | (b>>3);
  }
  int drawString(const char *text,int x,int y) {
    setCursor(x,y); print(text); return strlen(text)*6*textsize_x;
  }
  int drawString(const String &text,int x,int y) { return drawString(text.c_str(),x,y); }
};
