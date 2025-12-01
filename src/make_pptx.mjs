#!/usr/bin/env node
// Full-deck PPTX for #431: one slide per PPTX-included beat, in manifest
// order. Narrated beats carry their literal text under a small kicker; demo
// beats embed the local MP4 with its poster as the visible cover, using the
// #430 spike's pinned PptxGenJS 4.0.1 addMedia({ type: 'video', cover })
// (the poster data-URI becomes the slide picture's blipFill image).
//
// Usage: node src/make_pptx.mjs [rootDir]
//   rootDir: where manifest.json lives and sprint-briefing.pptx is written
//            (default output/). Demo artifacts resolve from the paths that
//            build_plan.py recorded in manifest.json (experiment-root
//            relative), so the deck embeds local bytes only.
//
// No animations, transitions, template engine, or slide editor.
import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import PptxGenJS from 'pptxgenjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const KICKER = 'Sprint Review';

function main() {
  const rootDir = process.argv[2] ? resolve(process.argv[2]) : join(ROOT, 'output');
  const manifest = JSON.parse(readFileSync(join(rootDir, 'manifest.json'), 'utf8'));
  const beats = manifest.beats;
  const demos = Object.fromEntries(
    beats.filter((b) => b.kind === 'demo').map((b) => [b.demo_id, b]));
  const pptxBeats = beats.filter((b) => b.include_in.pptx);

  const pptx = new PptxGenJS();
  pptx.defineLayout({ name: 'WIDE16x9', width: 13.333, height: 7.5 });
  pptx.layout = 'WIDE16x9';
  pptx.author = 'generated-sprint-review-videos (#431)';
  pptx.title = 'Sprint briefing';

  for (const beat of pptxBeats) {
    const slide = pptx.addSlide();
    if (beat.kind === 'demo') {
      // Title, then the embedded clip with its poster as the visible cover.
      slide.addText(beat.title, {
        x: 0.5, y: 0.3, w: 12.3, h: 0.7, fontSize: 28, bold: true, color: '1F3864',
      });
      const cover = `data:image/png;base64,${
        readFileSync(join(ROOT, beat.artifacts.poster)).toString('base64')}`;
      // 5.7 x 10.13 inches keeps the 16:9 poster/clip aspect on the canvas.
      slide.addMedia({
        type: 'video',
        path: join(ROOT, beat.artifacts.clip),
        cover,
        x: 1.6, y: 1.05, w: 10.13, h: 5.7,
        objectName: `demo-video-${beat.demo_id}`,
      });
      if (beat.epic) {
        slide.addText(beat.epic, {
          x: 0.5, y: 6.85, w: 12.3, h: 0.35, fontSize: 14, color: '595959',
        });
      }
    } else {
      // Literal narration text under a kicker naming its context.
      const kicker = beat.demo_id ? demos[beat.demo_id].title : KICKER;
      slide.addText(kicker, {
        x: 0.5, y: 0.5, w: 12.3, h: 0.4, fontSize: 14, bold: true, color: '1F3864',
      });
      slide.addText(beat.text, {
        x: 0.5, y: 1.15, w: 12.3, h: 3.5, fontSize: 28, bold: true,
        color: '1F2937', valign: 'top',
      });
    }
  }

  const out = join(rootDir, 'sprint-briefing.pptx');
  return pptx.writeFile({ fileName: out }).then(() => {
    console.log(`wrote ${out} (${pptxBeats.length} slides)`);
  });
}

await main();
