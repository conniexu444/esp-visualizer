"""Compile the public page's greeting sketch with browser-controlled literals."""
import html
import re

from serve import ROOT, compile_sketch


page = ROOT / "docs"
source = html.unescape(re.search(r'<code id="sketch">(.+?)</code>', (page / "index.html").read_text(), re.S)[1])
# These two literals are the only parts of the sketch the demo lets visitors edit.
assert source.count('screen.print("Hello, world!");') == source.count("screen.setCursor(42, 112);") == 1
adapter = """
extern "C" int greetingByte(int) __attribute__((import_module("demo"), import_name("greetingByte")));
extern "C" int cursorX() __attribute__((import_module("demo"), import_name("cursorX")));
static const char* greeting() {
  static char value[20];
  for (int i = 0; i < 19; ++i) value[i] = greetingByte(i);
  return value;
}
"""
source = source.replace('screen.print("Hello, world!");', "screen.print(greeting());")
source = source.replace("screen.setCursor(42, 112);", "screen.setCursor(cursorX(), 112);")
(page / "hello.wasm").write_bytes(compile_sketch(adapter + source))
