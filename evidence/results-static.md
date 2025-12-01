# Static slide and PDF rendering validation (#431)

Run date: 2026-09-14T09:49:54

| Group | Check | Status | Detail |
|---|---|---|---|
| main | pptx slide count matches pptx beat list | PASS | 7 slides vs 7 beats |
| main | pptx titles and literal text in manifest order | PASS | slide order: opening -> new-checkout-intro -> new-checkout -> new-checkout-outro -> admin-controls-intro -> admin-controls -> closing |
| main | demo slides carry embedded media, narrated slides do not | PASS | slides with videoFile+p14:media: ['new-checkout', 'admin-controls'] (demo beats: ['new-checkout', 'admin-controls']) |
| main | pdf page count matches pdf beat list | PASS | 7 pages vs 7 beats |
| main | pdf pages are 16:9 | PASS | mediabox sizes: [(1440.0, 810.0), (1440.0, 810.0), (1440.0, 810.0), (1440.0, 810.0), (1440.0, 810.0), (1440.0, 810.0), (1440.0, 810.0)] (expected (1440, 810)pt = 20x11.25in) |
| main | pdf titles, narration, epic, and measured duration in order | PASS | page order: opening -> new-checkout-intro -> new-checkout -> new-checkout-outro -> admin-controls-intro -> admin-controls -> closing |
| main | opening pdf page has no poster image | PASS | embedded images: 0 |
| main | new-checkout-intro pdf page has no poster image | PASS | embedded images: 0 |
| main | new-checkout pdf card embeds one 16:9 poster image | PASS | embedded images: [(1920, 1080)] |
| main | new-checkout-outro pdf page has no poster image | PASS | embedded images: 0 |
| main | admin-controls-intro pdf page has no poster image | PASS | embedded images: 0 |
| main | admin-controls pdf card embeds one 16:9 poster image | PASS | embedded images: [(1920, 1080)] |
| main | closing pdf page has no poster image | PASS | embedded images: 0 |
| main | slide PNGs cover exactly the narrated video beats | PASS | got ['001-opening.png', '002-new-checkout-intro.png', '003-new-checkout-outro.png', '004-admin-controls-intro.png', '005-closing.png'], want ['001-opening.png', '002-new-checkout-intro.png', '003-new-checkout-outro.png', '004-admin-controls-intro.png', '005-closing.png'] |
| main | slide PNG set matches the narrated WAV set | PASS | slides: ['opening', 'new-checkout-intro', 'new-checkout-outro', 'admin-controls-intro', 'closing'], wavs: ['opening', 'new-checkout-intro', 'new-checkout-outro', 'admin-controls-intro', 'closing'] |
| main | 001-opening.png is 1920x1080 and nonblank | PASS | (1920, 1080), luma stddev 19.3 |
| main | 002-new-checkout-intro.png is 1920x1080 and nonblank | PASS | (1920, 1080), luma stddev 28.9 |
| main | 003-new-checkout-outro.png is 1920x1080 and nonblank | PASS | (1920, 1080), luma stddev 27.3 |
| main | 004-admin-controls-intro.png is 1920x1080 and nonblank | PASS | (1920, 1080), luma stddev 27.1 |
| main | 005-closing.png is 1920x1080 and nonblank | PASS | (1920, 1080), luma stddev 23.0 |
| main | metrics recorded for every statically rendered beat | PASS | ['admin-controls', 'admin-controls-intro', 'closing', 'new-checkout', 'new-checkout-intro', 'new-checkout-outro', 'opening'] + pdf + control |
| main | layout declares exactly one local font family | PASS | families: ['Roboto Local']; @font-face rules: 2 |
| main | opening text unclipped inside the canvas | PASS | 2 text boxes inside (1920, 1080), doc 1920x1080 |
| main | opening text rendered with ink and contrast | PASS | 2 text boxes carry dark pixels |
| main | new-checkout-intro text unclipped inside the canvas | PASS | 2 text boxes inside (1920, 1080), doc 1920x1080 |
| main | new-checkout-intro text rendered with ink and contrast | PASS | 2 text boxes carry dark pixels |
| main | new-checkout text unclipped inside the canvas | PASS | 4 text boxes inside (1920, 1080), doc 1920x1080 |
| main | new-checkout text rendered with ink and contrast | PASS | 4 text boxes carry dark pixels |
| main | new-checkout poster visible and matches the local asset | PASS | poster loaded: True, mean abs diff vs source 0.2 (< 25), region luma stddev 39.9 |
| main | new-checkout demo card is nonblank | PASS | page luma stddev 83.7 |
| main | new-checkout-outro text unclipped inside the canvas | PASS | 2 text boxes inside (1920, 1080), doc 1920x1080 |
| main | new-checkout-outro text rendered with ink and contrast | PASS | 2 text boxes carry dark pixels |
| main | admin-controls-intro text unclipped inside the canvas | PASS | 2 text boxes inside (1920, 1080), doc 1920x1080 |
| main | admin-controls-intro text rendered with ink and contrast | PASS | 2 text boxes carry dark pixels |
| main | admin-controls text unclipped inside the canvas | PASS | 4 text boxes inside (1920, 1080), doc 1920x1080 |
| main | admin-controls text rendered with ink and contrast | PASS | 4 text boxes carry dark pixels |
| main | admin-controls poster visible and matches the local asset | PASS | poster loaded: True, mean abs diff vs source 0.2 (< 25), region luma stddev 46.0 |
| main | admin-controls demo card is nonblank | PASS | page luma stddev 94.1 |
| main | closing text unclipped inside the canvas | PASS | 2 text boxes inside (1920, 1080), doc 1920x1080 |
| main | closing text rendered with ink and contrast | PASS | 2 text boxes carry dark pixels |
| main | pdf document text unclipped within page bands | PASS | 18 boxes across 7 pages |
| main | local font loaded in the browser for every page | PASS | fontOk/fontReady on 7 pages; faces: ['Roboto Local/400/loaded', 'Roboto Local/700/loaded'] |
| main | control render without the local font differs | PASS | mean abs diff between real and no-font render: 2.44 (> 2) — the local font is what renders the text |
| main | pdf rendered without PowerPoint or LibreOffice | PASS | no soffice/libreoffice/powerpoint on PATH, yet output/sprint-briefing.pdf exists |
| pptx-only | src/make_pptx.mjs exits 0 | PASS | exit 0 |
| pptx-only | src/make_static.mjs exits 0 | PASS | exit 0 |
| pptx-only | deck slides match the pptx beat list in order | PASS | slides: opening -> deck-only-intro -> deck-only -> deck-only-outro -> both-demo -> closing |
| pptx-only | deck embeds media exactly on pptx-included demo slides | PASS | media slides: ['deck-only', 'both-demo'], want ['deck-only', 'both-demo'] |
| pptx-only | pdf pages match the pdf beat list in order | PASS | pages: opening -> deck-only-intro -> deck-only -> deck-only-outro -> both-demo -> closing |
| pptx-only | slide PNGs cover the narrated video beats only | PASS | got ['001-opening.png', '002-closing.png'], want ['001-opening.png', '002-closing.png'] |
| pptx-only | video-excluded beats get no PNG | PASS | deck-only-intro/outro are excluded from the video; slides: ['001-opening.png', '002-closing.png'] |
| video-only | src/make_pptx.mjs exits 0 | PASS | exit 0 |
| video-only | src/make_static.mjs exits 0 | PASS | exit 0 |
| video-only | deck slides match the pptx beat list in order | PASS | slides: opening -> both-demo -> closing |
| video-only | deck embeds media exactly on pptx-included demo slides | PASS | media slides: ['both-demo'], want ['both-demo'] |
| video-only | pdf pages match the pdf beat list in order | PASS | pages: opening -> both-demo -> closing |
| video-only | slide PNGs cover the narrated video beats only | PASS | got ['001-opening.png', '002-clip-only-intro.png', '003-closing.png'], want ['001-opening.png', '002-clip-only-intro.png', '003-closing.png'] |
| video-only | video-included beat excluded from pptx/pdf still rendered | PASS | clip-only-intro has a PNG although clip-only appears in neither the deck nor the PDF |
| main | pixel identity between renderers | INFO | not required: PPTX and static pages share beat data and assets but may render differently; the checks above compare text, order, and content, not pixels |
| main | full-deck embedded media and internal relationships | INFO | confirmed with the #430 spike's inspection approach in evidence/results.md (byte identity, internal rels, moved-deck standalone check) |
| main | desktop PowerPoint playback | INFO | UNVERIFIED: this headless host has no desktop PowerPoint (no display, no LibreOffice). output/sprint-briefing.pptx is retained for the final review; package inspection cannot establish player compatibility |
| main | text legibility | INFO | automated checks prove text boxes stay inside the canvas and carry dark pixels with contrast; human visual review of the rendered slides remains part of the final review |

Result: 62 checks, 0 failed
