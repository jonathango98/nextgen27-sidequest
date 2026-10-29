// Scan page: reads QR codes with the phone camera (ARCH-025, UI-034).
// Saving a scan comes with connections.scan-save (POST /scan).
(function () {
  "use strict";

  var root = document.querySelector("[data-scanner]");
  if (!root) return;

  var video = root.querySelector("video");
  var status = document.querySelector(".scan-result");
  var alert = document.querySelector("[role=alert]");
  var again = document.querySelector("[data-scan-again]");
  var prefix = root.dataset.format + ".";

  // UI-034: a frame is checked this often, well inside the one second budget.
  var CHECK_EVERY_MS = 150;

  var stream = null;
  var detector = null;
  var running = false;

  function show(el, text) {
    el.textContent = text;
    el.hidden = !text;
  }

  function showAgain(text) {
    again.textContent = text;
    again.hidden = false;
  }

  async function makeDetector() {
    // ARCH-004: use the phone's own detector when it reads QR codes, ZXing everywhere else.
    if ("BarcodeDetector" in window) {
      try {
        var formats = await window.BarcodeDetector.getSupportedFormats();
        if (formats.indexOf("qr_code") !== -1) {
          return new window.BarcodeDetector({ formats: ["qr_code"] });
        }
      } catch (e) {
        // Fall through to ZXing.
      }
    }
    var api = window.BarcodeDetectionAPI;
    // ARCH-004: the .wasm file comes from our server, never the library's CDN default.
    api.prepareZXingModule({
      overrides: {
        locateFile: function (path, base) {
          return path.endsWith(".wasm") ? root.dataset.wasm : base + path;
        },
      },
    });
    return new api.BarcodeDetector({ formats: ["qr_code"] });
  }

  function stop() {
    running = false;
    if (stream) {
      stream.getTracks().forEach(function (track) {
        track.stop();
      });
      stream = null;
    }
  }

  // Also called by the browser tests, since a test camera cannot show a real QR code.
  function handle(text) {
    if (text.startsWith(prefix)) {
      stop();
      show(alert, "");
      show(status, "Got it!");
      showAgain("Scan again");
    } else {
      // ARCH-025, API table NOT_A_CODE: keep scanning for the right code.
      show(alert, "This isn't a Side Quest code.");
    }
  }

  async function tick() {
    if (!running) return;
    if (video.readyState >= video.HAVE_CURRENT_DATA) {
      try {
        var codes = await detector.detect(video);
        if (running && codes.length) handle(codes[0].rawValue);
      } catch (e) {
        // A frame that cannot be read is skipped.
      }
    }
    setTimeout(tick, CHECK_EVERY_MS);
  }

  async function start() {
    show(status, "");
    show(alert, "");
    again.hidden = true;
    try {
      detector = detector || (await makeDetector());
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
    } catch (e) {
      // Blocked, missing, or no camera support at all.
      stop();
      show(alert, "No camera");
      showAgain("Try again");
      return;
    }
    running = true;
    tick();
  }

  again.addEventListener("click", start);
  window.addEventListener("pagehide", stop);
  window.sqScanner = { handle: handle };
  start();
})();
