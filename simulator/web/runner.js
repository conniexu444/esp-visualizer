// Each run gets its own worker and isolated WebAssembly memory.
onmessage = async ({data}) => {
  const input = new Int32Array(data.input);
  let wasm, lastFrame = -Infinity, serial = '', lastSerial = 0;
  const start = performance.now();
  function flushSerial() {
    if (serial) postMessage({serial});
    serial = '';
    lastSerial = performance.now();
  }
  function sendFrame(force = false) {
    if (!force && performance.now() - lastFrame < 16) return;
    lastFrame = performance.now();
    if (serial && performance.now() - lastSerial > 50) flushSerial();
    // Only transfer pixels that changed since the last frame.
    const address = wasm.pixels();
    const pixels = address ? new Uint16Array(wasm.memory.buffer, address, 240*240) : black;
    if (!force && previous.every((value, i) => value === pixels[i])) return;
    previous.set(pixels);
    const buffer = previous.slice().buffer;
    postMessage({frame:buffer}, [buffer]);
  }
  const previous = new Uint16Array(240*240), black = previous.slice();
  const imports = {
    bench: {
      time: () => performance.now()-start,
      touch: () => Atomics.load(input, 0),
      sleep(ms) {
        sendFrame();
        if (ms > 0) Atomics.wait(input, 1, 0, ms >>> 0);
      },
      serial(byte) {
        if (serial.length < 8192) serial += String.fromCharCode(byte);
        if (performance.now()-lastSerial > 50) flushSerial();
      },
    },
    wasi_snapshot_preview1: {
      fd_close: () => 8, fd_seek: () => 8, fd_write: () => 8,
      proc_exit(code) { throw Error('Sketch exited with code ' + code); }
    }
  };
  try {
    wasm = (await WebAssembly.instantiate(data.binary, imports)).instance.exports;
    wasm._initialize();
    postMessage({ready:true});
    wasm.sketch_setup();
    sendFrame(true);
    flushSerial();
    while (true) {
      wasm.sketch_loop();
      sendFrame();
      Atomics.wait(input, 1, 0, 1);
    }
  } catch (error) {
    flushSerial();
    postMessage({error:error.message});
  }
};
