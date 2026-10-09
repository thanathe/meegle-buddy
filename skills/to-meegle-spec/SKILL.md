---
name: to-meegle-spec
description: "Turn the current conversation into a spec (PRD): ALWAYS written to a markdown file, then — only after the user confirms — a parent card (Feature / Story / Requirement) in Meegle (Feishu / Lark Project) that links to it. Works in any Meegle space: reads the space, types and fields from the meegle-buddy config, nothing hardcoded. Never publishes to GitHub. Use whenever the user asks for a spec or PRD: 'write a spec', 'make a PRD', 'เขียน spec', 'ทำ PRD', 'สรุปเป็น spec', 'เปิด feature ใน meegle'. Prefer this over to-prd / to-spec, which publish to GitHub Issues."
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# to-meegle-spec

Turn the conversation into a spec. Output 1: a markdown file, always. Output 2: a parent card in
Meegle, only if the user says yes. Nothing else.

All paths below are relative to **this skill's folder** (the folder this SKILL.md is in).
`CONFIG` means: `python3 scripts/meegle_config.py`.

## RULES — read these first, they override everything below

1. **NEVER use GitHub.** Do not run `gh` (no `gh issue`, `gh pr`, `gh api`). Do not create GitHub
   issues or pull requests. Do not run any other spec or PRD skill instead of this one.
2. **NEVER run `git commit`, `git push`, `but commit` or `but push`.** Write the file and stop.
3. **NEVER create the Meegle card without the user saying yes** in step 5.
4. **NEVER invent** a project key, type key, field key, option id, work item id, user key, estimate,
   priority or date. Keys come from `CONFIG`; everything else comes from the user.
5. **Talk to the user in Thai.** Write the spec itself in English.
6. **Do not interview the user.** Build the spec from what the conversation already says. The only
   questions are in steps 2 and 5, and the setup questions in step 6 if they are needed.

If you are unsure what to do at any point: write the file, stop, and ask the user in Thai.

## Step 1 — Read the context

- Read the conversation so far.
- If the user gave a file path or a Meegle id, read it in full.
- Look at the repo the work belongs to. If it has `CONTEXT.md`, use its terms and avoid the words
  it says to avoid. If it has ADRs in the area, follow them.

## Step 2 — Agree the test seams (one question)

Decide where the feature will be tested. Prefer a seam that already exists, at the highest level
possible. One seam is ideal.

Ask the user in Thai, for example:

> จะทดสอบฟีเจอร์นี้ที่จุด `<seam>` ตรงกับที่คิดไว้ไหมครับ

Wait for the answer. Adjust if they disagree.

## Step 3 — Write the spec file

1. Choose the location:
   - If the repo already keeps specs or design docs in a folder (for example `docs/`), put the file
     there, next to the related docs.
   - Otherwise use `docs/specs/` in the repo where most of the work will happen.
   - File name: `YYYY-MM-DD-<short-slug>.md`, using today's date.
2. Write the spec with the template at the bottom of this file.
3. The first line under the title is `**Status:** ready-for-agent`. This is only a text marker;
   nothing enforces it.
4. Save the file. **Do not commit it** (rule 2).

## Step 4 — Show the user

Tell the user in Thai where the file is, and give a 3–5 line summary. Let them ask for changes.
Edit the file until they are happy.

## Step 5 — Ask before creating the Meegle card (one question)

Ask exactly this, in Thai:

> spec เขียนไว้ที่ `<path>` แล้วครับ จะให้เปิดการ์ดใน Meegle ด้วยไหม
> (ถ้างานยังไม่ได้รับอนุมัติ แนะนำให้เก็บเป็นไฟล์ไว้ก่อนครับ)

- **No** → **stop. The task is done.** The file is the deliverable.
- **Yes** → step 6.

## Step 6 — Create the card (only after yes)

Read `references/meegle-cli.md` **in full** first.

### 6a. Check the setup

```bash
command -v meegle && meegle auth status --format json
python3 scripts/meegle_config.py flow
```

- `meegle` missing or not logged in → stop, tell the user how to install (see `meegle-cli.md`).
- `ERROR: no meegle-buddy config` → stop. Tell the user in Thai to set up the **meegle-buddy** skill
  first (it discovers their spaces and fields). Do not create anything.
- `NOT SET` → do 6b once. Otherwise skip to 6c.

### 6b. First time only — choose the types and save them

1. `python3 scripts/meegle_config.py projects` → ask the user which space (default is marked).
2. `python3 scripts/meegle_config.py types --project <P>` → ask the user:
   - which type holds a spec (often "Features", "Story" or "Requirement"), and
   - which type holds the tasks under it (often "Tech Tasks", "Task" or "Sub-task").
3. `python3 scripts/meegle_config.py summary <TASK_TYPE> --project <P>` → under
   "LINK-TO-ANOTHER-CARD FIELDS", ask which field links a task to its spec card.
4. `python3 scripts/meegle_config.py summary <SPEC_TYPE> --project <P>` → under "URL FIELDS", ask
   which field should hold the spec link (may be none).
5. Save:

```bash
python3 scripts/meegle_config.py set-flow --project <P> --spec-type <SPEC_TYPE> \
  --task-type <TASK_TYPE> --parent-field <FIELD> --docs-field <FIELD>
```

### 6c. Collect the values

1. `python3 scripts/meegle_config.py summary <spec_type_key> --project <project_key>`, using the
   keys printed by `flow`.
2. Make a list of every field to send:
   - `template`, if a TEMPLATE line is printed
   - `name` = short title of the feature
   - every field under "REQUIRED FIELDS (always)"
   - every field under "REQUIRED ONLY WHEN" whose condition matches what you chose
   - roles under "required at create", sent as `role_owners` (see `meegle-cli.md`)
   - the docs field from `flow` = the spec file path (or its web URL, if the user gives one)
   - `description` = problem + solution in 3–5 lines, then `**Status:** ready-for-agent`.
     **Not** the whole spec.
3. For every value you do not have, **ask the user**. A field that links to another card needs a
   work item id; look it up by name (`meegle-cli.md`) and let the user confirm it.
4. "THIS USER'S USUAL VALUES" may be suggested, but the user must confirm them.
5. Leave out optional fields the conversation did not settle (priority, effort, dates).

### 6d. Confirm, create, check

1. Show the user a Thai summary: every field, its value, and what it means. Wait for an explicit yes.
2. Run `meegle workitem create` (shape in `meegle-cli.md`).
3. Read the card back with `meegle workitem get` and check name, required fields and roles.
4. Give the user the card id (and the URL if the response has one).

If a command fails, show the user the error. Retry at most once, only after fixing the cause the
error names. Never retry with guessed values.

## Step 7 — Break down into tasks (optional)

Only if a card now exists **and** the user asks for it: run `/to-meegle-tickets` with the card id.
Do not break the work down on your own.

## Done

The task ends after step 5 (no card) or step 6 (card created). Report in Thai:

- the spec file path
- the Meegle card id, if one was created
- that nothing was committed or pushed

Background on why the spec is a file first: `references/why-file-first.md`. Not needed to follow
the steps.

## Spec template

<spec-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can
(state machine, reducer, schema, type shape), inline it within the relevant decision and note
briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the
important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this spec.

## Further Notes

Any further notes about the feature.

</spec-template>
