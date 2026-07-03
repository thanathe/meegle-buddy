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
- **Conditional rules:** each time the user picks a `select` value, check the type's `conditional_rules` (see [config-format.md](config-format.md)) for an entry matching `(when_field == this field, when_option == chosen option)`. Every key in its `require[]` becomes **required for this create** — add them to the ask-list (using their `fields[]` labels/options) even if they're marked optional. Tell the user why (Thai): "เลือก «<label>» แล้ว ระบบบังคับกรอก «<field>» เพิ่มครับ". Collect driver fields (the ones appearing in any `when_field`) **early** so the follow-ups surface before the confirm step.
- **Title (`name`):** "ชื่อการ์ด / หัวข้อ คืออะไรครับ?".
- **select / multi_select:** present `options` labels in Thai (AskUserQuestion), then map the chosen label → its `value` (the **option_id**). ⚠️ Put the **option_id** in `field_value`, NEVER the human label — e.g. if the user picks "Option A" whose entry is `{label:"Option A", value:"opt_a1b2c3"}`, send `field_value:"opt_a1b2c3"`. For `multi_select` the value is a **stringified** array of `{option_id}` objects (see cli-reference.md). No stored options → ask the user to type it, or read an existing card to show valid values.
- **user / multi_user:** default to the user's own `user_key`; for someone else resolve via `meegle user search --user-keys "<name>" --project-key <PK> --format json`. Multi-user is a **stringified** array. Don't guess keys. (Owner/assignee are often a *role*, not a field — usually set via `--role-operate` after create; **but in some spaces the owner role is REQUIRED at create** — see Follow-ups below.)
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

- **Owner / assignee** — usually via `--role-operate` *after* create (role key from config `roles`):
  ```bash
  meegle workitem update --work-item-id <NEW_ID> --project-key <PK> \
    --role-operate '[{"op":"add","role_key":"<ROLE_KEY>","user_keys":["<USER_KEY>"]}]' --format json
  ```
  ⚠️ **Some spaces make the owner role REQUIRED at create** — then a plain create errors with the role name "必填" (required). In that case pass the owner **in the create `--fields` itself**, as a field whose key is the fully-qualified role field `role_<project_key>_<work_item_type_key>_owner` and whose `field_value` is the **single user_key as a string** (not an array). Discover whether this applies from `meta-create-fields` (the role may be listed) or by reacting to the "必填" error; record it on the type's config so it's done up-front next time. `--role-operate` and the `role_owners` param are **ignored** by `create` in these spaces — it must be a field.
- **Link / relation fields** (`workitem_related_*`) — these can fail **at create** with `字段「…」当前选项值已失效` even when the target id is valid. If so, create the card WITHOUT the link, then set it via a follow-up `workitem update --fields` (value = the target work-item id as a string).
- Any field the create response shows empty but you intended to set — re-send via `workitem update`.
- **Show under a specific story node** — if the parent is a node-driven workflow and the user wants the card under a particular node (not just the parent's rollup list), the link field is not enough. Follow [node-binding.md](node-binding.md) (the CLI can't set the node-edge; it's a web-UI/endpoint step).

### Step 5 — verify before reporting done (do NOT skip)

A `"success"` / `mcp_result` response does **not** prove a value stuck. Read the card back and confirm each intended field literally appears:
```bash
meegle workitem get --work-item-id <NEW_ID> --project-key <PK> \
  --fields "<each field you set>" --format json
# + workflow get-node ... if you set node schedules
```
Tick every field you meant to set — everything in the config's `create_fields`, plus the follow-ups you intended (role owner, relation/link fields, node schedules, estimate/effort). A half-filled card (links/schedule/estimate silently missing) is the most common failure; this read-back catches it.

Report the new card's id/link in Thai. For estimate/schedule, continue with [schedule](schedule.md). To log time against it, see [timelog](timelog.md).

## If create fails on a required field

The error usually names the missing/invalid field (or a STRING-protocol issue). Map it to the config field, fix the value (stringify if needed — see cli-reference self-heal table), ask the user if a value is missing, and retry. If a field that should be required wasn't in `create_fields`, add it to the config so it's asked next time.

⚠️ **必填 (required) error on a field that `meta-create-fields` says is optional** → that's a **conditional linkage rule** the API doesn't expose, keyed to some select value you sent (usually a category-like field). After fixing this create, save/extend a `conditional_rules` entry on the type — `when_field`/`when_option` = the driver value that was in effect, `require` += the field that errored, `server_enforced: true` — so next time it's asked up-front. Do NOT flip the field to globally `required: true`; that forces it on cards where it doesn't apply.
