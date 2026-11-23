import SwiftUI

@main
struct DeviceEmulatorApp: App {
    @State private var device = Device()

    var body: some Scene {
        Window("Roundbench Device", id: "emulator") {
            BoardWindow(device: device)
                .task { device.launch() }
                .onDisappear { device.stop() }
                .onReceive(NotificationCenter.default.publisher(for: NSApplication.willTerminateNotification)) { _ in
                    device.stop()
                }
        }
        .defaultSize(width: 892, height: 655)
    }
}

private struct BoardWindow: View {
    let device: Device
    @State private var scale: CGFloat = 1.25

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .top, spacing: 24) {
                VStack(alignment: .leading, spacing: 12) {
                    HStack(alignment: .firstTextBaseline) {
                        Text("Roundbench")
                            .font(.system(size: 39, weight: .medium, design: .serif))
                        Spacer()
                        Text("ESP32-S3 desktop emulator")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(.secondary)
                    }
                    BoardDisplay(device: device, scale: scale)
                    HStack(spacing: 14) {
                        Picker("Scale", selection: $scale) {
                            Text("1×").tag(CGFloat(1))
                            Text("1.25×").tag(CGFloat(1.25))
                        }
                        .fixedSize()
                        Spacer()
                        Text(device.touchPoint.map { "X \(Int($0.x))   Y \(Int($0.y))" } ?? "240 × 240")
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(.secondary)
                    }
                }
                CommandPanel(device: device)
                    .frame(width: 196)
                    .padding(.top, 13)
            }
            Divider()
            SketchInspector(device: device)
                .frame(minHeight: 140, maxHeight: .infinity)
        }
        .padding(24)
        .frame(minWidth: 740, minHeight: 630)
        .background(Color(red: 0.98, green: 0.95, blue: 0.90))
        .preferredColorScheme(.light)
    }
}

private struct BoardDisplay: View {
    let device: Device
    let scale: CGFloat
    private var diameter: CGFloat { 240 * scale }

    var body: some View {
        ZStack {
            Circle().fill(Color(white: 0.045))
            if let image = device.image {
                Image(decorative: image, scale: 1)
                    .resizable()
                    .interpolation(.none)
                    .frame(width: diameter, height: diameter)
                    .clipShape(Circle())
            } else {
                Text(device.running ? "Waiting for LCD output" : device.status)
                    .font(.callout.monospaced())
                    .foregroundStyle(.white.opacity(0.8))
            }
        }
        .frame(width: diameter, height: diameter)
        .overlay { Circle().strokeBorder(.white.opacity(0.15), lineWidth: 2).allowsHitTesting(false) }
        .contentShape(Circle())
        .gesture(DragGesture(minimumDistance: 0)
            .onChanged { device.touch($0.location, down: true, size: diameter) }
            .onEnded { device.touch($0.location, down: false, size: diameter) })
        .accessibilityLabel("Virtual round touchscreen")
        .frame(maxWidth: .infinity)
        .frame(height: 312)
        .background(Color(red: 0.23, green: 0.17, blue: 0.14))
        .clipShape(.rect(cornerRadius: 18))
        .overlay {
            RoundedRectangle(cornerRadius: 18).strokeBorder(.black.opacity(0.12))
                .allowsHitTesting(false)
        }
    }
}

private struct CommandPanel: View {
    let device: Device
    private let rust = Color(red: 0.52, green: 0.25, blue: 0.17)

    var body: some View {
        VStack(alignment: .leading, spacing: 15) {
            Text("Device controls")
                .font(.system(size: 19, weight: .semibold, design: .serif))
            Button { device.start() } label: {
                Label(device.firmware ? "Boot firmware" : "Build and run", systemImage: "play.fill")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .tint(rust)
            .keyboardShortcut("r")

            Grid(alignment: .leading, horizontalSpacing: 7, verticalSpacing: 7) {
                GridRow {
                    action("Open…") { device.open() }.keyboardShortcut("o")
                    action("Touch demo") { device.demo() }
                }
                GridRow {
                    action("Reset") { device.post(["reset": true]) }.disabled(!device.running)
                    action("Stop") { device.stop() }.disabled(!device.busy)
                }
            }
            Divider()
            Text("Waveshare ESP32-S3-Touch-LCD-1.28")
                .font(.system(size: 13, weight: .medium))
                .fixedSize(horizontal: false, vertical: true)
            Text(device.firmware && device.image == nil
                 ? "Read firmware output in the UART0 console."
                 : "Click or drag on the round screen to send touch input.")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
            Text(device.status)
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(rust)
        }
    }

    private func action(_ title: String, perform: @escaping () -> Void) -> some View {
        Button(action: perform) { Text(title).frame(maxWidth: .infinity) }
            .buttonStyle(.bordered)
            .controlSize(.regular)
    }
}
