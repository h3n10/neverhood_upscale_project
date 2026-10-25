# T17 — Independent read-only QA: frame_000 UHD generative candidate

**Review:** 2026-10-24; reviewer: VID, isolated QA scope. **Disposition: UNCERTAIN — HOLD.** This is not approval for archive repacking, production, or handoff.

## Exact pair reviewed
- Source: `work_directory/extracted/video/c.blb/0/frames/frame_000.png` — 320×240 indexed PNG; SHA-256 `a80e5a88f19e63b26048ddf8facf29335531341741070a983288d2b9cf250245`. Source identity is also recorded in `work_directory/extracted/video/c.blb/0/metadata.json` (c.blb entry 0, frame 0 of 85; 15.0015 fps).
- Generative identity: Gemini 3 Pro Image Preview, v3; provenance/prompt in `work_directory/upscaled/gemini_test/frame_000_gemini_v3_meta.json`. Raw 4800×3584 generated image: `work_directory/upscaled/gemini_test/frame_000_gemini_v3_4800x3584.png`, SHA-256 `859897a6e124dec1a02098d878b55a6253c095b10570f95b200316a85107cd3a`.
- Exact 4:3 candidate compared: `work_directory/qa/T14_frame000_uhd/frame_000_gemapi3_2880x2160.png` — SHA-256 `7560ef1750f1b0820910e31518a822710008c09a00fd663f9c304ab09db2fd71`. The 3840×2160 presentation variant is `work_directory/qa/T14_frame000_uhd/frame_000_gemapi3_3840x2160_pillarbox.png`, SHA-256 `a80795c64947f57b8b9c70114b65824196add7343069cd032eb1ebE97eb1e815` (4:3 image centered with 480-pixel side bars).

## Independent findings
Applied the intent-aware criteria in `knowledge/qa_process.md` and its T15 addendum. Compared the exact source and UHD master visually; independently recomputed screening values in memory from those files. Prior T14/T15 reports were consulted for file/provenance identification, not relied on for their verdicts or rankings. No image, script, source, or prior report was changed.

| Criterion | Finding |
|---|---|
| Layout / registration | **PASS (screening).** Both frames are 4:3. Macro framing, major boundaries, object placement and pose align on visual comparison. Candidate downscaled to source dimensions had zero-shift best match in a ±3 source-pixel search (blurred-luma correlation 0.9966); independently replicated band-limited, color-matched SSIM was 0.9814 (T15 provisional gate ≥0.95). |
| Color / mood | **PASS (screening).** Broad teal-green recess, orange-red foreground and warm cream figure remain recognizable; no clear global relighting or mood reversal. Downscaled RGB mean shift was R −1.94, G −3.44, B +3.27 levels. 32×24 block-mean approximate Lab ΔE76 mean 4.89 (p95 7.99), within the provisional T15 mean ≤6 and max-channel-shift ≤8 gates. This is approximate ΔE76, not ΔE00; local shifts and the slightly cooler/less-green cast remain visible on close comparison. |
| Content / shape / pose | **PASS for gross structure; UNCERTAIN for reconstructed fine features.** I see no clear added/removed major object or changed character pose/silhouette. The mouth/teeth shape is discernible in the source pixels, so I do not classify it as a confirmed invention. Candidate adds/defines many fine wall fissures, surface marks and figure/clothing creases that cannot be verified from this compressed 320×240 frame. I cannot establish that each is source-supported rather than model reconstruction. |
| Artistic intent | **UNCERTAIN.** The result retains a clay-like, warm-lit scene and is not obviously plastic/airbrushed, but the pronounced new microtexture and sharper relief may exceed what this source can substantiate. No approved deviation map or artist/user judgment establishing the acceptable reconstruction range was present in the evidence reviewed. |
| Temporal consistency | **NOT ASSESSED / missing evidence.** Only frame 000 has this candidate identity here; no corresponding generative neighboring frames were available for flicker, identity or cadence review. |

## Recommendation to MGR
Keep this candidate and any dependent generative batch **on hold** pending a human art/rights-owner decision on the unverified microdetail (with acceptable regions/deviations recorded) and required method/style and rights/privacy approvals. If intended for video, also require a consecutive-frame temporal review. The still passes provisional layout/color screens, but those do not resolve the content-detail uncertainty. No archive repacking or production authorization is given by T17.

**Evidence reviewed:** `work_directory/qa/T14_frame000_uhd/qa_report.md`; `work_directory/qa/T14_frame000_uhd/qa_report_v2_intent_aware.md`; `work_directory/qa/T14_frame000_uhd/crop_mouth_source_vs_v3.png`; source/candidate paths above. No hosted service was used in this review.
