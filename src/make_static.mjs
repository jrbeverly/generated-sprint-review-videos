#!/usr/bin/env node
// Static renderer for #431: one fixed 1920x1080 (16:9) HTML/CSS layout
// (src/layout.html) and one local font, rendered by the pinned Playwright
// Chromium (kept experiment-local under assets/browsers).
//
//   - Every beat with a static representation (PDF-included beats plus
//     narrated video beats) is rendered once through the fixed layout into
//     an ordinary work file (work/pages/<id>.html/.png) plus per-page layout
//     metrics (work/pages/metrics.json) for validate_static.py. Video-only
//     demo beats have no static page: the timeline plays their clip.
//   - output/slides/NNN-<id>.png: one PNG per narrated video beat, numbered
//     in script order — the same set make_narration.py narrates. Video-
//     included beats are rendered even when excluded from PPTX/PDF.
//   - output/sprint-briefing.pdf: one 16:9 page per PDF-included beat, in
//     manifest order, printed directly from the same layout by Chromium — no
//     PowerPoint, no LibreOffice, no conversion of embedded video. Demo beats
//     are static cards: poster, title, optional epic, measured duration.
//   - A control render without the local font proves the font is actually
//     used (this host has system fonts that would otherwise be the fallback).
//
// Usage: node src/make_static.mjs [rootDir [workDir]]
//   rootDir: where manifest.json lives and slides/sprint-briefing.pdf go
//            (default output/)
//   workDir: where the per-beat pages and metrics go (default work/pages)
//
// No animation, transitions, template engine, or slide editor. The font and
// the posters are inlined as data URIs, so the render needs no network and
// no system font.
import { copyFileSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
process.env.PLAYWRIGHT_BROWSERS_PATH ??= join(ROOT, 'assets', 'browsers');
const { chromium } = await import('playwright');

const LAYOUT = readFileSync(join(ROOT, 'src', 'layout.html'), 'utf8');
const FONT_DIR = join(ROOT, 'node_modules', '@fontsource', 'roboto', 'files');
const FONT_400 = readFileSync(join(FONT_DIR, 'roboto-latin-400-normal.woff2'));
const FONT_700 = readFileSync(join(FONT_DIR, 'roboto-latin-700-normal.woff2'));
const CANVAS = { width: 1920, height: 1080 };
const KICKER = 'SPRINT REVIEW';
const FONTS_RE = /\/\*__FONTS_BEGIN__\*\/[\s\S]*?\/\*__FONTS_END__\*\//;

const escapeHtml = (s) =>
  s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const dataUri = (buf, mime) => `data:${mime};base64,${buf.toString('base64')}`;

function layoutWithFonts() {
  const faces = [
    "@font-face { font-family: 'Roboto Local'; font-style: normal; font-weight: 400; src: url('"
      + dataUri(FONT_400, 'font/woff2') + "') format('woff2'); }",
    "@font-face { font-family: 'Roboto Local'; font-style: normal; font-weight: 700; src: url('"
      + dataUri(FONT_700, 'font/woff2') + "') format('woff2'); }",
  ].join('\n');
  return LAYOUT.replace(FONTS_RE, faces);
}
const layoutNoFonts = () => LAYOUT.replace(FONTS_RE, '');

// --- fixed content structures per beat kind (no template engine) ------------

function narratedContent(beat, demoTitle) {
  const kicker = demoTitle ?? KICKER;
  return [
    `    <div class="kicker">${escapeHtml(kicker)}</div>`,
    `    <h1 class="headline">${escapeHtml(beat.text)}</h1>`,
  ].join('\n');
}

function demoCardContent(beat) {
  const poster = dataUri(readFileSync(join(ROOT, beat.artifacts.poster)), 'image/png');
  const lines = [
    `    <div class="kicker">${KICKER}</div>`,
    '    <div class="card">',
    `      <img class="poster" src="${poster}" alt="Demo poster frame">`,
    `      <h1 class="card-title">${escapeHtml(beat.title)}</h1>`,
  ];
  if (beat.epic) lines.push(`      <div class="epic">${escapeHtml(beat.epic)}</div>`);
  lines.push(`      <div class="duration">Demo duration: ${beat.duration_seconds.toFixed(1)} seconds</div>`);
  lines.push('    </div>');
  return lines.join('\n');
}

function beatContent(beat, demos) {
  const demoTitle = beat.demo_id ? demos[beat.demo_id]?.title : null;
  if (beat.kind === 'demo') return demoCardContent(beat);
  return narratedContent(beat, demoTitle);
}

// The comment at the top of layout.html also mentions __CONTENT__, so the
// replacement targets the exact body slot rather than the first occurrence.
const SLOT = '<body>\n__CONTENT__\n</body>';

function pageHtml(layout, beat, demos) {
  return layout.replace(SLOT, `<body>\n<div class="page">\n${beatContent(beat, demos)}\n</div>\n</body>`);
}

// --- browser rendering ------------------------------------------------------

const METRICS_FN = () => {
  const box = (el) => {
    const r = el.getBoundingClientRect();
    return {
      cls: el.className, text: (el.textContent || '').trim().replace(/\s+/g, ' '),
      x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
    };
  };
  const posterEl = document.querySelector('img.poster');
  const poster = posterEl ? (() => {
    const r = posterEl.getBoundingClientRect();
    return {
      x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
      naturalW: posterEl.naturalWidth, naturalH: posterEl.naturalHeight,
      complete: posterEl.complete,
    };
  })() : null;
  return {
    textBoxes: [...document.querySelectorAll('.kicker, .headline, .card-title, .epic, .duration')].map(box),
    poster,
    fontReady: document.fonts.status === 'loaded',
    fontOk: document.fonts.check('16px "Roboto Local"')
      && document.fonts.check('bold 16px "Roboto Local"'),
    fontFaces: [...document.fonts].map((f) => `${f.family}/${f.weight}/${f.status}`),
    docWidth: document.documentElement.scrollWidth,
    docHeight: document.documentElement.scrollHeight,
  };
};

// Both weights of the local font are loaded explicitly: Chromium loads
// declared faces lazily, and pages that never use the regular weight would
// otherwise leave it unloaded and make the font metrics misleading.
const LOAD_FONTS_FN = () => Promise.all([
  document.fonts.load('16px "Roboto Local"'),
  document.fonts.load('bold 16px "Roboto Local"'),
]);

async function renderHtml(browser, htmlPath, pngPath) {
  const page = await browser.newPage({ viewport: CANVAS });
  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(LOAD_FONTS_FN);
  await page.evaluate(() => Promise.all([...document.images].map(
    (img) => (img.complete ? Promise.resolve()
      : new Promise((res) => { img.onload = img.onerror = res; })))));
  const metrics = await page.evaluate(METRICS_FN);
  await page.screenshot({ path: pngPath });
  await page.close();
  return metrics;
}

async function renderPdf(browser, htmlPath, pdfPath) {
  const page = await browser.newPage({ viewport: CANVAS });
  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(LOAD_FONTS_FN);
  const metrics = await page.evaluate(METRICS_FN);
  await page.pdf({ path: pdfPath, printBackground: true, preferCSSPageSize: true });
  await page.close();
  return metrics;
}

// --- main -------------------------------------------------------------------

async function main() {
  const rootDir = process.argv[2] ? resolve(process.argv[2]) : join(ROOT, 'output');
  const workDir = process.argv[3] ? resolve(process.argv[3]) : join(ROOT, 'work', 'pages');
  const manifest = JSON.parse(readFileSync(join(rootDir, 'manifest.json'), 'utf8'));
  const beats = manifest.beats;
  const demos = Object.fromEntries(
    beats.filter((b) => b.kind === 'demo').map((b) => [b.demo_id, b]));
  const videoNarrated = beats.filter((b) => b.text !== undefined && b.include_in.video);
  const pdfBeats = beats.filter((b) => b.include_in.pptx); // PDF follows PPTX
  // Beats with a static representation: PDF-included beats plus narrated
  // video beats (their PNGs feed the video timeline even when the beat is
  // excluded from PPTX/PDF). A video-only demo beat has no static page at
  // all — the timeline plays its clip instead.
  const staticBeats = beats.filter(
    (b) => b.include_in.pptx || (b.text !== undefined && b.include_in.video));

  // A failed run must not leave a previous run's claim behind.
  rmSync(join(rootDir, 'slides'), { recursive: true, force: true });
  rmSync(join(rootDir, 'sprint-briefing.pdf'), { force: true });
  rmSync(workDir, { recursive: true, force: true });
  mkdirSync(join(rootDir, 'slides'), { recursive: true });
  mkdirSync(workDir, { recursive: true });

  const layout = layoutWithFonts();

  // Every beat is rendered once through the fixed layout; the PNGs live in
  // workDir for inspection and the narrated video ones are copied to slides/.
  const metrics = { pages: {}, pdf: null, control: null };
  const browser = await chromium.launch({
    channel: 'chromium', headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  try {
    for (const beat of staticBeats) {
      const htmlPath = join(workDir, `${beat.id}.html`);
      writeFileSync(htmlPath, pageHtml(layout, beat, demos));
      metrics.pages[beat.id] =
        await renderHtml(browser, htmlPath, join(workDir, `${beat.id}.png`));
    }

    const opening = beats.find((b) => b.id === 'opening');
    const controlPath = join(workDir, 'control-no-font.png');
    writeFileSync(controlPath.replace(/\.png$/, '.html'),
      pageHtml(layoutNoFonts(), opening, demos));
    metrics.control = await renderHtml(browser,
      controlPath.replace(/\.png$/, '.html'), controlPath);

    const pdfHtml = layout.replace(
      SLOT,
      `<body>\n${pdfBeats.map((b) => `<div class="page">\n${beatContent(b, demos)}\n</div>`).join('\n')}\n</body>`);
    const pdfHtmlPath = join(workDir, 'briefing-pdf.html');
    writeFileSync(pdfHtmlPath, pdfHtml);
    metrics.pdf = await renderPdf(browser, pdfHtmlPath, join(rootDir, 'sprint-briefing.pdf'));
  } finally {
    await browser.close();
  }

  videoNarrated.forEach((beat, index) => {
    copyFileSync(join(workDir, `${beat.id}.png`),
      join(rootDir, 'slides', `${String(index + 1).padStart(3, '0')}-${beat.id}.png`));
  });
  writeFileSync(join(workDir, 'metrics.json'), JSON.stringify(metrics, null, 2) + '\n');

  console.log(`rendered ${staticBeats.length} pages to ${workDir}`);
  console.log(`slides: ${videoNarrated.length} narrated video PNGs -> ${join(rootDir, 'slides')}`);
  console.log(`pdf: ${pdfBeats.length} pages -> ${join(rootDir, 'sprint-briefing.pdf')}`);
}

await main();
