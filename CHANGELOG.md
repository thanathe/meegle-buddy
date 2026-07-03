# Changelog

All notable changes to **meegle-buddy**. Format loosely follows [Keep a Changelog](https://keepachangelog.com/); versions are the git semver tags `vMAJOR.MINOR.PATCH`. Dates are ISO (Asia/Bangkok).

## [1.0.2] — 2026-07-03
### Added
- **install.sh** — pretty one-liner installer (`curl -fsSL …/install.sh | bash`): banner + 3-step wizard that installs the skill via the `skills` CLI (global, all agents), then checks the `meegle` CLI and login state and prints the exact follow-up command (`npx @lark-project/meegle@latest install` / device-code login) when something is missing. `--dry-run` supported; README gains a TL;DR install section.

## [1.0.1] — 2026-07-03
### Fixed
- **SKILL.md frontmatter**: quote the `description` value — the unquoted text contained `Keywords: ` (colon + space), which strict YAML parsers read as a nested mapping. Claude Code's lenient loader accepted it, but the `skills` CLI (`npx skills add <owner>/<repo>`) reported "No valid skills found". The repo is now installable via `npx skills@latest add thanathe/meegle-buddy`.

## [1.0.0] — 2026-07-03

First complete release — discovery-driven setup, create-card, timelog, schedule, node-binding, field-drift sync (LIGHT/FULL), and conditional linkage rules all in place.

### Added
- **Prerequisites** (SKILL): document the one-stop setup wizard `npx @lark-project/meegle@latest install` (CLI ≥ 1.0.11) — install/upgrade + host config + login in one command; manual install + device-code flow kept as fallback.
- **cli-reference self-heal**: `TOOL_DISCOVERY_FAILED` row (CLI ≥ 1.0.7 keeps local commands bootable when server discovery fails) and a tip to re-run with `--envelope` (CLI ≥ 1.0.8) to get `meta.logid` for Meegle support.
- **conditional_rules** (config-format + check-fields + create-card + SKILL): first-class support for Meegle **form linkage** — fields that become required only when another field has a certain value (e.g. "Category = Option A ⇒ a relation field becomes required"). No CLI/API endpoint exposes these rules (`meta-create-fields` returns only statically-required fields), so FULL sync gains a discovery step: MQL fill-rate inference per driver option (≥80% filled under one option, ≈0% elsewhere ⇒ proposed rule), confirmed by the user, saved as `conditional_rules` on the type. create-card applies matching rules when the user picks a select value, and a `必填`-on-"optional"-field create error is now recorded as a conditional rule (keyed to the driver value in effect) instead of flipping the field to globally required.

## [0.1.11] — 2026-06-16
### Added
- **timelog / cli-reference**: a "VERIFY the link stuck" step, because a `work_item_related_select` link **fails silently on the wrong target type** — give it a wid whose work-item type isn't in the field's `related_work_item_info` (e.g. a parent/grouping item instead of the child it actually wants) and the API returns success-with-no-error (`{"mcp_result":""}`) but stores `null`. After setting any relation link, read it back via MQL (`workitem get` brief omits relation fields); a new self-heal row covers the "set OK but reads null" case. Also: if MQL shows the link set but the card UI says "Empty", that's a **stale UI cache** → hard-refresh. Kept fully discovery-based — the accepted type comes from each field's `related_work_item_info`, nothing hardcoded.

## [0.1.10] — 2026-06-16
### Changed
- **node-binding**: rewrote Path A (manual UI steps) from Thai to English so the skill body stays English-only and cheaper to load. Only short Thai trigger/sample phrases remain by design (intent detection + user-facing examples).

## [0.1.9] — 2026-06-16
### Added
- **create-card**: document that some spaces require the **owner role AT create** — a plain create errors with the role name `必填`. Pass the owner in the create `--fields` as `role_<project_key>_<work_item_type_key>_owner` with a single `user_key` string; `--role-operate` and `role_owners` are ignored by create in those spaces.
- **node-binding**: troubleshooting the in-page fetch on the heavy Meego SPA — **fire-and-store + poll** instead of awaiting inside the eval (avoids the ~45s `Runtime.evaluate` cap / "renderer frozen"), and open a **fresh same-host tab** if the card page is stuck in `readyState:"loading"` (cookie + CSRF are shared across the host).

## [0.1.8] — 2026-06-16
### Added
- **node-binding** (`references/node-binding.md`): attach a card under a specific story **node**, discovery-based. Detect-first checks (node-field / relation-def / WBS) to confirm the CLI can't do it, then two paths — **Path A** guides the user to click "Add current" in the web UI (works for everyone), **Path B** automates it via a browser-control MCP (e.g. Claude-in-Chrome) with a capture-once hook so `relation_uuid` / node keys / CSRF stay discovered, never hardcoded. Wired into SKILL.md routing + create-card follow-ups.

## [0.1.7] — 2026-06-02
### Changed
- Genericize: use a neutral example slug in init (no real space slug) — keep the skill shareable.

## [0.1.6] — 2026-06-02
### Fixed
- Self-heal rows: `comment add` is plain-text only (multi-line/markdown/emoji fail); editing another user's card errors on permission.

## [0.1.5] — 2026-06-01
### Changed
- init captures the **full** required-field set per type, and explains the API does **not** enforce required fields — guardrail against half-empty cards.

## [0.1.4] — 2026-06-01
### Fixed
- Per-node schedule recipe uses `--set` dot-path (not `--node-schedule` JSON). Added read-back verification + self-heal rows.

## [0.1.0] – [0.1.3] — 2026-05-31 … 06-01
### Added
- Initial release: a generic, **no-hardcoded-field** helper for Feishu/Lark Project (Meegle/Meego) that discovers each person's spaces, work-item types, fields, and workflows and saves a personal config.
- Device-code login promoted for reliability (plain `auth login` hangs in agent shells).
### Changed
- create-card: select fields send the **option_id**, not the human label.
- Documented rich-text (Markdown) in `multi_text` description fields.
- init/cli: space lookup is **EXACT-match** — prefer the slug.
