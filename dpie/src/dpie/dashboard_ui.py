from dpie._version import __version__

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>DPIE Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background:#0f172a; color:#e2e8f0; font-family: system-ui, -apple-system, sans-serif; }
    .card { background:#111827; border:1px solid #334155; color:#e2e8f0; }
    .muted { color:#94a3b8; }
    pre { background:#020617; color:#7dd3fc; border:1px solid #1e293b; padding:1rem; border-radius:.5rem; max-height:420px; overflow:auto; }
    .badge-risk-high{background:#dc2626}.badge-risk-med{background:#d97706}.badge-risk-low{background:#16a34a}
  </style>
</head>
<body class="p-3 p-md-4">
  <div class="container-fluid">
    <div class="d-flex flex-wrap gap-2 justify-content-between align-items-center mb-3">
      <h3 class="m-0">DPIE Developer Dashboard <span class="badge bg-primary">v__DPIE_VERSION__</span></h3>
      <div class="d-flex gap-2">
        <a class="btn btn-outline-info btn-sm" href="/docs" target="_blank">Swagger</a>
        <a class="btn btn-outline-secondary btn-sm" href="/api/v1/health" target="_blank">Health</a>
      </div>
    </div>
    <div class="row g-3">
      <div class="col-lg-5">
        <div class="card p-3">
          <h6 class="text-info">Analysis Input</h6>
          <label class="form-label small">Target URL</label>
          <input id="url" class="form-control form-control-sm bg-dark text-light border-secondary" value="https://example.com/checkout"/>
          <label class="form-label small mt-2">Mode</label>
          <select id="mode" class="form-select form-select-sm bg-dark text-light border-secondary">
            <option value="fast">fast</option>
            <option value="deep" selected>deep</option>
            <option value="full">full</option>
          </select>
          <label class="form-label small mt-2">HTML / DOM snippet</label>
          <textarea id="html" rows="7" class="form-control form-control-sm bg-dark text-light border-secondary"><button class="cta">Subscribe now - it's free and you must agree!</button>
<a href="#" class="decline">No thanks, I prefer paying full price</a>
<span class="fine-print">Auto-renews at $99/mo after 3 days trial. Cancel anytime with $25 fee.</span></textarea>
          <label class="form-label small mt-2">Structured elements (JSON array, optional)</label>
          <textarea id="elements" rows="6" class="form-control form-control-sm bg-dark text-light border-secondary">[
  {"element_type":"button","element_text":"Subscribe now - it's free and you must agree!","element_selector":".cta","element_attributes":{"class":"cta"}},
  {"element_type":"a","element_text":"No thanks, I prefer paying full price","element_selector":".decline","element_attributes":{"class":"decline"}},
  {"element_type":"span","element_text":"Auto-renews at $99/mo after 3 days trial. Cancel anytime with $25 fee.","element_selector":".fine-print","element_attributes":{"class":"fine-print"}}
]</textarea>
          <div class="d-flex gap-2 mt-3">
            <button class="btn btn-primary btn-sm" onclick="runAnalysis()">Run Analysis</button>
            <button class="btn btn-outline-light btn-sm" onclick="loadAgents()">Refresh Agents</button>
          </div>
          <div id="status" class="small muted mt-2">Ready.</div>
        </div>
        <div class="card p-3 mt-3">
          <h6 class="text-warning">Registered Agents</h6>
          <pre id="agents">Loading...</pre>
        </div>
      </div>
      <div class="col-lg-7">
        <div class="card p-3">
          <div class="d-flex justify-content-between align-items-center">
            <h6 class="text-success m-0">Results</h6>
            <div id="summary" class="small"></div>
          </div>
          <pre id="output">Run an analysis to see results.</pre>
        </div>
      </div>
    </div>
  </div>
<script>
async function loadAgents(){
  try {
    const r = await fetch('/api/v1/agents');
    const d = await r.json();
    document.getElementById('agents').textContent = JSON.stringify(d, null, 2);
  } catch(e){ document.getElementById('agents').textContent = 'Error: '+e.message; }
}
function parseElements(){
  const raw = document.getElementById('elements').value.trim();
  if(!raw) return { ok:true, value:null };
  try {
    const v = JSON.parse(raw);
    if (v === null) return { ok:true, value:null };
    if (!Array.isArray(v)) return { ok:false, error:'Elements must be a JSON array (or empty).' };
    for (let i=0;i<v.length;i++){
      if (v[i] === null || typeof v[i] !== 'object' || Array.isArray(v[i])) {
        return { ok:false, error:`Element at index ${i} must be an object.` };
      }
    }
    return { ok:true, value:v };
  } catch(e){
    return { ok:false, error: e && e.message ? e.message : String(e) };
  }
}
async function runAnalysis(){
  const status = document.getElementById('status');
  const out = document.getElementById('output');
  const summary = document.getElementById('summary');
  status.textContent = 'Running...'; out.textContent = 'Working...'; summary.textContent='';
  const parsed = parseElements();
  if(!parsed.ok){ status.textContent='Invalid elements JSON: '+parsed.error; out.textContent='Fix the elements input and try again.'; return; }
  const payload = {
    url: document.getElementById('url').value,
    html: document.getElementById('html').value,
    mode: document.getElementById('mode').value,
  };
  if (parsed.value !== null) payload.elements = parsed.value;
  try {
    const res = await fetch('/api/v1/analyze', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    const data = await res.json().catch(()=> ({}));
    if(!res.ok){ status.textContent=`Request failed (${res.status})`; out.textContent=JSON.stringify(data,null,2); return; }
    out.textContent = JSON.stringify(data, null, 2);
    const conf = Math.round((Number(data.aggregated_confidence)||0)*100);
    const riskVal = (data.aggregated_risk===null || data.aggregated_risk===undefined) ? null : Math.round((Number(data.aggregated_risk)||0)*100);
    const cls = (riskVal??0)>=70?'badge-risk-high':(riskVal??0)>=40?'badge-risk-med':'badge-risk-low';
    const riskBadge = riskVal===null ? '<span class="badge bg-secondary">risk n/a</span>' : `<span class="badge ${cls}">risk ${riskVal}%</span>`;
    summary.innerHTML = `<span class="badge bg-secondary">${(data.all_findings||[]).length} findings</span> <span class="badge bg-info text-dark">conf ${conf}%</span> ${riskBadge}`;
    status.textContent = `Done in ${data.total_execution_time_ms||0} ms (${data.status||'unknown'})`;
  } catch(e){ out.textContent='Error: '+(e && e.message ? e.message : String(e)); status.textContent='Failed.'; }
}
loadAgents();
</script>
</body>
</html>"""

def get_dashboard_html() -> str:
    return DASHBOARD_HTML.replace("__DPIE_VERSION__", __version__)
