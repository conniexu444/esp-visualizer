import AppKit
import SwiftUI
import UniformTypeIdentifiers

private let demoSource = Bundle.main.url(forResource: "TouchDial", withExtension: "ino")!
private let helper = Bundle.main.resourceURL!.appendingPathComponent("desktop/device.py")

@MainActor @Observable
final class Device {
    var status = "Ready"
    var name = "TouchDial.ino"
    var source = ""
    var console = ""
    var image: CGImage?
    var sendText = ""
    var touchPoint: CGPoint?
    var tab = 0
    var firmware = false
    var path: URL?
    var baseline = ""
    private var generation = 0
    private var process: Process?
    private var input: FileHandle?
    var busy: Bool { process != nil }
    var changed: Bool { !firmware && baseline != source }
    var running: Bool { status == "Running" }

    func launch() {
        guard source.isEmpty && !busy else { return }
        if let draft = UserDefaults.standard.dictionary(forKey: "draft"),
           let text = draft["source"] as? String {
            source = text
            name = draft["name"] as? String ?? "Sketch.ino"
            path = (draft["path"] as? String).map { URL(fileURLWithPath:$0) }
            baseline = draft["baseline"] as? String ?? ""
            tab = 1
        } else { demo() }
    }

    func storeDraft() {
        guard !firmware else { return }
        var values = ["source": source, "name": name, "baseline": baseline]
        if let path { values["path"] = path.path }
        UserDefaults.standard.set(values, forKey:"draft")
    }

    func canReplace() -> Bool {
        guard changed else { return true }
        let alert = NSAlert()
        alert.messageText = "Keep your sketch edits?"
        alert.informativeText = "Save a copy before opening another program."
        alert.addButton(withTitle:"Save…")
        alert.addButton(withTitle:"Cancel")
        alert.addButton(withTitle:"Discard")
        switch alert.runModal() {
        case .alertFirstButtonReturn: return save()
        case .alertThirdButtonReturn: return true
        default: return false
        }
    }

    func demo() {
        guard canReplace() else { return }
        stop()
        path = nil
        firmware = false
        name = "TouchDial.ino"
        do { source = try String(contentsOf:demoSource, encoding:.utf8) }
        catch { fail(error.localizedDescription); return }
        baseline = source
        tab = 0
        UserDefaults.standard.removeObject(forKey:"draft")
        start(kind:"demo")
    }

    func open() {
        let panel = NSOpenPanel()
        panel.title = "Open Arduino Sketch or Merged ESP32-S3 Firmware"
        panel.allowedContentTypes = ["ino","bin"].compactMap { UTType(filenameExtension:$0) }
        guard panel.runModal() == .OK, let url = panel.url, canReplace() else { return }
        do {
            let isImage = url.pathExtension.lowercased() == "bin"
            let text = isImage ? "" : try String(contentsOf:url, encoding:.utf8)
            stop()
            image = nil
            path = url
            name = url.lastPathComponent
            firmware = isImage
            baseline = text
            source = text
            console = ""
            status = "Ready"
            tab = isImage ? 0 : 1
            if isImage {
                UserDefaults.standard.removeObject(forKey:"draft")
                start(kind:"firmware")
            } else { storeDraft() }
        } catch { fail(error.localizedDescription) }
    }

    @discardableResult func save() -> Bool {
        let panel = NSSavePanel()
        panel.nameFieldStringValue = name
        panel.allowedContentTypes = [UTType(filenameExtension:"ino")!]
        if let path { panel.directoryURL = path.deletingLastPathComponent() }
        guard panel.runModal() == .OK, let url = panel.url else { return false }
        do {
            try source.write(to:url, atomically:true, encoding:.utf8)
            baseline = source
            name = url.lastPathComponent
            path = url
            storeDraft()
            return true
        } catch { fail(error.localizedDescription); return false }
    }

    func start(kind: String? = nil) {
        stop()
        let token = generation
        let proc = Process(), out = Pipe(), pipe = Pipe()
        proc.executableURL = URL(fileURLWithPath:"/usr/bin/python3")
        proc.arguments = ["-B","-u",helper.path]
        proc.environment = ProcessInfo.processInfo.environment.merging(["PATH":"/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"]) { _,v in v }
        proc.standardOutput = out
        proc.standardInput = pipe
        proc.standardError = out
        do {
            try proc.run()
            process = proc
            input = pipe.fileHandleForWriting
            console = ""
            image = nil
            status = "Starting"
            tab = 0
            post(["kind":kind ?? (firmware ? "firmware":"sketch"), "source":source, "path":path?.path ?? ""])
        } catch { fail(error.localizedDescription); return }
        let reader = out.fileHandleForReading
        DispatchQueue.global(qos:.userInitiated).async {
            var pending = Data()
            while true {
                let chunk = reader.availableData
                if chunk.isEmpty { break }
                pending.append(chunk)
                while let eol = pending.firstIndex(of:10) {
                    let line = Data(pending[..<eol])
                    pending.removeSubrange(...eol)
                    DispatchQueue.main.async {
                        guard token == self.generation else { return }
                        self.receive(line)
                    }
                }
            }
            proc.waitUntilExit()
            DispatchQueue.main.async {
                guard token == self.generation else { return }
                self.process = nil
                self.input = nil
                if self.status != "Error" { self.status = "Stopped" }
            }
        }
    }

    func receive(_ line: Data) {
        guard let event = (try? JSONSerialization.jsonObject(with:line)) as? [String:Any] else {
            console += String(decoding:line,as:UTF8.self) + "\n"; return
        }
        if let status = event["state"] as? String { self.status = status }
        if let text = event["serial"] as? String {
            console += text.replacingOccurrences(of:"\r", with:"")
            if console.count > 30000 { console = String(console.suffix(25000)) }
        }
        if event["reset"] != nil { image = nil; console += "\n── Reset ──\n" }
        if let error = event["error"] as? String { fail(error) }
        if let text = event["frame"] as? String, let raw = Data(base64Encoded:text), raw.count == 115200 {
            var rgba = [UInt8](repeating:255,count:240*240*4)
            raw.withUnsafeBytes { (bytes:UnsafeRawBufferPointer) in
                for i in 0..<(240*240) {
                    let v = Int(bytes[2*i]) | Int(bytes[2*i+1]) << 8
                    rgba[4*i] = UInt8((v>>11)*255/31)
                    rgba[4*i+1] = UInt8(((v>>5)&63)*255/63)
                    rgba[4*i+2] = UInt8((v&31)*255/31)
                }
            }
            if let provider = CGDataProvider(data:Data(rgba) as CFData) {
                image = CGImage(width:240,height:240,bitsPerComponent:8,bitsPerPixel:32,bytesPerRow:960,
                    space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGBitmapInfo(rawValue:CGImageAlphaInfo.noneSkipLast.rawValue),
                    provider:provider,decode:nil,shouldInterpolate:false,intent:.defaultIntent)
            }
        }
    }

    func fail(_ message:String) { status = "Error"; console += "\n"+message+"\n"; tab=0 }
    func post(_ event:[String:Any]) {
        guard let input, var data = try? JSONSerialization.data(withJSONObject:event) else { return }
        data.append(10)
        try? input.write(contentsOf:data)
    }
    func stop() {
        generation += 1
        if let proc = process, proc.isRunning {
            // The backend owns a private process group for its build and VM.
            if getpgid(proc.processIdentifier) == proc.processIdentifier { kill(-proc.processIdentifier,SIGTERM) }
            else { proc.terminate() }
        }
        try? input?.close()
        input = nil
        process = nil
        touchPoint = nil
        status = "Stopped"
    }
    func touch(_ location:CGPoint, down:Bool, size:CGFloat) {
        guard image != nil, running else { return }
        let x = Int(max(0,min(239,location.x*240/size)))
        let y = Int(max(0,min(239,location.y*240/size)))
        let held = down && hypot(location.x-size/2,location.y-size/2) <= size/2
        touchPoint = held ? CGPoint(x:x,y:y) : nil
        post(["touch":[held ? 1:0,x,y]])
    }
}

struct SketchInspector: View {
    @Bindable var device: Device

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(device.name + (device.changed ? " •" : ""))
                    .font(.headline)
                    .lineLimit(1)
                Spacer()
                Picker("Inspector", selection: $device.tab) {
                    Text("Serial").tag(0)
                    if !device.firmware { Text("Sketch").tag(1) }
                }
                .labelsHidden()
                .pickerStyle(.segmented)
                .fixedSize()
            }
            if device.tab == 1 && !device.firmware {
                TextEditor(text:$device.source).font(.system(size:13,design:.monospaced))
                    .disableAutocorrection(true).border(.separator)
                    .onChange(of:device.source){ device.storeDraft() }
                HStack {Text("Arduino C++").foregroundStyle(.secondary); Spacer(); Button("Save sketch…"){device.save()} }
            } else {
                ScrollViewReader { proxy in
                    ScrollView {
                        Text(device.console.isEmpty ? (device.status == "Building" ? "Compiling for ESP32-S3…" : "Waiting for UART0…") : device.console)
                            .font(.system(size:12,design:.monospaced)).foregroundStyle(Color(red:0.76,green:0.91,blue:0.84))
                            .frame(maxWidth:.infinity,alignment:.leading).textSelection(.enabled)
                        Color.clear.frame(height:1).id("tail")
                    }.padding(10).background(Color(red:0.055,green:0.09,blue:0.08)).clipShape(RoundedRectangle(cornerRadius:7))
                        .onChange(of:device.console){proxy.scrollTo("tail",anchor:.bottom)}
                }
                HStack {
                    TextField("Send to UART0",text:$device.sendText).textFieldStyle(.roundedBorder).onSubmit {send()}
                    Button("Send"){send()}.disabled(device.sendText.isEmpty)
                }.disabled(!device.running)
            }
        }
    }

    private func send() {
        guard !device.sendText.isEmpty else { return }
        device.post(["uart": device.sendText])
        device.sendText = ""
    }
}
