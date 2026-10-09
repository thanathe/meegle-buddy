# Meegle CLI — how to create and read cards

Generic recipes for the `meegle` CLI (`@lark-project/meegle`). No team-specific values live here:
every key and id comes from `scripts/meegle_config.py` or from the user.

## Before anything

```bash
command -v meegle
meegle auth status --format json        # want "authenticated": true
```

Not installed or not logged in → stop. Tell the user (in Thai) to run, in their own terminal:

```bash
npx @lark-project/meegle@latest install
```

## Rules that cause most failures

1. **`field_value` is always a string.** Numbers, arrays and objects are sent as strings. A JSON
   array is sent as a *string containing JSON*.
2. **Only send fields the type has.** If `meegle_config.py summary` does not list a field for that
   type, do not send it. The server answers `field keys not found: <key>`.
3. **Read a type's required fields before every create:** `meegle_config.py summary <TYPE>`. Fill the
   "REQUIRED FIELDS (always)" list, then the "REQUIRED ONLY WHEN" rule that matches the values you
   chose.
4. **`{"mcp_result": ""}` is the normal response** for create/update, whether the write landed or
   not. Always re-read the card to check.
5. **One retry at most.** If a command fails twice, stop and show the user the error.

## Create a card

```bash
meegle workitem create --project-key <project_key> \
  --work-item-type <type_key> --format json \
  --fields '{"field_key":"template","field_value":"<template_id>"}' \
  --fields '{"field_key":"name","field_value":"<title>"}' \
  --fields '{"field_key":"<field_key>","field_value":"<value>"}'
```

- Send `template` when `summary` prints a TEMPLATE line.
- One `--fields` flag per field.
- If it fails with a **thrift marshal** error (`need STRUCT type, but got: STRING`), send the same
  fields through `-P` instead:

```bash
meegle workitem create --project-key <project_key> --work-item-type <type_key> --format json \
  -P '{"fields":[{"field_key":"template","field_value":"<template_id>"},{"field_key":"name","field_value":"<title>"}]}'
```

## Roles at create (owner, approver, PM …)

When `summary` says roles are sent as `role_owners`, send one field whose value is a
**JSON-stringified array** of `{role, owners}`. Role keys come from `summary` → ROLES → available.

```bash
--fields '{"field_key":"role_owners","field_value":"[{\"role\":\"<role_key>\",\"owners\":[\"<user_key>\"]},{\"role\":\"<role_key_2>\",\"owners\":[\"<user_key_2>\"]}]"}'
```

These do **not** work: a field named `role_<project>_<type>_<role>`, an object instead of an array,
or `--params role_owners`.

Find a person's user key by email (a bare name returns `[]`):

```bash
meegle user search --user-keys "<email>" --project-key <project_key> --format json
```

The current user's own key is `user_key` in the meegle-buddy `config.json`.

## Fields that point at another card

Fields listed under "LINK-TO-ANOTHER-CARD FIELDS" take a **work item id**, not a name. Get the id:

```bash
# by exact name
meegle workitem get --project-key <project_key> --name "<exact name>" --format json

# or copy it from a card that already has the field set
meegle workitem get --project-key <project_key> --work-item-id <id> --fields _all --format json
```

Never reuse an id from an example or an earlier run without the user confirming it.

## Dates — compute with Python, never by hand

Date-range fields want the string `"[start_ms,end_ms]"`. Use the timezone of the user's team
(ask if unsure; default `Asia/Bangkok`). Skips Saturday and Sunday:

```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
tz = ZoneInfo("Asia/Bangkok")

def add_workdays(d, n):
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d

start_day = datetime(2026, 10, 12, tzinfo=tz)   # first working day
days = 2                                         # working-day span agreed with the user
end_day = add_workdays(start_day, days - 1)
start = int(start_day.replace(hour=9).timestamp() * 1000)
end = int(end_day.replace(hour=18).timestamp() * 1000)
print(f"[{start},{end}]")
```

## Update a field after create

```bash
meegle workitem update --project-key <project_key> --work-item-id <id> --format json \
  --fields '{"field_key":"description","field_value":"<text>"}'
```

## Read a card back

```bash
meegle workitem get --project-key <project_key> --work-item-id <id> --fields _all --format json
```

Read `work_item_fields[]` by **`key`** and **`value`** (not `field_key` / `field_value`). Roles
are in `role_members[]`.

## When a create is refused

- `ErrFieldRequired` names **every** missing field at once. Read the keys from the message, ask the
  user for the values, and try once more.
- If a field was required although `summary` did not say so, tell the user. The meegle-buddy skill
  records it in that type's `conditional_rules` so it is known next time.

## Not possible through the CLI

- **Blocking links between cards.** Relations are read-only. Write blockers as text.
- **Binding a card under a workflow node** of its parent. Web UI only.
