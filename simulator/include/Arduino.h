#pragma once
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <type_traits>

#define ARDUINO 10819
#define HIGH 1
#define LOW 0
#define INPUT 1
#define OUTPUT 3
#define INPUT_PULLUP 5
#define PROGMEM
#define F(s) (s)
constexpr double PI = 3.14159265358979323846;
constexpr double TWO_PI = 2 * PI;
constexpr double DEG_TO_RAD = PI / 180;
using byte = uint8_t;
using boolean = bool;
using std::min;
using std::max;
class __FlashStringHelper;
class String : public std::string {
public:
  using std::string::string;
  String(const std::string &s) : std::string(s) {}
  template<class T, std::enable_if_t<std::is_integral_v<T>, int> = 0>
  explicit String(T value) : std::string(std::to_string(value)) {}
};
template<class T> constexpr T constrain(T x, T lo, T hi) { return std::clamp(x, lo, hi); }
inline long map(long x, long a, long b, long c, long d) { return (x-a)*(d-c)/(b-a)+c; }
inline long random(long n) { return n > 0 ? std::rand() % n : 0; }
inline long random(long a, long b) { return a < b ? a + random(b-a) : a; }
inline void randomSeed(unsigned seed) { std::srand(seed); }

#define SIM_IMPORT(n) __attribute__((import_module("bench"), import_name(n)))
extern "C" {
  double sim_time() SIM_IMPORT("time");
  void sim_sleep(unsigned ms) SIM_IMPORT("sleep");
  int sim_touch() SIM_IMPORT("touch");
  void sim_serial(unsigned char c) SIM_IMPORT("serial");
}
inline unsigned long millis() { return static_cast<unsigned long>(sim_time()); }
inline unsigned long micros() { return static_cast<unsigned long long>(sim_time()*1000); }
inline void delay(unsigned long ms) { sim_sleep(ms); }
inline void yield() { sim_sleep(0); }
inline int pinLevels[49] = {};
inline bool backlightOn = true;
inline void pinMode(int p, int mode) { if(p>=0 && p<49 && mode==INPUT_PULLUP) pinLevels[p]=HIGH; }
inline void digitalWrite(int p, int v) {
  if(p>=0 && p<49) pinLevels[p]=!!v;
  if(p==2) backlightOn=v;
}
inline int digitalRead(int p) { return p>=0 && p<49 ? pinLevels[p] : LOW; }
#include "Print.h"
class SerialPort : public Print {
public:
  void begin(unsigned long) {}
  explicit operator bool() const { return true; }
  size_t write(uint8_t c) override { sim_serial(c); return 1; }
};
inline SerialPort Serial;
inline double radians(double degrees) { return degrees * DEG_TO_RAD; }
inline double degrees(double angle) { return angle / DEG_TO_RAD; }
