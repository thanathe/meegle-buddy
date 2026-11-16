# Attach a card under a specific story NODE

Some spaces use a **node-driven** parent (e.g. a "Story / Feature" whose workflow is a graph of nodes: Intake → Discovery → Business Analysis → Development → …). Each node shows its own list of child cards (often "Tech Tasks"). Setting the child's link/relation field to the parent makes it appear in the parent's *rollup* list, but does **NOT** place it under a particular node — that binding is a separate node-edge created by the web UI's "Add … → Add current" button.

> **This binding is not settable by the `meegle` CLI.** It only exists in the web UI, so the user does it with a few clicks. Do not try to reach the web UI's internal endpoints or use the user's browser session (cookies, CSRF tokens) to do it for them.

## When this applies (detect first)

You created/linked a child card to a parent, but the user wants it to **show under a specific node** (they said "ใต้ node X" / "ในขั้น X" / pointed at a node's card table). Confirm the CLI genuinely can't do it for this space before reaching for the browser — run these against the **parent** type/instance:

```bash
# 1) Does the parent's node have a child-card field? (usually NO)
meegle workflow meta-node-fields --project-key <PK> --work-item-type <PARENT_TYPE> --page-num 1 --format json
# 2) Is there a relation definition for child→parent that the CLI could set? (usually only unrelated ones)
meegle relation meta-definitions --project-key <PK> --work-item-type <CHILD_TYPE> --format json
# 3) WBS only works on IPD projects; most aren't:
meegle wbs list-instance-rows --project-key <PK> --work-item-id <PARENT_ID> --format json   # "Not Ipd Project" → N/A
```

If none of those give a setter (the normal case), the node binding must be done in the web UI.

## Guide the user to click it

Walk the user through these clicks on the Meegle web page of the parent card (phrase each step to them in the user's language at runtime):

1. Click the target node (e.g. "Business Analysis") so the node's panel opens.
2. In the node's child-card table, click the ▾ caret next to the **"Add …"** button → **Add current** → **This space** → pick the card type.
3. Tick the just-created card → **Confirm**.

Then confirm it worked: ask the user to check the node's child count went up, or read the parent's rollup field back with `meegle workitem get`.

## Notes / guardrails
- Everything space-specific (host, project_key, parent_type, child_type, node keys) is **discovered per user** — keep it out of any shared default.
- Delete of cards is still web-UI-only; the CLI cannot delete.
