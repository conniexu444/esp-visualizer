// Rebuild the static editor support objects with the same compiler as the page.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const zlib = require('node:zlib');
const root = path.join(__dirname, '..');
const dir = path.join(root, 'docs/compiler');
vm.runInThisContext(fs.readFileSync(path.join(dir, 'shared.js'), 'utf8'));
vm.runInThisContext(fs.readFileSync(path.join(dir, 'compile.js'), 'utf8'));

async function build() {
  const read = name => new Uint8Array(zlib.gunzipSync(fs.readFileSync(path.join(dir, name + '.gz')))).buffer;
  const api = new API({readBuffer:read, compileStreaming: name => WebAssembly.compile(read(name)),
    hostWrite: text => process.stderr.write(text)});
  await api.ready;
  const headers = {};
  for (const folder of ['include', 'vendor/gfx']) {
    const location = path.join(__dirname, folder);
    for (const file of fs.readdirSync(location)) {
      if (!file.endsWith('.h') && file !== 'glcdfont.c') continue;
      const text = fs.readFileSync(path.join(location, file), 'utf8');
      headers[file] = text;
      api.memfs.addFile(file, new TextEncoder().encode(text));
    }
  }
  const objs = {};
  for (const [file, obj] of [['runtime.cpp','runtime.o'], ['vendor/gfx/Adafruit_GFX.cpp','gfx.o']]) {
    await compileObject(api, path.basename(file), fs.readFileSync(path.join(__dirname,file),'utf8'), obj);
    objs[obj] = Buffer.from(api.memfs.getFileContents(obj)).toString('base64');
  }
  fs.writeFileSync(path.join(dir, 'support.json'), JSON.stringify({headers, objects:objs}));
  const hello = fs.readFileSync(path.join(root, 'docs/index.html'), 'utf8').match(/(?:<code id="sketch">|<textarea[^>]*id="sketch"[^>]*>)([\s\S]*?)<\/(?:code|textarea)>/)[1].replaceAll('&lt;', '<').replaceAll('&gt;', '>');
  await compileObject(api, 'sketch.ino', hello, 'sketch.o');
  const wasm = await linkSketch(api);
  fs.writeFileSync(path.join(root, 'docs/hello.wasm'), wasm);
  console.log(WebAssembly.Module.imports(await WebAssembly.compile(wasm)));
}
build().catch(error=>{console.error(error);process.exitCode=1;});
