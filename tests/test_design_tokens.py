import re
from pathlib import Path

from app.config import load_config

APP_DIR = Path(__file__).resolve().parent.parent / "app"
TOKENS = APP_DIR / "static" / "css" / "tokens.css"
DESIGN_DOC = APP_DIR.parent / "foundation" / "07-design-system.md"

# A row of the 07 section 2 tables: | `--token` | `value` | ...
DOC_TOKEN_ROW = re.compile(r"^\| `(--[a-z0-9-]+)` \| `([^`]+)` \|", re.MULTILINE)
CSS_TOKEN = re.compile(r"(--[a-z0-9-]+):\s*([^;]+);")

RAW_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")
RAW_SIZE = re.compile(r"\b\d+(\.\d+)?(px|rem|em)\b")


def _files_that_must_use_tokens():
    css = [p for p in (APP_DIR / "static" / "css").glob("*.css") if p != TOKENS]
    html = list((APP_DIR / "templates").rglob("*.html"))
    return css + html


def test_ui_001_css_and_templates_use_tokens_not_raw_values():
    files = _files_that_must_use_tokens()
    assert files
    for path in files:
        text = path.read_text()
        assert not RAW_COLOR.search(text), f"raw color in {path.name}"
        assert not RAW_SIZE.search(text), f"raw size in {path.name}"


def _normal(value):
    return re.sub(r"\s+", "", value).lower()


def test_ui_001_tokens_match_design_doc():
    doc = dict(DOC_TOKEN_ROW.findall(DESIGN_DOC.read_text(encoding="utf-8")))
    css = {
        name: _normal(value) for name, value in CSS_TOKEN.findall(TOKENS.read_text())
    }
    assert doc
    for name, value in doc.items():
        assert name in css, f"{name} missing from tokens.css"
        assert css[name] == _normal(value), f"{name} differs from 07-design-system.md"


def test_ui_003_tap_min_token_matches_config():
    match = re.search(r"--tap-min:\s*(\d+)px", TOKENS.read_text())
    assert match
    assert int(match.group(1)) == load_config()["ui"]["min_tap_target_px"]
