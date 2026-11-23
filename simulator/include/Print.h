#pragma once
#include <cstdio>
#include <cstdint>
#include <string>
#include <type_traits>
class Print {
public:
  virtual size_t write(uint8_t c) = 0;
  size_t print(const char* s) { size_t n=0; if(s) while(*s) n+=write(*s++); return n; }
  size_t print(const std::string& s) { return print(s.c_str()); }
  size_t print(char c) { return write(c); }
  template<class T, std::enable_if_t<std::is_integral_v<T>, int> = 0>
  size_t print(T n, int base=10) {
    if(base<2 || base>36) base=10;
    using U = std::make_unsigned_t<std::conditional_t<std::is_same_v<T,bool>, int, T>>;
    bool negative=std::is_signed_v<T> && n<0 && base==10;
    U magnitude=negative ? U(0)-U(n) : U(n);
    char buf[70]; char *p=buf+sizeof(buf); *--p=0;
    do { *--p="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"[magnitude%base]; magnitude/=base; } while(magnitude);
    if(negative) *--p='-';
    return print(p);
  }
  size_t print(double n,int digits=2) { char b[96]; snprintf(b,sizeof b,"%.*f",digits,n); return print(b); }
  template<class... Args> size_t printf(const char *fmt,Args... args) {
    int n=snprintf(nullptr,0,fmt,args...); if(n<0) return 0;
    std::string s(n+1,'\0'); snprintf(s.data(),s.size(),fmt,args...); return print(s.c_str());
  }
  template<class... Args> size_t println(Args... args) { return print(args...)+write('\n'); }
  size_t println() { return write('\n'); }
};
constexpr int HEX=16, DEC=10, OCT=8, BIN=2;
