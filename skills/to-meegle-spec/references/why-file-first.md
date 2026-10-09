# Why the spec is a file first and a card second

Background for humans and strong models. The steps in SKILL.md do not depend on this file.

**Meegle is a delivery tracker, not a spec store.** Parent card types (Feature, Story, Requirement)
usually demand delivery metadata at create — a product, a version, a PM — and usually carry a URL
field for linking the document in from outside.

So this skill always writes the spec to a markdown file first, and creates the card only after the
user says yes. Reasons, in order of weight:

1. **The required fields are delivery metadata.** Work that is not approved yet often has no version
   and no PM. Opening a card announces a commitment — if there is none, the card is wrong.
2. **The card is built to link to an outside document.** Pasting a whole spec into `description`
   fights that design.
3. **Specs iterate.** Editing `description` over the CLI resends the whole body every time — no
   diff, no history, no review. A file has all three.
4. **How well `description` renders long markdown** (tables, checkboxes, code) is unverified. Do not
   bet a spec on it.
