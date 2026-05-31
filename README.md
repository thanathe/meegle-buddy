# meegle-buddy

A friendly Claude **skill** that helps anyone log time and open cards in **Feishu / Lark Project** (also called *Meegle* / *Meego*) — **without knowing any field IDs and without filling things in wrong.**

It's built to be shared with a whole team. Developers and non-developers alike can just say *"log my time today"* or *"open a card"* in plain language, and the skill asks simple questions and fills in everything correctly.

**Nothing is hardcoded.** The first time you use it, meegle-buddy looks at *your* spaces and *your* fields and remembers them. So it works for any team's setup, not just one.

---

## 🟢 Start here — which kind of user are you?

- **"I've never used Claude Code / I'm not a developer."** → read **[Part 1: Easy install](#part-1-easy-install-no-experience-needed)** below. It walks you through everything, step by step.
- **"I already use Claude Code."** → jump to **[Part 2: Quick install](#part-2-quick-install-for-claude-code-users)**.

---

# Part 1: Easy install (no experience needed)

You need three things, once. Take it slow — each step is copy-paste.

> 💡 Everything below is typed into the **Terminal** app.
> - **Mac:** press `⌘ + Space`, type `Terminal`, press Enter.
> - **Windows:** open **PowerShell** (press the Start button, type `PowerShell`, press Enter).

### Step 1 — Install Claude Code

Claude Code is the app that runs this skill. Follow the official installer here:

👉 **https://docs.claude.com/en/docs/claude-code/overview** (look for "Install" / "Quickstart").

When it's done, check it works by typing this in the Terminal and pressing Enter:

```bash
claude --version
```

If you see a version number, you're good. If it says "command not found", re-open the Terminal and try again, or re-run the installer.

> Claude Code needs an Anthropic account (the same login as Claude). The install page explains how to sign in.

### Step 2 — Install the `meegle` tool

This is the little program that actually talks to Feishu / Lark Project. You install it with `npm` (which comes with **Node.js**).

1. If you don't have Node.js yet, install it from 👉 **https://nodejs.org** (download the "LTS" version, run it, click Next/Agree).
2. Then in the Terminal, type:

   ```bash
   npm install -g @lark-project/meegle
   ```

3. Log in to your Lark / Feishu account. **Use the device-code flow** (this is the reliable one):

   ```bash
   meegle config set host project.larksuite.com    # set your company's host once
   meegle auth login --device-code
   ```

   It prints a link and a code — open the link in any browser (your phone works too), enter the code, approve, and the command finishes by itself.

   > 💡 **Why not just `meegle auth login`?** The plain version tries to pop open a browser automatically. Inside Claude Code, VS Code's terminal, an SSH session, or some setups, that browser **doesn't open reliably (works sometimes, hangs other times)**. `--device-code` avoids all that — it just gives you a link to open yourself. If your teammates say *"the login browser won't open"*, this is the fix.
   >
   > Pick the `host` your company uses: `project.larksuite.com`, `project.feishu.cn`, or `meegle.com` (ask a colleague if unsure).

4. Check it worked:

   ```bash
   meegle auth status --format json
   ```

   You want to see `"authenticated": true`. If not, run `meegle auth login --device-code` again.

> ⚠️ If installing `meegle` fails, ask whoever set up Lark Project at your company — some teams use a different host or a private setup. The skill itself doesn't change; only this install step does.
>
> 📖 **The `meegle` CLI is an official open-source tool by Larksuite** — full docs, all commands, and other agent skills (Cursor / Windsurf / Gemini CLI / etc.): **https://github.com/larksuite/meegle-cli**

### Step 3 — Install the skill

This copies meegle-buddy into the folder where Claude Code looks for skills.

**Mac / Linux** — paste this whole block into the Terminal and press Enter:

```bash
mkdir -p ~/.claude/skills
git clone <this-repo-url> ~/.claude/skills/meegle-buddy
```

**Windows (PowerShell):**

```powershell
mkdir "$HOME\.claude\skills" -Force
git clone <this-repo-url> "$HOME\.claude\skills\meegle-buddy"
```

> Replace `<this-repo-url>` with the address of this repository (whoever shared it with you has the link). No `git`? On the repo page click the green **"Code" → "Download ZIP"**, unzip it, and move the folder so it sits at `~/.claude/skills/meegle-buddy` (Mac) or `%USERPROFILE%\.claude\skills\meegle-buddy` (Windows).

### Step 4 — Use it 🎉

Open Claude Code (type `claude` in the Terminal, in any folder). Then just talk to it normally — **in Thai or English**:

- **First time:** say **"ตั้งค่า meegle"** (or *"set up meegle"*). It will ask which workspace you use and learn your fields. This takes a minute, once.
- **Log your day:** **"ลงเวลาวันนี้"** (or *"log my time today"*). It asks when you started and what you did, then records it.
- **Open a card:** **"เปิดการ์ด"** (or *"create a card"*).
- **Set an estimate / schedule:** *"ตั้ง estimate ให้การ์ดนี้"*.

That's it. You never have to remember any field names or IDs — the skill asks you plain questions and fills the rest.

---

# Part 2: Quick install (for Claude Code users)

**Prerequisites:** the [`meegle` CLI](https://github.com/larksuite/meegle-cli) (official, by Larksuite) installed and authenticated.

```bash
npm install -g @lark-project/meegle
meegle config set host project.larksuite.com   # your tenant host
meegle auth login --device-code                # device-code avoids browser-callback hangs in agent shells
meegle auth status --format json               # expect "authenticated": true
```

**Install the skill:**

```bash
git clone <this-repo-url> ~/.claude/skills/meegle-buddy
```

(just needs `SKILL.md` to land at `~/.claude/skills/meegle-buddy/SKILL.md`)

**Use it** — say any of: `ตั้งค่า meegle` / `set up meegle`, `ลงเวลาวันนี้` / `log time`, `เปิดการ์ด` / `create a card`, `เช็ค field` / `sync meegle`.

---

## What it does

- **Guided setup (one time):** asks which spaces you use, discovers your work-item types and their fields/workflows, and saves a personal config.
- **Open a card:** walks you through every required field for that work-item type, then creates it.
- **Log time:** asks when you started and what you did, lays out your day (skipping lunch), and creates time records — each with a description and linked to a parent card.
- **Estimate / effort / schedule:** takes the numbers you give and writes them to the right fields.
- **Keeps up with changing fields:** before each action it re-checks the live fields; if your team added a new field or made one required, it asks whether to include it — so it never goes stale while your setup is still changing.

## What it does **not** do

- No guessing of effort/complexity — you provide the numbers.
- No hardcoded field maps — it discovers yours.
- It does not bundle your login — each person authenticates their own `meegle` CLI.

---

## Where your settings live (and privacy)

The skill saves what it discovers in your **home folder**, never in this repo:

```
~/.claude/meegle-buddy/
├── config.json              # your spaces + preferences (e.g. usual start time)
└── projects/
    └── <project_key>.json   # your discovered field map per space
```

Because it lives in your home folder, your field map stays **private to you** and is never shared or committed. Each colleague who installs the skill builds their own.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `claude: command not found` | Claude Code isn't installed / not on PATH — re-run its installer, reopen Terminal. |
| `meegle: command not found` | Install Node.js, then `npm install -g @lark-project/meegle`. |
| **Login browser won't open / opens sometimes / login hangs** | Don't use plain `meegle auth login`. Run `meegle auth login --device-code` instead — it gives you a link to open yourself (no auto-browser, works in Claude Code / SSH / VS Code terminals). |
| `"authenticated": false` or auth errors | Run `meegle auth login --device-code` again; make sure the host is right (`meegle config set host <host>`). |
| The skill doesn't trigger | Make sure the folder is exactly at `~/.claude/skills/meegle-buddy/` with `SKILL.md` inside; restart Claude Code. |
| It can't find your space | Give it the **slug** from your Meegle URL (the short code), or paste the full URL. |
| A create fails saying a field is required | Tell the skill the value — it will add that field to your checklist so it's asked next time. |

---

## How it works (for the curious)

| File | Purpose |
|---|---|
| `SKILL.md` | Entry point + operating principles + routing |
| `references/init.md` | Guided discovery → builds your personal config |
| `references/create-card.md` | Open a work item with all required fields |
| `references/timelog.md` | Log time records (timestamps + linking) |
| `references/schedule.md` | Set estimate / effort / per-node schedule |
| `references/check-fields.md` | Drift check: ask before adding new/changed fields |
| `references/cli-reference.md` | The `meegle` commands + field-value rules |
| `references/config-format.md` | The shape of the saved config |

It's a thin, **discovery-driven** layer over the `meegle` CLI: it learns your field map once, then drives `meegle workitem` / `meegle workflow` for you.

---

## Official references

The `meegle` CLI this skill drives is an **official open-source tool by Larksuite**. For full command docs, auth options, config, and other agent skills:

- 📦 **Repo & docs:** https://github.com/larksuite/meegle-cli
- 📥 **npm package:** https://www.npmjs.com/package/@lark-project/meegle
- 🤖 **Official Meegle agent skill** (works for Cursor / Windsurf / Gemini CLI / Claude Code / etc.) — installable with:
  ```bash
  npx skills add larksuite/meegle-cli -y -g
  ```
  meegle-buddy is a *complementary* guided layer on top; you can install the official skill too if you want the full command catalog and MQL reference.

---

## License

MIT — see [LICENSE](LICENSE). Free to use and share.
