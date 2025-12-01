# Presentation-plan validation (#428)

Run date: 2026-09-14T09:49:49

| Group | Check | Status | Detail |
|---|---|---|---|
| main | fixture records PDF follows PPTX | PASS | note: Presentation plan for the #428 beat/artifact-metadata stage. PDF follows PPTX inclusion: t... |
| main | fixture ids are filename-safe | PASS | ids: ['new-checkout', 'admin-controls'] vs ^[a-z0-9][a-z0-9-]*$ |
| main | fixture leaves inclusion flags unset | PASS | both demos rely on the default flags |
| main | script beat order | PASS | got [('opening', 'opening'), ('new-checkout-intro', 'intro'), ('new-checkout', 'demo'), ('new-checkout-outro', 'outro'), ('admin-controls-intro', 'intro'), ('admin-controls', 'demo'), ('closing', 'closing')], want [('opening', 'opening'), ('new-checkout-intro', 'intro'), ('new-checkout', 'demo'), ('new-checkout-outro', 'outro'), ('admin-controls-intro', 'intro'), ('admin-controls', 'demo'), ('closing', 'closing')] |
| main | manifest beat order matches script | PASS | got [('opening', 'opening'), ('new-checkout-intro', 'intro'), ('new-checkout', 'demo'), ('new-checkout-outro', 'outro'), ('admin-controls-intro', 'intro'), ('admin-controls', 'demo'), ('closing', 'closing')] |
| main | fixed opening text | PASS | 'Welcome to this sprint review.' |
| main | fixed closing text | PASS | 'That concludes this sprint review. Thank you.' |
| main | literal intro/outro narration matches fixture | PASS | every supplied intro/outro text carried verbatim |
| main | no narration over demo beats | PASS | demo beats carry no text, so no TTS is ever placed over demo audio |
| main | epic/release/business_value carried | PASS | new-checkout: Checkout Modernization / 2026.08 / Reduced purchase friction; admin-controls: Enterprise Administration with release/business_value absent |
| main | default inclusion flags | PASS | both demo beats include_in {'pptx': True, 'video': True} |
| main | pptx beat list | PASS | got ['opening', 'new-checkout-intro', 'new-checkout', 'new-checkout-outro', 'admin-controls-intro', 'admin-controls', 'closing'] |
| main | pdf follows pptx | PASS | pdf list == pptx list: ['opening', 'new-checkout-intro', 'new-checkout', 'new-checkout-outro', 'admin-controls-intro', 'admin-controls', 'closing'] |
| main | video beat list | PASS | got ['opening', 'new-checkout-intro', 'new-checkout', 'new-checkout-outro', 'admin-controls-intro', 'admin-controls', 'closing'] |
| main | manifest records the pdf assumption | PASS | True |
| main | source master recorded | PASS | input/sprint-demo.mp4 |
| main | source duration measured from the master | PASS | manifest 16.000s, ffprobe 16.000s |
| main | new-checkout artifact paths | PASS | output/demos/new-checkout.mp4 exists: True, output/demos/new-checkout-poster.png exists: True |
| main | new-checkout measured duration | PASS | measured 5.200s vs declared 5.167s (delta 0.033s <= 0.035s) |
| main | new-checkout source range | PASS | 00:00:02.317..00:00:07.484 (2.317..7.484) |
| main | admin-controls artifact paths | PASS | output/demos/admin-controls.mp4 exists: True, output/demos/admin-controls-poster.png exists: True |
| main | admin-controls measured duration | PASS | measured 4.600s vs declared 4.579s (delta 0.021s <= 0.035s) |
| main | admin-controls source range | PASS | 00:00:09.623..00:00:14.202 (9.623..14.202) |
| main | mp4 offsets reserved for composition | PASS | offsets populated after composition, null before composition |
| main | extraction happens once per included demo | INFO | build_plan.py extracts each demo included in either output in a single extract_clip call, regardless of how many outputs use it |
| missing-optional-text | builder exit | PASS | exit 0 |
| missing-optional-text | script beat order | PASS | got [('opening', 'opening'), ('plain-demo', 'demo'), ('closing', 'closing')], want [('opening', 'opening'), ('plain-demo', 'demo'), ('closing', 'closing')] |
| missing-optional-text | manifest beat order matches script | PASS | got [('opening', 'opening'), ('plain-demo', 'demo'), ('closing', 'closing')] |
| missing-optional-text | pptx beat list | PASS | got ['opening', 'plain-demo', 'closing'], want ['opening', 'plain-demo', 'closing'] |
| missing-optional-text | pdf beat list | PASS | got ['opening', 'plain-demo', 'closing'], want ['opening', 'plain-demo', 'closing'] |
| missing-optional-text | video beat list | PASS | got ['opening', 'plain-demo', 'closing'], want ['opening', 'plain-demo', 'closing'] |
| missing-optional-text | pdf follows pptx | PASS | pdf == pptx: ['opening', 'plain-demo', 'closing'] |
| missing-optional-text | plain-demo clip extracted | PASS | work/plan-cases/missing-optional-text/demos/plain-demo.mp4 |
| missing-optional-text | plain-demo artifact path and measured duration | PASS | clip path work/plan-cases/missing-optional-text/demos/plain-demo.mp4, measured 5.200s vs declared 5.167s |
| missing-optional-text | plain-demo poster extracted | PASS | work/plan-cases/missing-optional-text/demos/plain-demo-poster.png |
| pptx-only | builder exit | PASS | exit 0 |
| pptx-only | script beat order | PASS | got [('opening', 'opening'), ('deck-only-intro', 'intro'), ('deck-only', 'demo'), ('deck-only-outro', 'outro'), ('both-demo', 'demo'), ('closing', 'closing')], want [('opening', 'opening'), ('deck-only-intro', 'intro'), ('deck-only', 'demo'), ('deck-only-outro', 'outro'), ('both-demo', 'demo'), ('closing', 'closing')] |
| pptx-only | manifest beat order matches script | PASS | got [('opening', 'opening'), ('deck-only-intro', 'intro'), ('deck-only', 'demo'), ('deck-only-outro', 'outro'), ('both-demo', 'demo'), ('closing', 'closing')] |
| pptx-only | pptx beat list | PASS | got ['opening', 'deck-only-intro', 'deck-only', 'deck-only-outro', 'both-demo', 'closing'], want ['opening', 'deck-only-intro', 'deck-only', 'deck-only-outro', 'both-demo', 'closing'] |
| pptx-only | pdf beat list | PASS | got ['opening', 'deck-only-intro', 'deck-only', 'deck-only-outro', 'both-demo', 'closing'], want ['opening', 'deck-only-intro', 'deck-only', 'deck-only-outro', 'both-demo', 'closing'] |
| pptx-only | video beat list | PASS | got ['opening', 'both-demo', 'closing'], want ['opening', 'both-demo', 'closing'] |
| pptx-only | pdf follows pptx | PASS | pdf == pptx: ['opening', 'deck-only-intro', 'deck-only', 'deck-only-outro', 'both-demo', 'closing'] |
| pptx-only | both-demo clip extracted | PASS | work/plan-cases/pptx-only/demos/both-demo.mp4 |
| pptx-only | both-demo artifact path and measured duration | PASS | clip path work/plan-cases/pptx-only/demos/both-demo.mp4, measured 4.600s vs declared 4.579s |
| pptx-only | deck-only clip extracted | PASS | work/plan-cases/pptx-only/demos/deck-only.mp4 |
| pptx-only | deck-only artifact path and measured duration | PASS | clip path work/plan-cases/pptx-only/demos/deck-only.mp4, measured 5.200s vs declared 5.167s |
| pptx-only | both-demo poster extracted | PASS | work/plan-cases/pptx-only/demos/both-demo-poster.png |
| pptx-only | deck-only poster extracted | PASS | work/plan-cases/pptx-only/demos/deck-only-poster.png |
| video-only | builder exit | PASS | exit 0 |
| video-only | script beat order | PASS | got [('opening', 'opening'), ('clip-only-intro', 'intro'), ('clip-only', 'demo'), ('both-demo', 'demo'), ('closing', 'closing')], want [('opening', 'opening'), ('clip-only-intro', 'intro'), ('clip-only', 'demo'), ('both-demo', 'demo'), ('closing', 'closing')] |
| video-only | manifest beat order matches script | PASS | got [('opening', 'opening'), ('clip-only-intro', 'intro'), ('clip-only', 'demo'), ('both-demo', 'demo'), ('closing', 'closing')] |
| video-only | pptx beat list | PASS | got ['opening', 'both-demo', 'closing'], want ['opening', 'both-demo', 'closing'] |
| video-only | pdf beat list | PASS | got ['opening', 'both-demo', 'closing'], want ['opening', 'both-demo', 'closing'] |
| video-only | video beat list | PASS | got ['opening', 'clip-only-intro', 'clip-only', 'both-demo', 'closing'], want ['opening', 'clip-only-intro', 'clip-only', 'both-demo', 'closing'] |
| video-only | pdf follows pptx | PASS | pdf == pptx: ['opening', 'both-demo', 'closing'] |
| video-only | both-demo clip extracted | PASS | work/plan-cases/video-only/demos/both-demo.mp4 |
| video-only | both-demo artifact path and measured duration | PASS | clip path work/plan-cases/video-only/demos/both-demo.mp4, measured 4.600s vs declared 4.579s |
| video-only | clip-only clip extracted | PASS | work/plan-cases/video-only/demos/clip-only.mp4 |
| video-only | clip-only artifact path and measured duration | PASS | clip path work/plan-cases/video-only/demos/clip-only.mp4, measured 5.200s vs declared 5.167s |
| video-only | both-demo poster extracted | PASS | work/plan-cases/video-only/demos/both-demo-poster.png |
| video-only | clip-only poster omitted | PASS | no work/plan-cases/video-only/demos/clip-only-poster.png |
| both-excluded | builder exit | PASS | exit 0 |
| both-excluded | script beat order | PASS | got [('opening', 'opening'), ('shown', 'demo'), ('closing', 'closing')], want [('opening', 'opening'), ('shown', 'demo'), ('closing', 'closing')] |
| both-excluded | manifest beat order matches script | PASS | got [('opening', 'opening'), ('shown', 'demo'), ('closing', 'closing')] |
| both-excluded | pptx beat list | PASS | got ['opening', 'shown', 'closing'], want ['opening', 'shown', 'closing'] |
| both-excluded | pdf beat list | PASS | got ['opening', 'shown', 'closing'], want ['opening', 'shown', 'closing'] |
| both-excluded | video beat list | PASS | got ['opening', 'shown', 'closing'], want ['opening', 'shown', 'closing'] |
| both-excluded | pdf follows pptx | PASS | pdf == pptx: ['opening', 'shown', 'closing'] |
| both-excluded | shown clip extracted | PASS | work/plan-cases/both-excluded/demos/shown.mp4 |
| both-excluded | shown artifact path and measured duration | PASS | clip path work/plan-cases/both-excluded/demos/shown.mp4, measured 4.600s vs declared 4.579s |
| both-excluded | skipped clip omitted | PASS | no work/plan-cases/both-excluded/demos/skipped.mp4 |
| both-excluded | shown poster extracted | PASS | work/plan-cases/both-excluded/demos/shown-poster.png |
| both-excluded | skipped poster omitted | PASS | no work/plan-cases/both-excluded/demos/skipped-poster.png |
| invalid-reversed | builder fails before claiming completion | PASS | exit 1, marker 'violates 0 <= start < end' in stderr: True, no script/manifest written: True |
| invalid-out-of-range | builder fails before claiming completion | PASS | exit 1, marker 'violates 0 <= start < end' in stderr: True, no script/manifest written: True |
| invalid-duplicate-id | builder fails before claiming completion | PASS | exit 1, marker 'duplicate demo id' in stderr: True, no script/manifest written: True |
| invalid-unsafe-id | builder fails before claiming completion | PASS | exit 1, marker 'filename-safe' in stderr: True, no script/manifest written: True |

Result: 77 checks, 0 failed
