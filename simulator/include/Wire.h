#pragma once
#include "Arduino.h"
// CST816S point-count and coordinate registers on the shared display I2C bus.
class TwoWire {
  int address=0, reg=0, remaining=0, point=0;
  bool firstByte=false;
public:
  bool begin(int=6,int=7,unsigned=0) { return true; }
  void beginTransmission(int addr) { address=addr; firstByte=true; }
  size_t write(uint8_t v) { if(firstByte) reg=v; firstByte=false; return 1; }
  int endTransmission(bool=true) { return address==0x15 ? 0 : 2; }
  int requestFrom(int addr,int count,bool=true) {
    remaining=addr==0x15 ? count : 0; point=sim_touch(); return remaining;
  }
  int available() const { return remaining; }
  int read() {
    if(!remaining) return -1;
    --remaining;
    switch(reg++) {
      case 2: return (point>>16)&1;
      case 3: case 5: return 0;
      case 4: return (point>>8)&255;
      case 6: return point&255;
      default: return 0;
    }
  }
};
inline TwoWire Wire;
