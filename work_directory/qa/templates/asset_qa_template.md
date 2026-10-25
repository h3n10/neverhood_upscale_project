# Asset QA / approval record

Copy one per asset or coherent clip set. Keep newest report in the corresponding QA folder; never overwrite source/reference files.

## Identification and authorization
- Report ID / date / reviewer(s):
- Tier: A hero / B important / C bulk
- Source archive + asset id / frame range:
- Source SHA-256 / original file path:
- Source dimensions, mode, palette hash or ICC/profile assumption:
- Original frame count / raw rate / derived FPS / PTS-duration manifest:
- Rights owner / project authority to process and distribute confirmed by:
- External transfer approved? No by default. If yes: provider, endpoint, region, plan, retention/training/deletion review, approving person/date:
- User style/method approval ID and date (required before bulk):

## Candidate pipeline
- Method/classical filter OR provider/model/version/endpoint:
- Weight/model hash/API version:
- Exact params, scale/output size, aspect/crop/registration/color transform:
- Prompt + system prompt hash (if any); reference-image hashes; seed/seed unsupported:
- Tool/software version, environment:
- Input/output file paths + SHA-256:
- Frame count / FPS / timing preserved? Audio/alpha/palette checks:
- Cost/request count/retries (no secrets):

## Automated gates (100% required)
| Gate | Result/value | Threshold/profile | PASS / FAIL / HOLD |
|---|---|---|---|
| Decode, file integrity, output dimensions/aspect/registration | | | |
| Palette/alpha/profile/color tags and source preservation | | | |
| Frame count, PTS, duration, audio, cut/keyframe integrity | | | |
| Downscale-back PSNR / SSIM | | | |
| Lab Delta E00 mean / p95 / histogram drift (or clearly label estimate) | | | |
| Luminance mean / contrast drift | | | |
| Edge/structure consistency, local maps | | | |
| New/lost/reshaped object flags and adjudication | | | |
| Temporal flicker/warp/identity/cadence checks (video) | | | |
| Regression vs frozen golden outputs | | | |

## Visual review and decision
- Contact sheet / blink compare / crops / flicker playback paths:
- Original, local baseline and candidate compared at matched size? yes/no
- Mood, lighting, palette, composition, silhouettes, expressions, clay texture:
- Additions/removals/uncertainties or changed regions (coordinates/frame ids):
- VLM reviewer used? If yes, transfer authorization, fixed model/prompt/version, response path and caveat:
- Human sampling coverage and selected sample seed/strata:
- Outcome: PASS / FAIL / HOLD / REWORK; reason:
- Rejection log ID and specific failure class:
- Rework attempt count / changed params / retest outcome:

## Sign-off
- Human artist/reviewer approval and date:
- User approval of style/method/output deviations and date:
- Manager approval for batch and spend cap (if applicable):
- Rights/privacy approval reference (if external):
- Analyst handoff authorized? No unless all gates/signoffs pass.
