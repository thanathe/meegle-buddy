#!/usr/bin/env python3
"""Read the meegle-buddy config and print short, plain summaries a small model can act on.

The config is written by the meegle-buddy skill (its init step). This script only reads it,
except `set-flow`, which writes spec-flow.json next to it.

Config home: $MEEGLE_BUDDY_HOME, else ~/.claude/meegle-buddy

Usage:
  meegle_config.py projects
  meegle_config.py types    [--project P]
  meegle_config.py summary  TYPE [--project P]
  meegle_config.py options  TYPE FIELD [--project P]
  meegle_config.py flow
  meegle_config.py set-flow --project P --spec-type T --task-type T --parent-field F [--docs-field F]

P = project key or slug. TYPE = type key or type name. Default project: spec-flow.json, then
config.json default_project_key.
"""
import json
import os
import sys

HOME = os.path.expanduser(os.environ.get("MEEGLE_BUDDY_HOME", "~/.claude/meegle-buddy"))
FLOW_FILE = os.path.join(HOME, "spec-flow.json")


def die(msg):
    print(f"ERROR: {msg}")
    sys.exit(1)


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def config():
    c = load(os.path.join(HOME, "config.json"))
    if c is None:
        die(f"no meegle-buddy config at {HOME}/config.json. Run the meegle-buddy skill setup first.")
    return c


def project_files():
    d = os.path.join(HOME, "projects")
    if not os.path.isdir(d):
        return []
    out = []
    for name in sorted(os.listdir(d)):
        if name.endswith(".json"):
            p = load(os.path.join(d, name))
            if isinstance(p, dict) and "work_item_types" in p:
                out.append(p)
    return out


def flow():
    return load(FLOW_FILE) or {}


def find_project(ref):
    ref = ref or flow().get("project_key") or config().get("default_project_key")
    if not ref:
        die("no project given and no default. Pass --project.")
    for p in project_files():
        if ref in (p.get("project_key"), p.get("slug"), p.get("name")):
            return p
    die(f"project '{ref}' has no profile in {HOME}/projects. Run meegle-buddy setup for it.")


def find_type(p, ref):
    for t in p["work_item_types"]:
        if ref in (t.get("type_key"), t.get("name")):
            return t
    die(f"type '{ref}' not in project {p.get('project_key')}. Run: meegle_config.py types")


def fkey(f):
    return f.get("field_key") or f.get("key")


def fname(f):
    return f.get("field_name") or f.get("name") or f.get("label") or ""


def opts(f, limit=20):
    o = f.get("options") or []
    s = ", ".join(f"{x.get('label')}={x.get('value')}" for x in o[:limit])
    return s + (f" … (+{len(o) - limit} more)" if len(o) > limit else "")


def cmd_projects(_):
    default = config().get("default_project_key")
    for p in project_files():
        mark = "  (default)" if default in (p.get("project_key"), p.get("slug")) else ""
        print(f"{p.get('project_key')}  slug={p.get('slug')}  name={p.get('name')}{mark}")


def cmd_types(a):
    p = find_project(a.get("project"))
    print(f"project {p.get('project_key')} ({p.get('name')})")
    for t in p["work_item_types"]:
        req = [fkey(f) for f in t.get("fields", []) if f.get("required")]
        print(f"- {t.get('type_key')}  name={t.get('name')}  required={len(req)}")


def cmd_summary(a):
    p = find_project(a.get("project"))
    t = find_type(p, a["args"][0])
    fields = t.get("fields", [])
    byk = {fkey(f): f for f in fields}
    print(f"TYPE {t.get('type_key')} ({t.get('name')}) in project {p.get('project_key')}")

    tpls = t.get("templates") or []
    default = next((x for x in tpls if x.get("is_default")), tpls[0] if tpls else None)
    if t.get("template_required") or default:
        tid = default.get("id") if default else "?"
        print(f"\nTEMPLATE: send field `template` = {tid}" + ("  (REQUIRED)" if t.get("template_required") else ""))

    print("\nREQUIRED FIELDS (always):")
    for f in fields:
        if f.get("required") and fkey(f) != "template":
            line = f"- {fkey(f)}  {fname(f)}  [{f.get('value_type')}]"
            if f.get("options"):
                line += f"  options: {opts(f)}"
            print(line)

    rules = t.get("conditional_rules") or []
    if rules:
        print("\nREQUIRED ONLY WHEN (conditional rules):")
        for r in rules:
            if "when_field" in r and r.get("require"):
                need = ", ".join(f"{k} {fname(byk.get(k, {}))}".strip() for k in r["require"])
                print(f"- if {r['when_field']} = {r.get('when_option')} ({r.get('when_label', '')}) -> also send: {need}")

    roles = t.get("roles") or []
    cr = t.get("create_roles") or {}
    if roles or cr:
        print("\nROLES:")
        if roles:
            print("- available: " + ", ".join(f"{r.get('key')} ({r.get('name')})" for r in roles))
        if cr.get("required_roles"):
            print(f"- required at create: {cr['required_roles']}")
        if cr.get("via"):
            print(f"- send as: {cr['via']}")

    sch = t.get("schedule") or {}
    if sch:
        print("\nSCHEDULE / ESTIMATE:")
        if sch.get("estimate_schedule_field"):
            print(f"- date range field: {sch['estimate_schedule_field']}  (value: string \"[start_ms,end_ms]\")")
        if sch.get("effort_field"):
            print(f"- effort field: {sch['effort_field']}  unit: {sch.get('effort_unit')}")

    conv = t.get("conventions") or {}
    defaults = []
    for k, v in conv.items():
        if isinstance(v, dict) and v.get("field_key") and v.get("default_value"):
            defaults.append(f"- {v['field_key']} default {v['default_value']}  ({k})")
    if defaults:
        print("\nTHIS USER'S USUAL VALUES (confirm before using):")
        print("\n".join(defaults))

    rel = [f for f in fields if f.get("value_type") in ("workitem_related_select", "workitem_related_multi_select")]
    if rel:
        print("\nLINK-TO-ANOTHER-CARD FIELDS (value = a work item id):")
        for f in rel:
            print(f"- {fkey(f)}  {fname(f)}")
    links = [f for f in fields if f.get("value_type") == "link"]
    if links:
        print("\nURL FIELDS:")
        for f in links:
            print(f"- {fkey(f)}  {fname(f)}")

    g = t.get("create_gotchas")
    if g:
        text = g if isinstance(g, str) else json.dumps(g, ensure_ascii=False)
        print("\nLEARNED THE HARD WAY (create_gotchas):\n" + text[:1200])


def cmd_options(a):
    p = find_project(a.get("project"))
    t = find_type(p, a["args"][0])
    for f in t.get("fields", []):
        if fkey(f) == a["args"][1]:
            for o in f.get("options") or []:
                print(f"{o.get('value')}  {o.get('label')}")
            return
    die(f"field {a['args'][1]} not found on type {t.get('name')}")


def cmd_flow(_):
    f = flow()
    if not f:
        print("NOT SET. Ask the user which types to use, then run set-flow.")
        return
    print(json.dumps(f, ensure_ascii=False, indent=2))


def cmd_set_flow(a):
    need = ["project", "spec-type", "task-type", "parent-field"]
    missing = [k for k in need if not a.get(k)]
    if missing:
        die("missing --" + ", --".join(missing))
    p = find_project(a["project"])
    spec = find_type(p, a["spec-type"])
    task = find_type(p, a["task-type"])
    data = {
        "project_key": p.get("project_key"),
        "spec_type_key": spec.get("type_key"),
        "spec_type_name": spec.get("name"),
        "task_type_key": task.get("type_key"),
        "task_type_name": task.get("name"),
        "parent_field": a["parent-field"],
        "docs_field": a.get("docs-field"),
    }
    os.makedirs(HOME, exist_ok=True)
    with open(FLOW_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"saved {FLOW_FILE}")
    print(json.dumps(data, ensure_ascii=False, indent=2))


def parse(argv):
    a = {"args": []}
    i = 0
    while i < len(argv):
        if argv[i].startswith("--"):
            a[argv[i][2:]] = argv[i + 1] if i + 1 < len(argv) else None
            i += 2
        else:
            a["args"].append(argv[i])
            i += 1
    return a


CMDS = {"projects": cmd_projects, "types": cmd_types, "summary": cmd_summary, "options": cmd_options,
        "flow": cmd_flow, "set-flow": cmd_set_flow}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__)
        sys.exit(1)
    a = parse(sys.argv[2:])
    if sys.argv[1] in ("summary",) and len(a["args"]) < 1:
        die("usage: summary TYPE")
    if sys.argv[1] == "options" and len(a["args"]) < 2:
        die("usage: options TYPE FIELD")
    CMDS[sys.argv[1]](a)
