"""Build an Arduino project for the emulated ESP32-S3, in a private staging area."""
import os
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FQBN = "esp32:esp32:esp32s3:FlashMode=dio,FlashSize=16M,PSRAM=disabled,CDCOnBoot=default"
EXTENSIONS = {".ino", ".h", ".hpp", ".c", ".cpp", ".S", ".tpp", ".cxx"}
INCLUDE = re.compile(r'^(\s*#\s*include\s*)[<"](TFT_eSPI|Wire)\.h[>"]', re.M)

def build(source, folder, work):
    sketch = work / "DeviceSketch"
    sketch.mkdir()
    companions = {}
    if folder and folder.parent.name == folder.stem:
        for f in folder.parent.iterdir():
            if f != folder and f.is_file() and f.suffix in EXTENSIONS:
                companions[f.name] = f.read_text()
        if (folder.parent / "src").is_dir():
            shutil.copytree(folder.parent / "src", sketch / "src")
    source_files = {"DeviceSketch.ino": source, **companions}
    # Only redirect board I/O in the temporary emulator build. Other Arduino
    # libraries, the RTOS, and the application still run as Xtensa firmware.
    display = any('TFT_eSPI.h' in s for s in source_files.values())
    if display:
        headers = ROOT / "simulator/include"
        shutil.copyfile(headers / "TFT_eSPI.h", sketch / "RoundbenchLCD.h")
        touch = (headers / "Wire.h").read_text().replace("class TwoWire", "uint32_t sim_touch();\nclass RoundbenchWire").replace("inline TwoWire Wire;", "inline RoundbenchWire deviceWire;\n#define Wire deviceWire")
        (sketch / "RoundbenchWire.h").write_text(touch)
        shutil.copyfile(HERE / "guest/board.cpp", sketch / "RoundbenchBoard.cpp")
    for name, text in source_files.items():
        if display:
            text = INCLUDE.sub(lambda m: m[1] + '"' + {"Wire":"RoundbenchWire", "TFT_eSPI":"RoundbenchLCD"}[m[2]] + '.h"', text)
            if name.endswith(".ino"):
                text = '#define setup deviceSketchSetup\n#define loop deviceSketchLoop\n' + text
        (sketch / name).write_text(text)
    cli = shutil.which("arduino-cli") or "/opt/homebrew/bin/arduino-cli"
    cache = Path(os.environ.get("ROUNDBENCH_CACHE", Path.home() / "Library/Caches/Roundbench"))
    cache.mkdir(exist_ok=True, parents=True)
    command = [cli, "compile", "-b", FQBN, "--jobs", "4", "--build-path", str(work/"build"),
               "--build-property", "compiler.cache_core=true", str(sketch)]
    env = {**os.environ, "ARDUINO_BUILD_CACHE_PATH":str(cache/"arduino")}
    subprocess.run(command, env=env, check=True)
    return work / "build/DeviceSketch.ino.merged.bin"


if __name__ == "__main__":
    import argparse
    import gzip
    import tempfile

    parser = argparse.ArgumentParser(description="Build the bundled demo from its Arduino source.")
    parser.add_argument("sketch", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    sketch = args.sketch.resolve()
    with tempfile.TemporaryDirectory(prefix="roundbench-demo-") as temp:
        image = build(sketch.read_text(), sketch, Path(temp))
        with image.open("rb") as source, gzip.open(args.output, "wb") as dest:
            shutil.copyfileobj(source, dest)
