#!/usr/bin/env python3
"""Split a Figma link into separate screens, read the design notes, export one PNG per screen.

Uses the Figma REST API only (stdlib, no MCP), so it runs in any agent harness that has Bash and
internet access.

If figma-build-kit has a cache for the file (~/.claude/figma-build-kit/<fileKey>.json), each
screen's components are checked against its design system: central vs custom/local.

Token (a Figma personal access token with the file_content:read scope), first one found:
  1. $FIGMA_TOKEN / FIGMA_ACCESS_TOKEN / FIGMA_API_KEY / FIGMA_API_TOKEN / FIGMA_PAT
  2. the file named by $FIGMA_TOKEN_FILE (plain token, or JSON with a "token" key)
  3. a token file an agent harness keeps for its own Figma connector (HARNESS_TOKEN_FILES below)
  4. the first line of ~/.claude/meegle-buddy/figma_token

Usage:
  figma_capture.py check
  figma_capture.py plan   <figma-url> [<figma-url> ...] [--single]
  figma_capture.py export <figma-url> [<figma-url> ...] [--single] [--out DIR] [--scale 2]
                          [--only 1,3,4]

check  says which token source was found (never the value), where it looked, and whether Figma
       accepts it. Run it first when the token seems missing.
plan   prints the screens it found and the notes attached to each. Nothing is written.
export does the same, then writes one PNG per screen plus manifest.json into --out.

A screen is never merged with another one: every screen gets its own PNG.

--single  treat each URL's node as one screen, even if it holds several screen-sized frames.
--only    export only these screen numbers (as printed by plan).
"""
import json
import math
import os
import glob
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.figma.com/v1"
HOME = os.path.expanduser(os.environ.get("MEEGLE_BUDDY_HOME", "~/.claude/meegle-buddy"))
BUILD_KIT = os.path.expanduser(os.environ.get("FIGMA_BUILD_KIT_HOME", "~/.claude/figma-build-kit"))

# Frames at least this big are screens; smaller frames are components, notes or decoration.
SCREEN_MIN_W, SCREEN_MIN_H = 280, 400
# Figma refuses renders above ~32 megapixels; stay under it.
MAX_PIXELS = 30_000_000
# Layer names that mark a designer note rather than UI.
NOTE_NAME = re.compile(
    r"note|annotation|annotate|comment|remark|memo|spec|description|desc\b|todo|"
    r"หมายเหตุ|โน้ต|โน๊ต|คำอธิบาย|อธิบาย",
    re.I,
)
CONTAINERS = {"CANVAS", "SECTION", "GROUP"}
FRAMES = {"FRAME", "COMPONENT", "COMPONENT_SET", "INSTANCE"}
NOTE_TYPES = {"STICKY", "SHAPE_WITH_TEXT"}


def die(msg):
    print(f"ERROR: {msg}")
    sys.exit(1)


# Harnesses name the variable differently; take the first one that is set.
TOKEN_VARS = ("FIGMA_TOKEN", "FIGMA_ACCESS_TOKEN", "FIGMA_API_KEY", "FIGMA_API_TOKEN", "FIGMA_PAT")
# Token files that agent harnesses write when you connect Figma in them (JSON with a "token" key).
# Add yours here if your harness keeps one elsewhere.
HARNESS_TOKEN_FILES = ("~/.dsh*/connectors/figma.json",)


def ssl_context():
    """Python from python.org on macOS ships without CA certs; fall back to certifi or the system bundle."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    ctx = ssl.create_default_context()
    if not ctx.get_ca_certs() and os.path.exists("/etc/ssl/cert.pem"):
        ctx.load_verify_locations("/etc/ssl/cert.pem")
    return ctx


SSL = ssl_context()


def read_token_file(path):
    """A plain-text token, or a JSON object with a "token" key."""
    with open(path, encoding="utf-8") as f:
        raw = f.read().strip()
    if raw.startswith("{"):
        return (json.loads(raw).get("token") or "").strip()
    return raw.splitlines()[0].strip() if raw else ""


def token_sources():
    """Yield (source, token or "", note) for every place a token may live, in priority order."""
    for v in TOKEN_VARS:
        yield f"env {v}", os.environ.get(v, "").strip(), "" if os.environ.get(v) else "not set"
    files = []
    if os.environ.get("FIGMA_TOKEN_FILE"):
        files.append(os.path.expanduser(os.environ["FIGMA_TOKEN_FILE"]))
    for pattern in HARNESS_TOKEN_FILES:
        hits = sorted(glob.glob(os.path.expanduser(pattern)))
        if not hits:
            yield f"harness file {pattern}", "", "no match (HOME=" + os.path.expanduser("~") + ")"
        files += hits
    files.append(os.path.join(HOME, "figma_token"))
    for path in files:
        try:
            yield path, read_token_file(path), ""
        except FileNotFoundError:
            yield path, "", "missing"
        except (OSError, ValueError) as e:
            yield path, "", f"unreadable: {e.__class__.__name__}: {e}"


def token():
    tok = next((t for _, t, _ in token_sources() if t), "")
    if not tok:
        die(
            f"NO_FIGMA_TOKEN. Set one of {', '.join(TOKEN_VARS)}, or save a personal access token "
            f"(scope file_content:read) to {os.path.join(HOME, 'figma_token')}"
        )
    return tok


def get(path, params):
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"X-Figma-Token": token()})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120, context=SSL) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(int(e.headers.get("Retry-After", "5")))
                continue
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code in (401, 403):
                die(f"FIGMA_AUTH {e.code}: token invalid or no access to this file. {body}")
            if e.code == 404:
                die(f"FIGMA_NOT_FOUND: file or node does not exist. {body}")
            die(f"FIGMA_HTTP {e.code}: {body}")
    die("FIGMA_RATE_LIMIT: still rate-limited after retries")


def parse_url(url):
    """figma.com/design|file/<key>/...?node-id=1-2  (branch URLs use the branch key)."""
    u = urllib.parse.urlparse(url)
    parts = [p for p in u.path.split("/") if p]
    if len(parts) < 2 or parts[0] not in ("design", "file", "proto", "board"):
        die(f"not a Figma file URL: {url}")
    key = parts[1]
    if len(parts) >= 4 and parts[2] == "branch":
        key = parts[3]
    node = urllib.parse.parse_qs(u.query).get("node-id", [""])[0].replace("-", ":")
    return key, node


def box(n):
    b = n.get("absoluteBoundingBox") or {}
    return b.get("x", 0), b.get("y", 0), b.get("width", 0), b.get("height", 0)


def visible(n):
    return n.get("visible", True)


def is_banner(n):
    """A wide, short strip across the flow (title / status header), not a screen."""
    _, _, w, h = box(n)
    return n["type"] in FRAMES and w > 2500 and w > 2.5 * h


def is_screen(n):
    _, _, w, h = box(n)
    return (n["type"] in FRAMES and w >= SCREEN_MIN_W and h >= SCREEN_MIN_H and visible(n)
            and not is_banner(n))


def has_screen(n):
    return any(is_screen(c) or (c["type"] in CONTAINERS and has_screen(c))
               for c in n.get("children", []) if visible(c))


def texts(n, limit=200):
    """All visible text under n, in reading order (top-to-bottom, left-to-right)."""
    out = []

    def walk(m):
        if not visible(m) or len(out) >= limit:
            return
        if m["type"] == "TEXT" and m.get("characters", "").strip():
            x, y, _, _ = box(m)
            out.append((round(y / 8), x, m["characters"].strip()))
        elif m["type"] in NOTE_TYPES:
            t = (m.get("characters") or "").strip()
            if t:
                x, y, _, _ = box(m)
                out.append((round(y / 8), x, t))
        for c in m.get("children", []):
            walk(c)

    walk(n)
    return [t for _, _, t in sorted(out)]


def is_note(n):
    if not visible(n):
        return False
    if n["type"] in NOTE_TYPES or n["type"] == "TEXT":
        return True
    return bool(NOTE_NAME.search(n.get("name", "")))


def ds_keys(file_key):
    """Component / component-set keys the figma-build-kit cache lists for this file, or None."""
    try:
        with open(os.path.join(BUILD_KIT, f"{file_key}.json"), encoding="utf-8") as f:
            cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    comps = cache.get("components")
    if not comps:
        return None
    keys = set()
    for v in (comps.values() if isinstance(comps, dict) else comps):
        if isinstance(v, dict) and v.get("key"):
            keys.add(v["key"])
    return keys or None


def components_used(screen_node, comps, sets, known):
    """Count component instances in a screen, grouped by set name (or component name)."""
    used = {}

    def walk(m):
        if not visible(m):
            return
        if m["type"] == "INSTANCE":
            c = comps.get(m.get("componentId", ""), {})
            s = sets.get(c.get("componentSetId", ""), {})
            name = s.get("name") or c.get("name") or m.get("name", "")
            if known is None:
                where = "unknown"
            elif c.get("key") in known or s.get("key") in known:
                where = "design-system"
            else:
                where = "custom"
            u = used.setdefault(name, {"name": name, "count": 0, "where": where})
            u["count"] += 1
            return  # do not count the parts inside a component
        for c in m.get("children", []):
            walk(c)

    walk(screen_node)
    return sorted(used.values(), key=lambda u: (u["where"] != "custom", -u["count"]))


def collect(root, single):
    """Return (screens, loose_notes, headers, connectors, owner).

    loose_notes: text beside the screens, not yet tied to one. headers: text of banner strips.
    connectors: visible arrows. owner: node id -> id of the screen / block it sits in, so arrows
    that end on a button inside a screen are read as pointing at that screen.
    """
    screens, loose, headers, connectors, owner = [], [], [], [], {}

    def own(n, top_id):
        owner[n["id"]] = top_id
        for c in n.get("children", []):
            own(c, top_id)

    def block(n, kind):
        t = texts(n) or ([n["characters"].strip()] if (n.get("characters") or "").strip() else [])
        own(n, n["id"])
        if t:
            loose.append({"id": n["id"], "name": n.get("name", ""), "box": box(n), "text": t,
                          "kind": kind})

    def walk(n, top):
        kids = n.get("children", [])
        frame_kids = [c for c in kids if is_screen(c)]
        # A frame that only wraps several screens is a container, not a screen.
        wrapper = n["type"] in FRAMES and len(frame_kids) >= 2 and not single
        if n["type"] in CONTAINERS or wrapper or (top and n["type"] not in FRAMES):
            for c in kids:
                if not visible(c):
                    continue
                if is_screen(c):
                    walk(c, False)
                elif c["type"] == "CONNECTOR":
                    connectors.append(c)
                elif is_banner(c):
                    headers.extend(texts(c))
                elif c["type"] in CONTAINERS and has_screen(c):
                    walk(c, False)
                elif c["type"] in CONTAINERS or is_note(c):
                    block(c, "note")
                else:
                    block(c, "fragment")  # a loose UI piece (dropdown, modal state)
            return
        if n["type"] in FRAMES:
            inner = []
            for c in kids:
                if visible(c) and c["type"] != "TEXT" and NOTE_NAME.search(c.get("name", "")):
                    inner.extend(texts(c))
            own(n, n["id"])
            screens.append({
                "id": n["id"],
                "name": n.get("name", ""),
                "box": box(n),
                "notes": inner,
                "ui_text": texts(n, limit=80),
                "_node": n,
            })

    walk(root, True)
    return screens, loose, headers, connectors, owner


def split_rows(screens, loose):
    """Wide, short notes above a row of screens are row titles (e.g. Add / Edit / Delete)."""
    if not screens:
        return loose
    sw = sorted(s["box"][2] for s in screens)[len(screens) // 2]
    rows = [n for n in loose if n["kind"] == "note" and n["box"][2] >= 3 * sw and n["box"][3] <= 400]
    for s in screens + loose:
        x, y, w, _ = s["box"]
        above = [r for r in rows if r["box"][1] <= y and r["box"][0] <= x + w / 2 <= r["box"][0] + r["box"][2]]
        if above and s not in rows:
            s["row"] = " / ".join(max(above, key=lambda r: r["box"][1])["text"])
    return [n for n in loose if n not in rows]


def flow_edges(connectors, owner, screens, loose):
    """Arrows between screens and decision blocks, as (from, label, to) display strings."""
    label = {s["id"]: f"[{s['no']}] {s['name']}" for s in screens}
    for n in loose:
        row = f" ({n['row']})" if n.get("row") else ""
        label.setdefault(n["id"], ("◇ " if n["kind"] == "note" else "") + " ".join(n["text"])[:60] + row)
    edges = []
    for c in connectors:
        a = owner.get((c.get("connectorStart") or {}).get("endpointNodeId"))
        b = owner.get((c.get("connectorEnd") or {}).get("endpointNodeId"))
        # The arrowhead marks where the arrow points; designers sometimes draw it backwards.
        if ("ARROW" in (c.get("connectorStartStrokeCap") or "")
                and "ARROW" not in (c.get("connectorEndStrokeCap") or "")):
            a, b = b, a
        if a and b and a != b and a in label and b in label:
            edges.append((label[a], (c.get("characters") or "").strip(), label[b]))
    return edges


def attach_notes(screens, loose, in_flow=()):
    """Give each loose note to the nearest screen (edge-to-edge distance).

    Fragments and notes that an arrow points at (decisions) are part of the flow, not notes.
    """
    def dist(a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        dx = max(bx - (ax + aw), ax - (bx + bw), 0)
        dy = max(by - (ay + ah), ay - (by + bh), 0)
        return math.hypot(dx, dy)

    unassigned = []
    for note in loose:
        if note["kind"] == "fragment" or note["id"] in in_flow:
            continue
        if not screens:
            unassigned.append(note)
            continue
        best = min(screens, key=lambda s: dist(s["box"], note["box"]))
        if dist(best["box"], note["box"]) > 2000:
            unassigned.append(note)
        else:
            best["notes"].extend(note["text"])
    return unassigned


def reading_order(screens):
    # Rows first (screens whose tops are within half a screen height share a row), then left-to-right.
    if not screens:
        return screens
    h = sorted(s["box"][3] for s in screens)[len(screens) // 2] or 1
    return sorted(screens, key=lambda s: (round(s["box"][1] / (h / 2)), s["box"][0]))


def discover(urls, single):
    found, unassigned, flows = [], [], []
    for url in urls:
        key, node = parse_url(url)
        if node:
            data = get(f"/files/{key}/nodes", {"ids": node})
            entry = (data.get("nodes") or {}).get(node)
            if not entry:
                die(f"FIGMA_NOT_FOUND: node {node} in file {key}")
            fname = data.get("name", "")
        else:
            data = get(f"/files/{key}", {"depth": 2})
            pages = data["document"]["children"]
            if len(pages) > 1:
                die(f"URL has no node-id and the file has {len(pages)} pages. "
                    "Copy the link of a frame or section (right click > Copy link to selection).")
            # depth=2 is not enough for notes; fetch the page in full.
            pid = pages[0]["id"]
            fname = data.get("name", "")
            entry = get(f"/files/{key}/nodes", {"ids": pid})["nodes"][pid]
        root = entry["document"]
        known = ds_keys(key)
        screens, loose, headers, connectors, owner = collect(root, single)
        for s in screens:
            s["components"] = components_used(s.pop("_node"), entry.get("components") or {},
                                              entry.get("componentSets") or {}, known)
            s["design_system_cache"] = known is not None
        loose = split_rows(screens, loose)
        for s in reading_order(screens):
            s.update(no=len(found) + 1, file_key=key, file_name=fname,
                     link=f"https://www.figma.com/design/{key}/?node-id={s['id'].replace(':', '-')}")
            found.append(s)
        edges = flow_edges(connectors, owner, screens, loose)
        in_flow = {owner.get((c.get(e) or {}).get("endpointNodeId"))
                   for c in connectors for e in ("connectorStart", "connectorEnd")}
        lost = attach_notes(screens, loose, in_flow)
        unassigned.extend(dict(n, file_key=key) for n in lost)
        flows.append({"file_key": key, "title": root.get("name", ""), "header": headers,
                      "edges": edges})
    return found, unassigned, flows


def slug(s):
    s = re.sub(r"[^\w\-]+", "-", s, flags=re.U).strip("-").lower()
    return s[:50] or "screen"


def export(screens, out, scale):
    os.makedirs(out, exist_ok=True)
    by_file = {}
    for s in screens:
        _, _, w, h = s["box"]
        sc = scale
        while sc > 0.5 and w * h * sc * sc > MAX_PIXELS:
            sc /= 2
        s["scale"] = sc
        by_file.setdefault((s["file_key"], sc), []).append(s)
    for (key, sc), group in by_file.items():
        for i in range(0, len(group), 10):
            batch = group[i:i + 10]
            res = get(f"/images/{key}", {"ids": ",".join(s["id"] for s in batch),
                                         "format": "png", "scale": sc})
            if res.get("err"):
                die(f"FIGMA_RENDER: {res['err']}")
            for s in batch:
                src = (res.get("images") or {}).get(s["id"])
                if not src:
                    s["png"] = None
                    s["error"] = "Figma returned no image for this node"
                    continue
                path = os.path.join(out, f"{s['no']:02d}-{slug(s['name'])}.png")
                with urllib.request.urlopen(src, timeout=120, context=SSL) as r, open(path, "wb") as f:
                    f.write(r.read())
                s["png"] = os.path.abspath(path)


def check():
    found = None
    for src, tok, note in token_sources():
        state = f"FOUND ({len(tok)} chars{', figd_' if tok.startswith('figd_') else ''})" if tok else note or "empty"
        print(f"  {src}: {state}")
        if tok and not found:
            found = src
    if not found:
        print("RESULT: NO_FIGMA_TOKEN")
        return
    me = get("/me", {})
    print(f"RESULT: OK via {found} — Figma user {me.get('handle')}")


def mark_repeats(screens):
    """Flag screens that repeat an earlier one, and pieces much narrower than the rest."""
    first = {}
    for s in screens:
        w, h = round(s["box"][2]), round(s["box"][3])
        sig = (s["file_key"], w, h, tuple(sorted(s["ui_text"])),
               tuple((c["name"], c["count"]) for c in s.get("components", [])))
        if sig in first:
            s["same_as"] = first[sig]
        else:
            first[sig] = s["no"]
    by_file = {}
    for s in screens:
        by_file.setdefault(s["file_key"], []).append(s["box"][2])
    for s in screens:
        widths = sorted(by_file[s["file_key"]])
        if s["box"][2] < 0.6 * widths[len(widths) // 2]:
            s["partial"] = True  # a modal or dropdown drawn on its own, not a full screen


def show(screens, unassigned, flows):
    for fl in flows:
        print(f"FLOW: {fl['title']}" + (f"  | header: {' / '.join(fl['header'])}" if fl["header"] else ""))
        for a, lab, b in fl["edges"]:
            print(f"  {a} {'-' + lab + '->' if lab else '->'} {b}")
    print(f"\nSCREENS: {len(screens)}  (each one is captured as its own image)")
    for s in screens:
        w, h = int(s["box"][2]), int(s["box"][3])
        row = f"  row: {s['row']}" if s.get("row") else ""
        print(f"\n[{s['no']}] {s['name']}  ({w}x{h})  node {s['id']}{row}")
        if s.get("same_as"):
            print(f"    SAME AS [{s['same_as']}] — identical screen, skip it")
        if s.get("partial"):
            print("    PART, NOT A FULL SCREEN (modal / dropdown on its own) — keep only if it adds something")
        if s.get("png"):
            print(f"    png: {s['png']}")
        if s.get("error"):
            print(f"    ERROR: {s['error']}")
        if s.get("components"):
            ds = [f"{u['name']} x{u['count']}" for u in s["components"] if u["where"] == "design-system"]
            cu = [f"{u['name']} x{u['count']}" for u in s["components"] if u["where"] == "custom"]
            un = [f"{u['name']} x{u['count']}" for u in s["components"] if u["where"] == "unknown"]
            if ds:
                print("    DESIGN-SYSTEM COMPONENTS: " + ", ".join(ds[:15]))
            if cu:
                print("    CUSTOM / LOCAL COMPONENTS: " + ", ".join(cu[:15]))
            if un:
                print("    COMPONENTS (no figma-build-kit cache to compare): " + ", ".join(un[:15]))
        if s["notes"]:
            print("    NOTES:")
            for t in s["notes"]:
                print("      - " + t.replace("\n", "\n        "))
        else:
            print("    NOTES: (none)")
    if unassigned:
        print("\nNOTES NOT NEAR ANY SCREEN:")
        for n in unassigned:
            print(f"  - [{n['name']}] " + " / ".join(n["text"]))
    if not screens:
        print("\nNo screen-sized frame found. Retry with --single to capture the node itself.")
        return
    keep = [str(s["no"]) for s in screens if not s.get("same_as")]
    if len(keep) < len(screens):
        print(f"\nSUGGESTED: --only {','.join(keep)}  ({len(screens) - len(keep)} repeated screen(s) left out)")


def main(argv):
    if argv[:1] == ["check"]:
        check()
        return
    if len(argv) < 2 or argv[0] not in ("plan", "export"):
        print(__doc__)
        sys.exit(1)
    cmd, args = argv[0], argv[1:]
    single = "--single" in args
    out, scale, only = "figma-screens", 2.0, None
    urls = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--single":
            pass
        elif a == "--out":
            out, i = args[i + 1], i + 1
        elif a == "--scale":
            scale, i = float(args[i + 1]), i + 1
        elif a == "--only":
            only, i = {int(x) for x in args[i + 1].split(",") if x.strip()}, i + 1
        else:
            urls.append(a)
        i += 1
    if not urls:
        die("give at least one Figma URL")
    screens, unassigned, flows = discover(urls, single)
    mark_repeats(screens)
    if only:
        screens = [s for s in screens if s["no"] in only]
    if cmd == "export":
        export(screens, out, scale)
        with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"flows": flows, "screens": screens, "unassigned_notes": unassigned}, f,
                      ensure_ascii=False, indent=2)
        print(f"MANIFEST: {os.path.abspath(os.path.join(out, 'manifest.json'))}")
    show(screens, unassigned, flows)


if __name__ == "__main__":
    main(sys.argv[1:])
