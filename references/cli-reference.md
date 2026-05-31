# meegle CLI reference

All Meegle work goes through the **`meegle`** command-line tool (NOT `lark-cli`). General shape:

```bash
meegle <resource> <method> [flags] --format json
```

Always pass `--format json` so you can parse the result. Always pass `--project-key` explicitly from the config. **When unsure of a flag, ask the CLI itself** — it is self-describing:

```bash
meegle inspect                 # list all commands
meegle inspect workitem.create # parameter schema (shows <string> vs <object[]>)
meegle <resource> <method> --help
```

## Auth (run first each session)

```bash
meegle auth status --format json     # expect {"authenticated": true, ...}
meegle user me --format json         # current user -> user_key
# login (if needed):  meegle auth login   (pick host, e.g. project.larksuite.com)
```

## Discovery (read-only) — used at init

`--project-key` accepts the **slug** (the short code in the Meegle URL, e.g. `ab12cd`), the **space name**, OR the long **project key** — all of them work for every command.

```bash
# Resolve a space (slug/name -> project_key). Returns projects[].
meegle project search --project-key "<slug-or-name-or-key>" --format json

# Work-item types in a space. Returns list[]. Skip disabled types (is_disable == 1).
meegle workitem meta-types --project-key <PK> --format json

# Fields needed at CREATE — the foolproof "fill everything" source. Returns FieldConfList[].
meegle workitem meta-create-fields --project-key <PK> --work-item-type <TYPE> --format json

# All fields of a type (for options + non-create fields). Returns list[] + pagination. --page-num REQUIRED (50/page)
meegle workitem meta-fields --project-key <PK> --work-item-type <TYPE> --page-num 1 --format json
#   narrow with: --field-keys '["field_abc123"]'  (exact)  or  --field-query "<text>"  (fuzzy)

# Roles -> role_key. Returns list[]. --page-num REQUIRED
meegle workitem meta-roles --project-key <PK> --work-item-type <TYPE> --page-num 1 --format json

# Workflow node fields / live nodes (node "id" = its state_key)
meegle workflow meta-node-fields --project-key <PK> --work-item-type <TYPE> --format json
meegle workflow get-node --work-item-id <ID> --node-id-list '["_all"]' --field-key-list '["_all"]' --project-key <PK> --format json

# Name/email -> user_key. Returns user info.
meegle user search --user-keys '["<name-or-email>"]' --project-key <PK> --format json
```

### ⚠️ Response envelopes differ per command — read the right key

| command | top-level array key | each item's useful keys |
|---|---|---|
| `project search` | `projects` | `project_key`, `name`, `simple_name` (= slug) |
| `workitem meta-types` | `list` | `type_key`, `name`, `api_name`, `is_disable` (2 = enabled, 1 = disabled → skip) |
| `workitem meta-create-fields` | `FieldConfList` | `field_key`, `field_name`, **`field_type_key`** (the type), **`is_required`** (1 = required, 2 = not), `field_alias` |
| `workitem meta-fields` | `list` (+ `pagination`) | `field_key`, `field_name`, **`value_type`** (the type), options for selects |
| `workitem meta-roles` | `list` | `role_key`, `name` |

**Authoritative "required when creating" = `meta-create-fields` → `is_required == 1`.** Do NOT use `meta-fields` for the required flag — a field can look required there because it's required at a workflow node/transition, not at create. Use `meta-create-fields` for the create checklist (it already carries `field_type_key` + `is_required`), and `meta-fields` mainly to fetch **select options** and to discover fields outside the create form.

> If `meta-fields`/`meta-create-fields` doesn't include a select field's choices, learn valid option ids by reading an existing item (`meegle workitem get`/`query`). **Never reuse another team's option codes.**

## Inspect existing items (learn real option values / link shapes)

```bash
meegle workitem query --project-key <PK> --mql "<MQL>" --format json   # see base meegle skill for MQL syntax
meegle workitem get   --work-item-id <ID> --project-key <PK> --format json
```

## ⚠️ The #1 write rule: `field_value` is ALWAYS a string (STRING protocol)

Field values are passed with **`--fields`**. Two accepted forms:

```bash
# (A) one flag, JSON array of objects  (canonical)
--fields '[{"field_key":"name","field_value":"My title"},{"field_key":"priority","field_value":"2"}]'

# (B) repeat the flag, one object each  (easier to build incrementally)
--fields '{"field_key":"name","field_value":"My title"}' \
--fields '{"field_key":"priority","field_value":"2"}'
```

**Every `field_value` must be a STRING.** Scalars go in as plain strings. **Arrays and objects must be JSON-stringified** (embedded JSON with escaped quotes) — passing a raw array/object errors with `need STRING type, but got: LIST` / `MAP`.

| field type (from field_type_key / value_type) | meaning | field_value (always a string) |
|---|---|---|
| `work_item_template` / `template` | template id — **required on create** | `"145405865"` |
| `text` / `multi_text` / `link` / `bool` / `number` | single literal | `"My item"` / `"100"` / `"true"` |
| `user` | single user_key | `"7509072868295085608"` |
| `multi_user` | user_key array, **stringified** | `"[\"7509072868295085608\",\"...\"]"` |
| `select` / `radio` / `tree_select` | one option_id | `"437794"` |
| `multi_select` | array of `{option_id}`, **stringified** | `"[{\"option_id\":\"111\"},{\"option_id\":\"222\"}]"` |
| `tree_multi_select` | option_id string array, **stringified** | `"[\"id1\",\"id2\"]"` |
| `date` / `date_time` | ms timestamp (string) | `"1722182400000"` |
| `schedule` | `[start_ms, end_ms]`, **stringified** | `"[1722182400000,1722355199999]"` |
| `work_item_related_select` | linked work-item id | `"145405865"` |
| `work_item_related_multi_select` | id array, **stringified** | `"[145405865,145405866]"` |

Compute `date`/`schedule` millisecond values with Python (Bangkok tz) — see [timelog.md](timelog.md). (Type-key spelling can vary slightly by version, e.g. `work_item_related_select` vs `workitem_related_select` — match what discovery returns.)

## Write

### Create a work item / card

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

- **`template` is a field and is required on create** — there is no `--template-id` flag.
- Include **every** field from `meta-create-fields` with `is_required == 1` — that's the complete create checklist for your work-item type.
- Capture the new work-item id from the JSON output.

### Update an existing item

```bash
meegle workitem update \
  --work-item-id <ID> --project-key <PK> \
  --fields '[{"field_key":"<field>","field_value":"<value-as-string>"}]' \
  --format json
```

> Some values don't "stick" at create on certain setups (e.g. a time record's adjusted/end time). Set those with a follow-up `update`.

### Set people on roles (owner / assignee)

Roles **cannot** go through `--fields` on update. Use `--role-operate` (a JSON array of operations):

```bash
meegle workitem update \
  --work-item-id <ID> --project-key <PK> \
  --role-operate '[{"op":"add","role_key":"<ROLE_KEY>","user_keys":["<USER_KEY>"]}]' \
  --format json
```

`<ROLE_KEY>` from `meta-roles`; `<USER_KEY>` from `meegle user me` (yourself) or `meegle user search` (someone else). Never guess user keys.
(On *create*, an owner can instead be set via the `role_owners` field, stringified: `{"field_key":"role_owners","field_value":"[{\"role\":\"<role_id>\",\"owners\":[\"<USER_KEY>\"]}]"}` — but the follow-up `--role-operate` update is simpler and reliable.)

### Per-node schedule (estimate dates + owner on a workflow node)

```bash
# schedule (dates + points) for a node — node-id is the node's state_key
meegle workflow update-node \
  --work-item-id <ID> --node-id <STATE_KEY> --project-key <PK> \
  --node-schedule '{"estimate_start_date":<ms>,"estimate_end_date":<ms>,"owners":["<USER_KEY>"],"points":<days>}'

# owners (separate call!)
meegle workflow update-node \
  --work-item-id <ID> --node-id <STATE_KEY> --project-key <PK> \
  --node-owners '["<USER_KEY>"]'
```

> `workflow update-node` **cannot change schedule, per-person schedule, and owners in one call** — split them. For per-person schedules use `--schedules` (array, one entry per person). If a shape is rejected, read an item that already has node schedules (`workflow get-node`) and mirror it.

## When a command fails (self-heal)

| Error contains | Fix |
|---|---|
| `need STRING type, but got: LIST` / `MAP` | the `field_value` must be a **stringified** JSON string, not a raw array/object |
| `invalid select option` | use a valid option_id from `meta-fields`; if ambiguous, ask the user |
| `creating ... missing template` | add `{"field_key":"template","field_value":"<id>"}` |
| `node not found` | get the real node state_key via `workflow get-node` — don't guess |
| auth error | tell the user (Thai) to `meegle auth login`, then retry |
| role update via fields rejected | use `--role-operate`, not `--fields` |
| empty / `KeyError` when parsing | you read the wrong envelope key — check the table above (`list` vs `FieldConfList` vs `projects`) |

Auto-retry at most twice after a targeted fix; then stop and explain to the user.
