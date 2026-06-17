# Estimate / effort / schedule

Goal: set a card's estimate, effort, and schedule from numbers the user gives — **no complexity scoring, no auto-derivation**. You ask for the estimate and dates; you only convert units and write them to the right fields from the config. Talk to the user in Thai. Commands + `field_value` string rules: [cli-reference.md](cli-reference.md).

## What the config gives you

From the card type's `schedule` block (see config-format.md):

- `estimate_schedule_field` — field holding the estimate timeline.
- `estimate_field_kind` — `"schedule_range"` (one `schedule` field taking `[startMs,endMs]`) or `"two_fields"` (separate start + end date fields).
- `effort_field` — field holding effort.
- `effort_unit` — `"minutes"`, `"hours"`, or `"days"`.
- `minutes_per_day` — to convert man-days → minutes when `effort_unit` is minutes (commonly 480 = 8h).
- `node_schedule` — whether this type also schedules per workflow node.
- `templates[].nodes` — node ids (state_keys) for per-node scheduling.

No `schedule` block → the type doesn't support estimation; tell the user.

> **Quick required-field check (LIGHT):** before writing, run the LIGHT check from [check-fields.md](check-fields.md) on this card type (one `meta-create-fields` call, cached once per conversation). If a schedule/effort field just became required, ask the user (Thai) and update the config first. For a full review of node/optional fields, the user can run "เช็ค field / sync meegle".

## Step 1 — ask the user (plain terms)

- "งานนี้ใช้เวลาประมาณเท่าไหร่ครับ?" → effort (man-days / hours / count; clarify the unit).
- "เริ่มเมื่อไหร่ ถึงเมื่อไหร่ครับ?" → schedule start/end dates.

Do **not** infer effort from any complexity guess. Take the user's number as given. If they give only effort, you may propose a date range to confirm; if only dates, ask for effort.

## Step 2 — convert

Compute timestamps with Python (Bangkok tz) — snippet in [timelog.md](timelog.md). For an all-day range, use start-of-day for start and end-of-day for end.

Convert effort to `effort_unit`: minutes = man_days × `minutes_per_day` (when unit is minutes); hours → minutes (×60) if needed.

## Step 3 — write the card-level estimate + effort

Build values as **strings**; the `schedule` value_type must be a **stringified** `[startMs,endMs]`.

```bash
# estimate_field_kind = "schedule_range"
meegle workitem update --work-item-id <ID> --project-key <PK> \
  --fields '[
    {"field_key":"<estimate_schedule_field>","field_value":"[<startMs>,<endMs>]"},
    {"field_key":"<effort_field>","field_value":"<effortInUnit>"}
  ]' --format json

# estimate_field_kind = "two_fields"
meegle workitem update --work-item-id <ID> --project-key <PK> \
  --fields '[
    {"field_key":"<estimate_start_field>","field_value":"<startMs>"},
    {"field_key":"<estimate_end_field>","field_value":"<endMs>"},
    {"field_key":"<effort_field>","field_value":"<effortInUnit>"}
  ]' --format json
```

If a value is rejected, read a card that already has an estimate (`meegle workitem get`) and mirror its shape.

## Step 4 — per-node schedule (only if `node_schedule` is true)

If work runs across workflow nodes (e.g. coding node, testing node) and the user wants each scheduled, set the schedule per node. `--node-id` is the node's **state_key**.

🚫 **DO NOT pass `--node-schedule '<json>'` (or `-P`/`--params` JSON)** — the CLI marshals it as a string and errors `need STRUCT type, but got: STRING`. ✅ **Use `--set` with dot-path** instead. `owners` MUST use array-index `owners[0]=` (plain `owners=<key>` errors `unsupported type:float64, expected type:LIST`). The owner inherited from the assignee role is reused, so `owners[0]` in this same call covers it — no separate owner call needed. `points` accepts floats (e.g. 0.5).

```bash
meegle workflow update-node --work-item-id <ID> --node-id <STATE_KEY> --project-key <PK> \
  --set node_schedule.estimate_start_date=<ms> \
  --set node_schedule.estimate_end_date=<ms> \
  --set node_schedule.points=<days> \
  --set 'node_schedule.owners[0]=<USER_KEY>'
```
Returns `"success"`. (Confirmed working 2026-06-01; the old `--node-schedule` JSON form does not.)

Lay node timelines sequentially (one node after the previous) unless the user says otherwise. Do not split or pad time using any complexity rule — just use the durations the user gave. For per-person schedules use `--schedules`. If a shape is rejected, read an item that already has node schedules (`workflow get-node`) and mirror it.

> ⚠️ If the card type has an **auto-calculated** estimate/complexity field (e.g. a rollup on a parent, or a computed Complexity), do NOT try to write it — `workitem update` errors `计算字段值不可编辑` / `无权编辑`. Set the driving inputs (node points / child cards) and let it compute.

## Step 5 — confirm

Before writing, show the user in Thai: effort (with unit), schedule dates, and any per-node plan. Wait for "โอเค". After writing, confirm success and show the card link.
