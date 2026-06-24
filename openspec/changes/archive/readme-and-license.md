# Archive: README and LICENSE

## Change Summary

Closed two long-standing gaps flagged by a peer review of `mcp-fusion360` against three comparable Fusion 360 MCP servers (Joe-Spencer, AuraFriday, ArchimedesCrypto): the absence of a `README.md` and the absence of a `LICENSE` file at the project root. Both gaps were explicitly deferred from the `face-index-and-runtime-coverage` change (archived 2026-06-24) and listed as a blocker for going public — a fresh clone left the user with no install steps, no tool reference, and ambiguous legal status.

The change delivers exactly two new files at the project root, both pure documentation. `LICENSE` is the unmodified MIT SPDX text with one project-specific line: `Copyright (c) 2026 Ignacio Molini` (the holder matches the `author` field in `Fusion360MCP.manifest:5`). `README.md` is a 10-section document (1 H1 + 9 H2 + 7 H3) covering value proposition, architecture, all 11 MCP tools grouped by their 4 capabilities, install for both Windows and macOS, three MCP client configuration JSON blocks (Claude Desktop, Cursor, OpenCode), one concrete usage example, project layout, testing strategy, and license pointer. The README is honest about what is and isn't in the permanent spec tree via a `[^1]` footnote on `measure_clearance`.

The change is documentation-only by design: no code, no spec, no design, and no test files were modified. No new MCP tools were introduced. No component (Component A: Fusion Add-in; Component B: Node.js MCP wrapper) was touched. The implementation is purely additive — a fresh clone now has a discoverable entry point and an explicit legal status.

## Spec Promotion Summary

**None.** This change had no spec-level changes. The proposal explicitly states "documentation files are not behavioral contracts and do not introduce new spec-level requirements" and the verify report confirms "0 spec changes". The `openspec/specs/` tree is unchanged by this archive phase. The existing permanent specs (`design-introspection/`, `parameter-management/`, `cutout-modeling/`) remain as they were after the `face-index-and-runtime-coverage` archive.

The README's tool list references 10 tools from the 3 permanent specs and 1 tool (`measure_clearance`) from the in-flight `geometry-analysis` spec still living in `openspec/changes/fusion360-mcp-server/specs/geometry-analysis/spec.md`. The in-flight spec is documented transparently via a `[^1]` footnote, not hidden; promoting `geometry-analysis` to permanent specs is a separate future change (see Follow-up Work below).

## Verification Status

**PASS** (0 CRITICAL findings, 3 warnings, 4 suggestions).

- LICENSE: 21 lines, MIT SPDX verbatim with the only allowed modification (the copyright line)
- README: 246 lines, 1 H1 + 9 H2 = 10 sections per C1, all 11 tools documented in 4 capability groups (2/5/3/1 split)
- Tool list accuracy: 11 unique tool entries, cross-checked against `mcp-server/src/tools.ts:1-221`
- `measure_clearance` footnote: present at line 88, references `openspec/changes/fusion360-mcp-server/specs/geometry-analysis/spec.md`
- `face_selector` documented in all 3 cutout tools (lines 73, 76, 79) — addresses the `face-index-and-runtime-coverage` deprecation
- 3 MCP client config JSON blocks: all parse as valid JSON (Claude Desktop, Cursor, OpenCode)
- 0 fake badges, 0 TODOs, 0 `curl` examples, 0 broken links
- Build commands in README match `mcp-server/package.json:7-12` exactly
- Install paths cover Windows (`%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`) and macOS (`~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns\`)
- Tasks checkboxes: **11/11 marked `[x]`** — the lesson from `face-index-and-runtime-coverage` (mark checkboxes as you go) was applied successfully
- Total lines: 267 (LICENSE 21 + README 246), under the 400-line review budget (D1)

### User Decisions Honored

| Decision | Requirement | Result |
|----------|-------------|--------|
| **A1** | All 11 tools documented; `measure_clearance` has footnote about spec location | ✅ PASS — 11 tool entries; footnote `[^1]:` references the in-flight spec |
| **B2** | No Acknowledgments section | ✅ PASS — zero matches for `^## .*Acknowledg` |
| **C1** | No Status/Badges section; renumbered to 10 numbered sections (1 H1 + 9 H2) | ✅ PASS — H1=1, H2=9, total 10 sections; no shields.io badges |

## Artifacts Produced

| Phase | File System | Engram Topic Key |
|---|---|---|
| Proposal | `openspec/changes/readme-and-license/proposal.md` | `sdd/readme-and-license/proposal` |
| Design | `openspec/changes/readme-and-license/design.md` | `sdd/readme-and-license/design` |
| Tasks | `openspec/changes/readme-and-license/tasks.md` | `sdd/readme-and-license/tasks` |
| Verify report | `openspec/changes/readme-and-license/verify-report.md` | `sdd/readme-and-license/verify-report` |
| Archive report | `openspec/changes/archive/readme-and-license.md` (this file) | `sdd/readme-and-license/archive-report` |
| Apply progress | (Engram only) | `sdd/readme-and-license/apply-progress` (observation #261) |

### Permanent Specs (promoted by this archive phase)

**None.** This change had no spec changes — see "Spec Promotion Summary" above.

## Files Delivered

### Documentation (project root)

| File | Change | Lines | Purpose |
|---|---|---|---|
| `LICENSE` | new file | 21 | MIT SPDX text with `Copyright (c) 2026 Ignacio Molini`; holder matches `Fusion360MCP.manifest:5` |
| `README.md` | new file | 246 | 10 sections (1 H1 + 9 H2 + 7 H3), 11 tool entries, 3 MCP client configs, 1 usage example |

No other files modified. No `mcp-server/src/` edits, no `Fusion360MCP/` edits, no `openspec/specs/` edits.

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| License | MIT (over Apache-2.0) | User decision during proposal phase. Maximizes permissiveness, matches what most small MCP servers use, keeps the LICENSE under 25 lines. The Autodesk IP patent concern is documented in the proposal's risk table; user chose MIT anyway. |
| Copyright holder | `Ignacio Molini` | Matches `Fusion360MCP.manifest:5` (`"author": "Ignacio Molini"`); single source of truth for the author identity. |
| README language | English only | Project convention; `prd.md` is Spanish but everything in `mcp-server/`, `Fusion360MCP/`, and `openspec/` is English. |
| Section count | 10 (per C1) — no Status, no Acknowledgments | User chose the minimum-noise option; renumbered 1-9 instead of 1-12 to avoid empty slots. |
| Tool list grouping | 4 capabilities, 11 tools, 2/5/3/1 split | Maps 1:1 to the proposal's capability table; gives the reader a mental model. The split is the spec's, not the prompt's: the orchestrator prompt initially guessed 4/3/3/1 but the spec files (3 permanent + 1 in-flight) define 2/5/3/1. Defer to the spec. |
| Source of truth for tool list | `openspec/specs/` (3 caps) + `openspec/changes/fusion360-mcp-server/specs/geometry-analysis/spec.md` (1 cap) | The README documents what is implemented, not what is permanently spec'd. The in-flight spec is acknowledged via the `[^1]` footnote. |
| `face_selector` documentation | Document BOTH `face_index` (deprecated) and `face_selector` (preferred) in the 3 cutout entries | Matches the deprecation wording in `mcp-server/src/tools.ts:80,105,134` from the `face-index-and-runtime-coverage` change. |
| MCP client config | 3 fenced JSON blocks (Claude Desktop, Cursor, OpenCode) | All three use `command: "node"` + `args: ["<abs path>/mcp-server/dist/index.js"]` with a placeholder path. OpenCode uses `mcp` not `mcpServers` — matches its documented schema. |
| Acknowledgments | **OMITTED** (per B2) | The proposal listed Joe-Spencer, AuraFriday, ArchimedesCrypto as prior art, but the user chose to drop the section to keep the README focused on the user's needs. The credit decision is deferred to a future change. |
| Status / Badges | **OMITTED** (per C1) | No build/coverage badges — there is no CI. The optional shields.io license badge was dropped with the rest of the section. |
| No screenshots | Text + ASCII diagram only | Proposal rule; visual assets are out of scope. |
| No TODO items | None in README | Open work belongs in issues, not docs. |
| `prd.md` treatment | Mentioned in project tree, marked "(Spanish, legacy — not the source of truth)" | Honest about the bilingual artifact without linking prominently. |
| Absolute path in MCP config | Placeholder `/absolute/path/to/mcp-fusion360/mcp-server/dist/index.js` with explicit "substitute your clone path" caveat | User-specific paths must not be embedded. |

## PR Strategy

**Single PR** (no chained PRs needed). 267 lines across 2 new files, well under the 400-line review budget (D1). The implementation is purely additive (two new files at the project root; no existing file modified). No branch yet — the user is committing when ready.

If the user later wants the change under a strict 400-line cap (it already is, so this is hypothetical), the recommended split would be:

1. **PR 1** — `LICENSE` only (21 lines): self-contained, no dependencies, ships in seconds.
2. **PR 2** — `README.md` only (246 lines): depends on PR 1 only for the License section to link; can land independently.

No chained PR needed under the current numbers.

## Known Limitations

- **README is at the upper bound of the line forecast (246/250 lines; total 267/240).** The 11 tool entries (each with Input/Output shape) plus the 3 JSON config blocks consume ~100 lines by themselves. The content is structured cleanly (1 H1 + 9 H2 + 7 H3), so trimming would be cosmetic. Accepted by user per the proposal's stated risk tolerance ("slight overage tolerated per `face-index-and-runtime-coverage` precedent").
- **MCP protocol version stated as "JSON-RPC 1.0" in two places** (Architecture diagram line 19 and bullet line 25). The MCP specification uses JSON-RPC 2.0 as its wire format. The "1.0" reference is inaccurate; the internal HTTP path (Component B ↔ Component A) correctly says "JSON-RPC 2.0". Documentation wording, not a contract. Suggested fix: change to "JSON-RPC 2.0" or "MCP over JSON-RPC" to avoid pinning a version.
- **`geometry-analysis` is not in permanent specs.** The README's `measure_clearance` entry has a footnote acknowledging this. Until `geometry-analysis` is promoted to `openspec/specs/geometry-analysis/spec.md`, the README references a spec that lives in a change folder. This is a transparency choice, not a defect.
- **No badges / no CI status.** The README is honest about not having a build pipeline; a future change that adds CI (e.g. GitHub Actions) should re-introduce the Status section with a real badge.
- **No troubleshooting section.** Common failure modes (add-in not loaded → port 9876 unreachable; `dist/index.js` not built → `MODULE_NOT_FOUND`; wrong `args` path → "spawn failed") are not documented. Suggested for a future README revision.
- **Documentation-only verification.** No automated tests exist for a README. The verify report covers structural checks (heading hierarchy, tool count, JSON validity) and content cross-references (file paths, build commands) but cannot prove semantic correctness.

## Follow-up Work

### Deferred from this change (out of scope per proposal)

- **Add `CONTRIBUTING.md` and `SECURITY.md`** at the project root. The proposal explicitly listed these as out of scope. External contributors currently have no policy on how to file issues or report security issues. Natural follow-up change.
- **Add a "Troubleshooting" section to the README** — between `## Usage` and `## Development`. Common failure modes (port 9876 unreachable, `dist/index.js` missing, wrong `args` path) would help new users diagnose setup issues. The verify report lists this as Suggestion #3.
- **Tighten the JSON-RPC version reference** — change "JSON-RPC 1.0" to "JSON-RPC 2.0" (matching the MCP spec) or "MCP over JSON-RPC" in the Architecture diagram and bullet. Cosmetic; the verify report lists this as Suggestion #4.

### Carried from the previous change (already documented, not introduced here)

- **The `get_document_info` generic Fusion API error** — NOT in scope of this change (already documented in `openspec/changes/archive/face-index-and-runtime-coverage.md:135`). The `get_document_info` handler is unchanged at `handlers.py:653-698`. The user has agreed to file a separate follow-up issue.
- **Promote the remaining 3 capabilities from `fusion360-mcp-server` to `openspec/specs/`** — `fusion360-add-in`, `geometry-analysis`, `mcp-wrapper`. This is now visible in the README via the `measure_clearance` footnote. The `geometry-analysis` promotion remains a separate future change. Once promoted, the README footnote can be retired and the README can be regenerated from the now-complete permanent spec tree.
- **The 21 `UNTESTED` scenarios in `fusion360-mcp-server/verify-report.md`** — manual runtime evidence still pending (B1-B4 curl sanity, C1-C5 read tools, D1-D3 modification tools, E1-E6 cutout tools, F1-F2/F4-F7 Component B E2E, G1-G11 from `fusion360-extended-tools`). Documentation-only changes don't close any of these.
- **Slot cutout `length_mm == width_mm` boundary case** — pre-existing, not introduced by this change. The handler uses strict inequality, so `length_mm == width_mm` (a circular obround) is rejected.

### Branch state at archive

- **Implementation**: on the working tree, frozen after verify. No commits created by `sdd-archive`. The user is committing when ready.
- **Change folder**: `openspec/changes/readme-and-license/` is left in place as an audit trail (matches the `face-index-and-runtime-coverage` convention). Only the archive report is consolidated into `openspec/changes/archive/`.
- **README**: 246 lines, English, MIT-style project entry point at `README.md` (project root).
- **LICENSE**: 21 lines, MIT SPDX verbatim with `Copyright (c) 2026 Ignacio Molini` at `LICENSE` (project root).
- **No spec, design, code, or test files modified** by this change.

## Rollback Notes

This archive marks the change as complete. Future modifications should start a new SDD change referencing this archive. If the change must be rolled back after the PR merges:

1. `git rm LICENSE README.md` from the project root.
2. No other artifacts to revert — no spec, design, code, or test files were modified.
3. The `openspec/changes/readme-and-license/` folder remains in the archive for audit; no rollback action needed.

The change is purely additive (two new files); rollback does not touch any persistent design data, persistent specs, or any other repo file.

## Archive Notes

**Archived on**: 2026-06-24
**Archived by**: `sdd-archive` sub-agent (orchestrator-delegated)
**Convention used**: single-file archive (`openspec/changes/archive/{change-name}.md`), matching the pattern established by `face-index-and-runtime-coverage.md`, `fusion360-extended-tools.md`, and `fusion360-mcp-server.md`. The change folder (`openspec/changes/readme-and-license/`) is left in place as an audit trail; only the archive report is consolidated into `openspec/changes/archive/`.

**Path note (intentional)**: the `sdd-archive` skill SKILL.md describes the archive path as `openspec/changes/archive/YYYY-MM-DD-{change-name}/` (a date-prefixed folder containing the full change), but the project convention established by the three previous archives is the single-file form `openspec/changes/archive/{change-name}.md` (no date prefix, no folder). This archive follows the project convention, matching the `face-index-and-runtime-coverage` precedent flagged in that archive's "Path discrepancy" note. The change folder is also NOT moved to an archive subfolder — it stays at `openspec/changes/readme-and-license/` for audit. Same convention as `face-index-and-runtime-coverage`.

**Artifact store mode**: OpenSpec (filesystem only).

### What was deferred

- **The 21 `UNTESTED` scenarios in `fusion360-mcp-server/verify-report.md`** — documentation changes don't close runtime gates. The user can pick these up incrementally; each is independent.
- **`CONTRIBUTING.md` and `SECURITY.md`** — explicitly out of scope per the proposal. The README's "Development" section points at the project layout but does not link to either.
- **The `get_document_info` generic Fusion API error** — separate follow-up issue, not in this change's scope.
- **Troubleshooting section** — the verify report lists it as Suggestion #3; defer to a future README revision.

### What follow-ups remain

- **Promote the remaining 3 capabilities to `openspec/specs/`** — `fusion360-add-in`, `geometry-analysis`, `mcp-wrapper` from the prior `fusion360-mcp-server` archive are not yet in the permanent specs tree. This change's `measure_clearance` footnote makes the gap more visible but does not close it. The `geometry-analysis` promotion is the most user-facing one (it's the one referenced in the README).
- **Add `CONTRIBUTING.md` and `SECURITY.md`** — natural follow-up change.
- **Tighten the JSON-RPC version reference** in the README Architecture section (Suggestion #4 from the verify report).
- **Add a Troubleshooting section to the README** (Suggestion #3 from the verify report).
- **Open the PR for the implementation** — the two new files are on the working tree, ready to commit and push when the user is ready.

### Engram observations at archive

- `sdd/readme-and-license/proposal`
- `sdd/readme-and-license/design`
- `sdd/readme-and-license/tasks`
- `sdd/readme-and-license/verify-report`
- `sdd/readme-and-license/apply-progress` (observation #261)
- `sdd/readme-and-license/archive-report` (this sub-agent's output, written at the end of this archive phase)

## Lessons Learned

1. **The "mark checkboxes as you go" lesson from `face-index-and-runtime-coverage` was successfully applied.** That change required exceptional stale-checkbox reconciliation at archive time (the apply agent had stopped at 6.1 without marking the remaining tasks). This change's `sdd-apply` marked all 11 checkboxes as each phase completed, so the archive's "Task Completion Gate" passed cleanly with no reconciliation. **Recommendation for future changes**: continue the discipline — the apply phase's final action is always to mark the just-completed task `[x]`, even if more work is coming. The two minutes it costs per task save the archive phase from having to fabricate a reconciliation rationale.

2. **Defer to the spec file as the source of truth, even when the orchestrator prompt disagrees.** The initial orchestrator prompt for this change mentioned "4 parameter management tools" in its tool list, but the permanent `parameter-management/spec.md` defines only 2 tools (`get_active_design_parameters` + `update_user_parameter`). The apply agent correctly used 2, the verify report cross-checked against the spec, and the final distribution came out to 2/5/3/1 (parameter-management / design-introspection / cutout-modeling / geometry-analysis) — matching the 3 permanent specs plus the 1 in-flight spec, totaling 11 tools. **Recommendation for future changes**: when the orchestrator prompt and the spec file disagree, always trust the spec file. The spec is the contract; the prompt is a brief. If the spec is wrong, fix the spec first; if the prompt is wrong, the spec wins.

3. **The `geometry-analysis` spec gap is now visible in user-facing documentation.** The `face-index-and-runtime-coverage` archive documented this as a follow-up but it was hidden from users. The README's `[^1]` footnote on `measure_clearance` now surfaces it to anyone reading the README. **Implication**: the gap became more visible, which increases pressure to promote `geometry-analysis` to permanent specs. That's a feature, not a bug — the README is honest about what is and isn't spec'd.

4. **The orchestrator's path description in the SKILL.md diverges from the project's established convention.** The `sdd-archive` SKILL.md says the archive goes in `openspec/changes/archive/YYYY-MM-DD-{change-name}/` (a date-prefixed folder) AND that the change folder is moved there. The project's three existing archives all use `openspec/changes/archive/{change-name}.md` (a single file, no date prefix) AND keep the change folder in place. This archive followed the project convention. **Recommendation for future changes**: archive sub-agents should prefer the project's established convention over the SKILL.md's default unless the orchestrator explicitly overrides. The `face-index-and-runtime-coverage` archive's "Path discrepancy" note already documented this — the lesson carried forward.

5. **Documentation-only changes can still benefit from a full SDD cycle.** This change was just two files, both prose, but the proposal (105 lines), design (124 lines), and tasks (60 lines) captured real decisions: license choice, copyright holder, section count, tool distribution, `face_selector` documentation, MCP config formats, in-flight spec acknowledgment. None of these are "trivial" decisions. The verify report's 16 checks (LICENSE SPDX integrity, README structure, tool count, JSON validity, file path references, decision-honoring) caught a real prompt-vs-spec discrepancy in the tool count. **Recommendation for future changes**: don't shortcut the SDD cycle for "just docs" changes. The ceremony is cheap relative to the cost of an undocumented decision.

6. **The `face_selector` deprecation from `face-index-and-runtime-coverage` was carried into the README correctly.** Each cutout tool entry documents BOTH `face_index` (deprecated) and `face_selector` (preferred), matching the wording in `mcp-server/src/tools.ts:80,105,134`. This is a small thing, but it means the user-facing docs and the tool descriptions agree on the deprecation contract. **Recommendation for future changes**: when a change introduces a deprecation, the next documentation change is the place to surface it. The README is a snapshot, and the snapshot should reflect the current contract.
