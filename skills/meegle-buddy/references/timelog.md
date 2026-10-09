# Log time (Time Records)

Goal: lay out the day's work as time records — each with start/end (or duration), a description, and a link to a parent card — using the discovered `timelog` mapping so nothing lands in the wrong field. Talk to the user in Thai. Commands + `field_value` string rules: [cli-reference.md](cli-reference.md).

## Step 1 — setup + space

- Ensure config exists (else run [init](init.md)).
- Pick the space (named, or `default_project_key`). Read its project file.
- Find the type with `role: "timerecord"`. If the space has none, tell the user it can't log time here and offer another space.
- **Quick required-field check (LIGHT):** run the LIGHT check from [check-fields.md](check-fields.md) on the timerecord type before logging (one `meta-create-fields` call, cached once per conversation). If a field just became required, ask the user (Thai) and update the config first. For a full review the user can run "เช็ค field / sync meegle".

## Step 2 — ask the day's shape

1. **Start of day:** "เข้างานกี่โมงครับ?" (offer `work_start_default`).
2. **What was worked on:** ask for the tasks and how long each took (or start/end). Keep it conversational — a non-dev might just say "เช้าประชุม บ่ายทำเอกสาร".
3. Lay out slots **sequentially** from the start time, and **always skip lunch** (`config.lunch`, default 12:00–13:00). No record over lunch, no overlaps, keep inside working hours.

## Step 3 — compute timestamps with Python (Bangkok tz)

Never hand-calculate epoch ms. Pass the result as a **string** in `field_value`.

```bash
python3 - <<'PY'
from datetime import datetime
from zoneinfo import ZoneInfo
tz = ZoneInfo("Asia/Bangkok")
def ms(date_str, hhmm):
    h, m = map(int, hhmm.split(":"))
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=h, minute=m, tzinfo=tz)
    return int(dt.timestamp() * 1000)
print(ms("2026-05-31", "09:00"), ms("2026-05-31", "10:30"))   # slot start, end
PY
```

Use the correct date when logging a past day.

## Step 4 — build each time record

For every slot, use the type's `timelog` mapping from the config:

- `start_field` ← slot start (ms, as a string)
- `adjusted_field` ← slot end (ms, as a string) **if present**
- `duration_field` ← duration in the unit the field expects (often **minutes**), **if** the space logs by duration
- `description_field` ← short summary of that slot (**required — never blank**)
- `link_field` ← the parent card's work-item id (value_type is usually `workitem_related_select` → a plain id string)
- `template` ← the timerecord type's `template_id` (required on create)

**Always link each record to a parent card** (work item / meeting / task / issue / project). Never create a floating record. No obvious parent → ask which card to link, or create one first ([create-card](create-card.md)).

## Step 5 — confirm, then create each record

Show the full day's plan in Thai as a table (time → task → linked card) plus total hours. Wait for "โอเค / ลงเลย".

A time record is a work item of the timerecord type:

```bash
meegle workitem create \
  --project-key <PK> --work-item-type <TIMERECORD_TYPE> \
  --fields '[
    {"field_key":"template","field_value":"<TEMPLATE_ID>"},
    {"field_key":"name","field_value":"<short summary>"},
    {"field_key":"<start_field>","field_value":"<startMs>"},
    {"field_key":"<description_field>","field_value":"<desc>"},
    {"field_key":"<link_field>","field_value":"<parent_work_item_id>"}
  ]' \
  --format json
```

### Fields that don't stick at create

On many setups the **adjusted/end time** and the **owner** don't apply at create — set them with a follow-up `update` on the new record id:

```bash
# end/adjusted time
meegle workitem update --work-item-id <NEW_ID> --project-key <PK> \
  --fields '[{"field_key":"<adjusted_field>","field_value":"<endMs>"}]' --format json
# owner (role_key from the config's roles for this type)
meegle workitem update --work-item-id <NEW_ID> --project-key <PK> \
  --role-operate '[{"op":"add","role_key":"<ROLE_KEY>","user_keys":["<USER_KEY>"]}]' --format json
```

If a value is rejected with `need STRING type ...`, stringify it (see cli-reference). If unsure of a field's shape, read an existing time record (`meegle workitem get`) and mirror it.

### Step 6 — VERIFY the parent link stuck (it fails silently)

The `link_field` is a `work_item_related_select` — it accepts only the work-item type(s) listed in its `related_work_item_info` (from `meta-fields`). Set it to a wid of any **other** type and the API returns **success with no error but stores null**. So after creating, read each record's link back via MQL and confirm it's not null:

```bash
meegle workitem query --project-key <PK> \
  --mql "SELECT \`<link_field>\` FROM \`<PK>\`.\`<TIMERECORD_TYPE>\` WHERE \`work_item_id\`=<NEW_ID> LIMIT 1" --format json
# null → NOT linked (wrong target type? give a wid of the type the field accepts); {"key_label_value":{...}} → OK
```

If the user says "the card shows Empty" but MQL shows the link **is** set, it's just a **stale UI cache** — tell them to hard-refresh (Cmd/Ctrl+Shift+R). `workitem get` brief also omits relation fields, so always check with MQL, not `get`.

Report success in Thai (how many records, total hours). If a day looks short (e.g. a known recurring meeting is missing), gently ask — but never invent entries.
