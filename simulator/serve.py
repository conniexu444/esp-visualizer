"""Loopback-only Arduino sketch compiler and display workbench."""
import argparse
import functools
import hashlib
import errno
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SIM = Path(__file__).resolve().parent
ROOT = SIM.parent
ZIG = ROOT / ".sim-tools/ziglang/zig"
DEMO = ROOT / "examples/TouchDial/TouchDial.ino"
BUILD_LOCK = threading.Lock()
FILES = {
    "/": (SIM / "web/index.html", "text/html; charset=utf-8"),
    "/app.js": (SIM / "web/app.js", "text/javascript"),
    "/runner.js": (SIM / "web/runner.js", "text/javascript"),
    "/style.css": (SIM / "web/style.css", "text/css"),
    "/TouchDial.ino": (DEMO, "text/plain; charset=utf-8"),
}

@functools.lru_cache(maxsize=4)
def compile_sketch(source):
    with tempfile.TemporaryDirectory(prefix="roundbench-") as tmp:
        path = Path(tmp)
        (path / "sketch.ino").write_text(source, encoding="utf-8")
        command = [str(ZIG), "c++", "-target", "wasm32-wasi", "-mexec-model=reactor",
                   "-std=c++17", "-O2", "-s", "-fno-color-diagnostics", "-ferror-limit=4",
                   "-DARDUINO=10819", "-I" + str(SIM / "include"), "-I" + str(SIM / "vendor/gfx"),
                   "-include", "Arduino.h", str(SIM / "runtime.cpp"), str(SIM / "vendor/gfx/Adafruit_GFX.cpp"),
                   "-x", "c++", "sketch.ino", "-Wl,--export=sketch_setup", "-Wl,--export=sketch_loop",
                   "-Wl,--export=pixels", "-Wl,--max-memory=67108864", "-o", "preview.wasm"]
        env = {**os.environ, "ZIG_GLOBAL_CACHE_DIR": str(ROOT / ".sim-cache")}
        result = subprocess.run(command, cwd=path, env=env, capture_output=True, timeout=90)
        if result.returncode:
            raise ValueError(result.stderr.decode(errors="replace")[:6000] or "Compilation failed.")
        return (path / "preview.wasm").read_bytes()

class Workbench(BaseHTTPRequestHandler):
    def send_data(self, status, body, mime="text/plain; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.headers.get("Host") != self.server.local_host:
            return self.send_data(403, "Local access required.")
        if self.path == "/identity":
            return self.send_data(200, self.server.identity)
        item = FILES.get(self.path)
        if not item:
            return self.send_data(404, "Unknown resource.")
        self.send_data(200, item[0].read_bytes(), item[1])

    def do_POST(self):
        if (self.headers.get("Host") != self.server.local_host or
                self.headers.get("Origin") != "http://" + self.server.local_host):
            return self.send_data(403, "Open the local workbench to compile.")
        if self.path != "/compile" or self.headers.get("Content-Type") != "text/plain":
            return self.send_data(400, "Expected a sketch.")
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 512 * 1024:
                return self.send_data(413, "Enter a sketch of up to 512 KiB.")
            source = self.rfile.read(size).decode("utf-8")
            with BUILD_LOCK:
                binary = compile_sketch(source)
        except ValueError as exc:
            return self.send_data(422, str(exc))
        except (OSError, subprocess.TimeoutExpired) as exc:
            return self.send_data(500, str(exc))
        self.send_data(200, binary, "application/wasm")

    def log_message(self, *args):
        pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    if not ZIG.is_file():
        sys.exit("Compiler missing. See the installation command in README.md.")
    host = f"127.0.0.1:{args.port}"
    url = "http://" + host
    identity = "Roundbench/" + hashlib.sha256(str(ROOT).encode()).hexdigest()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Workbench)
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            raise
        try:
            with urllib.request.urlopen(url + "/identity", timeout=1) as response:
                existing = response.read(256).decode() == identity
        except OSError:
            raise
        if not existing:
            sys.exit(f"Port {args.port} is occupied. Launch with --port 8766.")
        if args.open:
            webbrowser.open(url)
        print("Already running at", url)
        return
    server.local_host = host
    server.identity = identity
    print("Roundbench is ready at " + url, flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
