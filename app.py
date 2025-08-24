import os
import sys
import json
import shutil
import datetime as dt
import subprocess
from flask import Flask, request, render_template_string, Response, send_from_directory, jsonify

# === CONFIGS ===
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))   # dossier d'où est lancé app.py
LOG_DIR = os.path.join(PROJECT_DIR, "log_app")              # dossier des logs de l'app
DEFAULT_STRATEGY = "eZ3_scalp3m"
GIT_PATHS_FILE = os.path.join(PROJECT_DIR, "git_path.txt")

BASE_CONFIG_FOR_CMD = os.path.join(PROJECT_DIR, "user_data", "config_base.json")
CONFIGS_DIR = os.path.join(PROJECT_DIR, "user_data", "configs")
EXCHANGE_CONFIG_PATH = os.path.join(CONFIGS_DIR, "config_exchange.json")
# ===============

app = Flask(__name__)
os.makedirs(LOG_DIR, exist_ok=True)

# ---------- Helpers ----------
def find_python_exe():
    for v in [".venv", "venv"]:
        candidate = os.path.join(PROJECT_DIR, v, "Scripts", "python.exe")
        if os.path.exists(candidate):
            return candidate
    return sys.executable or "python"

def ymd(date_obj): return date_obj.strftime("%Y%m%d")

def default_start_date():
    today = dt.date.today()
    return ymd(today - dt.timedelta(days=60))

def html_default_date_input():
    d = dt.date.today() - dt.timedelta(days=60)
    return d.strftime("%Y-%m-%d")

def default_end_date():
    return ymd(dt.date.today())

def html_end_date_input():
    return dt.date.today().strftime("%Y-%m-%d")

def win_quote(arg: str):
    if any(c in arg for c in (' ', '\t', '"')):
        return '"' + arg.replace('"', r'\"') + '"'
    return arg

def strategies_dir():
    return os.path.join(PROJECT_DIR, "user_data", "strategies")

def list_strategies():
    sdir = strategies_dir()
    if not os.path.isdir(sdir):
        return []
    return sorted(os.path.splitext(fn)[0] for fn in os.listdir(sdir) if fn.endswith(".py"))

def list_strategy_jsons():
    sdir = strategies_dir()
    if not os.path.isdir(sdir):
        return []
    out = []
    for fn in os.listdir(sdir):
        if not fn.endswith(".json"):
            continue
        if fn.endswith(".json.bak") or fn.endswith(".json.tmp") or fn.endswith(".json.tmpbak"):
            continue
        out.append(fn)
    return sorted(out)

def list_strategy_jsons_no_bakprefix():
    all_jsons = list_strategy_jsons()
    return [fn for fn in all_jsons if not fn.startswith("BAK_")]

def read_git_paths_list():
    if not os.path.exists(GIT_PATHS_FILE):
        return []
    with open(GIT_PATHS_FILE, "r", encoding="utf-8", errors="ignore") as f:
        lines = [ln.strip() for ln in f.read().splitlines()]
    lines = [ln for ln in lines if ln and not ln.lstrip().startswith("#")]
    out = []
    for p in lines:
        if not os.path.isabs(p):
            p = os.path.join(PROJECT_DIR, p)
        out.append(os.path.normpath(p))
    return out

# ---------- pair_whitelist robuste ----------
def read_pair_whitelist_from_exchange_config():
    """
    Renvoie la liste des paires depuis PROJECT_DIR/user_data/configs/config_exchange.json,
    qu'elle soit dans pairlists[StaticPairList], à la racine, ou plus profond.
    """
    path = EXCHANGE_CONFIG_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    def _clean_list(lst):
        return [p for p in lst if isinstance(p, str) and p.strip()]

    pls = data.get("pairlists")
    if isinstance(pls, list):
        for item in pls:
            if isinstance(item, dict) and item.get("method") == "StaticPairList":
                wl = item.get("pair_whitelist")
                if isinstance(wl, list):
                    return _clean_list(wl)
        for item in pls:
            if isinstance(item, dict) and isinstance(item.get("pair_whitelist"), list):
                return _clean_list(item["pair_whitelist"])

    wl_root = data.get("pair_whitelist")
    if isinstance(wl_root, list):
        return _clean_list(wl_root)

    def _find_first_pw(obj):
        if isinstance(obj, dict):
            if isinstance(obj.get("pair_whitelist"), list):
                return obj["pair_whitelist"]
            for v in obj.values():
                found = _find_first_pw(v)
                if found is not None:
                    return found
        elif isinstance(obj, list):
            for it in obj:
                found = _find_first_pw(it)
                if found is not None:
                    return found
        return None

    deep = _find_first_pw(data)
    if isinstance(deep, list):
        return _clean_list(deep)
    return []

# ---------- Build commandes ----------
def build_cmd(action, strategy, start_ymd, *, end_ymd=None, timeframe=None, epochs=None, spaces=None, erase=False):
    py = find_python_exe()
    base = [py, "-m", "freqtrade"]
    cfg  = ["--config", os.path.relpath(BASE_CONFIG_FOR_CMD, PROJECT_DIR)]

    if action == "download":
        cmd = base + ["download-data"] + cfg + ["--timerange", f"{start_ymd}-"]
        cmd += ["--timeframes", timeframe or "1h"]
        if erase:
            cmd += ["--erase"]
        return cmd

    if action == "backtest":
        end = end_ymd or default_end_date()
        return base + ["backtesting"] + cfg + [
            "--strategy", strategy,
            "--timerange", f"{start_ymd}-{end}"
        ]

    if action == "backtest_bear":
        return base + ["backtesting"] + cfg + [
            "--strategy", strategy,
            "--timerange", "20220110-20220618"
        ]

    if action == "hyperopt":
        cmd = base + ["hyperopt"] + cfg + [
            "--strategy", strategy,
            "--timeframe", "3m",
            "--epochs", str(epochs if epochs is not None else 100),
            "--hyperopt-loss", "OnlyProfitHyperOptLoss",
            "--timerange", f"{start_ymd}-"
        ]
        if spaces:
            if len(spaces) == 1 and spaces[0].lower() == "all":
                cmd += ["--spaces", "all"]
            elif len(spaces) == 1 and spaces[0].lower() == "default":
                pass
            else:
                filtered = [s for s in spaces if s.lower() != "default"]
                if filtered:
                    cmd += ["--spaces"] + filtered
        return cmd

    if action == "apply_strategy":
        return None

    raise ValueError("Action inconnue")

# ---------- SSE helpers ----------
def sse_format(event: str | None, data: str):
    lines = []
    if event:
        lines.append(f"event: {event}")
    for ln in data.splitlines() or [""]:
        lines.append(f"data: {ln}")
    lines.append("")
    return "\n".join(lines) + "\n"

def is_warn_err(line: str):
    l = line.lower()
    return ("error" in l or "warning" in l or "critical" in l or "traceback" in l or "exception" in l)

# ---------- Routes ----------
@app.get("/")
def index():
    strategies = list_strategies()
    json_files = list_strategy_jsons()
    json_files_apply = list_strategy_jsons_no_bakprefix()
    default_strategy = DEFAULT_STRATEGY if DEFAULT_STRATEGY in strategies else (strategies[0] if strategies else DEFAULT_STRATEGY)

    git_paths_list = read_git_paths_list()
    pair_count = len(read_pair_whitelist_from_exchange_config())

    html = """
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <title>Freqtrade - Controle Panel</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root { color-scheme: light dark; }
    body { font-family: system-ui, Arial, sans-serif; margin: 24px; }
    .wrap { max-width: 1200px; margin: 0 auto; }
    .card { border: 1px solid #4444; border-radius: 14px; padding: 16px; box-shadow: 0 2px 10px #0001; margin-bottom: 16px; }
    .card h2 { margin: 0 0 10px 0; }
    .row { display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; }
    .row.space-between { justify-content: space-between; align-items: center; }
    label { display:block; margin: 0 0 4px; font-weight: 600; }
    input, button, select { font-size: 16px; padding: 8px 10px; }
    input[type="date"], input[type="number"], select { width: 260px; }
    #start_date, #end_date { width: 160px; padding: 6px 8px; font-size: 14px; }
    button { cursor: pointer; border-radius: 10px; border: 1px solid #5555; }
    button.primary { background: #2563eb; color: white; border-color: #1d4ed8; }
    .grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
    .panel { border: 1px dashed #8886; border-radius: 12px; padding: 10px; }
    .title { font-weight: 700; margin-bottom: 6px; }
    .status { font-size: 14px; opacity: .9; margin-bottom: 6px; }
    .ok { color: #16a34a; font-weight: 600; }
    .err { color: #dc2626; font-weight: 600; }
    .warn { color: #d97706; font-weight: 600; }
    pre { white-space: pre-wrap; background: #1112; padding: 10px; border-radius: 10px; max-height: 45vh; overflow: auto; }
    a { text-decoration: none; }
    .inline { display:flex; flex-direction: column; }
    .inline > label { margin-bottom: 4px; }
    .git-path-select { flex: 1; min-width: 400px; max-width: 100%; }
    .flex-grow { flex: 1; }
    .spaces-wrap { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
    .spaces-wrap label { font-weight: normal; }
    .tf-wrap { display:flex; gap:12px; flex-wrap:wrap; }
    .tf-wrap label { font-weight: normal; }
    .muted { color: #888; font-weight: 600; }
    .progress { width: 100%; height: 10px; background:#0002; border-radius: 8px; overflow:hidden; }
    .progress > div { height: 100%; width: 0%; background: #2563eb; transition: width .2s ease; }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .result { border-top: 1px dashed #8886; margin-top: 8px; padding-top: 8px; }
  </style>
</head>
<body>
<div class="wrap">
  <h1>Freqtrade - Controle Panel</h1>

  <!-- Strategy -->
  <div class="card">
    <h2>Strategy</h2>

    <div class="row" style="justify-content:space-between; align-items:flex-end">
      <div class="row" style="gap:18px; flex-wrap:wrap; flex:1; align-items:center">
        <div class="row" style="gap:12px; align-items:flex-end">
          <div class="inline">
            <label for="strategy">Script</label>
            <select id="strategy">
              {% for s in strategies %}
                <option value="{{s}}" {% if s==default_strategy %}selected{% endif %}>{{s}}</option>
              {% endfor %}
            </select>
          </div>
          <div class="inline">
            <label for="start_date">Start date</label>
            <input id="start_date" type="date" value="{{ default_date_input }}" />
          </div>
          <div class="inline">
            <label for="end_date">End date</label>
            <input id="end_date" type="date" value="{{ default_end_date_input }}" />
          </div>
        </div>

        <div class="inline" style="margin-top:12px">
          <div class="muted">pair_whitelist (config_exchange.json) : <span id="pairCount">{{ pair_count }}</span></div>
        </div>
      </div>

      <div class="row" style="gap:12px">
        <button class="primary" onclick="openLogs()">Logs</button>
      </div>
    </div>
  </div>

  <!-- Download -->
  <div class="card">
    <h2>Download</h2>
    <div class="row" style="gap:12px; align-items:flex-end">
      <div class="inline" style="flex:1">
        <label>Timeframes</label>
        <div class="tf-wrap">
          <label><input type="checkbox" name="tf" value="3m"> 3m</label>
          <label><input type="checkbox" name="tf" value="5m"> 5m</label>
          <label><input type="checkbox" name="tf" value="15m"> 15m</label>
          <label><input type="checkbox" name="tf" value="30m"> 30m</label>
          <label><input type="checkbox" name="tf" value="1h" checked> 1h</label>
          <label><input type="checkbox" name="tf" value="2h"> 2h</label>
          <label><input type="checkbox" name="tf" value="4h"> 4h</label>
          <label><input type="checkbox" name="tf" value="6h"> 6h</label>
          <label><input type="checkbox" name="tf" value="12h"> 12h</label>
          <label><input type="checkbox" name="tf" value="1d" checked> 1d</label>
        </div>
      </div>
      <div class="inline">
        <label for="dl_erase">Erase</label>
        <input id="dl_erase" type="checkbox" />
      </div>
      <div class="inline" style="align-items:flex-start">
        <label style="visibility:hidden">Action</label>
        <button class="primary" onclick="startDownload()">Download data</button>
      </div>
    </div>

    <div style="margin-top:10px">
      <div class="progress"><div id="dlProgressBar"></div></div>
      <div id="dlProgressText" class="muted" style="margin-top:6px">0 / 0 (0%)</div>
    </div>
  </div>

  <!-- Backtest -->
  <div class="card">
    <h2>Backtest</h2>
    <div class="row" style="justify-content:space-between; gap:12px">
      <div class="inline flex-grow">
        <label for="bt_json_sel">Fichier .json (user_data/strategies)</label>
        <select id="bt_json_sel" class="flex-grow" style="min-width:400px">
          <option value="">— Utiliser le {strategy}.json courant —</option>
          {% for jf in json_files %}
            <option value="{{jf}}">{{jf}}</option>
          {% endfor %}
        </select>
      </div>
      <div class="row" style="gap:12px">
        <div class="inline" style="align-items:flex-start">
          <label style="visibility:hidden">Backtest</label>
          <button id="btn-backtest" class="primary" onclick="startBacktest()">Backtest</button>
        </div>
        <div class="inline" style="align-items:flex-start">
          <label style="font-size:12px; opacity:.8">Période BEAR<br>20220110-20220618</label>
          <button id="btn-backtest-bear" class="primary" onclick="startStream('backtest_bear')">Backtest BEAR</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Hyperopt -->
  <div class="card">
    <h2>Hyperopt</h2>
    <div class="row" style="gap:24px; align-items:center">
      <div class="inline">
        <label for="epochs">Epochs (défaut 100)</label>
        <input id="epochs" type="number" min="1" step="1" value="100" />
      </div>

      <div class="inline" style="flex:1">
        <label>Spaces</label>
        <div class="spaces-wrap" id="spacesWrap">
          <label><input type="checkbox" name="spaces" value="all"> all</label>
          <label><input type="checkbox" name="spaces" value="buy"> buy</label>
          <label><input type="checkbox" name="spaces" value="sell"> sell</label>
          <label><input type="checkbox" name="spaces" value="roi"> roi</label>
          <label><input type="checkbox" name="spaces" value="stoploss"> stoploss</label>
          <label><input type="checkbox" name="spaces" value="trailing"> trailing</label>
          <label><input type="checkbox" name="spaces" value="protection"> protection</label>
          <label><input type="checkbox" name="spaces" value="trades"> trades</label>
          <label><input type="checkbox" name="spaces" value="default" checked> default</label>
        </div>
      </div>

      <div class="inline" style="align-items:flex-start">
        <label style="visibility:hidden">Action</label>
        <button id="btn-hyperopt" class="primary" onclick="startHyperopt()">Lancer Hyperopt</button>
      </div>
    </div>
  </div>

  <!-- Apply Strategy -->
  <div class="card">
    <h2>Apply Strategy Hyperopt</h2>
    <div class="row" style="justify-content:space-between; gap:12px">
      <div class="inline flex-grow">
        <label for="apply_json_sel">Fichier .json (user_data/strategies)</label>
        <select id="apply_json_sel" class="flex-grow" style="min-width:400px">
          {% for jf in json_files_apply %}
            <option value="{{jf}}">{{jf}}</option>
          {% endfor %}
        </select>
      </div>
      <div class="inline" style="align-items:flex-start">
        <label style="visibility:hidden">Apply</label>
        <button class="primary" onclick="startApplyStrategy()">Apply</button>
      </div>
    </div>
  </div>

  <!-- Git -->
  <div class="card">
    <h2>Git</h2>
    <div class="row space-between">
      <div class="inline" style="flex:1">
        <label for="git_path">Chemin</label>
        <select id="git_path" class="git-path-select">
          {% for p in git_paths_list %}
            <option value="{{p}}">{{p}}</option>
          {% endfor %}
        </select>
      </div>
      <button class="primary" onclick="startGitPush()">PUSH</button>
    </div>
  </div>

  <!-- Panneaux de sortie -->
  <div class="grid">
    <div class="panel">
      <div class="title">Download data</div>
      <div id="status-download" class="status">Prêt.</div>
      <pre id="out-download"></pre>
    </div>
    <div class="panel">
      <div class="title">Backtest</div>
      <div id="status-backtest" class="status">Prêt.</div>
      <pre id="out-backtest"></pre>
    </div>
    <div class="panel">
      <div class="title">Backtest BEAR</div>
      <div id="status-backtest_bear" class="status">Prêt.</div>
      <pre id="out-backtest_bear"></pre>
    </div>
    <div class="panel">
      <div class="title">Hyperopt</div>
      <div id="status-hyperopt" class="status">Prêt.</div>
      <pre id="out-hyperopt"></pre>
    </div>
    <div class="panel">
      <div class="title">Apply Strategy Hyperopt</div>
      <div id="status-apply_strategy" class="status">Prêt.</div>
      <pre id="out-apply_strategy"></pre>
    </div>
    <div class="panel">
      <div class="title">Git PUSH</div>
      <div id="status-git_push" class="status">Prêt.</div>
      <pre id="out-git_push"></pre>
    </div>
  </div>
</div>

<script>
  const sources = {};

  // === Grisage croisé ===
  function setDisabled(el, disabled){ if(!el) return; el.disabled = !!disabled; }
  function lockFor(action){
    const btnBT      = document.getElementById('btn-backtest');
    const btnBTBear  = document.getElementById('btn-backtest-bear');
    const btnHopt    = document.getElementById('btn-hyperopt');
    if(action === 'hyperopt'){
      setDisabled(btnBT, true); setDisabled(btnBTBear, true);
    } else if(action === 'backtest' || action === 'backtest_bear'){
      setDisabled(btnHopt, true);
    }
  }
  function unlockAll(){
    const btnBT      = document.getElementById('btn-backtest');
    const btnBTBear  = document.getElementById('btn-backtest-bear');
    const btnHopt    = document.getElementById('btn-hyperopt');
    setDisabled(btnBT, false); setDisabled(btnBTBear, false); setDisabled(btnHopt, false);
  }

  // === Divers UI ===
  function toYMD(dstr){ if(!dstr) return ""; const [y,m,d]=dstr.split("-"); return `${y}${m}${d}`; }
  function openLogs(){ window.open('/logs/', '_blank'); }
  function appendColored(outEl, cls, text){
    const span = document.createElement('span');
    span.className = cls;
    span.textContent = text;
    outEl.appendChild(span);
    outEl.appendChild(document.createTextNode("\\n"));
    outEl.scrollTop = outEl.scrollHeight;
  }

  // === Hyperopt Spaces rules ===
  function applySpacesRules(){
    const boxes = Array.from(document.querySelectorAll("input[name='spaces']"));
    if (!boxes.length) return;
    const allBox = boxes.find(b => b.value === "all");
    const defBox = boxes.find(b => b.value === "default");
    const wantedDefault = ["buy","sell","roi","stoploss"];

    const setDis = (b, disabled) => {
      b.disabled = !!disabled;
      const lbl = b.parentElement;
      lbl.style.opacity = disabled ? .6 : 1;
    };

    if (allBox && allBox.checked){
      boxes.forEach(b => { if (b !== allBox){ b.checked = false; setDis(b, true); } else setDis(b, false); });
      return;
    }

    if (defBox && defBox.checked){
      boxes.forEach(b => {
        if (b.value === "default"){ setDis(b, false); }
        else if (wantedDefault.includes(b.value)){ b.checked = true; setDis(b, true); }
        else { b.checked = false; setDis(b, true); }
      });
      return;
    }

    boxes.forEach(b => setDis(b, false));
  }

  document.addEventListener("DOMContentLoaded", () => {
    applySpacesRules();
    document.querySelectorAll("input[name='spaces']").forEach(b => b.addEventListener("change", applySpacesRules));
  });

  async function refreshStrategies(){
    const r = await fetch('/api/list_strategies'); if(!r.ok) return;
    const { strategies=[] } = await r.json();
    const sel = document.getElementById('strategy'); const cur = sel.value; sel.innerHTML = "";
    strategies.forEach(s => { const opt = document.createElement('option'); opt.value=s; opt.textContent=s; if(s===cur) opt.selected=true; sel.appendChild(opt); });
  }
  async function refreshJsons(){
    const a = await fetch('/api/list_jsons'); const b = await fetch('/api/list_jsons_apply');
    if(a.ok){
      const { json_files=[] } = await a.json();
      const sel = document.getElementById('bt_json_sel'); const cur = sel.value; sel.innerHTML = "";
      const ph = document.createElement('option'); ph.value=""; ph.textContent="— Utiliser le {strategy}.json courant —"; if(cur==="") ph.selected=true; sel.appendChild(ph);
      json_files.forEach(p => { const opt = document.createElement('option'); opt.value=p; opt.textContent=p; if(p===cur) opt.selected=true; sel.appendChild(opt); });
    }
    if(b.ok){
      const { json_files_apply=[] } = await b.json();
      const sel2 = document.getElementById('apply_json_sel'); const cur2 = sel2.value; sel2.innerHTML = "";
      json_files_apply.forEach(p => { const opt = document.createElement('option'); opt.value=p; opt.textContent=p; if(p===cur2) opt.selected=true; sel2.appendChild(opt); });
    }
  }
  async function refreshGitPaths(){
    const r = await fetch('/api/git_paths'); if(!r.ok) return;
    const { git_paths_list=[] } = await r.json();
    const sel = document.getElementById('git_path'); const cur = sel.value; sel.innerHTML = "";
    git_paths_list.forEach(p => { const opt = document.createElement('option'); opt.value=p; opt.textContent=p; if(p===cur) opt.selected=true; sel.appendChild(opt); });
  }
  async function refreshLists(){ await Promise.allSettled([refreshStrategies(), refreshJsons(), refreshGitPaths()]); }

  // === Download: progression UI ===
  function collectTimeframes(){ return Array.from(document.querySelectorAll("input[name='tf']:checked")).map(b => b.value); }
  function setDownloadProgress(current, total){
    const bar = document.getElementById('dlProgressBar');
    const txt = document.getElementById('dlProgressText');
    const pct = total > 0 ? Math.min(100, Math.floor(100*current/total)) : 0;
    bar.style.width = pct + "%";
    txt.textContent = `${current} / ${total} (${pct}%)`;
  }

  // === Lancements d'actions / SSE ===
  function startStream(action, extraParams={}){
    if(sources[action]) sources[action].close();
    lockFor(action);

    const strategy = document.getElementById('strategy').value.trim();
    const start_date = document.getElementById('start_date')?.value || "";
    const end_date = document.getElementById('end_date')?.value || "";
    const start_ymd = toYMD(start_date);
    const end_ymd = toYMD(end_date);

    const outEl = document.getElementById('out-'+action);
    const stEl  = document.getElementById('status-'+action);
    outEl.textContent = ""; stEl.textContent = "Exécution en cours…";

    const params = new URLSearchParams({ action, strategy, start_ymd, ...extraParams });
    if(action === 'backtest' && end_ymd) params.set('end_ymd', end_ymd);

    const src = new EventSource('/run_stream?'+params.toString());
    sources[action] = src;

    if(action === 'download'){ setDownloadProgress(0, 0); }

    src.addEventListener('meta', ev => {
      try{
        const meta = JSON.parse(ev.data);
        if(action === 'download' && typeof meta.total_steps === 'number') setDownloadProgress(0, meta.total_steps);
      }catch(_){}
    });

    // UI: on n'affiche pas les 'line' (seulement warn/err + result)
    src.addEventListener('line', _ev => {});

    // Progression Download
    src.addEventListener('progress', ev => {
      try{ const data = JSON.parse(ev.data); setDownloadProgress(data.current||0, data.total||0); }catch(_){}
    });

    // WARN / ERR visibles
    src.addEventListener('warn', ev => appendColored(document.getElementById('out-'+action), "warn", ev.data));
    src.addEventListener('err',  ev => appendColored(document.getElementById('out-'+action), "err",  ev.data));

    // RESULT (bloc résumé)
    src.addEventListener('result', ev => {
      const pre = document.getElementById('out-'+action);
      const div = document.createElement('div');
      div.className = 'result';
      div.textContent = ev.data;
      pre.appendChild(div);
      pre.scrollTop = pre.scrollHeight;
    });

    src.addEventListener('end', ev => {
      try{
        const data = JSON.parse(ev.data);
        const ok = data.returncode === 0;
        const cls = ok ? 'ok' : 'err';
        const txt = ok ? 'Terminé ✓' : 'Terminé avec erreurs ✗';
        const link = data.log_download ? ` — Log : <a href="${data.log_download}" target="_blank">ouvrir</a>` : '';
        stEl.innerHTML = `<span class="${cls}">${txt}</span>${link}`;
        if(action === 'download' && ok && data.total_steps){ setDownloadProgress(data.total_steps, data.total_steps); }
      }catch(_){
        stEl.innerHTML = `<span class="err">Terminé (parsing meta échoué)</span>`;
      }
      src.close(); delete sources[action];
      unlockAll();
      refreshLists();
    });

    src.onerror = () => {
      stEl.innerHTML = '<span class="err">Erreur de streaming</span>';
      src.close(); delete sources[action];
      unlockAll();
    };
  }

  function startDownload(){
    const tfs = collectTimeframes();
    const erase = document.getElementById('dl_erase').checked ? "1" : "0";
    startStream('download', { tfs: tfs.join(","), erase });
  }
  function startBacktest(){
    const chosen = document.getElementById('bt_json_sel')?.value || "";
    const extra = {}; if(chosen) extra.bt_json = chosen;
    startStream('backtest', extra);
  }
  function startHyperopt(){
    const epochs = Math.max(1, parseInt(document.getElementById('epochs').value || '100', 10));
    const spaces = Array.from(document.querySelectorAll("input[name='spaces']:checked")).map(b => b.value);
    startStream('hyperopt', { epochs:String(epochs), spaces: spaces.join(",") });
  }
  function startApplyStrategy(){
    const chosen = document.getElementById('apply_json_sel')?.value || "";
    if(!chosen){ alert("Sélectionne un fichier .json à appliquer !"); return; }
    startStream('apply_strategy', { apply_json: chosen });
  }
  function startGitPush(){
    const val = document.getElementById('git_path')?.value || "";
    if(!val){
      document.getElementById('status-git_push').textContent = "Aucun chemin Git sélectionné.";
      document.getElementById('out-git_push').textContent = "";
      return;
    }
    startStream('git_push', { git_path_single: val });
  }
</script>
</body>
</html>
"""
    return render_template_string(
        html,
        strategies=strategies,
        default_strategy=default_strategy,
        default_date_input=html_default_date_input(),
        default_end_date_input=html_end_date_input(),
        git_paths_list=read_git_paths_list(),
        json_files=json_files,
        json_files_apply=json_files_apply,
        pair_count=pair_count
    )

@app.get("/run_stream")
def run_stream():
    """
    Stream SSE par action.
    UI: n'affiche que WARN/ERR, mais on envoie un évènement 'result' pour les blocs résultats.
    """
    action    = (request.args.get("action") or "").strip()
    strategy  = (request.args.get("strategy") or DEFAULT_STRATEGY).strip()
    start_ymd = (request.args.get("start_ymd") or "").strip() or default_start_date()
    end_ymd   = (request.args.get("end_ymd") or "").strip()
    bt_json   = (request.args.get("bt_json") or "").strip()
    apply_json = (request.args.get("apply_json") or "").strip() if action == "apply_strategy" else ""

    epochs_param = request.args.get("epochs", "").strip()
    try:
        epochs = int(epochs_param) if epochs_param else 100
        if epochs < 1: epochs = 100
    except:
        epochs = 100

    spaces_csv = (request.args.get("spaces") or "").strip()
    spaces = [s for s in spaces_csv.split(",") if s] if spaces_csv else None
    if spaces == ["default"]:
        spaces = None

    tfs_csv = (request.args.get("tfs") or "").strip()
    timeframes = [t for t in tfs_csv.split(",") if t] if tfs_csv else None
    erase = ((request.args.get("erase") or "0").strip() == "1")

    git_path_single = request.args.get("git_path_single", "").strip() if action == "git_push" else ""

    if action == "backtest":
        if not end_ymd:
            end_ymd = default_end_date()
        if start_ymd and end_ymd and start_ymd > end_ymd:
            def bad_dates():
                yield sse_format("err", f"Plage de dates invalide: START({start_ymd}) > END({end_ymd}).")
                payload = {"returncode": 1, "log_download": ""}
                yield sse_format("end", json.dumps(payload))
            return Response(bad_dates(), mimetype="text/event-stream")

    try:
        if action == "git_push":
            cmd = ["git", "-C", git_path_single, "status"]
        elif action == "download":
            cmd = None
        elif action == "backtest":
            cmd = build_cmd("backtest", strategy, start_ymd, end_ymd=end_ymd)
        elif action == "backtest_bear":
            cmd = build_cmd("backtest_bear", strategy, start_ymd)
        elif action == "hyperopt":
            cmd = build_cmd("hyperopt", strategy, start_ymd, epochs=epochs, spaces=spaces)
        elif action == "apply_strategy":
            cmd = None
        else:
            raise ValueError("Action inconnue")
    except Exception as e:
        def err_stream():
            yield sse_format("err", f"Erreur: {e}")
            payload = {"returncode": 1, "log_download": ""}
            yield sse_format("end", json.dumps(payload))
        return Response(err_stream(), mimetype="text/event-stream")

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(LOG_DIR, f"{action}_{ts}.log")

    pairs = read_pair_whitelist_from_exchange_config()
    tfs_list = timeframes if timeframes else ["1h", "1d"]
    total_steps_download = (len(pairs) * len(tfs_list)) if action == "download" else 0
    prog_current = 0

    def emit_progress():
        if action != "download":
            return ""
        payload = {"current": prog_current, "total": total_steps_download}
        return sse_format("progress", json.dumps(payload))

    def generate():
        nonlocal prog_current

        # Entête (la UI ignore 'line', mais on garde pour meta/cohérence)
        if action == "git_push":
            cmd_str = f"git push in {git_path_single or '(none)'}"
        elif action == "apply_strategy":
            cmd_str = f"APPLY {strategy}.json <= {apply_json or '(none)'}"
        elif action == "download":
            cmd_str = "freqtrade download-data (multi-timeframes) --config config_base.json"
        else:
            cmd_str = " ".join(win_quote(x) for x in cmd) if cmd else "(no external command)"
        header = f"CMD> {cmd_str}"
        yield sse_format("line", header)

        meta = {"logfile": log_path, "cwd": PROJECT_DIR, "cmd": cmd_str}
        if action == "download":
            meta["total_steps"] = total_steps_download
        yield sse_format("meta", json.dumps(meta))

        rc = 0
        is_download      = (action == "download")
        is_backtest      = (action == "backtest")
        is_backtest_bear = (action == "backtest_bear")
        is_hyperopt      = (action == "hyperopt")
        is_gitpush       = (action == "git_push")
        is_apply         = (action == "apply_strategy")

        sdir = strategies_dir()
        strat_json_path = os.path.join(sdir, f"{strategy}.json")

        # Prépare fichier log
        with open(log_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(header + "\n")

        # === APPLY STRATEGY ===
        if is_apply:
            try:
                if not apply_json:
                    msg = "[APPLY] Aucun fichier sélectionné."
                    yield sse_format("err", msg)
                    with open(log_path, "a", encoding="utf-8") as f: f.write("ERR: " + msg + "\n")
                    rc = 1
                else:
                    chosen_path = os.path.join(sdir, apply_json)
                    if apply_json == f"{strategy}.json":
                        msg = f"[APPLY] Le fichier sélectionné est déjà {strategy}.json : aucune modification appliquée."
                        yield sse_format("warn", msg)
                        with open(log_path, "a", encoding="utf-8") as f: f.write("WARN: " + msg + "\n")
                    else:
                        if os.path.isfile(strat_json_path):
                            ts_backup = dt.datetime.now().strftime("%Y%m%d_%H%M")
                            backup_name = os.path.join(sdir, f"BAK_{strategy}_{ts_backup}.json")
                            shutil.move(strat_json_path, backup_name)
                        if not os.path.isfile(chosen_path):
                            msg = f"[APPLY] Fichier choisi introuvable: {chosen_path}"
                            yield sse_format("err", msg)
                            with open(log_path, "a", encoding="utf-8") as f: f.write("ERR: " + msg + "\n")
                            rc = 1
                        else:
                            shutil.move(chosen_path, strat_json_path)
            except Exception as e:
                rc = 1
                err = f"[APPLY] Erreur: {e}"
                yield sse_format("err", err)
                with open(log_path, "a", encoding="utf-8") as f: f.write("ERR: " + err + "\n")

        # === GIT PUSH ===
        elif is_gitpush:
            if not git_path_single:
                msg = "Aucun chemin sélectionné."
                yield sse_format("warn", msg)
                with open(log_path, "a", encoding="utf-8") as f: f.write("WARN: " + msg + "\n")
                rc = 1
            else:
                for cmd_ in (["git","-C",git_path_single,"add","-A"],
                             ["git","-C",git_path_single,"commit","-m",f"auto push {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
                             ["git","-C",git_path_single,"push"]):
                    try:
                        proc = subprocess.Popen(
                            cmd_, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1,
                            cwd=PROJECT_DIR
                        )
                    except Exception as e:
                        err = f"[GIT] Impossible d'exécuter: {e}"
                        yield sse_format("err", err)
                        with open(log_path, "a", encoding="utf-8") as f: f.write("ERR: " + err + "\n")
                        rc = 1
                        break

                    for raw in proc.stdout:
                        line = raw.rstrip("\r\n")
                        low = line.lower()
                        # UI: WARN/ERR only
                        if is_warn_err(low):
                            yield sse_format("warn" if "warn" in low else "err", line)
                        # Log: complet pour git
                        with open(log_path, "a", encoding="utf-8") as f: f.write(line + "\n")
                    code = proc.wait()
                    if code != 0:
                        rc = 1

        # === BACKTEST / BEAR / HYPEROPT ===
        elif is_backtest or is_backtest_bear or is_hyperopt:
            try:
                if is_backtest:
                    cmd_local = build_cmd("backtest", strategy, start_ymd, end_ymd=end_ymd)
                elif is_backtest_bear:
                    cmd_local = build_cmd("backtest_bear", strategy, start_ymd)
                else:
                    cmd_local = build_cmd("hyperopt", strategy, start_ymd, epochs=epochs, spaces=spaces)

                proc = subprocess.Popen(
                    cmd_local, cwd=PROJECT_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", bufsize=1,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
            except Exception as e:
                yield sse_format("err", f"Impossible de démarrer le processus: {e}")
                payload = {"returncode": 1, "log_download": ""}
                yield sse_format("end", json.dumps(payload))
                return

            # Capture des résultats
            result_buf = []
            seen_result = False
            start_token = "hyperopt results" if is_hyperopt else "result for strategy"

            for raw in proc.stdout:
                line = raw.rstrip("\r\n")
                low = line.lower()

                # Log complet pour ces actions
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")

                # UI: WARN / ERR uniquement
                if is_warn_err(low):
                    yield sse_format("warn" if "warn" in low else "err", line)

                # Capture résultat
                if not seen_result and start_token in low:
                    seen_result = True
                if seen_result:
                    result_buf.append(line)

            rc = proc.wait()

            # Envoie le bloc résultat à la fin (évènement dédié)
            if result_buf:
                yield sse_format("result", "\n".join(result_buf))

        # === DOWNLOAD (multi-TF) ===
        elif is_download:
            if total_steps_download == 0:
                yield sse_format("warn", "[DOWNLOAD] Aucune étape planifiée (pas de paires/timeframes).")
                log_download = "/logs/" + os.path.basename(log_path)
                yield sse_format("end", json.dumps({"returncode": 0, "log_download": log_download, "total_steps": total_steps_download}))
                return

            for tf in tfs_list:
                try:
                    cmd_local = build_cmd("download", strategy, start_ymd, timeframe=tf, erase=erase)
                    proc = subprocess.Popen(
                        cmd_local, cwd=PROJECT_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace", bufsize=1,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    )
                except Exception as e:
                    err = f"[DOWNLOAD] Impossible de démarrer la commande (tf={tf}): {e}"
                    yield sse_format("err", err)
                    with open(log_path, "a", encoding="utf-8") as f: f.write("ERR: " + err + "\n")
                    continue

                for raw in proc.stdout:
                    line = raw.rstrip("\r\n")
                    low = line.lower()

                    # Progression : basée sur "... Downloaded data for ...".
                    if "downloaded data for" in low:
                        if prog_current < total_steps_download:
                            prog_current += 1
                            yield emit_progress()

                    # UI: WARN/ERR seulement
                    if is_warn_err(low):
                        yield sse_format("warn" if "warn" in low else "err", line)
                        # Log Download: WARN/ERR seulement
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(("WARN: " if "warn" in low else "ERR: ") + line + "\n")

                code = proc.wait()
                if code != 0:
                    msg = f"[DOWNLOAD] Commande terminée avec code {code} (tf={tf})"
                    yield sse_format("warn", msg)
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write("WARN: " + msg + "\n")

        log_download = "/logs/" + os.path.basename(log_path)
        payload = {"returncode": rc, "log_download": log_download}
        if action == "download":
            payload["total_steps"] = total_steps_download
        yield sse_format("end", json.dumps(payload))

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}
    return Response(generate(), mimetype="text/event-stream", headers=headers)

@app.get("/logs/")
def list_logs():
    files = sorted(os.listdir(LOG_DIR))
    links = "\n".join(f'<li><a href="{fn}" target="_blank">{fn}</a></li>' for fn in files)
    html = f"""
    <h2>Logs</h2>
    <ul>
      {links or "<li>(vide)</li>"}
    </ul>
    """
    return html

@app.get("/logs/<path:filename>")
def get_log(filename):
    return send_from_directory(LOG_DIR, filename, as_attachment=False)

# --- APIs pour refresh UI ---
@app.get("/api/list_strategies")
def api_list_strategies():
    return jsonify({"strategies": list_strategies()})

@app.get("/api/list_jsons")
def api_list_jsons():
    return jsonify({"json_files": list_strategy_jsons()})

@app.get("/api/list_jsons_apply")
def api_list_jsons_apply():
    return jsonify({"json_files_apply": list_strategy_jsons_no_bakprefix()})

@app.get("/api/git_paths")
def api_git_paths():
    return jsonify({"git_paths_list": read_git_paths_list()})

if __name__ == "__main__":
    # .\\.venv\\Scripts\\python.exe -m pip install flask
    # .\\.venv\\Scripts\\python.exe app.py
    app.run(host="127.0.0.1", port=5000, debug=False)
