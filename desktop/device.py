"""Native app helper. Guest firmware runs inside Espressif QEMU."""
import base64
import contextlib
import gzip
import json
import os
import queue
import re
import selectors
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from build_sketch import build

HERE = Path(__file__).resolve().parent
QEMU = HERE.parent / "qemu"
if not QEMU.is_dir():
    QEMU = HERE.parent / ".sim-tools/qemu"
FRAME_BYTES = 240 * 240 * 2

def emit(key, value):
    print(json.dumps({key: value}, separators=(",", ":")), flush=True)

def prepare_flash(image, output):
    size = image.stat().st_size
    if size < 0x9000 or size > 32 * 1024**2:
        raise ValueError("Choose a merged ESP32-S3 flash image including its bootloader and partition table.")
    with image.open("rb") as stream:
        header = stream.read(24)
        if header[0] != 0xe9 or int.from_bytes(header[12:14], "little") != 9:
            raise ValueError("The image must start with an ESP32-S3 bootloader at offset zero.")
        stream.seek(0)
        prefix = stream.read(min(size, 0x100000))
        if not any(prefix[i:i+2] == b"\xaa\x50" for i in range(0x1000, len(prefix)-1, 0x1000)):
            raise ValueError("No partition table found. Open the .merged.bin export instead of an app-only binary.")
        flash_size = 1024**2 << (header[3] >> 4)
        if size > flash_size or flash_size not in {2**n for n in range(21,26)}:
            raise ValueError("The flash image length does not match its bootloader flash-size setting.")
        stream.seek(0)
        with output.open("wb") as dest:
            shutil.copyfileobj(stream, dest)
            left = flash_size - size
            while left:
                n = min(left, 65536)
                dest.write(b"\xff"*n)
                left -= n

def boot(flash, work, qemu_home=QEMU):
    commands = queue.Queue()
    def read_input():
        for line in sys.stdin:
            try:
                commands.put(json.loads(line))
            except ValueError:
                continue
        commands.put({"stop": True})
    threading.Thread(target=read_input, daemon=True).start()
    with contextlib.ExitStack() as stack:
        uart, serial_peer = socket.socketpair()
        board, board_peer = socket.socketpair()
        for sock in (uart, serial_peer, board, board_peer):
            stack.enter_context(sock)
        args = [str(qemu_home/"bin/qemu-system-xtensa"), "-L", str(qemu_home/"share/qemu"),
                "-machine", "esp32s3", "-m", "2M", "-display", "none", "-monitor", "none", "-nic", "none",
                "-chardev", f"socket,id=console,fd={serial_peer.fileno()}", "-serial", "chardev:console",
                "-chardev", f"socket,id=board,fd={board_peer.fileno()}", "-serial", "chardev:board",
                "-qmp", "stdio", "-drive", f"file={str(flash).replace(',', ',,')},if=mtd,format=raw"]
        error_log = stack.enter_context((work/"qemu.log").open("w+b"))
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=error_log,
                                   pass_fds=(serial_peer.fileno(), board_peer.fileno()), bufsize=0)
        serial_peer.close()
        board_peer.close()
        def shutdown():
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        stack.callback(shutdown)
        def qmp(command, **args):
            message = {"execute":command, "arguments":args, "id":command}
            process.stdin.write(json.dumps(message).encode()+b"\n")
        select = stack.enter_context(selectors.DefaultSelector())
        select.register(process.stdout, selectors.EVENT_READ, "qmp")
        select.register(uart, selectors.EVENT_READ, "serial")
        select.register(board, selectors.EVENT_READ, "board")
        qbuf = b""
        bbuf = b""
        address = None
        pending = False
        ready = False
        serial_buffer = bytearray()
        next_serial = 0.0
        previous = None
        frame = work/"lcd.raw"
        next_frame = 0.0
        while process.poll() is None:
            for key, _ in select.select(0.025):
                data = os.read(key.fd, 65536)
                if not data:
                    select.unregister(key.fileobj)
                    continue
                if key.data == "serial":
                    serial_buffer.extend(data)
                elif key.data == "board":
                    bbuf += data
                    while b"\n" in bbuf:
                        line, bbuf = bbuf.split(b"\n", 1)
                        match = re.fullmatch(rb"LCD ([0-9a-fA-F]{8})\r?", line)
                        if match:
                            addr = int(match[1], 16)
                            if 0x3fc80000 <= addr <= 0x3fd00000-FRAME_BYTES:
                                address = addr
                    bbuf=bbuf[-64:]
                else:
                    qbuf += data
                    while b"\n" in qbuf:
                        line,qbuf = qbuf.split(b"\n",1)
                        msg = json.loads(line)
                        if "QMP" in msg:
                            qmp("qmp_capabilities")
                        elif "error" in msg:
                            raise RuntimeError(msg["error"]["desc"])
                        elif msg.get("id")=="qmp_capabilities":
                            ready = True
                            emit("state","Running")
                        elif msg.get("id")=="pmemsave":
                            pending = False
                            pixels = frame.read_bytes()
                            if pixels != previous and len(pixels)==FRAME_BYTES:
                                emit("frame",base64.b64encode(pixels).decode("ascii"))
                                previous = pixels
            while not commands.empty():
                cmd=commands.get()
                if "stop" in cmd:
                    return
                if "touch" in cmd and address:
                    down,x,y=cmd["touch"]
                    board.sendall(bytes((250,int(bool(down)),min(239,max(0,x)),min(239,max(0,y)))))
                if "uart" in cmd:
                    uart.sendall(str(cmd["uart"]).encode()[:4096]+b"\n")
                if "reset" in cmd and ready:
                    address = previous = None
                    qmp("system_reset")
                    emit("reset",True)
            now = time.monotonic()
            if serial_buffer and now >= next_serial:
                emit("serial", serial_buffer.decode("utf-8", errors="replace"))
                serial_buffer.clear()
                next_serial=now+0.04
            if address and ready and not pending and now >= next_frame:
                qmp("pmemsave",val=address,size=FRAME_BYTES,filename=str(frame))
                pending=True
                next_frame=now+0.08
        error_log.seek(0)
        raise RuntimeError(error_log.read(4096).decode(errors="replace") or "The emulated device stopped.")

def main():
    with tempfile.TemporaryDirectory(prefix="roundbench-device-") as temp:
        work=Path(temp)
        req=json.loads(sys.stdin.readline())
        kind=req["kind"]
        if kind == "sketch":
            emit("state", "Building")
            # Keep compiler diagnostics separate from the app's event stream.
            with (work/"build.log").open("w+") as log:
                old_stdout=os.dup(1)
                old_stderr=os.dup(2)
                try:
                    os.dup2(log.fileno(),1)
                    os.dup2(log.fileno(),2)
                    image=build(req["source"],Path(req["path"]) if req.get("path") else None,work)
                except subprocess.CalledProcessError:
                    log.seek(0)
                    raise RuntimeError(log.read()[-9000:])
                finally:
                    os.dup2(old_stdout,1)
                    os.dup2(old_stderr,2)
                    os.close(old_stdout)
                    os.close(old_stderr)
        elif kind == "demo":
            image=work/"demo.bin"
            with gzip.open(HERE/"TouchDial.bin.gz","rb") as src, image.open("wb") as dest:
                shutil.copyfileobj(src,dest)
        elif kind == "firmware":
            image=Path(req["path"])
        else:
            raise ValueError("Unknown input format.")
        flash=work/"flash.bin"
        prepare_flash(image,flash)
        emit("state","Booting")
        boot(flash,work)

if __name__ == "__main__":
    # Keep build and emulator children in a dedicated group. Closing the app
    # stops the entire session, including any active compilation.
    try:
        os.setpgid(0,0)
    except PermissionError:
        pass
    def stop(*_):
        raise SystemExit
    signal.signal(signal.SIGTERM,stop)
    try:
        main()
    except Exception as exc:
        emit("error",str(exc))
        sys.exit(1)
