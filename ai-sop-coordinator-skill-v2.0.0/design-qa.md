# Dashboard Design QA

## V2.0.0 lifecycle and automation QA

This stable release preserves the V1.8.4 G1-G3 review controls and adds deterministic D/E task dispatch, task-scoped code branches, commit confirmation, independent review, main integration, G4/G5, and rollout controls. Rollback and incident authority boundaries remain human-controlled as documented.

- The common Markdown structure was exercised with generated G1, G2, and G3 stage sections.
- G1 emphasizes users, pain points, user stories, requirement sources, atomic requirements, and business acceptance.
- G2 emphasizes candidate solutions, comparison, validation evidence, production gaps, and system boundaries.
- G3 emphasizes technical design, development tasks, test strategy, release criteria, risk, and rollback.
- Member and artifact coverage use hidden deterministic markers while all decision content remains readable without opening YAML.
- The pack is explicitly a read-only projection and cannot replace member facts, provenance, human approval, mandatory merge, or baseline freezing.
- Stale document hashes and source fingerprints are rejected before approval; the exact reviewed Markdown is archived in the baseline.

## Visual source of truth

- User-provided dashboard screenshot in the 2026-07-15 conversation.
- Key traits retained: white canvas, soft-gray cards, restrained blue accents, compact status chips, horizontal stage stepper, left-side progress, right-side G1-G3 status, and low visual noise.
- The implementation is a data-driven GitHub README SVG, so page height and task rows intentionally adapt to actual project state instead of copying the screenshot crop height.

## Implementation under test

- Renderer: `ai-sop-coordinator/assets/github-dashboard/sop_readme_dashboard.py`
- Fixture: the current private project's `sop/project-state.yaml`
- Render viewport: 1200 px wide; computed height 1540 px for eight current-stage tasks.
- Raster QA: SVG rendered locally to a 1200 px PNG and inspected at original size and resized preview size. The raster preview is not included in the release because it contains private project state.

## Iterations

1. Replaced the old dense table layout with the screenshot's hierarchy and visual language.
2. Removed button-like tabs because the README SVG is intentionally non-interactive.
3. Added Git collaboration state, current Gate emphasis, dynamic footer placement, no-task wording, overflow counts, localized collaboration labels, and private-path suppression.

## Final checks

- No clipped footer or task cards at 0, 8, or 12 task inputs.
- No local `git_root` or GitHub token content is rendered.
- Zero-total stages display `待开始` instead of a misleading `0%`.
- The current Gate, merge-pending Gate, risk, blockers, task validation, and Git availability use distinct state-aware treatments.
- SVG parses as XML and renders correctly with system Chinese fonts.
