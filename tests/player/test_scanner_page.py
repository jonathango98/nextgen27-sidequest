import pytest
import segno
from playwright.sync_api import expect

from app.config import load_config

QR_FORMAT = load_config()["qr"]["format_version"]
FAKE_SQ_CODE = f"{QR_FORMAT}.P.testpid02.000000"  # fake data (ENG-047)
OTHER_CODE = "https://example.com/menu"
# Chromium's test camera: a moving test picture instead of a real one, allowed without a prompt.
FAKE_CAMERA = ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"]
NOT_A_CODE = "This isn't a Side Quest code."


@pytest.fixture
def scanner_page(playwright, live_server, browser_context_args):
    browser = playwright.chromium.launch(args=FAKE_CAMERA)
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    page.problems = []
    page.on(
        "console", lambda m: page.problems.append(m.text) if m.type == "error" else None
    )
    page.on("pageerror", lambda e: page.problems.append(str(e)))
    yield page
    context.close()
    browser.close()


def _open_with_camera(page, live_server):
    page.goto(f"{live_server}/scan")
    page.wait_for_function(
        "document.querySelector('video').readyState >= 2", timeout=5000
    )


def _camera_live(page):
    return page.evaluate(
        "() => { const s = document.querySelector('video').srcObject;"
        " return !!s && s.getTracks().some(t => t.readyState === 'live'); }"
    )


def test_arch_025_side_quest_code_is_read(scanner_page, live_server):
    _open_with_camera(scanner_page, live_server)
    assert _camera_live(scanner_page)
    # No empty button under the camera while it scans.
    expect(scanner_page.locator("[data-scan-again]")).to_be_hidden()
    scanner_page.evaluate("code => window.sqScanner.handle(code)", FAKE_SQ_CODE)
    expect(scanner_page.get_by_role("status")).to_have_text("Got it!")
    expect(scanner_page.get_by_role("button", name="Scan again")).to_be_visible()
    assert not _camera_live(scanner_page)
    assert scanner_page.problems == []


def test_arch_025_other_code_says_not_a_side_quest_code(scanner_page, live_server):
    _open_with_camera(scanner_page, live_server)
    scanner_page.evaluate("code => window.sqScanner.handle(code)", OTHER_CODE)
    expect(scanner_page.get_by_role("alert")).to_have_text(NOT_A_CODE)
    # Keeps scanning so the player can try the right code.
    assert _camera_live(scanner_page)
    expect(scanner_page.get_by_role("status")).to_be_hidden()


def test_arch_025_scan_again_restarts_camera(scanner_page, live_server):
    _open_with_camera(scanner_page, live_server)
    scanner_page.evaluate("code => window.sqScanner.handle(code)", FAKE_SQ_CODE)
    scanner_page.get_by_role("button", name="Scan again").click()
    scanner_page.wait_for_function(
        "document.querySelector('video').srcObject?.active === true"
    )
    expect(scanner_page.get_by_role("status")).to_be_hidden()


def test_arch_025_no_camera_shows_message(scanner_page, live_server):
    scanner_page.add_init_script(
        "navigator.mediaDevices.getUserMedia ="
        " () => Promise.reject(new DOMException('blocked', 'NotAllowedError'));"
    )
    scanner_page.goto(f"{live_server}/scan")
    expect(scanner_page.get_by_role("alert")).to_have_text("No camera")
    expect(scanner_page.get_by_role("button", name="Try again")).to_be_visible()
    assert scanner_page.problems == []


def test_arch_004_zxing_reads_sq1_code_from_our_server(scanner_page, live_server):
    # Hide the browser's own detector, as on iPhone Safari, so ZXing does the work.
    scanner_page.add_init_script("delete window.BarcodeDetector;")
    outside = []
    scanner_page.on(
        "request",
        lambda r: outside.append(r.url) if not r.url.startswith(live_server) else None,
    )
    with scanner_page.expect_response(lambda r: r.url.endswith(".wasm")) as wasm:
        _open_with_camera(scanner_page, live_server)
    assert wasm.value.status == 200
    image = segno.make(FAKE_SQ_CODE).png_data_uri(scale=8)
    read = scanner_page.evaluate(
        """async image => {
            const img = new Image();
            img.src = image;
            await img.decode();
            const detector = new BarcodeDetectionAPI.BarcodeDetector({formats: ["qr_code"]});
            const codes = await detector.detect(img);
            return codes.map(c => c.rawValue);
        }""",
        image,
    )
    assert read == [FAKE_SQ_CODE]
    assert outside == []
    assert scanner_page.problems == []
