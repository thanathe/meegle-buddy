# Changelog

All notable changes to **meegle-buddy**. Format loosely follows [Keep a Changelog](https://keepachangelog.com/); versions are the git semver tags `vMAJOR.MINOR.PATCH`. Dates are ISO (Asia/Bangkok).

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
