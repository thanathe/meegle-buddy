# Init — guided first-run setup (and adding/refreshing projects)

Goal: build the user's personal config under `~/.claude/meegle-buddy/` by **discovering** their spaces, work-item types, create-required fields, roles, and workflow nodes — so later actions need no field IDs and never miss a required field. Talk to the user in Thai throughout. This is the one place where you do the careful thinking; keep it patient and clear.

Run this when: no config exists yet, the user wants to add another project, or fields/workflows changed and need a refresh. All commands use the **`meegle`** CLI — see [cli-reference.md](cli-reference.md).

## Step 0 — prerequisites

```bash
command -v meegle || echo "MISSING"
meegle auth status --format json
```

If `meegle` is missing or auth fails, stop and guide the user (in Thai) to install/log in (`meegle auth login`). Don't continue until `auth status` shows authenticated.

```bash
mkdir -p ~/.claude/meegle-buddy/projects
meegle user me --format json     # read user_key into config.user_key
```

## Step 1 — pick spaces

Ask which Meegle space(s) the user works in. **Prefer the slug from the URL** — it's the most reliable:

> "ปกติทำงานใน space ไหนของ Meegle ครับ? วิธีที่ชัวร์สุดคือก๊อป **slug จาก URL** มา (เช่น `ab12cd` — อยู่ใน address bar ตอนเปิด space นั้น) หรือจะบอกชื่อเต็มก็ได้ (มีหลายอันก็ได้)"

> ⚠️ **`project search` matches the space name EXACTLY — not fuzzy/partial.** A partial name ("Product") or a slightly-off spelling returns **empty** (`projects: []`). Only the exact full name works. The **slug never has this problem** — steer the user to the slug, and treat any name they give as a best-effort guess that may miss.

### Resolve each space (slug-first, with fallback)

`--project-key` accepts the **slug**, the **exact name**, or the long **project key** — all work for every later command. Resolve like this:

1. **Slug or pasted URL** (extract the slug from the URL path) → validate directly:
   ```bash
   meegle workitem meta-types --project-key "<slug>" --format json   # returns list[] of work-item types
   ```
   Got a `list[]` of types back → ✅ valid.

2. **A name** → confirm it resolves:
   ```bash
   meegle project search --project-key "<name>" --format json   # returns projects[] (name, project_key, simple_name=slug)
   ```
   - Exactly one hit → grab its `simple_name` (slug) and use that as the canonical `project_key`.
   - **`projects: []` (empty)** → the name wasn't an exact match. **Don't give up or retry name variants — ask for the slug/URL** (Thai): "หาด้วยชื่อนี้ไม่เจอครับ (ระบบต้องตรงเป๊ะ) — ขอ slug จาก URL หรือพาสต์ลิงก์ space มาได้ไหมครับ?" then resolve via step 1.
   - Multiple hits → show them and let the user pick.

3. Store the **slug** as `project_key` in the config (works everywhere, human-recognizable).

Save each chosen space into `config.json` → `spaces[]` (project_key = the slug, name, slug). Ask which is the default → `default_project_key`.

## Step 2 — defaults

Ask (Thai), with sensible defaults:
- "ปกติเข้างานกี่โมงครับ?" → `work_start_default` (default 09:00)
- Confirm lunch 12:00–13:00 (skipped in timelog) → `lunch`

Save `config.json`.

## Step 3 — per project: discover types

For **each** chosen space:

```bash
meegle workitem meta-types --project-key <PK> --format json
```

Show the types in Thai and ask which they care about:

> "ใน <space> มี work item แบบนี้ จะใช้เปิดการ์ด/ลงงานแบบไหนบ้างครับ?"

For each selected type, ask its **role**:
- การ์ดที่เอาไว้เปิด/ทำงาน (เช่น Task, Story, Issue, Meeting — ตามที่ meta-types คืนมา) → `role: "card"`
- ตัวที่ใช้ลงเวลา / Time Record → `role: "timerecord"` (at most one per space; some spaces have none)

Keep it light — most non-dev users need one card type and maybe the time-record type.

## Step 4 — per type: discover create-fields, roles, workflow, schedule

For each selected type (note `--page-num 1` is required on meta-fields/meta-roles):

```bash
meegle workitem meta-create-fields --project-key <PK> --work-item-type <TYPE> --format json
meegle workitem meta-fields        --project-key <PK> --work-item-type <TYPE> --page-num 1 --format json
meegle workitem meta-roles         --project-key <PK> --work-item-type <TYPE> --page-num 1 --format json
meegle workflow meta-node-fields   --project-key <PK> --work-item-type <TYPE> --format json    # card types w/ nodes
```

Build the type entry per [config-format.md](config-format.md):

1. **Fields** — from `meta-create-fields` (`FieldConfList[]`), record every field with `is_required == 1` as `required:true`, plus obviously useful optional ones (component, link, owner). **`meta-create-fields.is_required` is the authoritative "required at create" flag — do NOT use `meta-fields`' required flag** (a field can show required there because it's required at a workflow node/transition, not at create). Store each field's type from `field_type_key` (this decides how `field_value` is built — see cli-reference.md) into the config's `value_type`. For **select** fields, capture `options: [{label, value}]` (value = option_id) from `meta-fields` (`list[]`). If options aren't in the output, learn them from an existing item (`meegle workitem get`/`query`) — never copy another team's codes; if you still can't, store without options and ask the user to type the value at run time.
2. **template** — every create needs a `template` field. Get the template id(s):
   `meegle workitem meta-fields --project-key <PK> --work-item-type <TYPE> --field-keys '["template"]' --page-num 1 --format json`. Store under `templates` (with `id`); mark a default. Put `"template"` first in `create_fields`.
3. **create_fields** — ordered ask-list: `template`, then all required fields, then useful optional ones.
4. **roles** — store owner/assignee role keys for `--role-operate`.
5. **nodes** — if the type has workflow nodes you'll schedule, capture each node's **state_key** (the id used by `workflow update-node`) into the template's `nodes`. Read them from an existing item via `workflow get-node ... --node-id-list '["_all"]'` if needed.
6. **schedule** — if the type supports estimation, record which field holds the estimate timeline (and whether it's one `schedule` field or two start/end fields → `estimate_field_kind`), which holds effort, the effort unit, and minutes-per-day (commonly 480). No complexity logic.

### For the timerecord type — map the timelog fields

Inspect its fields and identify by name (English or Thai), storing under `timelog` (plus its own `template_id`):
- `start_field` — date/datetime field for start time.
- `adjusted_field` — date/datetime field for end/adjusted time, if present (often needs a follow-up update — see timelog.md).
- `duration_field` — number field for duration/minutes, if the space logs by duration.
- `description_field` — the required text field for the work summary.
- `link_field` + `link_value_type` — how a record attaches to its parent card (usually a `workitem_related_select` field). Learn the parent-link field by reading an existing time record (`meegle workitem get`/`query`).

If auto-mapping is unclear, show candidate fields to the user (Thai, AskUserQuestion) and let them confirm. Getting this right is what makes daily logging foolproof.

## Step 5 — save & confirm

Write `~/.claude/meegle-buddy/projects/<project_key>.json` per project; update `config.json`. Summarize in Thai:

> "ตั้งค่าเรียบร้อยครับ ✅
> - Space: <names>
> - การ์ดที่เปิดได้: <card types>
> - ลงเวลาได้ที่: <timerecord type or 'ยังไม่มี'>
> ต่อไปสั่งได้เลย เช่น 'เปิดการ์ด' หรือ 'ลงเวลาวันนี้'"

## Refresh / add later

- Add a project: re-run Steps 1, 3–5 for the new space only.
- Refresh fields (workflow/fields changed): re-run Step 4 and overwrite that project's file; bump `discovered_at`.

> You don't have to refresh manually — every create/timelog/schedule run does an automatic **field freshness check** ([check-fields.md](check-fields.md)) and asks you about any new / newly-required / removed field on the spot. This is important here because the team changes fields often while the workflow is still being adjusted.
