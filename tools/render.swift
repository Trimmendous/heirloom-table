// Rasterise HTML/SVG files to exact-size PNGs with WebKit (macOS system frameworks only).
//
//   swiftc -O tools/render.swift -o tools/.bin/render
//   tools/.bin/render jobs.json            # [{"html": "/abs/in.html", "out": "/abs/out.png", "w": 640, "h": 400, "opaque": false, "wait": 0.3}]
//
// Also used to screenshot the web clone: an html path may carry a query (?screen=recipe&...)
// because the page is loaded with loadFileURL + the query appended.
import Cocoa
import WebKit

struct Job: Decodable { let html: String; let out: String; let w: Int; let h: Int; let opaque: Bool?; let wait: Double? }

let args = CommandLine.arguments
guard args.count >= 2, let data = FileManager.default.contents(atPath: args[1]),
      let allJobs = try? JSONDecoder().decode([Job].self, from: data) else {
    FileHandle.standardError.write("usage: render jobs.json\n".data(using: .utf8)!); exit(2)
}
let root = URL(fileURLWithPath: args.count >= 3 ? args[2] : FileManager.default.currentDirectoryPath)

let app = NSApplication.shared
app.setActivationPolicy(.prohibited)

final class Runner: NSObject, WKNavigationDelegate {
    let jobs: [Job]
    let root: URL
    init(jobs: [Job], root: URL) { self.jobs = jobs; self.root = root }
    var idx = 0
    var failures = 0
    var win: NSWindow!
    var web: WKWebView!

    func start() { next() }

    func next() {
        guard idx < jobs.count else { exit(failures == 0 ? 0 : 1) }
        let j = jobs[idx]
        let rect = NSRect(x: 0, y: 0, width: j.w, height: j.h)
        win = NSWindow(contentRect: rect, styleMask: [.borderless], backing: .buffered, defer: false)
        let cfg = WKWebViewConfiguration()
        cfg.preferences.setValue(true, forKey: "allowFileAccessFromFileURLs")
        web = WKWebView(frame: rect, configuration: cfg)
        if !(j.opaque ?? false) { web.setValue(false, forKey: "drawsBackground") }
        web.navigationDelegate = self
        win.contentView = web
        var path = j.html, query = ""
        if let q = path.firstIndex(of: "?") { query = String(path[q...]); path = String(path[..<q]) }
        let fileURL = URL(fileURLWithPath: path)
        let url = URL(string: fileURL.absoluteString + query)!
        web.loadFileURL(url, allowingReadAccessTo: root)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        let j = jobs[idx]
        DispatchQueue.main.asyncAfter(deadline: .now() + (j.wait ?? 0.25)) { self.snap(j) }
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { fail("\(error)") }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { fail("\(error)") }

    func fail(_ msg: String) {
        FileHandle.standardError.write("render failed \(jobs[idx].out): \(msg)\n".data(using: .utf8)!)
        failures += 1; idx += 1; next()
    }

    func snap(_ j: Job) {
        let c = WKSnapshotConfiguration()
        c.rect = CGRect(x: 0, y: 0, width: j.w, height: j.h)
        web.takeSnapshot(with: c) { img, err in
            guard let img = img else { self.fail("\(String(describing: err))"); return }
            // Redraw into a bitmap of the exact pixel size (snapshots may come back @2x).
            guard let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: j.w, pixelsHigh: j.h,
                                             bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                                             colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0) else { self.fail("rep"); return }
            rep.size = NSSize(width: j.w, height: j.h)
            NSGraphicsContext.saveGraphicsState()
            NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
            NSGraphicsContext.current?.imageInterpolation = .high
            img.draw(in: NSRect(x: 0, y: 0, width: j.w, height: j.h))
            NSGraphicsContext.restoreGraphicsState()
            guard let png = rep.representation(using: .png, properties: [:]) else { self.fail("png"); return }
            do { try png.write(to: URL(fileURLWithPath: j.out)) } catch { self.fail("\(error)"); return }
            self.idx += 1
            self.next()
        }
    }
}

let runner = Runner(jobs: allJobs, root: root)
DispatchQueue.main.async { runner.start() }
DispatchQueue.main.asyncAfter(deadline: .now() + Double(30 + allJobs.count * 10)) {
    FileHandle.standardError.write("render timeout\n".data(using: .utf8)!); exit(3)
}
app.run()
