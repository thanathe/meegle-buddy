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

`--project-key` accepts the **slug** (the short code in the Meegle URL, e.g. `ab12cd`), the **exact space name**, OR the long **project key** — all of them work for every command. **Prefer the slug** — `project search` matches names *exactly*, so a partial/misspelled name finds nothing (see init.md Step 1).

```bash
# Resolve a space name -> slug + project_key. Returns projects[] (name, project_key, simple_name=slug).
# ⚠️ EXACT name match only — a partial/misspelled name returns projects: [] (empty). The slug never has this issue.
meegle project search --project-key "<exact-name-or-slug>" --format json

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

> ⚠️ **`work_item_related_select` fails SILENTLY when the target is the wrong work-item TYPE.** Each related-select accepts only the type(s) declared in its `related_work_item_info[].work_item_type` (from `meta-fields`). Pass a wid of any **other** type and the API returns success-with-no-error (`{"mcp_result":""}`) but stores **null** — the link silently vanishes. (It also does NOT apply at `create` — set relation links with a follow-up `update`.) **So after setting any relation link, VERIFY it via MQL:** `SELECT \`<field>\` FROM ... WHERE \`work_item_id\`=<id>` (`workitem get` brief omits relation fields). If MQL shows it set but the user sees "Empty" on the card, that's a **stale UI cache** — hard-refresh. _(Tip: if the user hands you a wid that won't link, it's often a parent/grouping item of the wrong type — read its `work_item_type` and find the child of the accepted type.)_

### Rich text in `multi_text` fields (e.g. Description)

`multi_text` fields render **Markdown**, so you can format the description with headings/bold/bullets instead of a flat blob.

⚠️ **The one hard rule: escape line breaks as `\n` inside the JSON string.** A **raw** newline in the `field_value` makes create/update fail (server error / invalid JSON). Always use the `\n` escape.

Supported (verified on create + update):
- `**bold**`, `*italic*` / `_italic_`, `~~strikethrough~~`, `` `code` ``, `<u>underline</u>`
- `- ` bullet lists, `1. ` numbered lists
- use sparingly: code block ` ```lang\n...\n``` `, quote `> text`, horizontal rule `---`, colour `<span style=\"color: rgb(245,74,69)\">x</span>`, highlight `<span style=\"background-color: rgb(250,211,85)\">x</span>` (escape the inner quotes `\"` inside the JSON)

Example:

```bash
--fields '{"field_key":"description","field_value":"**Summary line.**\n- point A\n- point B\n\n1. step one\n2. step two"}'
```

Keep it readable — a bold summary line plus a few bullets is plenty; don't over-format.

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

🚫 **The `--node-schedule '<json>'` flag does NOT work** — it errors `need STRUCT type, but got: STRING` (the CLI marshals the JSON object as a string). Same for `-P`/`--params`. ✅ **Use `--set` dot-path.** `owners` needs array-index `owners[0]=` (plain `owners=<key>` → `unsupported type:float64, expected type:LIST`). `points` accepts floats.

```bash
# schedule (dates + points + owner) for a node in ONE call — node-id is the node's state_key
meegle workflow update-node \
  --work-item-id <ID> --node-id <STATE_KEY> --project-key <PK> \
  --set node_schedule.estimate_start_date=<ms> \
  --set node_schedule.estimate_end_date=<ms> \
  --set node_schedule.points=<days> \
  --set 'node_schedule.owners[0]=<USER_KEY>'
```
Returns `"success"`. The owner inherited from the assignee role is reused via `owners[0]` — no separate `--node-owners` call needed. (Confirmed working 2026-06-01.)

> For per-person schedules use `--schedules` (array, one entry per person). If a shape is rejected, read an item that already has node schedules (`workflow get-node`) and mirror it.

## When a command fails (self-heal)

| Error contains | Fix |
|---|---|
| `need STRING type, but got: LIST` / `MAP` | the `field_value` must be a **stringified** JSON string, not a raw array/object |
| `need STRUCT type, but got: STRING` (on `update-node`) | don't pass `--node-schedule '<json>'` — use `--set node_schedule.<key>=<val>` dot-path |
| `unsupported type:float64, expected type:LIST` (owners) | set owners with array-index: `--set 'node_schedule.owners[0]=<key>'`, not `owners=<key>` |
| `计算字段值不可编辑` / `无权编辑 "<field>"` | either the field is **auto-calculated/rollup** (e.g. Complexity, parent estimate) — don't write it; OR you're **not the card's owner/creator** (can't edit others' cards) — post a comment or ask the owner instead |
| `create comment fail` (Service Internal Error, on `comment add`) | comment content must be **plain single-line text** — drop multi-line / markdown / emoji; also ensure `--project-key` is passed (`project_key is empty` if omitted) |
| `字段「…」当前选项值已失效` (relation/link at create) | create WITHOUT the link, then set it via a follow-up `workitem update --fields` |
| relation/link set returns OK but the value reads back **null** (no error) | **wrong target TYPE** — the related-select only accepts the type(s) in its `related_work_item_info` (`meta-fields`); pass a wid of that type, then verify via MQL. (If MQL is set but the card shows "Empty", it's a stale UI cache — hard-refresh.) |
| `invalid select option` | use a valid option_id from `meta-fields`; if ambiguous, ask the user |
| `creating ... missing template` | add `{"field_key":"template","field_value":"<id>"}` |
| `node not found` | get the real node state_key via `workflow get-node` — don't guess |
| auth error | tell the user (Thai) to `meegle auth login`, then retry |
| role update via fields rejected | use `--role-operate`, not `--fields` |
| empty / `KeyError` when parsing | you read the wrong envelope key — check the table above (`list` vs `FieldConfList` vs `projects`) |

Auto-retry at most twice after a targeted fix; then stop and explain to the user.
