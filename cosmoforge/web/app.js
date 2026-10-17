"use strict";
let DATA = null, LIVE = false, TITLE = "Cosmos", PROVIDER = null;
const API_BASE = (window.COSMOS_API_BASE || "").replace(/\/$/, "");

const KIND_COLORS = {
  root:"#f5c451", bigbang:"#ff8a3d", epoch:"#d9b64a",
  universe:"#5b8def", planet:"#3fbf7f", event:"#c678dd"
};
const KIND_LABEL = {
  root:"Cosmos", bigbang:"Origin", epoch:"Epoch",
  universe:"Universe", planet:"Planet", event:"Event"
};
const CAN_EXPAND = {root:1, bigbang:1, universe:1, planet:1, event:1, epoch:0};
const ROW = 38, GAP = 62, MINW = 150, PADX = 16, CHAR = 7.7, NODEH = 26;
const SEC_PER_YEAR = 31557600;

const svg = document.getElementById("map");
const viewport = document.getElementById("viewport");
const linksG = document.getElementById("links");
const nodesG = document.getElementById("nodes");
const panel = document.getElementById("panel");
const searchBox = document.getElementById("search");
const zoomSlider = document.getElementById("zoom");
const zoomVal = document.getElementById("zoomval");
const tl = document.getElementById("timeline");
const tlBody = document.getElementById("tl-body");
const tlSvg = document.getElementById("tl");
const toast = document.getElementById("toast");
const seedInput = document.getElementById("seed");
const archiveModal = document.getElementById("archive-modal");
const archiveName = document.getElementById("archive-name");
const archiveList = document.getElementById("archive-list");
const archiveStatus = document.getElementById("archive-status");

let collapsed = new Set();
let query = "";
let scale = 1, tx = 40, ty = 40;
let bounds = { w: 1200, h: 800 };
let byId = new Map();
let parentIndex = new Map();
let selectedId = null;
let knownIds = new Set();
let freshIds = new Set();
let smoothTimer = 0;
let busy = null;
let lastTap = { t: 0, x: 0, y: 0 };
let evolving = false, evolveTimer = 0, evolveBusy = false, evolveCount = 0;
const tlPlay = { active:false, raf:0, t:0, maxAge:1, x:null, top:0, bottom:0,
                 dots:[], bars:[], head:null, clock:null };

/* ------------------------------------------------------------------ */
/* helpers                                                             */
/* ------------------------------------------------------------------ */
function sevColor(sev){
  const s = Math.max(0, Math.min(1, Number(sev) || 0.5));
  return `hsl(${285 - 15 * s}, 62%, ${62 - 12 * s}%)`;
}
function nodeColor(n){
  if (n.kind === "event") return sevColor((n.meta && n.meta.severity) || 0.5);
  return KIND_COLORS[n.kind] || "#9aa4bb";
}
function labelText(n){
  const icon = { root:"✦", bigbang:"✷", epoch:"·", universe:"◆", planet:"●", event:"▲" }[n.kind] || "•";
  return icon + "  " + n.label;
}
function nodeWidth(n){ return Math.max(MINW, labelText(n).length * CHAR + PADX * 2 + 6); }
function escapeHtml(s){
  return String(s == null ? "" : s).replace(/[&<>"]/g, c =>
    ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[c]));
}
function pathD(x1, y1, x2, y2){
  const mx = (x1 + x2) / 2;
  return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
}
function walkAll(node, depth, fn){
  fn(node, depth);
  (node.children || []).forEach(c => walkAll(c, depth + 1, fn));
}
function showToast(msg){
  toast.textContent = msg;
  toast.classList.add("show");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toast.classList.remove("show"), 2600);
}
function syncChrome(){
  const bar = document.getElementById("bar");
  if (bar) document.documentElement.style.setProperty("--barh", bar.offsetHeight + "px");
}
window.addEventListener("resize", syncChrome);

/* ------------------------------------------------------------------ */
/* mind map                                                            */
/* ------------------------------------------------------------------ */
function computeLayout(){
  const vis = [];
  let cursor = 0;
  const depthWidth = {};
  let maxDepth = 0;
  byId = new Map();

  function visit(node, depth){
    node._depth = depth;
    node._w = nodeWidth(node);
    byId.set(node.id, node);
    depthWidth[depth] = Math.max(depthWidth[depth] || 0, node._w);
    maxDepth = Math.max(maxDepth, depth);
    const folded = collapsed.has(node.id);
    const kids = (!folded && node.children && node.children.length) ? node.children : [];
    node._kids = kids;
    vis.push(node);
    if (!kids.length){ node._y = cursor; cursor += ROW; }
    else {
      kids.forEach(k => visit(k, depth + 1));
      node._y = (kids[0]._y + kids[kids.length - 1]._y) / 2;
    }
  }
  visit(DATA, 0);

  const offset = [];
  let x = 0;
  for (let d = 0; d <= maxDepth; d++){ offset[d] = x; x += (depthWidth[d] || MINW) + GAP; }
  vis.forEach(n => { n._x = offset[n._depth]; });
  bounds = { w: Math.max(x - GAP, 400), h: Math.max(cursor, 200) };
  return vis;
}

function render(){
  parentIndex = new Map();
  walkAll(DATA, 0, n => (n.children || []).forEach(c => parentIndex.set(c.id, n.id)));

  const vis = computeLayout();
  const q = query.trim().toLowerCase();
  const hits = new Set();
  if (q){
    vis.forEach(n => {
      if ((n.label + " " + (n.detail || "")).toLowerCase().indexOf(q) >= 0) hits.add(n.id);
    });
  }
  const prev = knownIds;
  const linkParts = [], nodeParts = [];
  freshIds = new Set();
  let enterIndex = 0;
  vis.forEach(n => {
    const dim = q && !hits.has(n.id) ? " dim" : "";
    const hit = hits.has(n.id) ? " hit" : "";
    const isNew = !prev.has(n.id);
    if (isNew) freshIds.add(n.id);
    const delay = isNew ? Math.min(enterIndex++ * 34, 260) : 0;
    const enter = isNew ? " enter" : "";
    (n._kids || []).forEach(k => {
      const isNewLink = !prev.has(k.id);
      linkParts.push(`<path class="link${isNewLink ? " enter" : ""}" data-parent="${escapeHtml(n.id)}" data-child="${escapeHtml(k.id)}" d="${pathD(n._x + n._w, n._y, k._x, k._y)}" stroke="${nodeColor(k)}" stroke-opacity="0.55" pathLength="1"${isNewLink ? ` style="--d:${delay}ms"` : ""}/>`);
    });
    const color = nodeColor(n);
    const textColor = (n.kind === "root" || n.kind === "bigbang") ? "#0b0f19" : "#08111f";
    nodeParts.push(
      `<g class="node${dim}${hit}${enter}" data-id="${escapeHtml(n.id)}" transform="translate(${n._x},${n._y})"${isNew ? ` style="--d:${delay}ms"` : ""}>` +
      `<rect x="0" y="${-NODEH/2}" width="${n._w}" height="${NODEH}" rx="9" fill="${color}"/>` +
      `<text x="${PADX}" y="1" fill="${textColor}">${escapeHtml(labelText(n))}</text>` +
      `</g>`
    );
  });
  linksG.innerHTML = linkParts.join("");
  nodesG.innerHTML = nodeParts.join("");
  knownIds = new Set(vis.map(n => n.id));
  applyTransform();
  syncZoomUI();
  if (!tl.classList.contains("hidden")) renderTimeline();
}

function applyTransform(smoothMotion){
  if (smoothMotion){
    viewport.classList.add("smooth");
    clearTimeout(smoothTimer);
    smoothTimer = setTimeout(() => viewport.classList.remove("smooth"), 470);
  }
  viewport.setAttribute("transform", `translate(${tx},${ty}) scale(${scale})`);
}
function stopSmooth(){
  viewport.classList.remove("smooth");
  clearTimeout(smoothTimer);
}
function syncZoomUI(){
  zoomSlider.value = Math.round(scale * 100);
  zoomVal.textContent = Math.round(scale * 100) + "%";
}
function visibleCenter(){
  const rect = svg.getBoundingClientRect();
  const panelH = tl.classList.contains("hidden") ? 0 : tl.offsetHeight;
  return { cx: rect.width / 2, cy: Math.max(60, (rect.height - panelH) / 2) };
}
function setScale(next, cx, cy, animate){
  next = Math.min(3.5, Math.max(0.08, next));
  if (cx == null){ const c = visibleCenter(); cx = c.cx; cy = c.cy; }
  tx = cx - (cx - tx) * (next / scale);
  ty = cy - (cy - ty) * (next / scale);
  scale = next;
  applyTransform(!!animate); syncZoomUI();
}
function fit(animate){
  const c = visibleCenter();
  const s = Math.min((svg.getBoundingClientRect().width - 90) / bounds.w,
                     (c.cy * 2 - 60) / bounds.h, 1.6);
  scale = Math.max(0.08, s);
  tx = Math.max(20, (svg.getBoundingClientRect().width - bounds.w * scale) / 2);
  ty = Math.max(20, c.cy - bounds.h * scale / 2);
  applyTransform(animate !== false); syncZoomUI();
}
function resetZoom(){
  scale = 1;
  const c = visibleCenter();
  tx = 40; ty = Math.max(20, c.cy - bounds.h / 2);
  applyTransform(true); syncZoomUI();
}
function centerOnNode(id, animate){
  const node = byId.get(id);
  if (!node) return;
  const c = visibleCenter();
  tx = c.cx - (node._x + node._w / 2) * scale;
  ty = c.cy - node._y * scale;
  applyTransform(!!animate);
}
function flashNode(id){
  let el = null;
  try { el = document.querySelector(`g.node[data-id="${CSS.escape(id)}"]`); }
  catch (_) { el = document.querySelector(`g.node[data-id="${String(id).replace(/"/g, '\\"')}"]`); }
  if (!el) return;
  el.classList.add("hit");
  clearTimeout(flashNode._t);
  flashNode._t = setTimeout(() => el.classList.remove("hit"), 700);
}
function highlightChain(id){
  const chain = new Set(), links = new Set();
  let cur = id;
  while (cur){
    chain.add(cur);
    const parent = parentIndex.get(cur);
    if (!parent) break;
    links.add(parent + ">" + cur);
    cur = parent;
  }
  document.querySelectorAll("g.node").forEach(el =>
    el.classList.toggle("active", chain.has(el.getAttribute("data-id"))));
  document.querySelectorAll("path.link").forEach(el =>
    el.classList.toggle("active",
      links.has(el.getAttribute("data-parent") + ">" + el.getAttribute("data-child"))));
}
function clearHighlight(){
  document.querySelectorAll("g.node.active, path.link.active")
    .forEach(el => el.classList.remove("active"));
}
function revealNode(id){
  let cur = id;
  const path = [];
  while (cur){ path.push(cur); cur = parentIndex.get(cur); }
  path.forEach(p => collapsed.delete(p));
  render();
  const node = byId.get(id);
  if (!node) return;
  centerOnNode(id, true);
  clearHighlight(); highlightChain(id);
  selectedId = id;
  showPanel(node);
}
function findParentId(id){ return parentIndex.get(id); }

/* ------------------------------------------------------------------ */
/* details panel                                                       */
/* ------------------------------------------------------------------ */
function setStatus(msg, working){
  const stat = document.getElementById("pstat");
  if (!stat) return;
  stat.innerHTML = escapeHtml(msg) +
    (working ? ' <span class="dot"></span><span class="dot"></span><span class="dot"></span>' : "");
}
function showPanel(node){
  if (!node) return;
  selectedId = node.id;
  const rows = Object.keys(node.meta || {}).map(k =>
    `<tr><td>${escapeHtml(k)}</td><td>${escapeHtml(node.meta[k])}</td></tr>`).join("");
  const working = !!(LIVE && busy && busy.id === node.id);
  let actions = "";
  if (LIVE){
    const canExpand = CAN_EXPAND[node.kind] !== 0;
    actions = `<div class="actions">
      <button data-pact="expand" data-id="${escapeHtml(node.id)}" ${canExpand && !working ? "" : "disabled"}>✨ 展开子节点</button>
      <button data-pact="continue" data-id="${escapeHtml(node.id)}" ${working ? "disabled" : ""}>✍ 续写叙事</button>
    </div><div class="status" id="pstat">` +
      (working ? escapeHtml(busy.status) +
        ' <span class="dot"></span><span class="dot"></span><span class="dot"></span>' : "") +
      `</div>`;
  }
  panel.innerHTML =
    `<span class="close" data-close="1">✕</span>` +
    `<div class="kind">${escapeHtml(KIND_LABEL[node.kind] || node.kind)}</div>` +
    `<h2 style="color:${nodeColor(node)}">${escapeHtml(node.label)}</h2>` +
    `<p id="pdetail">${escapeHtml(node.detail || "")}</p>` +
    (rows ? `<table>${rows}</table>` : "") + actions;
  panel.classList.remove("hidden");
}
function parseSse(block){
  let event = "message", data = "";
  block.split("\n").forEach(line => {
    if (line.indexOf("event:") === 0) event = line.slice(6).trim();
    else if (line.indexOf("data:") === 0) data += line.slice(5).trim();
  });
  let parsed = {};
  try { parsed = JSON.parse(data || "{}"); } catch (_) { parsed = {}; }
  return { event: event, data: parsed };
}
async function consumeStream(res, id, node, base){
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let delta = "";
  const applyDelta = () => {
    node.detail = base ? base + "\n\n" + delta : delta;
    const p = document.getElementById("pdetail");
    if (p){ p.textContent = node.detail; p.classList.add("streaming"); }
  };
  while (true){
    const chunk = await reader.read();
    if (chunk.done) break;
    buffer += decoder.decode(chunk.value, { stream: true });
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0){
      const block = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      const msg = parseSse(block);
      if (msg.event === "phase"){
        if (busy){ busy.status = msg.data.message || "生成中"; setStatus(busy.status, true); }
      } else if (msg.event === "delta"){
        delta += String(msg.data.text || "");
        applyDelta();
      } else if (msg.event === "node"){
        node.children = (node.children || []).concat([msg.data]);
        collapsed.delete(id);
        if (busy) busy.status = "新分支正在生长";
        render();
        showPanel(byId.get(id) || node);
        const p = document.getElementById("pdetail");
        if (p) p.classList.add("streaming");
        setStatus(busy ? busy.status : "生成中", true);
        flashNode(msg.data.id);
      } else if (msg.event === "done"){
        if (msg.data.narrative) node.detail = msg.data.narrative;
      } else if (msg.event === "error"){
        throw new Error(msg.data.error || "生成失败");
      }
    }
  }
}
async function callExpand(id, action, btn){
  const node = byId.get(id);
  if (!node || (busy && busy.id === id)) return;
  const base = node.detail || "";
  busy = { id: id, action: action,
           status: action === "expand" ? "正在生成新的分支" : "正在续写叙事" };
  panel.classList.add("working");
  showPanel(node);
  let streamed = false;
  try {
    let res = null;
    try {
      res = await fetch(API_BASE + "/api/expand/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: id, action: action })
      });
      if (!res.ok || !res.body) res = null;
    } catch (_) { res = null; }

    if (res && res.body){
      streamed = true;
      await consumeStream(res, id, node, base);
    } else {
      const plain = await fetch(API_BASE + "/api/expand", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: id, action: action })
      });
      const data = await plain.json();
      if (!plain.ok) throw new Error(data.error || ("HTTP " + plain.status));
      if (data.narrative) node.detail = data.narrative;
      if (Array.isArray(data.children) && data.children.length){
        node.children = (node.children || []).concat(data.children);
        collapsed.delete(id);
      }
      render();
    }
    busy = null;
    panel.classList.remove("working");
    showPanel(byId.get(id) || node);
    setStatus(streamed ? "实时生成完成 ✓" : "完成 ✓");
    centerOnNode(id, true);
    flashNode(id);
    showToast(streamed ? "实时生成完成" : "生成完成");
  } catch (err){
    busy = null;
    panel.classList.remove("working");
    showPanel(byId.get(id) || node);
    setStatus("失败：" + err.message);
    showToast("LLM 调用失败：" + err.message);
  }
}

/* ------------------------------------------------------------------ */
/* seed regeneration + archives                                        */
/* ------------------------------------------------------------------ */
async function regenerateFromSeed(){
  if (!LIVE){ showToast("按种子生成需要 serve 模式"); return; }
  const raw = seedInput ? seedInput.value.trim() : "";
  const btn = document.querySelector('[data-act="regenerate"]');
  if (btn) btn.disabled = true;
  showToast(raw ? "正在按种子 " + raw + " 生成…" : "正在随机生成新宇宙…");
  const wasEvolving = evolving;
  try {
    const body = raw ? { seed: raw } : {};
    const res = await fetch(API_BASE + "/api/regenerate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
    stopEvolving();
    applyPayload(data);
    showToast("已生成新宇宙 · 种子 " + data.seed);
    if (wasEvolving && providerIsMock(PROVIDER)) startEvolving(false);
  } catch (err){
    showToast("生成失败：" + err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}
function archiveSetStatus(message){
  if (archiveStatus) archiveStatus.textContent = message || "";
}
function fmtArchiveDate(iso){
  if (!iso) return "";
  const date = new Date(iso);
  if (isNaN(date.getTime())) return iso;
  return date.toLocaleString();
}
function openArchive(){
  if (!LIVE){ showToast("存档需要 serve 模式"); return; }
  archiveModal.classList.remove("hidden");
  document.getElementById("archive-btn").classList.add("on");
  loadArchiveList();
  setTimeout(() => { if (archiveName) archiveName.focus(); }, 60);
}
function closeArchive(){
  archiveModal.classList.add("hidden");
  document.getElementById("archive-btn").classList.remove("on");
}
function renderArchiveList(items){
  if (!archiveList) return;
  if (!items.length){
    archiveList.innerHTML = '<div class="empty">还没有存档</div>';
    return;
  }
  archiveList.innerHTML = items.map(a => {
    const seed = (a.seed == null ? "—" : a.seed);
    const meta = "种子 " + seed +
      (a.nodes ? " · " + a.nodes + " 节点" : "") +
      (a.created ? " · " + fmtArchiveDate(a.created) : "");
    return `<div class="archive-item">
      <div class="archive-main"><b>${escapeHtml(a.name || a.id)}</b>
        <span>${escapeHtml(meta)}</span></div>
      <div class="archive-actions">
        <button data-archive-load="${escapeHtml(a.id)}">读取</button>
        <a href="${API_BASE}/api/archive?id=${encodeURIComponent(a.id)}"
           download="${escapeHtml(a.id)}.json">下载</a>
      </div></div>`;
  }).join("");
}
async function loadArchiveList(){
  archiveSetStatus("读取存档列表…");
  try {
    const res = await fetch(API_BASE + "/api/archives", { cache: "no-store" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
    const items = Array.isArray(data.archives) ? data.archives : [];
    renderArchiveList(items);
    archiveSetStatus(items.length ? "共 " + items.length + " 个存档" : "");
  } catch (err){
    archiveSetStatus("读取失败：" + err.message);
    if (archiveList) archiveList.innerHTML = '<div class="empty">读取失败</div>';
  }
}
async function saveArchive(){
  const btn = document.getElementById("archive-save");
  if (btn) btn.disabled = true;
  archiveSetStatus("正在保存…");
  try {
    const res = await fetch(API_BASE + "/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: archiveName ? archiveName.value.trim() : "" })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
    archiveSetStatus("已保存 · " + data.name);
    if (archiveName) archiveName.value = "";
    showToast("存档已保存：" + data.name);
    await loadArchiveList();
  } catch (err){
    archiveSetStatus("保存失败：" + err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}
async function loadArchive(archiveId){
  const wasEvolving = evolving;
  archiveSetStatus("正在读取存档…");
  try {
    const res = await fetch(API_BASE + "/api/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: archiveId })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
    stopEvolving();
    applyPayload(data);
    closeArchive();
    showToast("已读取存档 · 种子 " + data.seed);
    if (wasEvolving && providerIsMock(PROVIDER)) startEvolving(false);
  } catch (err){
    archiveSetStatus("读取失败：" + err.message);
  }
}

/* ------------------------------------------------------------------ */
/* autonomous evolution (dynamic mode)                                 */
/* ------------------------------------------------------------------ */
function providerIsMock(p){
  if (!p) return false;
  if (p.provider === "mock") return true;
  return Array.isArray(p.chain) && p.chain.some(providerIsMock);
}
function nodeCount(){
  let count = 0;
  walkAll(DATA, 0, () => { count += 1; });
  return count;
}
function evolveTarget(){
  const pools = { planet: [], event: [], universe: [] };
  const visible = [], all = [];
  walkAll(DATA, 0, n => {
    if (!pools[n.kind] || CAN_EXPAND[n.kind] === 0) return;
    all.push(n);
    if (byId.has(n.id)) visible.push(n);
  });
  const source = visible.length ? visible : all;
  source.forEach(n => pools[n.kind].push(n));
  const pool = pools.planet.concat(pools.event, pools.event, pools.universe);
  return pool.length ? pool[Math.floor(Math.random() * pool.length)] : null;
}
function updateEvolveUI(){
  const btn = document.getElementById("evolve-btn");
  if (!btn) return;
  btn.classList.toggle("on", evolving);
  btn.textContent = evolving ? "● 动态演化" : "动态演化";
  btn.title = evolving
    ? "正在持续生成新分支 · 点击暂停（本次已生长 " + evolveCount + "）"
    : "持续自动生成新分支";
}
function scheduleEvolve(delay){
  clearTimeout(evolveTimer);
  if (!evolving) return;
  evolveTimer = setTimeout(evolveOnce, delay == null ? 2200 + Math.random() * 2400 : delay);
}
function startEvolving(auto){
  if (!LIVE){ showToast("动态演化需要 serve 模式"); return; }
  if (evolving) return;
  evolving = true;
  updateEvolveUI();
  showToast(auto ? "已开启动态演化（mock 自动生成）" : "动态演化已开启");
  scheduleEvolve(600);
}
function stopEvolving(message){
  evolving = false;
  clearTimeout(evolveTimer);
  evolveTimer = 0;
  updateEvolveUI();
  if (message) showToast(message);
}
function toggleEvolving(){
  if (evolving) stopEvolving("动态演化已暂停");
  else startEvolving(false);
}
async function evolveOnce(){
  if (!evolving) return;
  if (document.hidden){ scheduleEvolve(1500); return; }
  if (tlPlay.active){ scheduleEvolve(1400); return; }
  if (evolveBusy){ scheduleEvolve(800); return; }
  if (nodeCount() > 420){ stopEvolving("宇宙已足够庞大，动态演化停止"); return; }
  const node = evolveTarget();
  if (!node){ stopEvolving("没有可展开的节点了"); return; }

  evolveBusy = true;
  const action = Math.random() < 0.28 ? "continue" : "expand";
  const base = node.detail || "";
  let delta = "";
  try {
    const res = await fetch(API_BASE + "/api/expand/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: node.id, action: action })
    });
    if (!res.ok || !res.body) throw new Error("HTTP " + res.status);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let added = 0;
    while (true){
      const chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });
      let cut;
      while ((cut = buffer.indexOf("\n\n")) >= 0){
        const block = buffer.slice(0, cut);
        buffer = buffer.slice(cut + 2);
        const msg = parseSse(block);
        if (msg.event === "delta"){
          delta += String(msg.data.text || "");
          node.detail = base ? base + "\n\n" + delta : delta;
          if (selectedId === node.id){
            const p = document.getElementById("pdetail");
            if (p){ p.textContent = node.detail; p.classList.add("streaming"); }
          }
        } else if (msg.event === "node"){
          node.children = (node.children || []).concat([msg.data]);
          collapsed.delete(node.id);
          added += 1;
          render();
          flashNode(msg.data.id);
        } else if (msg.event === "done"){
          if (msg.data.narrative) node.detail = msg.data.narrative;
        } else if (msg.event === "error"){
          throw new Error(msg.data.error || "生成失败");
        }
      }
    }
    if (added) evolveCount += added;
    if (selectedId === node.id) showPanel(byId.get(node.id) || node);
    render();
    updateEvolveUI();
    if (added) showToast("新生长 " + added + " 个节点 · " + node.label);
  } catch (err){
    stopEvolving("动态演化暂停：" + err.message);
  } finally {
    evolveBusy = false;
    if (evolving) scheduleEvolve();
  }
}

/* ------------------------------------------------------------------ */
/* mind map interactions                                               */
/* ------------------------------------------------------------------ */
function toggle(node){
  if (node.children && node.children.length){
    if (collapsed.has(node.id)) collapsed.delete(node.id);
    else collapsed.add(node.id);
  }
  render();
  showPanel(node);
}
panel.addEventListener("click", e => {
  if (e.target.getAttribute("data-close")){ panel.classList.add("hidden"); clearHighlight(); return; }
  const act = e.target.getAttribute && e.target.getAttribute("data-pact");
  if (act) callExpand(e.target.getAttribute("data-id"), act, e.target);
});
nodesG.addEventListener("mouseover", e => {
  const g = e.target.closest("g.node");
  if (g) highlightChain(g.getAttribute("data-id"));
});
nodesG.addEventListener("mouseout", e => { if (e.target.closest("g.node")) clearHighlight(); });

/* one-finger pan, two-finger pinch, tap to toggle, double-tap to zoom */
const pointers = new Map();
let gesture = null;
function endPointer(e){
  if (!pointers.has(e.pointerId)) return;
  const g = gesture;
  pointers.delete(e.pointerId);
  const tapped = g && g.kind === "pan" && !g.moved && Date.now() - g.t < 700;
  if (tapped && pointers.size === 0){
    const el = g.target && g.target.closest ? g.target.closest("g.node") : null;
    if (el){
      const node = byId.get(el.getAttribute("data-id"));
      if (node) toggle(node);
    } else {
      const now = Date.now();
      if (now - lastTap.t < 330 &&
          Math.hypot(e.clientX - lastTap.x, e.clientY - lastTap.y) < 42){
        const r = svg.getBoundingClientRect();
        setScale(scale * 1.7, e.clientX - r.left, e.clientY - r.top, true);
        lastTap.t = 0;
      } else {
        lastTap = { t: now, x: e.clientX, y: e.clientY };
        clearHighlight();
      }
    }
  }
  if (pointers.size === 0){ gesture = null; svg.classList.remove("dragging"); }
  else if (pointers.size === 1){
    const p = [...pointers.values()][0];
    gesture = { kind: "pan", sx: p.x, sy: p.y, lx: p.x, ly: p.y,
                moved: true, target: null, t: Date.now() };
  }
}
svg.addEventListener("pointerdown", e => {
  if (e.pointerType === "mouse" && e.button !== 0) return;
  stopSmooth();
  try { svg.setPointerCapture(e.pointerId); } catch (_) {}
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (pointers.size === 1){
    gesture = { kind: "pan", sx: e.clientX, sy: e.clientY, lx: e.clientX,
                ly: e.clientY, moved: false, target: e.target, t: Date.now() };
  } else if (pointers.size === 2){
    const pts = [...pointers.values()];
    const r = svg.getBoundingClientRect();
    gesture = { kind: "pinch",
                d: Math.max(1, Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y)),
                s0: scale, tx0: tx, ty0: ty,
                cx: (pts[0].x + pts[1].x) / 2 - r.left,
                cy: (pts[0].y + pts[1].y) / 2 - r.top,
                moved: true, target: null, t: Date.now() };
  }
});
svg.addEventListener("pointermove", e => {
  if (!pointers.has(e.pointerId)) return;
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (!gesture) return;
  if (gesture.kind === "pan" && pointers.size === 1){
    if (Math.hypot(e.clientX - gesture.sx, e.clientY - gesture.sy) > 7) gesture.moved = true;
    if (gesture.moved){
      tx += e.clientX - gesture.lx;
      ty += e.clientY - gesture.ly;
      applyTransform();
      svg.classList.add("dragging");
    }
    gesture.lx = e.clientX; gesture.ly = e.clientY;
  } else if (gesture.kind === "pinch" && pointers.size >= 2){
    const pts = [...pointers.values()].slice(0, 2);
    const r = svg.getBoundingClientRect();
    const d = Math.max(1, Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y));
    const cx = (pts[0].x + pts[1].x) / 2 - r.left;
    const cy = (pts[0].y + pts[1].y) / 2 - r.top;
    const next = Math.min(3.5, Math.max(0.08, gesture.s0 * d / gesture.d));
    scale = next;
    tx = cx - (gesture.cx - gesture.tx0) * (next / gesture.s0);
    ty = cy - (gesture.cy - gesture.ty0) * (next / gesture.s0);
    applyTransform(); syncZoomUI();
  }
});
svg.addEventListener("pointerup", endPointer);
svg.addEventListener("pointercancel", endPointer);
svg.addEventListener("wheel", e => {
  e.preventDefault();
  stopSmooth();
  const rect = svg.getBoundingClientRect();
  setScale(scale * (e.deltaY < 0 ? 1.12 : 0.89), e.clientX - rect.left, e.clientY - rect.top);
}, { passive: false });

window.addEventListener("keydown", e => {
  const tag = (e.target.tagName || "").toLowerCase();
  if (tag === "input" || tag === "textarea") return;
  if (e.key === "+" || e.key === "=") setScale(scale * 1.15, null, null, true);
  else if (e.key === "-" || e.key === "_") setScale(scale / 1.15, null, null, true);
  else if (e.key === "0") resetZoom();
  else if (e.key === "f" || e.key === "F") fit();
});

document.getElementById("bar").addEventListener("click", e => {
  const act = e.target.getAttribute && e.target.getAttribute("data-act");
  if (!act) return;
  if (act === "in") setScale(scale * 1.2, null, null, true);
  else if (act === "out") setScale(scale / 1.2, null, null, true);
  else if (act === "fit") fit();
  else if (act === "reset") resetZoom();
  else if (act === "expandall"){ collapsed.clear(); render(); }
  else if (act === "collapse"){
    collapsed.clear();
    walkAll(DATA, 0, (n, d) => { if (n.children && n.children.length && d >= 1) collapsed.add(n.id); });
    render();
  } else if (act === "evolve") toggleEvolving();
  else if (act === "regenerate") regenerateFromSeed();
  else if (act === "archive") openArchive();
  else if (act === "timeline") toggleTimeline();
  else if (act === "svg") exportSvg();
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) clearTimeout(evolveTimer);
  else if (evolving) scheduleEvolve(700);
});

if (seedInput){
  seedInput.addEventListener("keydown", e => {
    if (e.key === "Enter"){ e.preventDefault(); regenerateFromSeed(); }
  });
}
document.getElementById("archive-save").addEventListener("click", saveArchive);
document.getElementById("archive-refresh").addEventListener("click", loadArchiveList);
archiveModal.addEventListener("click", e => {
  if (e.target === archiveModal || e.target.getAttribute("data-archive-close")) closeArchive();
});
archiveList.addEventListener("click", e => {
  const id = e.target.getAttribute && e.target.getAttribute("data-archive-load");
  if (id) loadArchive(id);
});
window.addEventListener("keydown", e => {
  if (e.key === "Escape" && !archiveModal.classList.contains("hidden")) closeArchive();
});
zoomSlider.addEventListener("input", () => {
  stopSmooth();
  setScale(Number(zoomSlider.value) / 100, null, null, false);
});
searchBox.addEventListener("input", () => { query = searchBox.value; render(); });

function exportSvg(){
  const clone = svg.cloneNode(true);
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("viewBox", `0 0 ${Math.round(bounds.w + 80)} ${Math.round(bounds.h + 80)}`);
  clone.setAttribute("width", Math.round(bounds.w + 80));
  clone.setAttribute("height", Math.round(bounds.h + 80));
  const vp = clone.querySelector("#viewport");
  if (vp){
    vp.setAttribute("transform", "translate(40,40) scale(1)");
    const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bg.setAttribute("x", "0"); bg.setAttribute("y", "0");
    bg.setAttribute("width", "100%"); bg.setAttribute("height", "100%");
    bg.setAttribute("fill", "#0b0f19");
    vp.parentNode.insertBefore(bg, vp);
  }
  const blob = new Blob([clone.outerHTML], { type: "image/svg+xml" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "cosmos-mindmap.svg";
  a.click();
  URL.revokeObjectURL(a.href);
}

/* ------------------------------------------------------------------ */
/* timeline                                                            */
/* ------------------------------------------------------------------ */
function toggleTimeline(){
  const hidden = tl.classList.toggle("hidden");
  document.getElementById("tl-toggle").classList.toggle("on", !hidden);
  if (!hidden) renderTimeline();
  else stopPlayback(true);
}
function eventTree(node){
  const out = [];
  (node.children || []).forEach(c => {
    if (c.kind === "event"){ out.push(c); out.push(...eventTree(c)); }
  });
  return out;
}
function collectTimeline(){
  const universes = (DATA.children || []).filter(c => c.kind === "universe");
  const bb = (DATA.children || []).find(c => c.kind === "bigbang");
  let maxAge = 0;
  universes.forEach(u => { maxAge = Math.max(maxAge, Number((u.meta || {}).age_gyr || 0)); });
  maxAge = Math.ceil(Math.max(maxAge, 1));

  const rows = [];
  universes.forEach(u => {
    const uAge = Number((u.meta || {}).age_gyr || maxAge);
    rows.push({ label: u.label, id: u.id, barTo: uAge, bar: "#5b8def", events: [] });
    const uEvents = eventTree(u);
    if (uEvents.length)
      rows.push({ label: "宇宙事件", id: u.id, barTo: 0, bar: null, events: uEvents });
    (u.children || []).filter(c => c.kind === "planet").forEach(p => {
      rows.push({ label: p.label, id: p.id, barTo: uAge, bar: "#3fbf7f",
                  events: eventTree(p) });
    });
  });
  const epochs = bb ? (bb.children || []).filter(c => c.kind === "epoch") : [];
  return { rows, maxAge, epochs };
}
function niceStep(maxAge, plotW){
  const candidates = [0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 50];
  for (const s of candidates){ if (plotW / (maxAge / s) >= 64) return s; }
  return 100;
}
function updatePlayhead(t, silent){
  if (!tlPlay.head || !tlPlay.x) return;
  const x = tlPlay.x;
  const px = x(t);
  const head = tlPlay.head;
  head.classList.remove("hidden");
  head.querySelector("line").setAttribute("x1", px);
  head.querySelector("line").setAttribute("x2", px);
  head.querySelector("line").setAttribute("y1", tlPlay.top - 10);
  head.querySelector("line").setAttribute("y2", tlPlay.bottom + 2);
  const dot = head.querySelector("circle");
  dot.setAttribute("cx", px); dot.setAttribute("cy", tlPlay.top - 10);
  const label = head.querySelector("text");
  label.setAttribute("x", px); label.setAttribute("y", tlPlay.top - 16);
  label.setAttribute("text-anchor", px > tlPlay.x(tlPlay.maxAge) - 60 ? "end" : "middle");
  label.textContent = t.toFixed(2) + " Gyr";
  const clock = document.getElementById("tl-clock");
  if (clock) clock.textContent = t.toFixed(2) + " Gyr";
  tlPlay.dots.forEach(g => {
    const age = Number(g.getAttribute("data-age") || 0);
    const on = age <= t + 1e-9;
    g.classList.toggle("lit", on);
    g.classList.toggle("faded", !on);
    if (on && !g.__lit && !silent) flashNode(g.getAttribute("data-node"));
    g.__lit = on;
  });
  tlPlay.bars.forEach(rect => {
    const to = Number(rect.getAttribute("data-bar-to") || 0);
    rect.setAttribute("width", Math.max(2, x(Math.min(t, to)) - x(0)));
  });
}
function stopPlayback(reset){
  if (tlPlay.raf) cancelAnimationFrame(tlPlay.raf);
  tlPlay.raf = 0;
  tlPlay.active = false;
  const btn = document.getElementById("tl-play");
  if (btn) btn.textContent = "▶ 播放";
  if (reset && tlPlay.head){
    tlPlay.head.classList.add("hidden");
    updatePlayhead(tlPlay.maxAge, true);
  }
  tlPlay.dots.forEach(g => { g.__lit = false; });
}
function playTimeline(){
  if (tl.classList.contains("hidden")){
    tl.classList.remove("hidden");
    document.getElementById("tl-toggle").classList.add("on");
    renderTimeline();
  }
  if (tlPlay.active){ stopPlayback(true); return; }
  if (!tlPlay.head) renderTimeline();
  const btn = document.getElementById("tl-play");
  if (btn) btn.textContent = "⏸ 暂停";
  tlPlay.active = true;
  tlPlay.dots.forEach(g => { g.__lit = false; });
  updatePlayhead(0, true);
  const duration = Math.min(15000, Math.max(5200, tlPlay.maxAge * 1300));
  const started = performance.now();
  function frame(now){
    if (!tlPlay.active) return;
    const p = Math.min(1, (now - started) / duration);
    updatePlayhead(p * tlPlay.maxAge, false);
    if (p < 1){
      tlPlay.raf = requestAnimationFrame(frame);
    } else {
      tlPlay.active = false; tlPlay.raf = 0;
      if (btn) btn.textContent = "▶ 重播";
      setTimeout(() => { if (!tlPlay.active && tlPlay.head) tlPlay.head.classList.add("hidden"); }, 1000);
    }
  }
  tlPlay.raf = requestAnimationFrame(frame);
}
function renderTimeline(){
  if (tlPlay.active) stopPlayback(false);
  const { rows, maxAge, epochs } = collectTimeline();
  const box = tlBody.getBoundingClientRect();
  const W = Math.max(320, Math.floor(box.width));
  const gutter = Math.min(176, Math.max(90, Math.round(W * 0.24)));
  const padR = 22, stripH = 60, rowH = 24;
  const H = stripH + 10 + rows.length * rowH + 26;
  tlSvg.setAttribute("width", W); tlSvg.setAttribute("height", H);
  tlSvg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const plotW = Math.max(80, W - gutter - padR);
  const x = t => gutter + (Math.min(Math.max(t, 0), maxAge) / maxAge) * plotW;
  const p = [];
  p.push(`<rect x="0" y="0" width="${W}" height="${H}" fill="none"/>`);
  p.push(`<text x="10" y="16" class="tl-cap">大爆炸纪元 · 对数时间</text>`);

  /* log-scale epoch strip */
  const minLog = -44, maxLog = 9;
  const lx = s => gutter + ((Math.log10(Math.max(s, 1e-45)) - minLog) / (maxLog - minLog)) * plotW;
  p.push(`<line x1="${gutter}" y1="44" x2="${gutter + plotW}" y2="44" class="tl-axis"/>`);
  p.push(`<text x="${gutter - 6}" y="47" class="tl-gridlabel" text-anchor="end">10⁻⁴⁴s</text>`);
  p.push(`<text x="${gutter + plotW}" y="47" class="tl-gridlabel" text-anchor="end">10⁹s</text>`);
  epochs.forEach((e, i) => {
    const sec = Number((e.meta || {}).age_years || 0) * SEC_PER_YEAR;
    const px = lx(sec);
    const ty2 = (i % 2 === 0) ? 24 : 34;
    p.push(`<line x1="${px}" y1="38" x2="${px}" y2="50" class="tl-tick"/>`);
    p.push(`<circle cx="${px}" cy="44" r="3.4" fill="#ff8a3d"/>`);
    p.push(`<text x="${px}" y="${ty2}" class="tl-elabel" text-anchor="middle">${escapeHtml(e.label)}</text>`);
    p.push(`<g class="tl-ev" data-node="${escapeHtml(e.id)}"><rect x="${px - 7}" y="${ty2 - 11}" width="14" height="28" fill="transparent"/><title>${escapeHtml(e.label)} · ${escapeHtml(((e.meta||{}).age)||"")}</title></g>`);
  });

  /* linear Gyr axis + rows */
  const top = stripH + 10;
  const bottom = top + rows.length * rowH;
  const step = niceStep(maxAge, plotW);
  for (let t = 0; t <= maxAge + 1e-9; t += step){
    const px = x(t);
    p.push(`<line x1="${px}" y1="${top - 6}" x2="${px}" y2="${bottom}" class="tl-grid"/>`);
    p.push(`<text x="${px}" y="${bottom + 16}" class="tl-gridlabel" text-anchor="middle">${(Math.round(t * 100) / 100)}</text>`);
  }
  p.push(`<text x="${gutter - 6}" y="${top + 4}" class="tl-gridlabel" text-anchor="end">Gyr →</text>`);

  const labelMax = Math.max(8, Math.floor((gutter - 16) / 6.4));
  rows.forEach((row, i) => {
    const cy = top + i * rowH + rowH / 2 - 4;
    p.push(`<text x="10" y="${cy + 4}" class="tl-rowlabel" data-node="${escapeHtml(row.id)}" style="cursor:pointer">${escapeHtml(String(row.label).slice(0, labelMax))}</text>`);
    if (row.bar && row.barTo > 0){
      p.push(`<rect class="tl-bar" data-bar-to="${row.barTo}" x="${x(0)}" y="${cy - 4}" width="${Math.max(2, x(row.barTo) - x(0))}" height="8" rx="3" fill="${row.bar}"/>`);
    }
    row.events.forEach(ev => {
      const age = Number((ev.meta || {}).age_gyr || 0);
      const sev = Number((ev.meta || {}).severity || 0.5);
      const px = x(age), r = 2.6 + sev * 4;
      p.push(`<g class="tl-ev" data-node="${escapeHtml(ev.id)}" data-age="${age}">` +
        `<circle cx="${px}" cy="${cy}" r="${r + 6}" fill="transparent"/>` +
        `<circle class="tl-dot" cx="${px}" cy="${cy}" r="${r}" fill="${sevColor(sev)}" fill-opacity="0.92"/>` +
        `<title>${escapeHtml(ev.label)} · ${age.toFixed(2)} Gyr · 严重度 ${sev.toFixed(2)}</title></g>`);
    });
  });
  p.push(`<g id="tl-playhead" class="hidden"><line x1="0" y1="0" x2="0" y2="0"/>` +
         `<circle cx="0" cy="0" r="3.5"/><text x="0" y="0">0</text></g>`);
  tlSvg.innerHTML = p.join("");
  tlPlay.maxAge = maxAge; tlPlay.x = x; tlPlay.top = top; tlPlay.bottom = bottom;
  tlPlay.head = tlSvg.querySelector("#tl-playhead");
  tlPlay.dots = Array.from(tlSvg.querySelectorAll(".tl-ev[data-age]"));
  tlPlay.bars = Array.from(tlSvg.querySelectorAll(".tl-bar[data-bar-to]"));
  updatePlayhead(maxAge, true);
}
tlSvg.addEventListener("click", e => {
  const g = e.target.closest("[data-node]");
  if (g) revealNode(g.getAttribute("data-node"));
});
document.getElementById("tl-play").addEventListener("click", playTimeline);

/* touch-friendly timeline height handle */
let tlResize = null;
const tlHandle = document.getElementById("tl-handle");
tlHandle.addEventListener("pointerdown", e => {
  tlResize = { id: e.pointerId, y: e.clientY, h: tl.offsetHeight, raf: 0 };
  try { tlHandle.setPointerCapture(e.pointerId); } catch (_) {}
  e.preventDefault();
});
tlHandle.addEventListener("pointermove", e => {
  if (!tlResize || e.pointerId !== tlResize.id) return;
  const h = Math.min(window.innerHeight - 140, Math.max(140, tlResize.h + (tlResize.y - e.clientY)));
  tl.style.height = h + "px";
  if (!tlResize.raf) tlResize.raf = requestAnimationFrame(() => {
    if (!tlResize) return;
    tlResize.raf = 0;
    if (!tl.classList.contains("hidden")) renderTimeline();
  });
});
function tlResizeEnd(e){
  if (!tlResize || e.pointerId !== tlResize.id) return;
  if (tlResize.raf) cancelAnimationFrame(tlResize.raf);
  tlResize = null;
}
tlHandle.addEventListener("pointerup", tlResizeEnd);
tlHandle.addEventListener("pointercancel", tlResizeEnd);
if (window.ResizeObserver) new ResizeObserver(() => { if (!tl.classList.contains("hidden")) renderTimeline(); }).observe(tlBody);
window.addEventListener("resize", () => { if (!tl.classList.contains("hidden")) renderTimeline(); });

/* ------------------------------------------------------------------ */
/* legend + init                                                       */
/* ------------------------------------------------------------------ */
(function initLegend(){
  const el = document.getElementById("legend");
  const order = ["root","bigbang","epoch","universe","planet","event"];
  el.innerHTML = "<b style='font-size:11px;letter-spacing:1px;color:#8b97b0'>LEGEND</b>" +
    order.map(k => `<div class="row"><span class="chip" style="background:${KIND_COLORS[k]}"></span>${KIND_LABEL[k]}</div>`).join("");
})();

function applyPayload(payload){
  const timelineOpen = !tl.classList.contains("hidden");
  DATA = payload.tree;
  if (!DATA) throw new Error("宇宙数据为空");
  LIVE = !!payload.live;
  PROVIDER = payload.provider || PROVIDER;
  TITLE = payload.title || DATA.label || "Cosmos";
  document.title = TITLE + " — Cosmos Mind Map";
  const brand = document.querySelector("#bar .brand");
  if (brand) brand.textContent = "✦ " + TITLE;
  if (seedInput){ seedInput.value = (payload.seed == null ? "" : payload.seed); seedInput.disabled = !LIVE; }
  const seedBtn = document.querySelector('[data-act="regenerate"]');
  if (seedBtn) seedBtn.disabled = !LIVE;
  const archiveBtn = document.getElementById("archive-btn");
  if (archiveBtn) archiveBtn.disabled = !LIVE;
  stopEvolving();
  busy = null;
  evolveBusy = false;
  evolveCount = 0;
  selectedId = null;
  collapsed.clear();
  knownIds = new Set();
  query = "";
  if (searchBox) searchBox.value = "";
  if (panel) panel.classList.add("hidden");
  clearHighlight();
  if (!LIVE){
    const toggle = document.getElementById("tl-toggle");
    if (toggle) toggle.title = "打开时间线";
  }
  if (timelineOpen){
    tl.classList.remove("hidden");
    document.getElementById("tl-toggle").classList.add("on");
  }
  syncChrome();
  render();
  fit();
}

async function boot(){
  let payload = window.COSMOS_BOOTSTRAP || null;
  if (!payload){
    const res = await fetch(API_BASE + "/api/bootstrap", { cache: "no-store" });
    if (!res.ok) throw new Error("无法加载宇宙数据 (HTTP " + res.status + ")");
    payload = await res.json();
  }
  if (window.innerWidth >= 1100){
    tl.classList.remove("hidden");
    document.getElementById("tl-toggle").classList.add("on");
  }
  applyPayload(payload);
  if (document.fonts && document.fonts.ready){
    document.fonts.ready.then(() => syncChrome());
  }
  if (LIVE && providerIsMock(PROVIDER)) startEvolving(true);
}
boot().catch(err => {
  console.error(err);
  showToast("加载失败：" + err.message);
  const brand = document.querySelector("#bar .brand");
  if (brand) brand.textContent = "✦ 加载失败";
});
