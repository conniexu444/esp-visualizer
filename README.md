# Roundbench

## Flash a sketch to the Waveshare ESP32-S3-Touch-LCD-1.28

### One-time Arduino IDE setup

1. Open **Boards Manager** in Arduino IDE. Search for **esp32 by Espressif Systems**, select **2.0.12**, and click **Install**. This version worked on the physical round display. The same display sketch uploaded with 3.3.12 but left the screen dark. [Waveshare Arduino setup guide](https://docs.waveshare.com/ESP32-S3-Touch-LCD-1.28/Arduino)
2. Download and unzip the board's example package. Inside `Arduino/libraries/`, copy both **`TFT_eSPI` (2.5.34)** and **`TFT_eSPI_Setups`** into your Arduino sketchbook's `libraries` folder. The second folder contains the driver and pin settings for this board. [Download the Waveshare example ZIP](https://files.waveshare.com/wiki/ESP32-S3-Touch-LCD-1.28/ESP32-S3-Touch-LCD-1.28-Demo.zip)
3. Reopen Arduino IDE. On a Mac using the default sketchbook location, the two files should appear at these paths.

   ```text
   ~/Documents/Arduino/libraries/TFT_eSPI/TFT_eSPI.h
   ~/Documents/Arduino/libraries/TFT_eSPI_Setups/Setup207_GC9A01.h
   ```

### Upload and check the touch example

1. In Arduino IDE, open [HelloColors.ino](examples/HelloColors/HelloColors.ino). This is the sketch Arduino compiles for the device. The ESP32 board package supplies the `Wire` library used to read taps.
2. Connect the board with a USB data cable. Under **Select Board → Select other board and port…**, choose **ESP32S3 Dev Module** and the port that appears when you plug in the board.
3. Click **✓ Verify** to compile. When you're ready to replace the program on the board, click **→ Upload**. After the upload is verified, the board restarts and displays “Hello, world!”.
4. Open **Tools → Serial Monitor**, select **115200 baud**, and tap the screen. The first tap turns the background navy and prints `Tap 1 - background changed to navy`.

## Mac device emulator

The round panel displays the guest framebuffer. Use **Scale** to change its size, the command panel to run your program, and the inspector underneath to edit sketches or read UART0.

Build and open **Roundbench Device.app** using the steps below. It starts with a prebuilt touch-dial firmware image. **Open…** accepts an Arduino sketch or a merged ESP32-S3 flash image. For a sketch, select **Build and run** to compile with the locally installed Arduino CLI, ESP32 core, and libraries. The **Sketch** tab includes an editor and **Save sketch…**. For firmware, use the export ending in **.merged.bin** that includes the bootloader, partition table, and app. **Reset** restarts the emulated device and **Stop** ends the session. The UART0 console supports sending and receiving text.

The Mac app boots actual Xtensa firmware using Espressif QEMU. Each launch uses a temporary flash copy. For supported TFT_eSPI sketches the emulator build redirects graphics and CST816S coordinate reads through a board adapter. The round display shows the guest's RGB565 framebuffer and a click or drag sends coordinates back to the firmware. The adapter reserves UART1. An ordinary imported hardware image can use the CPU and UART console; rendering its unmodified GC9A01A SPI driver and reading its physical CST816S, IMU, or radios are outside this model.

The packaged demo has been checked for boot, UART output, interactive touch, framebuffer changes and reset. The machine backend is documented in [Espressif's QEMU guide](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/tools/qemu.html).

### Build the desktop app on Apple Silicon

Use macOS 14 or later with Xcode command-line tools, Python 3, Arduino CLI, the Espressif ESP32 Arduino core (tested with 3.3.12), and the Adafruit GFX and BusIO libraries. Install Espressif’s macOS QEMU dependencies listed in its [ESP32-S3 setup guide](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/tools/qemu.html). From the project directory:

```sh
mkdir -p .sim-tools
curl -fL https://github.com/espressif/qemu/releases/download/esp-develop-9.2.2-20260417/qemu-xtensa-softmmu-esp_develop_9.2.2_20260417-aarch64-apple-darwin.tar.xz -o .sim-tools/qemu-xtensa.tar.xz
echo 'bb8c15810565d3df1665dc34962430885e11bc95575b228fb44698146be1e9d6  .sim-tools/qemu-xtensa.tar.xz' | shasum -a 256 -c - && tar -xJf .sim-tools/qemu-xtensa.tar.xz -C .sim-tools
desktop/package.sh
open "Roundbench Device.app"
```

Packaging compiles the touch-dial demo from its Arduino source.

## Browser sketch preview

A local sketch workbench for the Waveshare ESP32-S3-Touch-LCD-1.28. Double-click **Open Visualizer.command** in Finder. Keep its Terminal window open while working. After setup the visualizer runs offline, including with the board unplugged.

Drag across the touch-dial demo. The dial and Serial monitor show the value calculated by the running C++ sketch. Select **Open sketch** to load a single .ino file, or edit the source in place. Use **Run sketch** (⌘ Enter) to compile and restart, and **Stop sketch** to halt it even inside a delay or an infinite loop. Use **Save .ino** to export the editor contents. The browser also keeps the last draft locally.

## Compatibility

Sketches run as WebAssembly with Arduino setup() and loop() entry points. Use explicit declarations when calling functions defined later in the file. Supported interfaces include common TFT_eSPI drawing primitives, classic text, RGB565 colors, rotation, Serial.print/println/printf, millis/micros/delay and the Wire calls needed to read CST816S finger count and coordinates at address 0x15. The screen uses a round mask over a 240 × 240 framebuffer. The example includes the physical board's backlight and I2C pins.

This is a display and touch preview. Wi-Fi, Bluetooth, QMI8658 motion sensing, flash, RTOS scheduling, arbitrary ESP-IDF firmware, MicroPython and LVGL require other runtimes or hardware testing. Timing follows the laptop clock. An unsupported header or interface can produce a compiler error. Build for the actual ESP32-S3 with the appropriate libraries and Waveshare TFT_eSPI setup before flashing.

Board specifications and Arduino setup are in the [Waveshare documentation](https://docs.waveshare.com/ESP32-S3-Touch-LCD-1.28).

## Local setup

The project uses Python 3, a browser with shared WebAssembly memory support, and a local Zig 0.14.1 compiler. To restore the compiler in a new checkout, run this from the project directory:

```sh
python3 -m pip install --no-deps --target .sim-tools ziglang==0.14.1
python3 simulator/serve.py --open
```

The Python server listens on 127.0.0.1. It compiles source on the laptop, and the browser runs the resulting module in a dedicated worker. The display rasterizer is Adafruit GFX, distributed under its included BSD license in simulator/vendor/gfx/license.txt.

## Public web editor

The static site in `docs/` compiles edits on the visitor’s device using Clang and LLD in a dedicated worker. The initial Hello World example loads from a precompiled module; changing the editor text invokes the C++ compiler. The first edited run fetches approximately 19 MB of compressed compiler assets. Sketches using delays additionally load Binaryen to suspend and resume the running program. Stop terminates a build or a running sketch.

After changing the simulator headers, graphics library or default sketch, run `node simulator/build_pages_support.cjs` to refresh the support objects and default WebAssembly. Serve `docs/` via a static HTTP server to preview it. Upstream versions and licenses are recorded in `docs/compiler/NOTICE.txt`.
