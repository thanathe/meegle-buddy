# Attach a card under a specific story NODE

Some spaces use a **node-driven** parent (e.g. a "Story / Feature" whose workflow is a graph of nodes: Intake → Discovery → Business Analysis → Development → …). Each node shows its own list of child cards (often "Tech Tasks"). Setting the child's link/relation field to the parent makes it appear in the parent's *rollup* list, but does **NOT** place it under a particular node — that binding is a separate node-edge created by the web UI's "Add … → Add current" button.

> **This binding is not settable by the `meegle` CLI.** It rides an internal web endpoint that needs the logged-in browser session (cookie + CSRF), which the public CLI/OpenAPI token does not have. Stay discovery-based: never hardcode project keys, node keys, relation ids, or tokens — find them per user/per space as below.

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

If none of those give a setter (the normal case), the node binding must go through the web UI / its endpoint.

## Path A — guide the user to click it (works for everyone, no extra tools)

Tell the user (Thai) to do this in the Meegle web page of the parent card:

1. คลิก node ที่ต้องการ (เช่น "Business Analysis") ให้ panel ของ node เปิดขึ้น
2. ที่ตาราง child cards กดลูกศร ▾ ข้างปุ่ม **"Add …"** → **Add current** → **This space** → เลือกชนิดการ์ด
3. ติ๊กการ์ดที่เพิ่งสร้าง → **Confirm**

This is the safe default — recommend it whenever the session has no browser-control MCP connected.

## Path B — automate via a browser-control MCP (only if one is connected)

If the session has a browser MCP (e.g. **Claude-in-Chrome**, tools `mcp__Claude_in_Chrome__*`) and the user is logged into Meegle there, you can fire the same endpoint with an in-page `fetch` — no clicking. **Requires those MCP tools to be available in the session; meegle-buddy itself doesn't ship them, so check first and fall back to Path A if absent.**

### B1. Discover the exact request once (capture, don't hardcode)
The payload contains a space-specific `relation_uuid` and node key that you must learn from a real request — they differ per space/template. Capture it once:

1. `list_connected_browsers` → `select_browser`; `tabs_context_mcp {createIfEmpty:true}` → tabId.
2. `navigate` the tab to the parent card page on the user's host (`https://<host>/<space>/<parent_type>/detail/<parent_id>`). Origin must be a logged-in Meegle page so cookies/CSRF apply.
3. Install a capture hook with `javascript_tool` (matches any request whose URL contains `control/import`):
   ```js
   (() => { window.__cap=[];
     const f=window.fetch; window.fetch=function(i,n){try{const u=typeof i==='string'?i:i&&i.url;
       if(u&&u.includes('control/import')){let h={};if(n&&n.headers){n.headers.forEach?n.headers.forEach((v,k)=>h[k]=v):Object.assign(h,n.headers);} window.__cap.push({url:u,headers:h,body:n&&n.body});}}catch(e){} return f.apply(this,arguments)};
     const oo=XMLHttpRequest.prototype.open,os=XMLHttpRequest.prototype.send,sh=XMLHttpRequest.prototype.setRequestHeader;
     XMLHttpRequest.prototype.open=function(m,u){this.__u=u;this.__h={};return oo.apply(this,arguments)};
     XMLHttpRequest.prototype.setRequestHeader=function(k,v){if(this.__u&&this.__u.includes('control/import'))this.__h[k]=v;return sh.apply(this,arguments)};
     XMLHttpRequest.prototype.send=function(b){if(this.__u&&this.__u.includes('control/import'))window.__cap.push({url:this.__u,headers:this.__h,body:b});return os.apply(this,arguments)};
     return 'hooked'; })();
   ```
4. Have the user (or, if the browser MCP can click, you) do **Path A once** for any one card, then read `JSON.stringify(window.__cap)`. You now have: the endpoint URL, the **CSRF header name** (commonly `x-meego-csrf-token`), and the full body incl. `relation_uuid` and `parent_node_key`.

### B2. Map the node name → node key
```bash
meegle workflow get-node --project-key <PK> --work-item-id <PARENT_ID> --format json
# each entry: basic.node_key (e.g. state_2) + basic.name (e.g. "Business Analysis")
```
Pick the `node_key` for the node the user named.

### B3. Fire it via `javascript_tool` (in-page fetch carries the session)
Reuse the captured shape; read the CSRF value live from the cookie (find the `*csrf*` cookie name from the captured header / `document.cookie`):
```js
(async () => {
  const csrf=(document.cookie.match(/(?:^|; )<CSRF_COOKIE_NAME>=([^;]*)/)||[])[1];
  const res=await fetch("<CAPTURED_ENDPOINT_URL>",{method:"POST",credentials:"include",
    headers:{"Content-Type":"application/json","<CSRF_HEADER_NAME>":csrf,"x-meego-from":"web","x-lark-gw":"1"},
    body:JSON.stringify({
      wi_object_id:<PARENT_ID>, wi_ids:[<CHILD_ID>], bqls:[], use_migration_task:true,
      parent_work_item:{type:1,values:[{relation_uuid:"<CAPTURED_RELATION_UUID>",parent_node_key:"<NODE_KEY>",parent_work_item_id:<PARENT_ID>}]}
    })});
  return JSON.stringify({status:res.status, body:await res.text()});
})();
```
Success = `{"code":0,...}`. A `401` with code `10022 "CSRF Failed"` means the CSRF header name or value is wrong — re-check the captured header name (it is the Meego-specific one, NOT `x-csrf-token`) and the cookie value.

**Troubleshooting the in-page fetch (the Meego SPA is heavy):**
- **Don't `await` the fetch inside the `javascript_tool` eval.** On a busy/loading page the eval's await can exceed the MCP's ~45s `Runtime.evaluate` cap and report "renderer frozen", even though the request would have succeeded. Instead **fire-and-store**: kick off the fetch, write its result to a global (`window.__bindResult = ...` in a `.then()`), return immediately, then **poll** that global with a separate tiny eval (`window.__bindResult`) every few seconds.
- **If the card page itself is stuck** (`document.readyState` stays `"loading"`, evals keep timing out), don't fight it: open a **fresh tab on the same host** (`tabs_create_mcp` → `navigate` to e.g. `https://<host>/`, a lighter page that reaches `readyState:"complete"`) and fire the fetch from there. The session cookie + CSRF are shared across the whole host, so the bind still works; close the helper tab after.

### B4. Verify
`navigate` to refresh the parent page, open the node, confirm the node's child count went up (or `meegle` read-back of the parent's rollup field shows the child).

## Notes / guardrails
- `relation_uuid` is space/template-level (stable across cards in the same space) — cache it in the project config after capturing, but re-capture if it ever 401/404s.
- Everything space-specific (host, project_key, parent_type, child_type, node keys, relation_uuid, csrf cookie/header) is **discovered per user** — keep it out of any shared default.
- Delete of cards is still web-UI-only; the CLI cannot delete.
