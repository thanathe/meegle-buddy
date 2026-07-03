# Field freshness / drift check — TWO modes

This team changes field keys / required flags **often** (they're still adjusting their workflow), so the saved config goes stale. There are **two** ways to deal with that, chosen to balance correctness against speed:

- **LIGHT (automatic)** — runs before every write. Cheap (1 call) and cached per conversation. Catches the dangerous case: a field that just became **required**.
- **FULL (on-demand sync)** — the user explicitly asks ("เช็ค field" / "sync meegle"). Pulls everything and lists all new / changed / removed fields for the user to decide on.

> Running a FULL check on every action is slow (the `meta-fields` listing is paginated → several round-trips). Don't do that. Use LIGHT automatically; use FULL only when asked or when the config is stale.

---

## LIGHT mode (automatic — before every create / timelog / schedule)

**Goal:** make sure no *required* field is missing or new, with minimal latency.

**Skip if** you already ran a LIGHT or FULL check for this same `work_item_type` **earlier in this conversation** (cache it in your head — don't re-call). Otherwise:

```bash
meegle workitem meta-create-fields --project-key <PK> --work-item-type <TYPE> --format json   # ONE call
```

Compare the returned create-required fields to the type's `create_fields` + `fields[]` in the config:

- A **required** field the server returns that is **missing from the config** (or marked optional/skip in config) → **STOP and ask the user** (Thai), then update the config before continuing:
  > "field **<field name>** (ชนิด: <value_type>) ตอนนี้เป็น **ฟิลด์บังคับ** ตอนเปิด «<type>» แล้วครับ — ขอเพิ่มเข้า checklist นะครับ ใส่ค่าอะไรดี?"
- Everything else (new *optional* fields, renamed labels, removed fields) → LIGHT mode does **not** chase these; that's the FULL sync's job. Just continue.

If the LIGHT call shows nothing new-required → continue the flow silently.

> Why only `meta-create-fields`? It's a single call and it's exactly the set that will make `create` fail if you miss it. The heavier full listing is reserved for FULL mode.

After a LIGHT check (or a FULL sync), set `last_checked` on the project file to today so the skill can tell when it was last verified.

---

## FULL mode (on-demand — "เช็ค field" / "sync meegle [space] [type]")

**Goal:** review *all* drift and let the user curate the config. This is the "list everything and check" pass.

### Step 1 — pull the live fields

```bash
meegle workitem meta-create-fields --project-key <PK> --work-item-type <TYPE> --format json
meegle workitem meta-fields        --project-key <PK> --work-item-type <TYPE> --page-num 1 --format json
meegle workflow meta-node-fields   --project-key <PK> --work-item-type <TYPE> --format json   # card types w/ nodes
```

Paginate `meta-fields` (`--page-num 2,3,...`) until a page returns empty.

### Step 2 — diff against the saved config

Build three lists for this type:

1. **NEW** — a field key the server returns that is **not** in the config.
2. **REQUIRED CHANGED** — a field whose live `required` differs from the config's.
3. **GONE** — a field in the config that the server no longer returns.

If all three are empty → tell the user it's already up to date ("field ตรงกับระบบแล้วครับ ✅") and just bump `last_checked`.

### Step 3 — ask the user about each change (Thai, AskUserQuestion)

Don't decide for the user.

**Each NEW field** — show label + value_type, ask whether to add and whether required:
> "เจอ field ใหม่ใน «<type name>»: **<field name>** (ชนิด: <value_type>) — เพิ่มเข้า checklist ไหมครับ?"
- **เพิ่ม (required)** → add to `fields[]` with `required:true`, add key to `create_fields`.
- **เพิ่ม (optional)** → add to `fields[]` with `required:false`, add to `create_fields` (offered, skippable).
- **ไม่เพิ่ม** → add to `fields[]` with `required:false, "skip":true` (so you remember you asked and won't list it again next sync). 

If a NEW field is **select / multi_select**, fetch its options now:
`meegle workitem meta-fields --project-key <PK> --work-item-type <TYPE> --field-keys '["<field-key>"]' --page-num 1 --format json` → store `options:[{label,value}]`.

**Each REQUIRED CHANGED field** — confirm: "field «<name>» เปลี่ยนเป็น <required ↔ optional> จะอัปเดตตามไหม?"

**Each GONE field** — confirm: "field «<name>» หายไปแล้ว (อาจถูกเปลี่ยนชื่อ/ปิด) — เอาออกจาก config ไหม?"

### Step 3.5 — discover conditional (linkage) rules

Meegle create forms can make extra fields appear / become required **depending on another field's value** (e.g. picking category "Option A" requires one relation field, picking "Option B" requires a different one). ⚠️ **No CLI/API endpoint exposes these linkage rules** — `meta-create-fields` returns only the *statically* required fields, `meta-fields` has no linkage keys, and `workflow list-state-required` covers node/state transitions only (verified against the full `meegle inspect` command list). Some of these rules ARE still enforced server-side at create (the dreaded 必填 error on a field that "isn't required"), so the config must carry them.

Since the API won't tell you, **infer them from real cards** and confirm with the user:

1. **Pick driver candidates** — every `select`/`radio` field that is required at create for this type (usually 1–2, e.g. a Category field).
2. **One MQL query per driver** — select the driver + every not-statically-required `workitem_related_*` / `select` / `_business` field, over recent items:

   ```bash
   # FROM needs the EXACT space name (from `meegle project search`) — the slug does NOT work inside MQL
   meegle workitem query --project-key <PK> --mql \
     "SELECT \`work_item_id\`, \`<Driver Name>\`, \`<Candidate 1>\`, \`<Candidate 2>\` FROM \`<Space Name>\`.\`<Type Name>\` ORDER BY \`work_item_id\` DESC LIMIT 200" \
     --format json
   ```

   Response rows are `data.<n>[].moql_field_list[]`; a field is "filled" when its `value` is non-null and `value_type` is non-empty.
3. **Compute fill-rate per driver option.** A candidate field filled in **≥80%** of items with option X and **≈0%** elsewhere → propose the rule "when <driver> = X, <field> is required".
4. **Confirm each proposed rule with the user (Thai)** — they can see the real form; also let them dictate rules the data can't show (small n, brand-new option):
   > "จากการ์ดจริง ถ้า «<driver>» = «<label>» ดูเหมือน field «<name>» จะถูกบังคับกรอก (กรอก N/N ใบ) — บันทึกเป็นกฎไหมครับ?"
5. **Save** confirmed rules under the type's `conditional_rules` (shape in [config-format.md](config-format.md)). If any `require`d field isn't in `fields[]` yet, add it now (with options, fetched the usual way).

Also fold in rules learned **outside** sync: whenever a create fails 必填 on a field that `meta-create-fields` says is optional, the requiredness is almost certainly conditional — record which driver value was in effect and save/extend a `conditional_rules` entry instead of flipping the field to globally `required: true`.

### Step 4 — save

Write the updated `projects/<project_key>.json`, set `last_checked` and `last_synced` to today. Report a short Thai summary of what changed. If the user triggered sync standalone (not inside another flow), stop here; otherwise return to the flow with the fresh fields.

**Scope:** if the user named a type, sync just that type. If they named only a space, sync every type with `role: "card"` or `"timerecord"` in that space. If they named nothing, sync the `default_project_key`.

---

## Suggesting a sync (gentle, non-blocking)

When starting a create/timelog/schedule, if the project file's `last_synced` is more than ~7 days old (or missing), you may add a one-line Thai nudge — "ไม่ได้ sync field มา N วันแล้ว อยากให้เช็คก่อนไหมครับ?" — but do **not** force it. The LIGHT check already protects against missing required fields, so normal work proceeds without waiting.

## Notes

- Always respect the user's answer; never auto-add a field to the required checklist on your own.
- Keep `value_type` accurate when adding fields — it decides how `field_value` is built (string vs stringified JSON; see [cli-reference.md](cli-reference.md)).
- `skip:true` fields are remembered-as-declined: LIGHT mode ignores them; FULL mode shows them again only if their required flag changes.
