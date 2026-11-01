# Review scope: 128-GB DGX Spark documentation

**Purpose:** inventory the 14 project files tracked at the public base revision below. This work list is not a deployment guide or a claim that hardware tests ran; it excludes itself and the private `WORKLOG.md`.

## Target and constraints

- Target configuration: the owner's NVIDIA GB10 DGX Spark with **128 GB unified memory**, Ubuntu 24.04.5 LTS ARM64, based on owner-provided diagnostics.
- Document only the pinned 128-GB vLLM path for this Spark. Do not include or recommend other memory profiles.
- Keep installation, weight downloads, model launches, Docker permission changes, and Windows/Android builds pending unless separately authorized.
- Keep the distinction between source-verified, statically checked, and actually tested on the device.
- Inventory base: public `main` at `dca989162caf1523683851c64f77066bdd81254a` (14 project files, excluding this inventory). At that time, seven documentation files had local uncommitted 128-GB-only corrections; those edits are not included in this inventory publication.

## Existing tracked files in scope

| # | Repository path | Review focus | Status |
| ---: | --- | --- | --- |
| 1 | `.github/workflows/docs.yml` | Keep least-privilege CI, pinned action SHAs, and separate citation/local-link, Markdown, and external-link checks. |  |
| 2 | `.gitignore` | Ensure private work notes and audit artifacts cannot be staged accidentally. |  |
| 3 | `.markdownlint-cli2.jsonc` | Keep rules compatible with numeric citations; verify Markdown tables and whitespace. |  |
| 4 | `DGX_Spark_Setup_Commands.md` | Keep preflight and routing specific to the 128-GB target; remove other memory-profile guidance. |  |
| 5 | `README.md` | Make the 128-GB target and evidence limits clear at the entry point. |  |
| 6 | `docs/comfyui-zimage.md` | Preserve the separate ComfyUI/BF16 image workflow; verify pins, storage, loopback, resume behavior, and pending runtime status. |  |
| 7 | `docs/model-and-license-matrix.md` | Keep exact model IDs, revisions, storage, licenses, runtime status, and only the target 128-GB Qwen profile. |  |
| 8 | `docs/model-install-plan.md` | Align the storage layout and installation sequence with the pinned 128-GB recipe; remove 64-GB-specific cache instructions. |  |
| 9 | `docs/professionalization-roadmap.md` | Keep acceptance criteria precise for the owner's 128-GB system and the current evidence state. |  |
| 10 | `docs/toolkit-recommendations.md` | Keep baseline and optional components separated; avoid generic hardware-profile advice. |  |
| 11 | `docs/validation-status.md` | Retain the 128-GB owner-supplied hardware facts; clearly mark runtime and hardware checks pending. |  |
| 12 | `docs/windows-android-toolchain.md` | Keep Windows/Android commands separate from Spark; do not run builds on Spark. |  |
| 13 | `model/Qwen3.8-27B/README.md` | Reduce the user runbook to the pinned 128-GB launcher, target/draft revisions, safe Docker access, SSH, API checks, and stop procedure. |  |
| 14 | `scripts/check_docs.py` | Preserve citation-map and repository-local-link checks; ensure private notes and absolute workstation links are excluded/rejected. |  |

## Review order

1. Remove non-target memory-profile instructions and citations from the affected tracked files.
2. Re-render and verify citation maps; run local-link and Markdown checks.
3. Run `bash -n` on documented shell blocks only; do not execute installation commands.
4. Review the full diff and secret/path scan before staging or publication.
5. Report commit/publish status separately from hardware-test status.

## Excluded from the public file list

The private `WORKLOG.md`, local stashes, and secondary backup clone are not part of this tracked inventory and must not be published as project files.
