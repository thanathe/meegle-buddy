---
name: figma-to-meegle
description: "Open Meegle (Feishu / Lark Project) task cards from a Figma design: splits the link into separate screens, exports ONE image per screen (never one combined shot), drops repeated screens, reads the flow the designer drew (arrows, decisions, rows, status) and the text notes beside each screen, and (optionally) checks components against a figma-build-kit design-system cache. Checks existing and sibling cards first, writes the description in the team's own card style, then posts one comment per screen with its image — across one or several cards (FE / BE). Uses the meegle-buddy config, nothing hardcoded. Runs in any agent harness with Bash (Figma REST API, Figma MCP as fallback). Use when the user gives a figma.com link and wants a task / card from it, or says 'เปิด task จาก figma', 'แคปจอ figma ใส่ comment', 'แปะ screen ลง task', 'เปิดการ์ดจาก design', 'อ่าน note ใน figma แล้วเปิด task'."
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion
---

# figma-to-meegle

Figma link in → Meegle task card(s) out, with every screen attached as **its own** comment image
and the description written from what the designer drew and wrote.

All paths below are relative to **this skill's folder**. `CAPTURE` means
`python3 scripts/figma_capture.py`. `MEEGLE` means the meegle binary found in step 1.

## RULES — read these first

1. **One screen = one image = one comment.** Never merge screens into one picture. Never take a
   screenshot of a whole section/page and post that. The script already splits; do not undo it.
2. **NEVER create or update a card, or post comments, before the user says yes** (step 5).
3. **Never invent** keys, option ids or estimates. Card fields come from the **meegle-buddy**
   config and the user. If meegle-buddy is not set up → stop and say so in the user's language.
4. **The notes are the designer's words.** Put them in the description as written (translate only
   if the user asks). Do not add requirements the design does not show; put your own questions
   under "Open questions".
5. **Never edit a card someone already worked on.** New work goes on a new card that references it.
6. **Keep the context small.** Read the `plan` output and look at PNGs. Do not dump raw Figma node
   JSON (2–4K tokens per screen) — the script already extracted what matters.
7. **Talk to the user in their language.** The Thai phrases below are examples; say the same in
   the user's language.

## Step 1 — Check the setup

**meegle CLI.** Agent sandboxes often lack the user's PATH (nvm installs are invisible to
`command -v`). Find it in this order and use the full path as `MEEGLE` from then on:

```bash
command -v meegle \
  || zsh -lc 'command -v meegle' 2>/dev/null \
  || bash -lc 'command -v meegle' 2>/dev/null \
  || ls ~/.nvm/versions/node/*/bin/meegle ~/.volta/bin/meegle ~/.npm-global/bin/meegle \
        /opt/homebrew/bin/meegle /usr/local/bin/meegle 2>/dev/null | tail -1
```

Tell the user where it was found. If the binary is a node script and `node` is not on PATH
either, run it with the `node` next to it: `PATH="$(dirname <MEEGLE>):$PATH" <MEEGLE> ...`.
Then:

```bash
<MEEGLE> auth status --format json      # "authenticated": true
ls ~/.claude/meegle-buddy/config.json
python3 scripts/figma_capture.py check   # which Figma token source works (never prints the value)
```

- meegle not found anywhere / not logged in / no config → stop, point to the **meegle-buddy** setup.
- `check` says `RESULT: OK` → continue with the script (step 2).
- `check` says `NO_FIGMA_TOKEN` → read its lines: it shows every place it looked and why each
  failed (not set / missing / unreadable / HOME it used). Then, in this order:
  1. The harness has the token under another variable name, or in a file you can read → run with
     `FIGMA_TOKEN="$<VAR>"` or `FIGMA_TOKEN_FILE=<path>` in front of each `CAPTURE` command.
  2. A Figma MCP is available → use **Fallback: Figma MCP** below. Tell the user (in the user's language) what is
     lost: no automatic notes-to-screen matching, no flow, no duplicate check, no component check.
  3. Neither → ask the user (in the user's language) to make a personal access token: Figma → Settings → Security →
     Personal access tokens → scope **File content: Read**, and save it themselves (never paste
     it in chat), as one line in `~/.claude/meegle-buddy/figma_token`:
     - macOS: `pbpaste > ~/.claude/meegle-buddy/figma_token && chmod 600 ~/.claude/meegle-buddy/figma_token`
     - Linux: `xclip -o -selection clipboard > ~/.claude/meegle-buddy/figma_token && chmod 600 ~/.claude/meegle-buddy/figma_token`
     - Windows (PowerShell): `Get-Clipboard | Set-Content $HOME\.claude\meegle-buddy\figma_token`

## Step 2 — Find the screens fast

The user may give a link, or just a name ("หน้า Settings", "flow checkout").

1. **Link given** → use it. A link to a section/frame of several screens is fine; the script
   splits it.
2. **Only a name** → if you also use the **figma-build-kit** skill (optional), look in its
   working memory first, before asking for a link:
   `ls ~/.claude/figma-build-kit/*.json` (none → ask for the link). Read `file.name` and `fileMap` of each cache. `fileMap`
   records where each flow lives (page, section, frame ids, which section is `latest`). Its shape
   varies (structured or free text), so read it, do not parse it blindly. Build the link
   `https://www.figma.com/design/<fileKey>/?node-id=<id with : replaced by ->`. Nothing matches →
   ask for the link.
3. Run the plan (reads only, writes nothing):
   ```bash
   python3 scripts/figma_capture.py plan "<url>" ["<url2>" ...]
   ```
   A cached node id that comes back `FIGMA_NOT_FOUND` is stale: ask for a fresh link.

What the plan prints:

- **FLOW** — section title, the header strip's text (often the design status, e.g.
  `✅ Handoff` / `Ready for dev`; a status saying work is still in progress means the design may still change — say so), and every arrow
  between screens and decision blocks: `◇ API success? (Add) -No-> [7] ...`.
- **Per screen** — number, name, size, **row** (the title above that row, e.g. Add / Edit /
  Delete), **NOTES** (text, stickies and note-named layers, each tied to its nearest screen),
  **DESIGN-SYSTEM / CUSTOM components** when a figma-build-kit cache exists.
- **`SAME AS [n]`** — the screen repeats an earlier one (designers often copy the list screen as
  the start of every row). **`PART, NOT A FULL SCREEN`** — a modal or dropdown drawn on its own.
- **`SUGGESTED: --only ...`** — every screen except the repeats.

Show the user the screen list (in the user's language) with the suggested `--only`, and ask:
- ตัดจอซ้ำตามที่แนะนำไหม / จอ PART (modal ลอย) จะเก็บไว้ไหม
- ถ้าสคริปต์ยังไม่แยกจอ (เจอ 1 จอ ทั้งที่จริงมีหลายจอ) → ส่ง link ของ section หรือของแต่ละจอแทน
- ถ้ามันแยกจอที่ควรเป็นจอเดียว → ใช้ `--single`

## Step 3 — Export, one PNG per screen

```bash
OUT="<absolute path: scratchpad, or <repo>/figma/>/figma-$(date +%Y%m%d-%H%M%S)"
python3 scripts/figma_capture.py export "<url>" --only <chosen> --out "$OUT"
```

You get `$OUT/NN-<screen>.png` per screen plus `$OUT/manifest.json` (flows, screens, notes,
ui_text, components, figma link per screen). Numbers in file names keep the plan's numbering.
Look at 1–2 PNGs to check the split before going on.

## Step 3.5 — Existing cards and sibling cards

**a) Same feature.** Search the space for cards about this feature: two or three keywords from the
flow name, every card type in the config with `role: "card"`:

```bash
<MEEGLE> workitem query --project-key <PK> --format json \
  --mql "SELECT work_item_id, name, work_item_status, current_status_operator FROM \`<PK>\`.\`<type name or type_key>\` WHERE name LIKE '%<keyword>%'"
```

Rows are in `data["1"][].moql_field_list[]` as `key` / `value`. Use the type's display **name**
(as `meta-types` lists it) or its `type_key`. Read each hit in full (`workitem get --fields _all`,
plus `comment list`).

**b) Sibling cards** — other cards of the same product/project, even with different names (e.g.
"Invoices" next to "Billing settings"): search by the product's tag, project or the common name
prefix (`[FE][Billing]` → `LIKE '%Billing%'`), newest first. Read the 1–2 most
recent. They give you the team's **title pattern**, **description structure** and the **field
values** this product uses (project, tags, category, component). Use them as suggestions; the
user confirms.

Decide with the user (in the user's language), per feature card from (a):

| Card state | Do |
|---|---|
| Not found | open new card(s) (step 4) |
| Not started (no time logged / status still at the start) | **update that card**: rewrite its description from the new design, post the screens on it. No duplicate |
| In progress or Done | **review it against the new design** and open **new** card(s) for the delta only, referencing the old card id |

**The review** is a list the user sees before anything is written, each line tied to screen
numbers: "เพิ่ม: … / เปลี่ยน: … / ตัดออก: …". Also a separate list:

> **กติกาที่ขัดกับการ์ดเดิม** — a business rule in the old card that the new design contradicts
> (e.g. old: "1 person can belong to many teams" → new design: "1 user = 1 team").

Each contradiction goes into the new card's **Open questions** and, if it changes data or API,
into the backend card's scope. Never resolve it yourself. If nothing differs, say so and stop.

## Step 4 — Draft the card(s)

**How many cards.** One card per layer that has work: usually FE and BE, sometimes several FE
cards when the delta splits by row (Add / Edit / Delete) or by page. Propose the split; the user
decides. Then assign every exported screen to **exactly one** card — the card whose work it shows.
Backend-only cards may get none, or only the screens whose rule changed.

**Fields:** use **meegle-buddy** [create-card](../meegle-buddy/references/create-card.md) for every
field (space, type, template, required + conditional fields, owner, estimate). Prefill from the
sibling cards where they agree; ask for the rest.

**Title:** follow the siblings' pattern (e.g. `[FE][Billing] Settings — <what>`). No siblings →
short and in the team's usual language.

**Description** (Markdown, line breaks escaped as `\n` — meegle-buddy cli-reference "Rich text"):

- **Sibling cards exist** → copy **their** section structure (e.g. `Context / What to build /
  Acceptance criteria / Blocked by`) and fill it from the design. Add the Figma link, the old card
  id it builds on, and Open questions inside that structure.
- **No siblings** → use this template:

<description-template>

**<one-line summary of what to build>**

**Figma:** [<section or flow name>](<link to the section/frame the user gave>) · design status: <header text>
**Builds on:** <old card id + title, if any>

## Flow
- **<row, e.g. Add>:** <screen> → <screen> → API success? → Yes: <screen> / No: <screen>

## Screens
1. **<screen name>** — [Figma](<per-screen link>)
   - <note, as written>

## Flow-level notes
- <notes not near any screen>

## Components
- Design system: <names from DESIGN-SYSTEM COMPONENTS, deduplicated>
- Custom / new (likely more effort): <names from CUSTOM / LOCAL COMPONENTS>

## Open questions
- <contradictions with old cards, and anything the design leaves unclear — ask, do not decide>

</description-template>

Leave out "Components" when there is no figma-build-kit cache for the file. If the user has
figma-build-kit, mention (Thai example — say it in the user's language): "ไฟล์นี้ยังไม่ได้ sync design system ใน figma-build-kit — ถ้า
sync ก่อน จะบอกได้ว่าจอไหนใช้ component กลาง / จอไหนต้องทำใหม่". Do not run the sync yourself.

## Step 5 — One confirmation for everything

Show (in the user's language), for **each** card: title, fields, description, and its screens in order. Then ask once:

> จะเปิด <K> การ์ด และแนบรูปรวม <N> คอมเมนต์ (การ์ดละ: <card → count>) ยืนยันไหมครับ

Updating an existing not-started card? Confirm its new description + comments; do not create.

## Step 6 — Create (or update), then one comment per screen

Per card, in the order the user approved:

1. New card: create it exactly as meegle-buddy create-card step 4–5 says (create → follow-ups →
   read back). Not-started card: `workitem update` its `description` only. Keep `<WID>`.
2. For each of **this card's** screens, numbered `[i/M]` **within the card** (M = its screen count):
   ```bash
   <MEEGLE> attachment +upload "$OUT/04-create-filled.png" --resource-type 14 \
     --project-key <PK> --work-item-id <WID> --format json
   ```
   The response holds **`file_url`** and **`file_token`**. Then:
   ```bash
   <MEEGLE> comment add --project-key <PK> --work-item-id <WID> --format json \
     --content '[1/M] Create Filled - ![Create Filled](<file_url>)<!--<file_token>-->'
   ```
   Success is `{"action":"create","success":true}`. Keep `--content` on **one line** (multi-line
   fails with `create comment fail`). Notes are in the description; do not repeat them here.
3. **Comment rejected:** try once as an attachment: upload with `--resource-type 13`, then
   `comment add --content '[1/M] <screen>' --file-token <file_token>`. Still failing → stop, tell
   the user which screens were posted. Do not keep reshaping the payload.
4. **Verify:** `comment list --project-key <PK> --work-item-id <WID> --format json` shows M new
   comments in order. On read-back the alt text and the `<!--token-->` part are **stripped** —
   that is normal; the image still shows. Count comments and check the `[i/M]` order, nothing else.

## Step 7 — Write back to figma-build-kit (only if you use it and it already knows the file)

```bash
ls ~/.claude/figma-build-kit/<fileKey>.json 2>/dev/null || echo SKIP
```

`SKIP` → do nothing (do not create a cache; that is figma-build-kit's job). Otherwise, if the flow
was found by link (not from `fileMap`), add it to that cache's `fileMap` the way the file already
writes it (page, section id, frame ids). Touch nothing else in that cache.

## Done

Report in the user's language: each card id + link and its comment count, any screen that failed, the
contradictions and open questions, and where the PNGs are.

## Fallback: Figma MCP (no token for the script)

Only when step 1 found no usable token. Rule 1 still holds.

1. Get the structure once (the MCP's metadata / data tool on the section node). From it list the
   **top-level** frames that are screen-sized; skip hidden ones and wide header strips. Do this
   yourself — do not paste the raw dump back to the user.
2. Drop repeats yourself: same name + same size + same visible text → keep the first.
3. Export **one image per screen node**, one node per call or a node list — never the section.
   Save to an **absolute** path (e.g. `<repo>/figma/NN-<screen>.png`); relative paths fail in most
   MCP download tools. Check each file exists and is non-empty before step 6.
4. Notes: read text nodes outside the screens and tie each to the nearest screen by its absolute
   x/y. Arrows: if the dump lists connectors with start/end node ids, rebuild the flow; otherwise
   describe the flow from the screen names.
5. There is no `manifest.json` and no component check; continue at step 3.5.

## When the script fails

| Output | Do |
|---|---|
| `NO_FIGMA_TOKEN` | run `CAPTURE check`, then step 1 |
| `FIGMA_AUTH 403` | the token's owner cannot open this file in Figma |
| `FIGMA_NOT_FOUND` | wrong or stale node id — ask for a fresh "Copy link to selection" |
| `URL has no node-id ...` | ask for a link to the section/frame, not the whole file |
| `No screen-sized frame found` | re-run with `--single`, or the link points at a single component |
| `FIGMA_RATE_LIMIT` | wait a minute and retry once |
| `CERTIFICATE_VERIFY_FAILED` | `pip install certifi`, or make sure `/etc/ssl/cert.pem` exists |
