#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
stage=$(mktemp -d)
app="$stage/Roundbench Device.app/Contents"
res="$app/Resources"
mkdir -p "$app/MacOS" "$res/desktop/guest" "$res/qemu/bin" "$res/qemu/share/qemu" "$res/simulator/include" ".sim-cache/swift"
xcrun swiftc -O -parse-as-library -target arm64-apple-macos14 -module-cache-path "$PWD/.sim-cache/swift" desktop/native/{BoardWindow,DeviceApp}.swift -o "$app/MacOS/RoundbenchDevice"
cp desktop/device.py desktop/build_sketch.py "$res/desktop/"
python3 desktop/build_sketch.py examples/TouchDial/TouchDial.ino "$res/desktop/TouchDial.bin.gz"
cp desktop/guest/board.cpp "$res/desktop/guest/"
cp simulator/include/{Wire,TFT_eSPI}.h "$res/simulator/include/"
cp examples/TouchDial/TouchDial.ino "$res/"
cp -X .sim-tools/qemu/bin/qemu-system-xtensa "$res/qemu/bin/"
cp .sim-tools/qemu/share/qemu/esp32s3_rev0_rom.bin "$res/qemu/share/qemu/"
cp desktop/Info.plist "$app/"
codesign --force --sign - "$stage/Roundbench Device.app"
codesign --verify --strict "$stage/Roundbench Device.app"
ditto "$stage/Roundbench Device.app" "$PWD/Roundbench Device.app"

printf "%s\n" "$stage/Roundbench Device.app"
