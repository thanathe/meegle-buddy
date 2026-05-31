---
name: meegle-buddy
description: Friendly guided helper for Feishu/Lark Project (Meegle / Meego) that works for EVERYONE on the team, not just devs. No hardcoded field IDs — it discovers each person's spaces, work-item types, workflows, and field maps on first run and saves a personal config, then helps open cards, log time, and set estimate/effort/schedule with every required field filled in correctly. Use when the user wants to set up Meegle, open/create a card or work item, log time / ลงเวลา / ลง TR, or set estimate/schedule, and is NOT relying on a hardcoded team-specific skill. Keywords: meegle, meego, feishu project, lark project, ลงเวลา, ลง time, เปิดการ์ด, สร้างงาน, timelog, work item, estimate, schedule, sync meegle, เช็ค field, refresh fields.
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion
---

# meegle-buddy

A no-configuration-required helper for **Feishu / Lark Project (Meegle / Meego)**. It is built to be shared with a whole office — developers and non-developers alike — so anyone can open cards and log time **without ever touching a field ID** and without logging things in the wrong place or with fields missing.

The skill **never hardcodes** project keys, work-item types, field keys, template IDs, or node IDs. Instead it **discovers** them with the `meegle` CLI the first time a person uses it, builds a clean personal config, and from then on drives everything from that config.

## Operating principles (read every time)

1. **Talk to the user in Thai.** All questions, confirmations, and summaries you show the user are in Thai (e.g. "เข้างานกี่โมงครับ?", "จะลงการ์ดในโปรเจคไหน?"). These internal instructions stay in English for reliability.
2. **The hard thinking happens at init, not at run time.** Discovery and field-mapping are done once and saved. Day-to-day actions (open card / log time) should be mechanical: read config → ask the user plain questions → fill fields → submit. This keeps it cheap and reliable on small models.
3. **Never invent field keys, type keys, project keys, template IDs, or node IDs.** Always read them from the saved config (`~/.claude/meegle-buddy/`). If something you need is not in the config, run discovery (see [init](references/init.md)) — do not guess.
4. **Fill every required field.** Before any create/update, check the config's required list (from `meta-create-fields`) for that type and make sure each one has a value. If a required value is missing, ask the user. Never submit a partial card.
5. **Confirm before writing.** Always show the user a plain-Thai summary of exactly what will be created/updated and wait for "ok / โอเค / ลงเลย" before calling any `meegle ... create|update|workflow update-node` command.
6. **Compute timestamps with Python (Bangkok tz), never by hand.** See [timelog](references/timelog.md).
7. **No complexity scoring.** This skill deliberately does NOT estimate complexity or auto-derive effort from it. For estimate/effort/schedule it simply asks the user for the numbers and converts units. See [schedule](references/schedule.md).
8. **`field_value` is ALWAYS a string.** Every command is `meegle ... --format json` (NOT `lark-cli`). Field values go in repeated `--fields '{"field_key":"...","field_value":"..."}'` flags, and the value is always a *string* — arrays/objects must be JSON-stringified. This is the #1 cause of "logged wrong / rejected". See [cli-reference](references/cli-reference.md).
9. **The team changes fields often — guard against drift, but stay fast.** Two modes (see [check-fields](references/check-fields.md)): **LIGHT** runs automatically before every write — one `meta-create-fields` call, cached once per type per conversation — and only stops you when a field just became **required**. **FULL** runs when the user asks ("เช็ค field" / "sync meegle") and lists *all* new / changed / removed fields to curate. Never silently ignore a required field; never silently auto-add anything — ask the user, then update the config. Don't run FULL on every action (it's slow).

## Prerequisites (check on first run)

This skill drives the **`meegle`** CLI (NOT `lark-cli`) — the official Larksuite tool (`@lark-project/meegle`, https://github.com/larksuite/meegle-cli). Each person must have it installed and logged in. On the very first invocation, verify:

```bash
command -v meegle                   # must exist  (install: npm install -g @lark-project/meegle)
meegle auth status --format json    # must show "authenticated": true
```

If `meegle` is missing or not authenticated, stop and walk the user through setup (in Thai) — see the "Prerequisites" section of the [README](README.md). Do not try to do Meegle work until `auth status` succeeds.

**Login guidance (important):** when guiding login, always use the **device-code** flow, NOT plain `meegle auth login`. The plain flow relies on auto-opening a browser + a localhost callback, which hangs or fails unpredictably inside agent shells (Claude Code), SSH, and some terminals. Tell the user (Thai) to run:

```bash
meegle config set host <their-host>     # e.g. project.larksuite.com / project.feishu.cn / meegle.com
meegle auth login --device-code         # prints a link + code to open in any browser
```

If the user reports "browser won't open / login hangs", that's exactly this — point them to `--device-code`.

## Routing — pick the task

Figure out what the user wants and load the matching reference file. **Always make sure init has run first** (a config exists) before create/timelog/schedule.

| The user wants to… | Do this |
|---|---|
| Set up for the first time, add a project, or refresh fields | Follow [references/init.md](references/init.md) |
| Open / create a card or work item | Follow [references/create-card.md](references/create-card.md) |
| Log time / ลงเวลา / ลง TR | Follow [references/timelog.md](references/timelog.md) |
| Set estimate / effort / schedule on a card | Follow [references/schedule.md](references/schedule.md) |
| Check / refresh fields ("เช็ค field", "sync meegle") | Run FULL mode in [references/check-fields.md](references/check-fields.md) |
| (any of the above) needs a raw meegle command | See [references/cli-reference.md](references/cli-reference.md) |

### Is the user set up yet?

Before doing create/timelog/schedule, check for the config:

```bash
ls ~/.claude/meegle-buddy/config.json 2>/dev/null && echo "READY" || echo "NEEDS_INIT"
```

- `NEEDS_INIT` → run [init](references/init.md) first (tell the user in Thai you'll set things up quickly).
- `READY` → proceed, but if the chosen project has no saved profile under `~/.claude/meegle-buddy/projects/`, run the per-project part of init for it.

## The config (where everything discovered lives)

Personal, per-machine, **never committed to git**:

```
~/.claude/meegle-buddy/
├── config.json                 # spaces the user picked, defaults (work start time, user_key)
└── projects/
    └── <project_key>.json      # discovered work-item types, fields, workflow nodes, mappings
```

The exact shape is documented in [references/config-format.md](references/config-format.md). Read it before writing or reading config so you use the right keys.

## Tip: when a command's flags are unclear

The CLI is self-describing. Use it instead of guessing:

```bash
meegle inspect                 # list all commands
meegle inspect workitem.create # parameter schema for one command
meegle <resource> <method> --help
```
