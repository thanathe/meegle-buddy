# Config format

Everything the skill discovers is stored under `~/.claude/meegle-buddy/`. This is **per-person, per-machine, and must never be committed to git**. Always read/write these files with the keys below — do not invent new shapes.

> All names, `field_xxxxxx` keys, slugs, and option codes shown below are **made-up illustrative examples**. Yours come from running discovery (`meegle workitem meta-*`) on your own space. Never copy keys from this doc or from anyone else's config.

Create the directory before writing:

```bash
mkdir -p ~/.claude/meegle-buddy/projects
```

## `~/.claude/meegle-buddy/config.json`

Global preferences and the list of spaces the user chose to use.

```json
{
  "version": 1,
  "user_key": "<your-user-key>",
  "work_start_default": "09:00",
  "lunch": { "start": "12:00", "end": "13:00" },
  "default_project_key": "<a-project-key>",
  "spaces": [
    { "project_key": "<project-key>", "name": "My Workspace", "slug": "<short-slug>" }
  ]
}
```

- `user_key` — the current user's Meegle user key, from `meegle user me`. Used for owner/assignee roles and "my" queries.
- `work_start_default` — default daily start time for timelog; the skill still asks each day but offers this as the default.
- `lunch` — unpaid break to skip when laying out time slots.
- `default_project_key` — used when the user does not name a space.
- `spaces[]` — only the spaces the user said they actually use. `project_key` can be the **slug** (the short code in the Meegle URL, e.g. `ab12cd`), the space name, or the long key — any string that `meegle workitem meta-types --project-key <x>` accepts works as `--project-key` everywhere. `slug` is the short URL code (optional, for display/links).

## `~/.claude/meegle-buddy/projects/<project_key>.json`

One file per space, named by `project_key`. Holds the discovered, curated profile for that space.

```json
{
  "project_key": "<project-key>",
  "name": "My Workspace",
  "discovered_at": "2026-01-01",
  "last_checked": "2026-01-01",
  "last_synced": "2026-01-01",
  "work_item_types": [
    {
      "type_key": "<card-type-key>",
      "name": "Task",
      "role": "card",
      "template_required": true,
      "templates": [
        {
          "id": "<template-id>",
          "name": "Default Workflow",
          "is_default": true,
          "nodes": [
            { "id": "<state_key>", "name": "Doing",    "type": "task" },
            { "id": "<state_key>", "name": "Reviewing", "type": "task" }
          ]
        }
      ],
      "fields": [
        {
          "key": "<field-key>",
          "name": "Category",
          "value_type": "select",
          "required": true,
          "options": [
            { "label": "Option A", "value": "<option-id>" },
            { "label": "Option B", "value": "<option-id>" }
          ]
        },
        { "key": "name", "name": "Title", "value_type": "text", "required": true }
      ],
      "roles": [ { "key": "<role-key>", "name": "Owner" } ],
      "create_fields": ["template", "name", "<field-key>"],
      "conditional_rules": [
        {
          "when_field": "<driver-field-key>",
          "when_option": "<option-id>",
          "when_label": "Option A",
          "require": ["<field-key>", "<field-key>"],
          "server_enforced": true,
          "evidence": "fill-rate 100% (n=12) 2026-01-01 + user confirmed"
        }
      ],
      "schedule": {
        "estimate_schedule_field": "<field-key>",
        "estimate_field_kind": "schedule_range",
        "effort_field": "<field-key>",
        "effort_unit": "minutes",
        "minutes_per_day": 480,
        "node_schedule": true
      }
    },
    {
      "type_key": "<timerecord-type-key>",
      "name": "Time Record",
      "role": "timerecord",
      "template_required": true,
      "fields": [
        { "key": "<field-key>", "name": "Start Time",    "value_type": "date", "required": false },
        { "key": "<field-key>", "name": "Adjusted Time", "value_type": "date", "required": false },
        { "key": "<field-key>", "name": "Description",   "value_type": "text", "required": true }
      ],
      "roles": [ { "key": "<role-key>", "name": "Owner" } ],
      "timelog": {
        "template_id": "<template-id>",
        "start_field": "<field-key>",
        "adjusted_field": "<field-key>",
        "description_field": "<field-key>",
        "duration_field": null,
        "link_field": "<field-key>",
        "link_value_type": "work_item_related_select"
      }
    }
  ]
}
```

### Field object

| key | meaning |
|---|---|
| `key` | the real field key to send as `field_key` (e.g. `field_xxxxxx`, or a built-in like `name`/`description`/`template`/`priority`) |
| `name` | human label shown to the user (keep as discovered) |
| `value_type` | the Meegle field type — drives how to build `field_value` (see the table in [cli-reference.md](cli-reference.md)). E.g. `text`, `number`, `select`, `multi_select`, `user`, `multi_user`, `date`, `schedule`, `work_item_related_select`, `work_item_related_multi_select` |
| `required` | whether create requires it — from `meta-create-fields` (`is_required == 1`). Treat skill-added extras the same once in `create_fields`. |
| `options` | for select/multi-select: `[{label, value}]` where `value` is the **option_id**. Lets you show friendly labels and send the correct id. |

### Per-type curated keys

- `role` — `"card"` (something you open/work on) or `"timerecord"` (used for logging time). A space may have several `card` types and at most one `timerecord` type.
- `template_required` — Meegle requires a `template` field on create; store the template id(s).
- `create_fields` — the ordered ask-list for opening this card; **include `template`** and all required fields, then useful optional ones.
- `roles` — role keys (owner/assignee) for `--role-operate` (from `meta-roles`).
- `templates` — workflow templates, each with `nodes` (`id` is the node **state_key**, used by `workflow update-node`). Mark one `is_default`.
- `conditional_rules` — value-dependent required fields the Meegle form enforces via **linkage** (e.g. "Category = Option A ⇒ some relation field required"). ⚠️ The API does **not** expose these — they are inferred from real cards / 必填 errors and confirmed by the user during FULL sync (see the "conditional rules" step in [check-fields.md](check-fields.md)). Each rule: when `when_field` has option `when_option`, every key in `require[]` must be filled at create. `server_enforced` = whether create actually errors without it (`true` / `false` = UI-only, fill anyway for data consistency / `"unknown"`). `when_label` + `evidence` are for humans — keep them current. Fields named in `require[]` must exist in `fields[]`.
- `schedule` — estimate/effort/schedule mapping (see schedule.md). `estimate_field_kind` notes whether the estimate is a single `schedule` field (`schedule_range`) or two separate start/end fields (`two_fields`). Omit if the type has no estimation.
- `timelog` — how to build a time record (see timelog.md). Only on the `timerecord` type. Store its own `template_id`.

### Freshness keys

- `discovered_at` — when the profile was first built.
- `last_checked` — last time any drift check (LIGHT or FULL) verified this project. Bumped on every check.
- `last_synced` — last time a FULL sync curated the fields. The skill may gently suggest a FULL sync if this is more than ~7 days old.
- A field with `"skip": true` means the user was asked about it and chose not to add it — LIGHT mode ignores it; FULL mode re-lists it only if its required flag changes. See [check-fields.md](check-fields.md).

### Notes

- `value_type` matters: it tells you whether `field_value` is a plain string or a **JSON-stringified** array/object (see cli-reference.md). Getting this right is what prevents "need STRING type, but got: LIST" errors.
- Not every space has a separate time-record type. If a space can't log time, omit the timerecord type and tell the user.
- Keep the file small and curated — store fields used for create/timelog/schedule plus all required ones. Re-discover more later if needed.
- When in doubt about a key, re-run discovery rather than guessing.
