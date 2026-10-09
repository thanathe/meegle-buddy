---
name: to-meegle-tickets
description: "Break a spec, plan, or the current conversation into tracer-bullet task cards in Meegle (Feishu / Lark Project), each linked to a parent card and listing what blocks it. Writes the breakdown to a markdown file first, and creates cards only after the user confirms. Works in any Meegle space: reads types and fields from the meegle-buddy config, nothing hardcoded. Never uses GitHub. Use when the user says 'break this into tickets', 'แตก task', 'แตกการ์ด', 'สร้าง task จาก spec', 'เปิด task ใน meegle', or after /to-meegle-spec created a card. Prefer this over to-issues / to-tickets, which publish to GitHub Issues."
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# to-meegle-tickets

Break work into **task cards** in Meegle: thin vertical slices, each linked to a parent card (the
spec card), each saying which other tasks block it.

Output 1: a breakdown file, always. Output 2: Meegle task cards, only after the user says yes.

All paths below are relative to **this skill's folder** (the folder this SKILL.md is in).
`CONFIG` means: `python3 scripts/meegle_config.py`.

## RULES — read these first, they override everything below

1. **NEVER use GitHub.** Do not run `gh` (no `gh issue`, `gh pr`, `gh api`). Do not create GitHub
   issues or pull requests. Do not run any other ticket or issue skill instead of this one.
2. **NEVER run `git commit`, `git push`, `but commit` or `but push`.**
3. **NEVER create a card before the user says yes** to the whole batch in step 6.
4. **NEVER invent** a project key, type key, field key, option id, work item id, user key,
   estimate or date. Keys come from `CONFIG`; everything else comes from the user. Estimates are
   often required by Meegle — that is a reason to ask, not a reason to guess.
5. **NEVER send a field that `CONFIG summary` does not list** for the task type.
6. **NEVER create tasks without a parent card.** If there is none, stop and suggest
   `/to-meegle-spec`.
7. **NEVER modify the parent card.**
8. **Talk to the user in Thai.** Write task titles and bodies in English.

If you are unsure what to do at any point: save the breakdown file, stop, and ask the user in Thai.

## Step 1 — Check the setup

```bash
command -v meegle && meegle auth status --format json
python3 scripts/meegle_config.py flow
```

- `meegle` missing or not logged in → stop, tell the user how to install (see
  `references/meegle-cli.md`).
- `ERROR: no meegle-buddy config` → stop. Tell the user in Thai to set up the **meegle-buddy** skill
  first. Do not create anything.
- `NOT SET` → ask the user which space, which type is the parent (spec) card, which type is a task,
  and which task field links to the parent. Use `CONFIG projects`, `CONFIG types` and
  `CONFIG summary <TASK_TYPE>` ("LINK-TO-ANOTHER-CARD FIELDS") to show the choices. Then save:

```bash
python3 scripts/meegle_config.py set-flow --project <P> --spec-type <SPEC_TYPE> \
  --task-type <TASK_TYPE> --parent-field <FIELD>
```

From now on use the keys printed by `CONFIG flow`: `project_key`, `task_type_key`, `parent_field`.

## Step 2 — Find the parent card and the spec

- The user should give a parent card id or URL, or a spec file path. Read the spec in full.
- Read the parent card:
  `meegle workitem get --project-key <project_key> --work-item-id <parent_id> --fields _all --format json`
- Keep its field values. Tasks often need the same related values (for example the same product).
- **No parent card exists?** Stop. Tell the user in Thai to run `/to-meegle-spec` first.

## Step 3 — Read what a task card needs

```bash
python3 scripts/meegle_config.py summary <task_type_key> --project <project_key>
```

Note:
- the TEMPLATE line, if any
- "REQUIRED FIELDS (always)"
- "REQUIRED ONLY WHEN": which extra fields each choice brings in
- ROLES "required at create"
- SCHEDULE: the date-range field and the effort field with its unit
- "THIS USER'S USUAL VALUES": suggestions only, the user must confirm them

## Step 4 — Draft the slices

<vertical-slice-rules>

- Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests):
  vertical, NOT a horizontal slice of one layer
- A completed slice is demoable or verifiable on its own
- Each slice is sized to fit in a single fresh context window
- Any prefactoring is its own slice, sequenced first

</vertical-slice-rules>

Look at the code first if you have not. Use the words from the repo's `CONTEXT.md` if it has one,
and follow its ADRs. If a small refactor makes the main change easy, it becomes the first task.

For every slice write down:

| Item | Notes |
|---|---|
| Title | short, describes the behaviour |
| Blocked by | slice numbers, or "none" |
| What it delivers | the behaviour that works when it is done |
| Effort | in the unit `summary` printed (hours, points, …) |
| Working days + start date | only if the type has a date-range field |
| Every other required field | from step 3, including the conditional ones for the values chosen |
| Roles | one person per required role — a person the user named, otherwise `?`. Do not suggest anyone |

Exception, **wide refactors** (one mechanical change that breaks many call sites at once, such as
renaming a shared column): do not force them into one slice. Use three kinds of task:
1. **Expand**: add the new form next to the old one. Nothing breaks.
2. **Migrate**: move callers in batches, one task per batch. Each is blocked by Expand.
3. **Contract**: delete the old form. It is blocked by every Migrate task.

## Step 5 — Write the breakdown file, then review

1. Save the draft **before** asking anything, so nothing is lost:
   - next to the spec file, if there is one: `<spec-name>-tasks.md`
   - otherwise in `docs/specs/` of the repo: `YYYY-MM-DD-<slug>-tasks.md`

   One table row per slice (columns from step 4), plus a `Meegle id` column that stays empty for
   now. **Do not commit it** (rule 2).
2. Show the table in Thai and ask:
   - ขนาดของแต่ละ task โอเคไหม (ใหญ่ไป / เล็กไป)
   - ลำดับ blocked-by ถูกไหม
   - ควรรวมหรือแยก task ไหนเพิ่มไหม
   - ค่าที่ยังเป็น `?` (คน, ชั่วโมง, วันที่, field ที่บังคับ) คืออะไร
3. Update the file after each change. Every required value must be filled before step 6.

## Step 6 — One confirmation for the whole batch

Ask exactly this in Thai, with the final table:

> จะสร้าง task ทั้งหมด <N> ใบใน Meegle ใต้การ์ด <parent_id> ตามตารางนี้ ยืนยันไหมครับ

- **No** → stop. The breakdown file is the deliverable.
- **Yes** → step 7.

## Step 7 — Create the cards (only after yes)

Read `references/meegle-cli.md` **in full** first.

1. **Order:** create blockers first. A task can only point at a blocker that already has an id.
2. For each task:
   1. Compute the date range with the Python in `meegle-cli.md`, if the type has one.
   2. Run `meegle workitem create` with `template` (if any), `name`, the parent field from
      `CONFIG flow` = parent id, every required and matching conditional field, the effort field,
      and `role_owners`.
   3. Set `description` with `meegle workitem update`, using the ticket template below. Fill in
      "Blocked by" with the real ids of tasks already created.
   4. Read the card back with `meegle workitem get`. Check name, parent and roles.
   5. Write the new id into the breakdown file.
3. **If a create fails:** stop the batch. Show the user the error. Do not retry with guessed values.
   Tasks already created stay — list them.

## Done

Report in Thai:

- the breakdown file path
- every created task: id, title, people
- any task that failed, and why
- that blocked-by is **text only**: Meegle does not stop anyone starting a blocked task. Real
  links can only be set by hand in the Meegle web UI.
- that nothing was committed or pushed

## Ticket template (the `description` of each card)

<ticket-template>

## Parent

`<parent-id>` — <title>

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer
implementation.

Avoid specific file paths or code snippets — they go stale fast. Exception: if a prototype produced
a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema,
type shape), inline it here and note briefly that it came from a prototype.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Blocked by

- `<id>` — <title>

Or "None — can start immediately".

**Text only.** Meegle does not enforce this; nothing prevents starting early.

</ticket-template>
