# Create a card / work item

Goal: open a work item with **every required field filled**, driven by the saved config — no field IDs typed by the user, nothing missed. Talk to the user in Thai. Commands + the all-important `field_value` string rules are in [cli-reference.md](cli-reference.md).

## Step 1 — make sure setup exists

```bash
ls ~/.claude/meegle-buddy/config.json 2>/dev/null && echo READY || echo NEEDS_INIT
```

`NEEDS_INIT` → run [init](init.md) first. Otherwise read `config.json`.

## Step 2 — pick space + card type

- If the user named a space, use it; else use `default_project_key` (and say which you're using).
- Read `~/.claude/meegle-buddy/projects/<project_key>.json`. If missing, run the per-project part of init for this space first.
- Among `work_item_types` with `role: "card"`, pick the one the user means. If ambiguous, ask (Thai) listing the card types from the config, e.g. "จะเปิดเป็นแบบไหนครับ: <type A> / <type B>?".

## Step 2.5 — quick required-field check (LIGHT)

Run the **LIGHT** check from [check-fields.md](check-fields.md) on this card type (one `meta-create-fields` call, cached once per conversation). If a field just became **required** and isn't in the config, ask the user (Thai) and add it before collecting values. This is fast and only blocks on the dangerous case; a full review happens when the user runs "เช็ค field / sync meegle".

## Step 3 — collect field values

Walk the type's `create_fields` in order. **`template` comes first** (required on create) — pick the default template, or ask if there are several. For each remaining field, ask a plain Thai question using its `name`. Rules:

- **Required first.** Every required field (and everything in `create_fields`) must have a value before submit.
- **Title (`name`):** "ชื่อการ์ด / หัวข้อ คืออะไรครับ?".
- **select / multi_select:** present `options` labels in Thai (AskUserQuestion), then map the chosen label → its `value` (the **option_id**). ⚠️ Put the **option_id** in `field_value`, NEVER the human label — e.g. if the user picks "Option A" whose entry is `{label:"Option A", value:"opt_a1b2c3"}`, send `field_value:"opt_a1b2c3"`. For `multi_select` the value is a **stringified** array of `{option_id}` objects (see cli-reference.md). No stored options → ask the user to type it, or read an existing card to show valid values.
- **user / multi_user:** default to the user's own `user_key`; for someone else resolve via `meegle user search --user-keys "<name>" --project-key <PK> --format json`. Multi-user is a **stringified** array. Don't guess keys. (Owner/assignee are often a *role*, not a field — set those via `--role-operate` after create; see below.)
- **date:** ask plainly ("กำหนดส่งวันไหน?") and convert to epoch ms **as a string** with Python (snippet in [timelog.md](timelog.md)).
- **number / text:** ask directly (as a string).
- **multi_text (e.g. Description):** supports **Markdown** — you may format it with a bold summary line + bullets. ⚠️ Escape line breaks as `\n` (a raw newline crashes create). See the "Rich text" section in [cli-reference.md](cli-reference.md).
- Optional `create_fields`: offer them, allow "ข้าม".

Build each value as a **string** per the cli-reference value_type table — stringify any array/object.

## Step 4 — confirm, then create

Show a plain-Thai summary of exactly what will be created (type, title, each field with its human label and chosen value). Wait for "โอเค / ลงเลย".

```bash
meegle workitem create \
  --project-key <PK> --work-item-type <TYPE> \
  --fields '[
    {"field_key":"template","field_value":"<TEMPLATE_ID>"},
    {"field_key":"name","field_value":"<title>"},
    {"field_key":"<field>","field_value":"<value-as-string>"}
  ]' \
  --format json
```

Capture the new work-item id from the JSON output.

### Follow-ups (set after create)

- **Owner / assignee** — via `--role-operate` (role key from config `roles`):
  ```bash
  meegle workitem update --work-item-id <NEW_ID> --project-key <PK> \
    --role-operate '[{"op":"add","role_key":"<ROLE_KEY>","user_keys":["<USER_KEY>"]}]' --format json
  ```
- Any field the create response shows empty but you intended to set — re-send via `workitem update`.

Report the new card's id/link in Thai. For estimate/schedule, continue with [schedule](schedule.md). To log time against it, see [timelog](timelog.md).

## If create fails on a required field

The error usually names the missing/invalid field (or a STRING-protocol issue). Map it to the config field, fix the value (stringify if needed — see cli-reference self-heal table), ask the user if a value is missing, and retry. If a field that should be required wasn't in `create_fields`, add it to the config so it's asked next time.
