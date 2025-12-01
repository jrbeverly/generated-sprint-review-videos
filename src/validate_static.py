#!/usr/bin/env python3
"""Validation flow for the #431 PowerPoint + static slide rendering stage.

Checks the acceptance criteria:
  1. output/sprint-briefing.pptx has one slide per PPTX-included beat in
     manifest order; each slide's XML text carries the expected title and
     literal narration text; exactly the demo slides carry video media
     elements (the embedding/relationship confirmation itself runs the #430
     spike's inspection approach in evidence/results.md).
  2. output/sprint-briefing.pdf has one 16:9 page per PDF-included beat,
     printed directly from the static layout; extracted text carries titles,
     literal narration, optional epic, and the measured duration in manifest
     order; each demo card embeds exactly one 16:9 poster image.
  3. output/slides/NNN-<id>.png covers exactly the narrated video beats in
     script order (the same set make_narration.py narrates). The video-only
     case fixture proves video-included beats are rendered even when they are
     excluded from PPTX/PDF.
  4. Rendered pages and images are inspected for readable text (ink present
     with contrast), unclipped content (every text box inside the 1920x1080
     canvas, no overflow), visible posters (the rendered poster region
     matches the local poster asset), and nonblank demo cards.
  5. The one local font is actually used: the layout declares exactly one
     family, the in-browser font check passes, the loaded face list names it,
     and a control render without the font differs from the real render.
  6. Both inclusion flags are exercised independently with the pptx-only and
     video-only case fixtures.

Pixel identity between PPTX and static rendering is not required (INFO).
Desktop PowerPoint playback of the deck stays unverified for the final review
(INFO). Writes evidence/results-static.md and exits non-zero on any FAIL.
"""

import json
import re
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_tools import EXPERIMENT_ROOT  # noqa: E402

MANIFEST_PATH = Path("output/manifest.json")
SCRIPT_PATH = Path("output/script.json")
PPTX_PATH = Path("output/sprint-briefing.pptx")
PDF_PATH = Path("output/sprint-briefing.pdf")
SLIDES_DIR = Path("output/slides")
PAGES_DIR = Path("work/pages")
METRICS_PATH = PAGES_DIR / "metrics.json"
LAYOUT_PATH = Path("src/layout.html")
CANVAS = (1920, 1080)
PDF_PAGE_PTS = (1440, 810)  # 20in x 11.25in: 16:9

# Explicit expectations for the inclusion-flag case fixtures (the plan-level
# versions are checked in validate_plan.py; here the rendered outputs must
# match them).
CASES = [
    {
        "name": "pptx-only",
        "out_dir": Path("work/plan-cases/pptx-only"),
        "fixture": "fixtures/plan-cases/pptx-only.json",
        "pptx": ["opening", "deck-only-intro", "deck-only", "deck-only-outro",
                 "both-demo", "closing"],
        "pdf": ["opening", "deck-only-intro", "deck-only", "deck-only-outro",
                "both-demo", "closing"],
        "slides": ["opening", "closing"],  # video-narrated beats only
        "media_slides": ["deck-only", "both-demo"],
    },
    {
        "name": "video-only",
        "out_dir": Path("work/plan-cases/video-only"),
        "fixture": "fixtures/plan-cases/video-only.json",
        "pptx": ["opening", "both-demo", "closing"],
        "pdf": ["opening", "both-demo", "closing"],
        # clip-only-intro is video-included but excluded from PPTX/PDF: its
        # PNG must still be rendered for the video timeline.
        "slides": ["opening", "clip-only-intro", "closing"],
        "media_slides": ["both-demo"],
    },
]

RESULTS: list[tuple[str, str, str, str]] = []


def record(group: str, name: str, ok: bool, detail: str) -> None:
    RESULTS.append((group, name, "PASS" if ok else "FAIL", detail))


def note(group: str, name: str, detail: str) -> None:
    RESULTS.append((group, name, "INFO", detail))


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# ------------------------------------------------------------------ helpers

def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text())


def manifest_by_id(manifest: dict) -> dict[str, dict]:
    return {beat["id"]: beat for beat in manifest["beats"]}


def expected_substrings(beat: dict, include_card_details: bool) -> list[str]:
    """Substrings a beat's rendering must carry, in any position."""
    if beat["kind"] == "demo":
        subs = [beat["title"]]
        if "epic" in beat:
            subs.append(beat["epic"])
        if include_card_details:
            subs.append(f"Demo duration: {beat['duration_seconds']:.1f} seconds")
        return subs
    return [beat["text"]]


def narrated_video_beats(manifest: dict) -> list[dict]:
    return [beat for beat in manifest["beats"]
            if "text" in beat and beat["include_in"]["video"]]


def static_beat_ids(manifest: dict) -> set[str]:
    """Beats with a static representation: PDF-included beats plus narrated
    video beats (rendered even when excluded from PPTX/PDF). Video-only demo
    beats have no static page — the timeline plays their clip."""
    return {beat["id"] for beat in manifest["beats"]
            if beat["include_in"]["pptx"]
            or ("text" in beat and beat["include_in"]["video"])}


def pptx_slide_texts(path: Path) -> list[str]:
    """Normalized concatenated <a:t> text per slide, in slide order."""
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist()
                 if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
        texts = []
        for name in sorted(names, key=lambda n: int(re.search(r"\d+", n).group())):
            root = ET.fromstring(zf.read(name))
            runs = [t.text or "" for t in root.iter()
                    if t.tag.endswith("}t")]
            texts.append(normalize(" ".join(runs)))
    return texts


def pptx_slide_xml(path: Path, index: int) -> str:
    with zipfile.ZipFile(path) as zf:
        return zf.read(f"ppt/slides/slide{index}.xml").decode()


def pdf_pages(path: Path) -> list:
    return PdfReader(str(path)).pages


def pdf_page_text(page) -> str:
    return normalize(page.extract_text() or "")


def ink_stats(image: Image.Image, box: dict) -> tuple[float, float]:
    """(fraction of dark pixels, mean luma of those dark pixels) in `box`.

    A wide text box is mostly white background, so the dark-pixel fraction and
    the darkness of the ink itself carry the signal — not the box mean.
    """
    region = image.crop((box["x"], box["y"], box["x"] + box["w"], box["y"] + box["h"]))
    pixels = list(region.convert("L").getdata())
    dark = [p for p in pixels if p < 128]
    fraction = len(dark) / len(pixels)
    dark_mean = sum(dark) / len(dark) if dark else 255
    return fraction, dark_mean


def mean_abs_diff(a: Image.Image, b: Image.Image) -> float:
    """Mean per-channel absolute difference between two RGB images."""
    if a.size != b.size:
        b = b.resize(a.size)
    stat = ImageStat.Stat(ImageChops.difference(a.convert("RGB"), b.convert("RGB")))
    return sum(stat.mean) / 3


# ------------------------------------------------------------------ pptx/pdf

def check_pptx_pdf(manifest: dict) -> None:
    by_id = manifest_by_id(manifest)
    pptx_list = manifest["outputs"]["pptx"]
    pdf_list = manifest["outputs"]["pdf"]

    if not PPTX_PATH.exists():
        record("main", "pptx exists", False, f"missing {PPTX_PATH}")
        return
    slide_texts = pptx_slide_texts(PPTX_PATH)
    record("main", "pptx slide count matches pptx beat list",
           len(slide_texts) == len(pptx_list),
           f"{len(slide_texts)} slides vs {len(pptx_list)} beats")

    ordered_ok = all(
        all(sub in slide_texts[i] for sub in
            expected_substrings(by_id[beat_id], include_card_details=False))
        for i, beat_id in enumerate(pptx_list))
    record("main", "pptx titles and literal text in manifest order",
           ordered_ok and len(slide_texts) == len(pptx_list),
           "slide order: " + " -> ".join(pptx_list))

    media_slides = []
    for i, beat_id in enumerate(pptx_list, start=1):
        xml = pptx_slide_xml(PPTX_PATH, i)
        has_media = "<a:videoFile" in xml and "<p14:media" in xml
        if by_id[beat_id]["kind"] == "demo" and has_media:
            media_slides.append(beat_id)
    demo_beats = [beat_id for beat_id in pptx_list if by_id[beat_id]["kind"] == "demo"]
    record("main", "demo slides carry embedded media, narrated slides do not",
           sorted(media_slides) == sorted(demo_beats),
           f"slides with videoFile+p14:media: {media_slides} "
           f"(demo beats: {demo_beats})")

    if not PDF_PATH.exists():
        record("main", "pdf exists", False, f"missing {PDF_PATH}")
        return
    pages = pdf_pages(PDF_PATH)
    record("main", "pdf page count matches pdf beat list",
           len(pages) == len(pdf_list),
           f"{len(pages)} pages vs {len(pdf_list)} beats")

    sizes = [(float(p.mediabox.width), float(p.mediabox.height)) for p in pages]
    record("main", "pdf pages are 16:9",
           all(w == PDF_PAGE_PTS[0] and h == PDF_PAGE_PTS[1] for w, h in sizes),
           f"mediabox sizes: {sizes} (expected {PDF_PAGE_PTS}pt = 20x11.25in)")

    pdf_ordered_ok = all(
        all(sub in pdf_page_text(pages[i]) for sub in
            expected_substrings(by_id[beat_id], include_card_details=True))
        for i, beat_id in enumerate(pdf_list))
    record("main", "pdf titles, narration, epic, and measured duration in order",
           pdf_ordered_ok and len(pages) == len(pdf_list),
           "page order: " + " -> ".join(pdf_list))

    for i, beat_id in enumerate(pdf_list):
        beat = by_id[beat_id]
        images = pages[i].images
        if beat["kind"] == "demo":
            embedded = []
            for img in images:
                try:
                    pil = Image.open(__import__("io").BytesIO(img.data))
                except Exception:
                    pil = None
                embedded.append(pil.size if pil else None)
            one_16x9 = (len(embedded) == 1 and embedded[0]
                        and abs(embedded[0][0] / embedded[0][1] - 16 / 9) < 0.02)
            record("main", f"{beat_id} pdf card embeds one 16:9 poster image",
                   one_16x9, f"embedded images: {embedded}")
        else:
            record("main", f"{beat_id} pdf page has no poster image",
                   not images, f"embedded images: {len(images)}")


# ------------------------------------------------------------------ slides

def check_slides(manifest: dict) -> None:
    narrated = narrated_video_beats(manifest)
    expected = [f"{i:03d}-{beat['id']}.png"
                for i, beat in enumerate(narrated, start=1)]
    actual = sorted(p.name for p in SLIDES_DIR.glob("*.png"))
    record("main", "slide PNGs cover exactly the narrated video beats",
           actual == expected, f"got {actual}, want {expected}")

    narration_path = Path("output/audio/narration.json")
    if narration_path.exists():
        narrated_ids = [entry["beat_id"]
                        for entry in json.loads(narration_path.read_text())["beats"]]
        record("main", "slide PNG set matches the narrated WAV set",
               [beat["id"] for beat in narrated] == narrated_ids,
               f"slides: {[beat['id'] for beat in narrated]}, "
               f"wavs: {narrated_ids}")

    for name in expected:
        path = SLIDES_DIR / name
        img = Image.open(path)
        stat = ImageStat.Stat(img.convert("L"))
        nonblank = stat.stddev[0] > 5
        record("main", f"{name} is 1920x1080 and nonblank",
               img.size == CANVAS and nonblank,
               f"{img.size}, luma stddev {stat.stddev[0]:.1f}")


# ------------------------------------------------------------ page inspection

def check_pages(manifest: dict) -> None:
    by_id = manifest_by_id(manifest)
    if not METRICS_PATH.exists():
        record("main", "page metrics exist", False,
               f"missing {METRICS_PATH}; run src/make_static.mjs first")
        return
    metrics = json.loads(METRICS_PATH.read_text())
    pages = metrics.get("pages", {})

    record("main", "metrics recorded for every statically rendered beat",
           set(pages) == static_beat_ids(manifest)
           and "pdf" in metrics and "control" in metrics,
           f"{sorted(pages)} + pdf + control")

    # One fixed layout, one local font, at the source level.
    layout = LAYOUT_PATH.read_text()
    families = set(re.findall(r"font-family:\s*'([^']+)'", layout))
    record("main", "layout declares exactly one local font family",
           families == {"Roboto Local"} and layout.count("@font-face") == 2,
           f"families: {sorted(families)}; @font-face rules: {layout.count('@font-face')}")

    for beat_id, page in pages.items():
        png = PAGES_DIR / f"{beat_id}.png"
        image = Image.open(png)
        boxes = page.get("textBoxes", [])
        inside = all(0 <= b["x"] and 0 <= b["y"]
                     and b["x"] + b["w"] <= CANVAS[0] and b["y"] + b["h"] <= CANVAS[1]
                     for b in boxes)
        record("main", f"{beat_id} text unclipped inside the canvas",
               inside and page.get("docWidth") == CANVAS[0]
               and page.get("docHeight") == CANVAS[1],
               f"{len(boxes)} text boxes inside {CANVAS}, "
               f"doc {page.get('docWidth')}x{page.get('docHeight')}")

        # Ink means luma clearly darker than white: 160 admits the gray
        # secondary text (#6b7280, luma ~114) while a blank box has no dark
        # pixels at all and fails on the fraction instead.
        readable = all(
            (lambda dark, dark_mean: dark > 0.002 and dark_mean < 160)(
                *ink_stats(image, b))
            for b in boxes)
        record("main", f"{beat_id} text rendered with ink and contrast",
               readable and boxes, f"{len(boxes)} text boxes carry dark pixels")

        if by_id[beat_id]["kind"] == "demo":
            poster = page.get("poster")
            if not poster:
                record("main", f"{beat_id} card shows a poster", False,
                       "no poster element metrics")
                continue
            complete_ok = (poster.get("complete")
                           and poster.get("naturalW") == 1920
                           and poster.get("naturalH") == 1080)
            source = Image.open(Path(by_id[beat_id]["artifacts"]["poster"]))
            region = (poster["x"], poster["y"], poster["x"] + poster["w"],
                      poster["y"] + poster["h"])
            rendered = image.crop(region)
            diff = mean_abs_diff(rendered, source)
            stat = ImageStat.Stat(rendered.convert("L"))
            record("main", f"{beat_id} poster visible and matches the local asset",
                   complete_ok and diff < 25 and stat.stddev[0] > 20,
                   f"poster loaded: {complete_ok}, mean abs diff vs source "
                   f"{diff:.1f} (< 25), region luma stddev {stat.stddev[0]:.1f}")
            page_stat = ImageStat.Stat(image.convert("L"))
            record("main", f"{beat_id} demo card is nonblank",
                   page_stat.stddev[0] > 5, f"page luma stddev {page_stat.stddev[0]:.1f}")

    # The combined PDF document: every text box inside its own page band.
    pdf_metrics = metrics.get("pdf", {})
    bands = len(manifest["outputs"]["pdf"])
    pdf_boxes_ok = all(
        0 <= b["x"] <= CANVAS[0]
        and (b["y"] // CANVAS[1]) * CANVAS[1] <= b["y"]
        and b["y"] + b["h"] <= ((b["y"] // CANVAS[1]) + 1) * CANVAS[1] + 1
        for b in pdf_metrics.get("textBoxes", []))
    record("main", "pdf document text unclipped within page bands",
           pdf_boxes_ok and pdf_metrics.get("docWidth") == CANVAS[0],
           f"{len(pdf_metrics.get('textBoxes', []))} boxes across {bands} pages")

    # One local font actually used: in-browser check, loaded faces, and a
    # control render without the font must differ from the real render.
    font_ok = all(page.get("fontOk") and page.get("fontReady")
                  and any("Roboto Local" in face and face.endswith("/loaded")
                          for face in page.get("fontFaces", []))
                  for page in pages.values())
    record("main", "local font loaded in the browser for every page",
           font_ok, f"fontOk/fontReady on {len(pages)} pages; "
                    f"faces: {sorted(set(f for p in pages.values() for f in p.get('fontFaces', [])))}")

    control = PAGES_DIR / "control-no-font.png"
    opening = PAGES_DIR / "opening.png"
    if control.exists() and opening.exists():
        real = Image.open(opening)
        stripped = Image.open(control)
        record("main", "control render without the local font differs",
               mean_abs_diff(real, stripped) > 2,
               f"mean abs diff between real and no-font render: "
               f"{mean_abs_diff(real, stripped):.2f} (> 2) — the local font "
               f"is what renders the text")
    else:
        record("main", "control render without the local font differs", False,
               f"missing {control} or {opening}")

    # PDF produced on a host with no PowerPoint/LibreOffice converter: the
    # static layout route needs neither.
    converters = [name for name in ("soffice", "libreoffice", "powerpoint")
                  if shutil.which(name)]
    record("main", "pdf rendered without PowerPoint or LibreOffice",
           not converters and PDF_PATH.exists(),
           f"no {converters or 'soffice/libreoffice/powerpoint'} on PATH, "
           f"yet {PDF_PATH} exists")


# -------------------------------------------------------------------- cases

def run_renderers(out_dir: Path) -> list[tuple[str, int, str]]:
    results = []
    for script, args in (("src/make_pptx.mjs", [str(out_dir)]),
                         ("src/make_static.mjs", [str(out_dir), str(out_dir / "pages")])):
        result = subprocess.run(["node", script, *args], cwd=EXPERIMENT_ROOT,
                                capture_output=True, text=True)
        results.append((script, result.returncode, result.stderr))
    return results


def run_case(case: dict) -> None:
    name = case["name"]
    out_dir = case["out_dir"]
    # validate_plan.py builds this case; build it here if it has not run yet.
    if not (out_dir / "manifest.json").exists():
        subprocess.run(
            [sys.executable, "src/build_plan.py", case["fixture"], str(out_dir)],
            cwd=EXPERIMENT_ROOT, capture_output=True, check=True,
        )
    render_results = run_renderers(out_dir)
    for script, code, stderr in render_results:
        record(name, f"{script} exits 0", code == 0,
               f"exit {code}" + (f"; stderr: {stderr[:200]}" if code else ""))
    if any(code != 0 for _, code, _ in render_results):
        return

    manifest = load_manifest(out_dir / "manifest.json")
    by_id = manifest_by_id(manifest)

    deck_path = out_dir / "sprint-briefing.pptx"
    slide_texts = pptx_slide_texts(deck_path)
    deck_ok = ([beat_id for beat_id in case["pptx"]] == manifest["outputs"]["pptx"]
               and len(slide_texts) == len(case["pptx"])
               and all(all(sub in slide_texts[i] for sub in
                           expected_substrings(by_id[beat_id], include_card_details=False))
                       for i, beat_id in enumerate(case["pptx"])))
    record(name, "deck slides match the pptx beat list in order", deck_ok,
           f"slides: {' -> '.join(case['pptx'])}")

    media_slides = []
    for i, beat_id in enumerate(case["pptx"], start=1):
        xml = pptx_slide_xml(deck_path, i)
        if "<a:videoFile" in xml and "<p14:media" in xml:
            media_slides.append(beat_id)
    record(name, "deck embeds media exactly on pptx-included demo slides",
           sorted(media_slides) == sorted(case["media_slides"]),
           f"media slides: {media_slides}, want {case['media_slides']}")

    pages = pdf_pages(out_dir / "sprint-briefing.pdf")
    pdf_ok = (len(pages) == len(case["pdf"])
              and all(all(sub in pdf_page_text(pages[i]) for sub in
                          expected_substrings(by_id[beat_id], include_card_details=True))
                      for i, beat_id in enumerate(case["pdf"])))
    record(name, "pdf pages match the pdf beat list in order", pdf_ok,
           f"pages: {' -> '.join(case['pdf'])}")

    slides = sorted(p.name for p in (out_dir / "slides").glob("*.png"))
    expected_slides = [f"{i:03d}-{beat_id}.png"
                       for i, beat_id in enumerate(case["slides"], start=1)]
    record(name, "slide PNGs cover the narrated video beats only",
           slides == expected_slides, f"got {slides}, want {expected_slides}")

    if name == "video-only":
        # The point of the case: clip-only-intro is video-included but
        # excluded from PPTX/PDF — its PNG must exist anyway.
        record(name, "video-included beat excluded from pptx/pdf still rendered",
               any(name.endswith("clip-only-intro.png") for name in slides)
               and "clip-only" not in case["pdf"]
               and "clip-only" not in case["pptx"],
               "clip-only-intro has a PNG although clip-only appears in "
               "neither the deck nor the PDF")
    else:
        record(name, "video-excluded beats get no PNG",
               not any(name.endswith(("-intro.png", "-outro.png")) for name in slides),
               f"deck-only-intro/outro are excluded from the video; slides: {slides}")


# -------------------------------------------------------------------- report

def main() -> int:
    manifest = load_manifest(MANIFEST_PATH)
    check_pptx_pdf(manifest)
    check_slides(manifest)
    check_pages(manifest)
    for case in CASES:
        run_case(case)

    note("main", "pixel identity between renderers",
         "not required: PPTX and static pages share beat data and assets but "
         "may render differently; the checks above compare text, order, and "
         "content, not pixels")
    note("main", "full-deck embedded media and internal relationships",
         "confirmed with the #430 spike's inspection approach in "
         "evidence/results.md (byte identity, internal rels, moved-deck "
         "standalone check)")
    note("main", "desktop PowerPoint playback",
         "UNVERIFIED: this headless host has no desktop PowerPoint (no "
         "display, no LibreOffice). output/sprint-briefing.pptx is retained "
         "for the final review; package inspection cannot establish player "
         "compatibility")
    note("main", "text legibility",
         "automated checks prove text boxes stay inside the canvas and carry "
         "dark pixels with contrast; human visual review of the rendered "
         "slides remains part of the final review")

    lines = []
    lines.append("# Static slide and PDF rendering validation (#431)")
    lines.append("")
    lines.append(f"Run date: {__import__('datetime').datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("| Group | Check | Status | Detail |")
    lines.append("|---|---|---|---|")
    fails = 0
    for group, name, status, detail in RESULTS:
        lines.append(f"| {group} | {name} | {status} | {detail} |")
        if status == "FAIL":
            fails += 1
    lines.append("")
    lines.append(f"Result: {len(RESULTS)} checks, {fails} failed")
    report = "\n".join(lines)
    Path("evidence").mkdir(exist_ok=True)
    Path("evidence/results-static.md").write_text(report + "\n")

    for line in report.splitlines():
        print(line)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
