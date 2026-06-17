"""
Stock Exchange — The Ultimate Trading Challenge
=================================================
Run:   python stock_exchange.py
Open:  http://localhost:8080          ← Player view
Admin: http://localhost:8080/admin    ← Admin panel  (password: admin123)

No external dependencies — pure Python stdlib.
"""

import http.server
import socketserver
import json
import threading
import webbrowser
import random
import math
import urllib.parse
from datetime import datetime

PORT = 8080
ADMIN_PASSWORD = "admin123"

# ── Price volatility config ───────────────────────────────────────────────────
# Each ticker gets its own volatility (% max drift per tick) and mean-reversion strength
VOLATILITY = {
    "SREN": 0.004, "CB": 0.003, "ALV": 0.006,
    "GS": 0.005, "MRSH": 0.004, "BAH": 0.009,
    "JPM": 0.002, "MS": 0.007, "ACN": 0.008,
    "IFC": 0.005, "HSBC": 0.004, "MUVGn": 0.006,
}
MEAN_REVERSION = 0.015   # pull back toward base per tick
TICK_INTERVAL  = 2       # seconds between price ticks

# ── Shared game state ─────────────────────────────────────────────────────────
state = {
    "players":       {},       # token → {name, team, balance, portfolio, trades, joined_at}
    "admin_sessions": set(),
    "game_active":   False,
    "news_feed":     [],
    "price_history": {},       # ticker → list of (timestamp_str, price)  (last 30 ticks)
    "prices": {
        "SREN": {"name": "Swiss Re Group", "base": 145, "current": 145, "color": "#3b82f6"},
        "CB": {"name": "Chubb", "base": 309, "current": 309, "color": "#22c55e"},
        "ALV": {"name": "Allianz", "base": 113, "current": 113, "color": "#f97316"},
        "GS": {"name": "Goldman Sachs", "base": 1053, "current": 1053, "color": "#a855f7"},
        "MRSH": {"name": "Marsh McLennan", "base": 157, "current": 157, "color": "#eab308"},
        "BAH": {"name": "Booz Allen Hamilton", "base": 69, "current": 69, "color": "#ef4444"},
        "JPM": {"name": "JP Morgan", "base": 317, "current": 317, "color": "#42f9f9"},
        "MS": {"name": "Morgan Stanley", "base": 214, "current": 214, "color": "#ef2864"},
        "ACN": {"name": "Accenture", "base": 154, "current": 154, "color": "#a30542"},
        "IFC": {"name": "Intact Financial Corporation", "base": 187, "current": 187, "color": "#bee610"},
        "HSBC": {"name": "The Hongkong and Shanghai Banking Corporation", "base": 90, "current": 90, "color": "#70b0e0"},
        "MUVGn": {"name": "Munich Re", "base": 502, "current": 502, "color": "#d15536"},
    },
    "news_pool": [
        {"id":"N01","title":"Climate Catastrophe Alert","category":"Natural Disaster",
         "description":"Global reinsurers warn that insured losses from natural catastrophes could exceed $150 billion this year as hurricanes and floods become more frequent.",
         "impacts":{"SREN":-8,"MUVGn":-8,"CB":-5,"IFC":-6,"ALV":-3}},
        {"id":"N02","title":"Underwriting Excellence","category":"Earnings Report",
         "description":"A leading insurer reports a sharp rise in quarterly profits after maintaining one of the industry's best combined ratios and disciplined underwriting standards.",
         "impacts":{"CB":+10,"ALV":+3,"IFC":+2,"SREN":+1,"MUVGn":+1}},
        {"id":"N03","title":"Strategic Divestment Pays Off","category":"Corporate Action",
         "description":"A European financial services giant records a significant profit boost after divesting a stake in one of its Asian insurance ventures.",
         "impacts":{"ALV":+9,"HSBC":+2,"ACN":+1}},
        {"id":"N04","title":"Dealmaking Revival","category":"Banking",
         "description":"Central banks signal interest rates may remain elevated for longer, while mergers and acquisitions activity rebounds globally.",
         "impacts":{"GS":+8,"JPM":+7,"MS":+7,"HSBC":+5,"ACN":+2}},
        {"id":"N05","title":"Cyber Threat Escalation","category":"Cybersecurity",
         "description":"A wave of sophisticated cyberattacks on multinational corporations leads businesses to dramatically increase spending on cyber risk advisory and insurance services.",
         "impacts":{"MRSH":+10,"ACN":+6,"BAH":+4,"CB":3,"ALV":+2}},
        {"id":"N06","title":"Regulatory Crackdown","category":"Regulation",
         "description":"Regulators launch an investigation into audit quality and consulting independence across several major professional services firms.",
         "impacts":{"BAH":-10,"ACN":-3,"MRSH":-2}},
        {"id":"N07","title":"Trading Boom","category":"Financial Markets",
         "description":"One of the world's largest banks reports record trading revenues as market volatility drives increased client activity.",
         "impacts":{"JPM":+9,"GS":+8,"MS":+7,"HSBC":+3}},
        {"id":"N08","title":"Wealth Surge","category":"Wealth Management",
         "description":"Global wealth creation reaches an all-time high, pushing assets under management at major wealth-management firms to record levels.",
         "impacts":{"MS":+10,"JPM":5,"HSBC":4,"GS":3}},
        {"id":"N09","title":"AI Spending Frenzy","category":"Technology",
         "description":"Governments and Fortune 500 companies announce billions of dollars in spending on artificial intelligence transformation and cloud modernization projects.",
         "impacts":{"ACN":+10,"BAH":5,"MRSH":2,"JPM":1}},
        {"id":"N10","title":"Wildfire Crisis","category":"Natural Disaster",
         "description":"An unusually severe wildfire season causes insured losses across several provinces, leading analysts to revise claim estimates upward.",
         "impacts":{"IFC":-10,"CB":-6,"ALV":-4,"SREN":-3,"MUVGn":-3}},
        {"id":"N11","title":"Capital Strength Recorded","category":"Corporate Finance",
         "description":"A major international bank unveils a multi-billion-dollar share buyback after exceeding capital adequacy requirements.",
         "impacts":{"HSBC":+9,"JPM":+3,"MS":+2,"GS":+2}},
        {"id":"N12","title":"Reinsurance Price Surge","category":"Insurance Market",
         "description":"Property and casualty reinsurance rates rise sharply during annual renewals as insurers seek protection against increasing catastrophe losses.",
         "impacts":{"MUVGn":+10,"SREN":+10,"CB":-3,"IFC":-4,"ALV":-2}},
        {"id":"N13","title":"Asian Growth Opportunity","category":"Emerging Markets",
         "description":"A rapidly growing middle class in Asia drives strong demand for life insurance and retirement planning products.",
         "impacts":{"ALV":+8,"HSBC":+7,"MRSH":+2}},
        {"id":"N14","title":"Mega Brokerage Deal","category":"Brokerage",
         "description":"Several large corporations consolidate their insurance brokerage relationships under a single global risk advisory provider.",
         "impacts":{"MRSH":+10,"CB":2,"ALV":+2}},
        {"id":"N15","title":"Banking Rules Relaxed","category":"Regulation",
         "description":"Financial regulators ease restrictions on investment banking activities to stimulate economic growth.",
         "impacts":{"GS":+10,"MS":+8,"JPM":+7,"HSBC":+3}},
        {"id":"N16","title":"IPO Freeze","category":"Economic Slowdown",
         "description":"Economic uncertainty causes corporations to delay acquisitions and public listings worldwide.",
         "impacts":{"GS":-10,"MS":-8,"JPM":-6,"HSBC":-2}},
    ],
    "lock": threading.Lock()
}

# Initialise price history
for _t in state["prices"]:
    state["price_history"][_t] = []

# ── Helpers ───────────────────────────────────────────────────────────────────

def generate_token():
    return "%016x" % random.getrandbits(64)

def get_player(token):
    return state["players"].get(token)

def portfolio_value(player):
    total = player["balance"]
    for ticker, qty in player["portfolio"].items():
        total += state["prices"].get(ticker, {}).get("current", 0) * qty
    return round(total, 2)

def apply_news_impact(news_item):
    for ticker, pct in news_item["impacts"].items():
        if ticker in state["prices"]:
            state["prices"][ticker]["current"] = round(
                state["prices"][ticker]["current"] * (1 + pct / 100), 2)

def do_full_reset():
    """Reset everything except admin sessions and news pool."""
    with state["lock"]:
        state["players"].clear()
        state["news_feed"].clear()
        state["game_active"] = False
        for ticker, p in state["prices"].items():
            p["current"] = p["base"]
        for ticker in state["price_history"]:
            state["price_history"][ticker].clear()

# ── Background price fluctuation thread ──────────────────────────────────────

def price_tick():
    """Runs every TICK_INTERVAL seconds, nudges prices with mean-reversion Brownian motion."""
    while True:
        import time; time.sleep(TICK_INTERVAL)
        if not state["game_active"]:
            continue
        ts = datetime.now().strftime("%H:%M:%S")
        with state["lock"]:
            for ticker, p in state["prices"].items():
                vol  = VOLATILITY.get(ticker, 0.005)
                base = p["base"]
                cur  = p["current"]
                # Gaussian shock
                shock = random.gauss(0, vol)
                # Mean reversion: nudge back toward base proportionally
                reversion = MEAN_REVERSION * (base - cur) / base
                new_price = cur * (1 + shock + reversion)
                # Hard floor at 40% of base, ceiling at 250% of base
                new_price = max(base * 0.40, min(base * 2.50, new_price))
                p["current"] = round(new_price, 2)
                # Store history (keep last 40 ticks)
                hist = state["price_history"][ticker]
                hist.append((ts, p["current"]))
                if len(hist) > 40:
                    hist.pop(0)

threading.Thread(target=price_tick, daemon=True).start()

# ── CSS ───────────────────────────────────────────────────────────────────────

COMMON_CSS = """
:root{
  --bg:#0f1117;--bg2:#161a24;--bg3:#1e2330;
  --card:#1a1f2e;--card2:#222840;
  --border:rgba(255,255,255,0.07);--border2:rgba(255,255,255,0.16);
  --text:#e8eaed;--text2:#8c94a8;--text3:#555f78;
  --blue:#3b82f6;--blue2:#1d4ed8;--blue-glow:rgba(59,130,246,0.15);
  --green:#22c55e;--green-dim:#14532d;
  --red:#ef4444;--red-dim:#7f1d1d;
  --orange:#f97316;--gold:#f59e0b;
  --radius:8px;--radius-lg:14px;
  --font:'Inter',system-ui,-apple-system,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font);background:var(--bg);color:var(--text);line-height:1.6;min-height:100vh}
a{color:var(--blue);text-decoration:none}
input,select{font-family:inherit}
.btn{display:inline-flex;align-items:center;gap:6px;padding:10px 20px;border-radius:var(--radius);border:none;font-size:14px;font-weight:500;cursor:pointer;transition:all .15s}
.btn-primary{background:var(--blue);color:#fff}.btn-primary:hover{opacity:.88}
.btn-success{background:var(--green);color:#fff}.btn-success:hover{opacity:.88}
.btn-danger{background:var(--red);color:#fff}.btn-danger:hover{opacity:.88}
.btn-ghost{background:transparent;border:1px solid var(--border2);color:var(--text)}.btn-ghost:hover{background:var(--bg3)}
.btn-warn{background:var(--gold);color:#000}.btn-warn:hover{opacity:.88}
.btn-sm{padding:6px 14px;font-size:13px}
.btn:disabled{opacity:.35;cursor:not-allowed}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-lg);padding:24px}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:500}
.badge-up{background:var(--green-dim);color:var(--green)}
.badge-dn{background:var(--red-dim);color:var(--red)}
.badge-neu{background:var(--bg3);color:var(--text2)}
.badge-blue{background:var(--blue-glow);color:var(--blue)}
.up{color:var(--green)}.dn{color:var(--red)}
.label{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--text3);font-weight:500}
.flash{padding:12px 16px;border-radius:var(--radius);font-size:14px;margin-bottom:16px}
.flash-err{background:var(--red-dim);border:1px solid var(--red);color:#fca5a5}
.flash-ok{background:var(--green-dim);border:1px solid var(--green);color:#86efac}
.flash-warn{background:#451a03;border:1px solid var(--gold);color:#fde68a}
"""

def page(title, body):
    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title} — Stock Exchange</title>
<style>{COMMON_CSS}</style>
</head><body>{body}</body></html>"""

# ── Register page ─────────────────────────────────────────────────────────────

def render_register(flash="", flash_type="err"):
    fh = f'<div class="flash flash-{flash_type}">{flash}</div>' if flash else ""
    badge = ('<span class="badge badge-up">🟢 Game Live — join now!</span>'
             if state["game_active"] else
             '<span class="badge badge-neu">⏳ Waiting for admin to start</span>')
    return page("Register", f"""
<style>
body{{display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px}}
.wrap{{width:100%;max-width:420px}}
.logo{{font-size:28px;font-weight:700;letter-spacing:-.03em;text-align:center;margin-bottom:6px}}
.logo em{{font-style:normal;color:var(--blue)}}
.sub{{text-align:center;color:var(--text2);font-size:14px;margin-bottom:28px}}
.field{{margin-bottom:16px}}
.field label{{display:block;font-size:13px;color:var(--text2);margin-bottom:6px;font-weight:500}}
.field input{{width:100%;background:var(--bg3);border:1px solid var(--border2);border-radius:var(--radius);padding:10px 14px;color:var(--text);font-size:15px;outline:none}}
.field input:focus{{border-color:var(--blue)}}
</style>
<div class="wrap">
  <div class="logo"><em>Stock</em>Exchange</div>
  <div class="sub">The Ultimate Trading Challenge</div>
  <div style="text-align:center;margin-bottom:24px">{badge}</div>
  {fh}
  <div class="card">
    <form method="POST" action="/register">
      <div class="field"><label>Your name</label><input name="name" placeholder="e.g. Arjun Sharma" required autocomplete="off"/></div>
      <div class="field"><label>Team name</label><input name="team" placeholder="e.g. RiskRaptors" required autocomplete="off"/></div>
      <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;padding:12px">Join the game →</button>
    </form>
  </div>
  <p style="text-align:center;font-size:13px;color:var(--text3);margin-top:20px">Already registered? <a href="/trade">Go to trading floor</a></p>
</div>""")

# ── Trading Floor ─────────────────────────────────────────────────────────────

def render_trade(player, flash="", flash_type="err"):
    fh = f'<div class="flash flash-{flash_type}">{flash}</div>' if flash else ""
    pv   = portfolio_value(player)
    gain = pv - 100000
    gc   = "up" if gain >= 0 else "dn"
    gs   = "+" if gain >= 0 else ""

    price_cards = ""
    for ticker, p in state["prices"].items():
        chg  = round((p["current"] - p["base"]) / p["base"] * 100, 2)
        cc   = "up" if chg >= 0 else "dn"
        arrow = "▲" if chg >= 0 else "▼"
        held  = player["portfolio"].get(ticker, 0)
        sell_attr = '' if held > 0 else 'disabled'
        price_cards += f"""
<div class="p-card" id="pc-{ticker}" data-base="{p['base']}" data-color="{p['color']}">
  <div style="display:flex;justify-content:space-between;align-items:start">
    <div>
      <div class="label" style="color:{p['color']}">{ticker}</div>
      <div style="font-size:14px;font-weight:500;margin-top:3px;color:var(--text2)">{p['name']}</div>
    </div>
    <div style="text-align:right">
      <div class="pc-price" style="font-size:22px;font-weight:700;font-variant-numeric:tabular-nums">₹{p['current']:,.2f}</div>
      <div class="pc-chg {cc}" style="font-size:13px">{arrow} {abs(chg)}%</div>
    </div>
  </div>
  <canvas class="pc-spark" width="220" height="36" style="width:100%;margin:10px 0 2px;display:block"></canvas>
  <div style="padding-top:10px;border-top:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;gap:8px">
    <span style="font-size:13px;color:var(--text2)">Held: <strong class="pc-held" style="color:var(--text)">{held}</strong></span>
    <div style="display:flex;gap:6px;align-items:center">
      <input type="number" class="qty-input" id="qty-{ticker}" min="1" value="1"
             style="width:58px;background:var(--bg3);border:1px solid var(--border2);border-radius:var(--radius);padding:5px 8px;color:var(--text);font-size:14px;text-align:center"/>
      <button class="btn btn-success btn-sm" onclick="doTrade('{ticker}','buy')">Buy</button>
      <button class="btn btn-danger btn-sm" id="sell-{ticker}" onclick="doTrade('{ticker}','sell')" {sell_attr}>Sell</button>
    </div>
  </div>
</div>"""

    news_html = ""
    if state["news_feed"]:
        for n in reversed(state["news_feed"]):
            impacts = ", ".join(f"{t} {'+' if v>0 else ''}{v}%" for t,v in n["impacts"].items())
            news_html += f"""
<div class="news-item">
  <div style="display:flex;justify-content:space-between;align-items:start;gap:10px">
    <div>
      <div style="font-weight:600;font-size:14px">{n['title']}</div>
      <div style="font-size:13px;color:var(--text2);margin-top:3px">{n['description']}</div>
    </div>
    <span class="badge badge-blue" style="white-space:nowrap;flex-shrink:0">{n['category']}</span>
  </div>
  <div style="margin-top:7px;font-size:12px;color:var(--text3)">{n['released_at']}</div>
</div>"""
    else:
        news_html = '<p style="color:var(--text3);font-size:14px;text-align:center;padding:20px 0">No news yet — stay tuned.</p>'

    port_rows = ""
    for ticker, qty in player["portfolio"].items():
        if qty > 0:
            cp = state["prices"][ticker]["current"]
            val = round(cp * qty, 2)
            port_rows += f"<tr><td style='color:{state['prices'][ticker]['color']};font-weight:600'>{ticker}</td><td>{state['prices'][ticker]['name']}</td><td>{qty}</td><td>₹{cp:,.2f}</td><td>₹{val:,.2f}</td></tr>"
    if not port_rows:
        port_rows = '<tr><td colspan="5" style="text-align:center;color:var(--text3);padding:20px">No positions yet.</td></tr>'

    game_banner = ""
    if not state["game_active"]:
        game_banner = '<div style="background:var(--bg3);border:1px solid var(--border2);border-radius:var(--radius);padding:12px 16px;font-size:14px;color:var(--text2);margin-bottom:16px;text-align:center">⏳ Game not started yet. Trading is disabled.</div>'

    # Serialize history for JS
    hist_json = json.dumps({t: state["price_history"][t] for t in state["prices"]})

    return page("Trading Floor", f"""
<style>
.topbar{{background:var(--bg2);border-bottom:1px solid var(--border);padding:12px 20px;display:flex;align-items:center;justify-content:space-between;gap:12px;position:sticky;top:0;z-index:50;flex-wrap:wrap}}
.brand{{font-size:16px;font-weight:700}}.brand em{{font-style:normal;color:var(--blue)}}
.pill{{background:var(--bg3);border-radius:var(--radius);padding:5px 12px;font-size:13px;display:flex;align-items:center;gap:6px}}
.main{{max-width:1240px;margin:0 auto;padding:20px;display:grid;grid-template-columns:1fr 300px;gap:20px}}
@media(max-width:820px){{.main{{grid-template-columns:1fr}}}}
.p-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}}
.p-card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-lg);padding:16px;transition:border-color .2s}}
.p-card:hover{{border-color:var(--border2)}}
.sidebar{{display:flex;flex-direction:column;gap:16px}}
.news-item{{padding:12px 0;border-bottom:1px solid var(--border)}}.news-item:last-child{{border-bottom:none}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{text-align:left;padding:8px 12px;background:var(--bg3);color:var(--text3);font-size:11px;text-transform:uppercase;letter-spacing:.05em}}
td{{padding:9px 12px;border-bottom:1px solid var(--border)}}
#toast{{position:fixed;bottom:20px;right:20px;background:var(--card2);border:1px solid var(--border2);border-radius:var(--radius);padding:11px 18px;font-size:14px;display:none;z-index:300;box-shadow:0 8px 32px rgba(0,0,0,.5);transition:opacity .3s}}
.qty-input{{outline:none}}
#newsModal{{position:fixed;inset:0;background:rgba(0,0,0,.75);display:none;align-items:center;justify-content:center;z-index:500;backdrop-filter:blur(4px)}}
#newsModal.show{{display:flex}}
.nm-box{{background:var(--card2);border:2px solid var(--blue);border-radius:var(--radius-lg);max-width:520px;width:92%;padding:26px;animation:popIn .35s cubic-bezier(.34,1.56,.64,1);box-shadow:0 20px 60px rgba(0,0,0,.6)}}
@keyframes popIn{{from{{transform:scale(.7);opacity:0}}to{{transform:scale(1);opacity:1}}}}
.nm-badge{{display:inline-block;background:var(--red);color:#fff;font-size:11px;font-weight:700;letter-spacing:.1em;padding:4px 10px;border-radius:4px;margin-bottom:12px}}
.nm-title{{font-size:22px;font-weight:700;margin-bottom:8px}}
.nm-cat{{font-size:12px;color:var(--text3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px}}
.nm-desc{{font-size:14px;color:var(--text2);line-height:1.55;margin-bottom:16px}}
.nm-impacts{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}}
.nm-imp{{background:var(--bg3);border:1px solid var(--border2);border-radius:6px;padding:6px 10px;font-size:13px;font-weight:600}}
.nm-imp.up{{color:var(--green)}}.nm-imp.dn{{color:var(--red)}}
</style>
<div class="topbar">
  <div class="brand"><em>Stock</em>Exchange <span style="font-size:13px;color:var(--text3);font-weight:400">Trading Floor</span></div>
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <div class="pill">👤 {player['name']}</div>
    <div class="pill">🏷 {player['team']}</div>
    <div class="pill">💰 <strong id="live-bal">₹{player['balance']:,.2f}</strong></div>
    <div class="pill">📊 <strong id="live-pv" class="{gc}">₹{pv:,.2f}</strong></div>
    <div class="pill">P&L: <span id="live-pnl" class="{gc}">{gs}₹{abs(gain):,.2f}</span></div>
  </div>
</div>
{fh}
<div class="main">
  <div>
    {game_banner}
    <div class="label" style="margin-bottom:14px">Stock Exchange Market</div>
    <div class="p-grid">{price_cards}</div>
    <div class="card" style="margin-top:20px;padding:0;overflow:hidden">
      <div class="label" style="padding:14px 16px 10px">My Portfolio</div>
      <table>
        <thead><tr><th>Ticker</th><th>Stock</th><th>Qty</th><th>Price</th><th>Value</th></tr></thead>
        <tbody id="port-body">{port_rows}</tbody>
      </table>
    </div>
  </div>
  <div class="sidebar">
    <div class="card">
      <div class="label" style="margin-bottom:10px">📰 News Feed</div>
      <div id="news-feed">{news_html}</div>
    </div>
  </div>
</div>
<div id="newsModal" onclick="closeNews(event)">
  <div class="nm-box" onclick="event.stopPropagation()">
    <div class="nm-badge">📢 BREAKING NEWS</div>
    <div class="nm-cat" id="nm-cat"></div>
    <div class="nm-title" id="nm-title"></div>
    <div class="nm-desc" id="nm-desc"></div>
    <button class="btn btn-primary" style="width:100%" onclick="closeNews()">Got it — back to trading</button>
  </div>
</div>
<div id="toast"></div>
<script>
const PRICES_META = {json.dumps({t:{"base":p["base"],"name":p["name"],"color":p["color"]} for t,p in state["prices"].items()})};
let priceHistory = {hist_json};
let lastNewsCount = {len(state["news_feed"])};
let newsFeedCache = {json.dumps(state["news_feed"])};

// ── Sparkline renderer ────────────────────────────────────────────────────────
function drawSpark(canvas, ticker, color) {{
  const hist = priceHistory[ticker];
  if (!hist || hist.length < 2) return;
  const vals = hist.map(h => h[1]);
  const min = Math.min(...vals), max = Math.max(...vals);
  const w = canvas.width, h = canvas.height;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, w, h);
  const range = max - min || 1;
  const pts = vals.map((v, i) => [i / (vals.length - 1) * w, h - ((v - min) / range) * (h - 4) - 2]);
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, color + '55');
  grad.addColorStop(1, color + '00');
  ctx.beginPath();
  ctx.moveTo(pts[0][0], h);
  pts.forEach(([x, y]) => ctx.lineTo(x, y));
  ctx.lineTo(pts[pts.length-1][0], h);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();
  ctx.beginPath();
  pts.forEach(([x, y], i) => i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y));
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.stroke();
}}

function drawAllSparks() {{
  document.querySelectorAll('.p-card').forEach(card => {{
    const ticker = card.id.replace('pc-', '');
    const canvas = card.querySelector('.pc-spark');
    const color = card.dataset.color;
    if (canvas) drawSpark(canvas, ticker, color);
  }});
}}

// ── Toast ─────────────────────────────────────────────────────────────────────
function toast(msg, ok=true) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.display = 'block';
  t.style.borderColor = ok ? 'var(--green)' : 'var(--red)';
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.style.display = 'none', 3200);
}}

// ── Trade ─────────────────────────────────────────────────────────────────────
async function doTrade(ticker, action) {{
  const qty = parseInt(document.getElementById('qty-' + ticker).value) || 1;
  const res = await fetch('/api/trade', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{ticker, action, qty}})
  }});
  const d = await res.json();
  toast(d.msg, d.ok);
  if (d.ok) refresh();
}}

// ── Refresh loop ──────────────────────────────────────────────────────────────
async function refresh() {{
  const r = await fetch('/api/state');
  const d = await r.json();
  if (!d.ok) return;
  // Prices & sparks
  priceHistory = d.price_history;
  Object.entries(d.prices).forEach(([t, p]) => {{
    const card = document.getElementById('pc-' + t);
    if (!card) return;
    const base = parseFloat(card.dataset.base);
    const chg  = ((p.current - base) / base * 100).toFixed(2);
    const up   = chg >= 0;
    card.querySelector('.pc-price').textContent = '₹' + p.current.toLocaleString('en-IN', {{minimumFractionDigits:2}});
    const chgEl = card.querySelector('.pc-chg');
    chgEl.textContent = (up ? '▲ ' : '▼ ') + Math.abs(chg) + '%';
    chgEl.className = 'pc-chg ' + (up ? 'up' : 'dn');
    const heldEl = card.querySelector('.pc-held');
    const held = d.player.portfolio[t] || 0;
    if (heldEl) heldEl.textContent = held;
    const sellBtn = document.getElementById('sell-' + t);
    if (sellBtn) sellBtn.disabled = held === 0;
  }});
  drawAllSparks();
  // Stats
  const bal = d.player.balance;
  const pv  = d.player.portfolio_value;
  const gain = pv - 100000;
  document.getElementById('live-bal').textContent = '₹' + bal.toLocaleString('en-IN', {{minimumFractionDigits:2}});
  const pvEl = document.getElementById('live-pv');
  pvEl.textContent = '₹' + pv.toLocaleString('en-IN', {{minimumFractionDigits:2}});
  pvEl.className = gain >= 0 ? 'up' : 'dn';
  const pnlEl = document.getElementById('live-pnl');
  pnlEl.textContent = (gain >= 0 ? '+' : '') + '₹' + Math.abs(gain).toLocaleString('en-IN', {{minimumFractionDigits:2}});
  pnlEl.className = gain >= 0 ? 'up' : 'dn';
  // Portfolio table
  const pb = document.getElementById('port-body');
  if (Object.keys(d.player.portfolio).filter(t => d.player.portfolio[t] > 0).length === 0) {{
    pb.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text3);padding:20px">No positions yet.</td></tr>';
  }} else {{
    pb.innerHTML = Object.entries(d.player.portfolio).filter(([,q]) => q > 0).map(([t, q]) => {{
      const pr = d.prices[t].current;
      const val = (pr * q).toLocaleString('en-IN', {{minimumFractionDigits:2}});
      return `<tr><td style="color:${{d.prices[t].color}};font-weight:600">${{t}}</td><td>${{PRICES_META[t].name}}</td><td>${{q}}</td><td>₹${{pr.toLocaleString('en-IN',{{minimumFractionDigits:2}})}}</td><td>₹${{val}}</td></tr>`;
    }}).join('');
  }}
  // News popup
  const feed = d.news_feed || [];
  if (feed.length > lastNewsCount) {{
    const latest = feed[feed.length - 1];
    showNewsModal(latest);
    lastNewsCount = feed.length;
    newsFeedCache = feed;
    setTimeout(() => location.reload(), 8000);
  }}
}}


function showNewsModal(n) {{
  document.getElementById('nm-cat').textContent = n.category || '';
  document.getElementById('nm-title').textContent = n.title || '';
  document.getElementById('nm-desc').textContent = n.description || '';
  document.getElementById('newsModal').classList.add('show');
  try {{
    const ctx = new (window.AudioContext||window.webkitAudioContext)();
    const o = ctx.createOscillator(); const g = ctx.createGain();
    o.connect(g); g.connect(ctx.destination);
    o.frequency.value = 880; g.gain.value = 0.08;
    o.start(); o.frequency.exponentialRampToValueAtTime(440, ctx.currentTime+0.25);
    g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime+0.4);
    o.stop(ctx.currentTime+0.4);
  }} catch(e) {{}}
}}
function closeNews(e) {{
  if (e && e.target.id !== 'newsModal' && e.type === 'click') {{}}
  document.getElementById('newsModal').classList.remove('show');
}}

drawAllSparks();
setInterval(refresh, 3500);
</script>""")

# ── Admin Panel ───────────────────────────────────────────────────────────────

def render_admin(flash="", flash_type="ok"):
    fh = f'<div class="flash flash-{flash_type}">{flash}</div>' if flash else ""
    game_active = state["game_active"]
    toggle_label = "⏸ Pause Game" if game_active else "▶ Start Game"
    toggle_cls   = "btn-danger" if game_active else "btn-success"
    game_badge   = ('<span class="badge badge-up">🟢 Live</span>' if game_active
                    else '<span class="badge badge-neu">⏸ Paused</span>')

    # ── Stat cards
    total_trades = sum(p["trades"] for p in state["players"].values())

    # ── Leaderboard
    sorted_players = sorted(state["players"].values(), key=portfolio_value, reverse=True)
    lb_rows = ""
    for i, p in enumerate(sorted_players):
        pv   = portfolio_value(p)
        gain = pv - 100000
        gc   = "up" if gain >= 0 else "dn"
        medal = ["🥇","🥈","🥉"][i] if i < 3 else f"#{i+1}"
        lb_rows += f"""
<tr>
  <td>{medal}</td>
  <td><strong>{p['name']}</strong></td>
  <td style="color:var(--text2)">{p['team']}</td>
  <td>₹{p['balance']:,.0f}</td>
  <td>₹{pv:,.0f}</td>
  <td class="{gc}">{'+'if gain>=0 else ''}₹{abs(gain):,.0f}</td>
  <td style="color:var(--text2)">{p['trades']}</td>
  <td style="font-size:12px;color:var(--text3)">{p['joined_at']}</td>
</tr>"""
    if not lb_rows:
        lb_rows = '<tr><td colspan="8" style="text-align:center;color:var(--text3);padding:24px">No players yet.</td></tr>'

    # ── News cards
    released_ids = {n["id"] for n in state["news_feed"]}
    news_cards = ""
    for n in state["news_pool"]:
        done = n["id"] in released_ids
        impacts = " · ".join(f"{t} {'+'if v>0 else ''}{v}%" for t,v in n["impacts"].items())
        badge   = '<span class="badge badge-up" style="font-size:11px">✓ Released</span>' if done else '<span class="badge badge-neu" style="font-size:11px">Pending</span>'
        btn     = ('<button class="btn btn-ghost btn-sm" disabled>Released</button>'
                   if done else
                   f'<form method="POST" action="/admin/release" style="display:inline"><input type="hidden" name="news_id" value="{n["id"]}"><button type="submit" class="btn btn-primary btn-sm">📢 Release</button></form>')
        news_cards += f"""
<div class="news-card {'released' if done else ''}">
  <div style="display:flex;justify-content:space-between;align-items:start;gap:10px;margin-bottom:8px">
    <div style="font-weight:600;font-size:14px">{n['title']}</div>{badge}
  </div>
  <div style="font-size:12px;color:var(--text3);margin-bottom:4px">{n['category']}</div>
  <div style="font-size:13px;color:var(--text2);margin-bottom:10px">{n['description']}</div>
  <div style="font-size:12px;color:var(--text3);margin-bottom:12px">↕ {impacts}</div>
  {btn}
</div>"""

    # ── Price rows
    price_rows = ""
    for ticker, p in state["prices"].items():
        chg = round((p["current"] - p["base"]) / p["base"] * 100, 2)
        gc  = "up" if chg >= 0 else "dn"
        hist = state["price_history"].get(ticker, [])
        spark_data = json.dumps([v for _, v in hist])
        price_rows += f"""
<tr>
  <td><strong style="color:{p['color']}">{ticker}</strong></td>
  <td>{p['name']}</td>
  <td>₹{p['base']}</td>
  <td class="{gc}" style="font-weight:600">₹{p['current']:,.2f}</td>
  <td class="{gc}">{'+'if chg>=0 else ''}{chg}%</td>
  <td><canvas id="as-{ticker}" width="120" height="28" data-vals='{spark_data}' data-color="{p['color']}" style="display:block"></canvas></td>
</tr>"""

    return page("Admin Panel", f"""
<style>
.topbar{{background:var(--bg2);border-bottom:1px solid var(--border);padding:14px 24px;display:flex;align-items:center;justify-content:space-between;gap:12px;position:sticky;top:0;z-index:50}}
.brand{{font-size:16px;font-weight:700}}.brand em{{font-style:normal;color:var(--blue)}}
.main{{max-width:1340px;margin:0 auto;padding:24px}}
.sec-title{{font-size:17px;font-weight:600;margin-bottom:16px;display:flex;align-items:center;gap:8px}}
.stats-row{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:24px}}
.stat-box{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-lg);padding:16px 22px;min-width:130px}}
.stat-box .n{{font-size:26px;font-weight:700;color:var(--blue)}}.stat-box .l{{font-size:13px;color:var(--text2);margin-top:2px}}
.ctrl-row{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:28px;padding:18px;background:var(--card);border:1px solid var(--border);border-radius:var(--radius-lg)}}
.ctrl-row .spacer{{flex:1}}
.news-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin-bottom:32px}}
.news-card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-lg);padding:16px;transition:border-color .15s}}
.news-card:hover{{border-color:var(--border2)}}.news-card.released{{opacity:.5}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{text-align:left;padding:9px 14px;background:var(--bg3);color:var(--text3);font-size:11px;text-transform:uppercase;letter-spacing:.05em}}
td{{padding:10px 14px;border-bottom:1px solid var(--border)}}
.danger-zone{{margin-top:32px;padding:20px;border:1px solid var(--red-dim);border-radius:var(--radius-lg);background:#1a0a0a}}
.danger-zone h3{{color:var(--red);font-size:15px;margin-bottom:8px}}
.danger-zone p{{font-size:13px;color:var(--text2);margin-bottom:14px}}
</style>
<div class="topbar">
  <div class="brand"><em>Stock</em>Exchange &nbsp;<span style="font-size:13px;color:var(--gold);font-weight:500">⚡ Admin</span></div>
  <div style="display:flex;gap:10px;align-items:center">
    {game_badge}
    <a href="/" class="btn btn-ghost btn-sm" target="_blank">↗ Player view</a>
    <a href="/admin/logout" class="btn btn-ghost btn-sm">Logout</a>
  </div>
</div>
<div class="main">
  {fh}

  <!-- Stats -->
  <div class="stats-row">
    <div class="stat-box"><div class="n">{len(state['players'])}</div><div class="l">Players joined</div></div>
    <div class="stat-box"><div class="n">{len(state['news_feed'])}/{len(state['news_pool'])}</div><div class="l">News released</div></div>
    <div class="stat-box"><div class="n">{total_trades}</div><div class="l">Total trades</div></div>
    <div class="stat-box"><div class="n" id="adm-tick" style="font-size:20px">—</div><div class="l">Last price tick</div></div>
  </div>

  <!-- Controls -->
  <div class="ctrl-row">
    <span style="font-size:14px;font-weight:500">Game controls</span>
    <div class="spacer"></div>
    <form method="POST" action="/admin/toggle">
      <button type="submit" class="btn {toggle_cls}">{toggle_label}</button>
    </form>
    <form method="POST" action="/admin/reset_prices">
      <button type="submit" class="btn btn-ghost">↺ Reset prices</button>
    </form>
  </div>

  <!-- News -->
  <div class="sec-title">📰 News Clippings — Release Controls</div>
  <div class="news-grid">{news_cards}</div>

  <!-- Leaderboard -->
  <div class="sec-title">🏆 Live Leaderboard</div>
  <div class="card" style="padding:0;overflow:hidden;margin-bottom:28px">
    <table>
      <thead><tr><th>Rank</th><th>Name</th><th>Team</th><th>Cash</th><th>Portfolio</th><th>P&L</th><th>Trades</th><th>Joined</th></tr></thead>
      <tbody id="adm-lb">{lb_rows}</tbody>
    </table>
  </div>

  <!-- Price table -->
  <div class="sec-title">💹 Live Prices</div>
  <div class="card" style="padding:0;overflow:hidden;margin-bottom:28px">
    <table>
      <thead><tr><th>Ticker</th><th>Stock</th><th>Base</th><th>Current</th><th>Change</th><th>Trend</th></tr></thead>
      <tbody id="adm-prices">{price_rows}</tbody>
    </table>
  </div>

  <!-- Danger zone -->
  <div class="danger-zone">
    <h3>⚠ Danger Zone</h3>
    <p>Full reset clears all players, portfolios, trade history, and news — resets prices to base values. This cannot be undone.</p>
    <form method="POST" action="/admin/full_reset" onsubmit="return confirm('Full reset — are you absolutely sure? This deletes all players and resets everything.')">
      <button type="submit" class="btn btn-danger">🔄 Full Game Reset</button>
    </form>
  </div>
</div>

<script>
// Draw admin sparklines
function drawAdminSpark(canvas) {{
  const vals = JSON.parse(canvas.dataset.vals || '[]');
  const color = canvas.dataset.color;
  if (vals.length < 2) return;
  const w = canvas.width, h = canvas.height;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, w, h);
  const min = Math.min(...vals), max = Math.max(...vals);
  const range = max - min || 1;
  const pts = vals.map((v, i) => [i / (vals.length-1) * w, h - ((v-min)/range)*(h-3)-2]);
  ctx.beginPath();
  pts.forEach(([x,y],i) => i===0 ? ctx.moveTo(x,y) : ctx.lineTo(x,y));
  ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.stroke();
  // last dot
  ctx.beginPath();
  ctx.arc(pts[pts.length-1][0], pts[pts.length-1][1], 2.5, 0, Math.PI*2);
  ctx.fillStyle = color; ctx.fill();
}}
document.querySelectorAll('[id^="as-"]').forEach(drawAdminSpark);

// Live refresh
async function admRefresh() {{
  const r = await fetch('/api/admin_state');
  const d = await r.json();
  if (!d.ok) return;
  document.getElementById('adm-tick').textContent = d.last_tick || '—';
  // Rebuild price table rows inline
  const tbody = document.getElementById('adm-prices');
  if (tbody) {{
    tbody.querySelectorAll('canvas').forEach(c => {{
      const ticker = c.id.replace('as-','');
      const hist = d.price_history[ticker] || [];
      const vals = hist.map(h => h[1]);
      c.dataset.vals = JSON.stringify(vals);
      const p = d.prices[ticker];
      if (!p) return;
      const base = parseFloat(c.closest('tr').children[2].textContent.replace('₹','').replace(',',''));
      const chg = ((p.current - p.base) / p.base * 100).toFixed(2);
      const up = chg >= 0;
      const tr = c.closest('tr');
      tr.children[3].textContent = '₹' + p.current.toLocaleString('en-IN',{{minimumFractionDigits:2}});
      tr.children[3].className = up ? 'up' : 'dn';
      tr.children[4].textContent = (up?'+':'') + chg + '%';
      tr.children[4].className = up ? 'up' : 'dn';
      drawAdminSpark(c);
    }});
  }}
  // Leaderboard
  const lb = document.getElementById('adm-lb');
  if (lb && d.leaderboard) {{
    const medals = ['🥇','🥈','🥉'];
    lb.innerHTML = d.leaderboard.map((p,i) => {{
      const gc = p.gain >= 0 ? 'up' : 'dn';
      return `<tr>
        <td>${{medals[i] || '#'+(i+1)}}</td>
        <td><strong>${{p.name}}</strong></td>
        <td style="color:var(--text2)">${{p.team}}</td>
        <td>₹${{p.balance.toLocaleString('en-IN',{{maximumFractionDigits:0}})}}</td>
        <td>₹${{p.pv.toLocaleString('en-IN',{{maximumFractionDigits:0}})}}</td>
        <td class="${{gc}}">${{p.gain>=0?'+':''}}₹${{Math.abs(p.gain).toLocaleString('en-IN',{{maximumFractionDigits:0}})}}</td>
        <td style="color:var(--text2)">${{p.trades}}</td>
        <td style="font-size:12px;color:var(--text3)">${{p.joined_at}}</td>
      </tr>`;
    }}).join('') || '<tr><td colspan="8" style="text-align:center;color:var(--text3);padding:24px">No players yet.</td></tr>';
  }}
}}
setInterval(admRefresh, 3000);
</script>""")

def render_admin_login(flash=""):
    fh = f'<div class="flash flash-err">{flash}</div>' if flash else ""
    return page("Admin Login", f"""
<style>
body{{display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px}}
.wrap{{width:100%;max-width:380px}}
.logo{{font-size:24px;font-weight:700;text-align:center;margin-bottom:6px}}.logo em{{font-style:normal;color:var(--gold)}}
.sub{{text-align:center;color:var(--text2);font-size:14px;margin-bottom:28px}}
.field{{margin-bottom:16px}}.field label{{display:block;font-size:13px;color:var(--text2);margin-bottom:6px;font-weight:500}}
.field input{{width:100%;background:var(--bg3);border:1px solid var(--border2);border-radius:var(--radius);padding:10px 14px;color:var(--text);font-size:15px;outline:none}}
.field input:focus{{border-color:var(--gold)}}
</style>
<div class="wrap">
  <div class="logo"><em>⚡ Admin</em> Login</div>
  <div class="sub">Stock Exchange — Control Panel</div>
  {fh}
  <div class="card">
    <form method="POST" action="/admin/login">
      <div class="field"><label>Admin password</label><input type="password" name="password" placeholder="Enter password" required autofocus/></div>
      <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;padding:12px">Enter →</button>
    </form>
  </div>
</div>""")

# ── HTTP Handler ──────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):

    def send_html(self, html, code=200):
        b = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(b))
        self.send_header("ngrok-skip-browser-warning", "true")
        self.end_headers()
        self.wfile.write(b)

    def send_json(self, data, code=200):
        b = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(b))
        self.end_headers()
        self.wfile.write(b)

    def redirect(self, path):
        self.send_response(302)
        self.send_header("Location", path)
        self.end_headers()

    def get_cookie(self, name):
        for part in self.headers.get("Cookie","").split(";"):
            k, _, v = part.strip().partition("=")
            if k.strip() == name: return v.strip()
        return None

    def set_cookie(self, name, value):
        self.send_header("Set-Cookie", f"{name}={value}; Path=/; HttpOnly")

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length).decode("utf-8")

    def parse_form(self):
        return dict(urllib.parse.parse_qsl(self.read_body()))

    def player_token(self):
        return self.get_cookie("player_token")

    def is_admin(self):
        return self.get_cookie("admin_token") in state["admin_sessions"]

    # ── GET ───────────────────────────────────────────────────────────────────

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", "/register"):
            self.send_html(render_register())

        elif path == "/trade":
            tok = self.player_token()
            player = get_player(tok) if tok else None
            if not player: self.redirect("/")
            else: self.send_html(render_trade(player))

        elif path == "/api/state":
            tok = self.player_token()
            player = get_player(tok) if tok else None
            if not player:
                self.send_json({"ok": False}); return
            pv = portfolio_value(player)
            self.send_json({
                "ok": True,
                "prices": state["prices"],
                "price_history": state["price_history"],
                "player": {
                    "balance": player["balance"],
                    "portfolio_value": pv,
                    "portfolio": player["portfolio"],
                },
                "news_feed": state["news_feed"],
            })

        elif path == "/api/admin_state":
            if not self.is_admin():
                self.send_json({"ok": False}); return
            hist = state["price_history"]
            last_tick = hist[list(hist.keys())[0]][-1][0] if any(hist[t] for t in hist) else None
            sorted_players = sorted(state["players"].values(), key=portfolio_value, reverse=True)
            lb = [{"name":p["name"],"team":p["team"],"balance":p["balance"],
                   "pv":portfolio_value(p),"gain":portfolio_value(p)-100000,
                   "trades":p["trades"],"joined_at":p["joined_at"]} for p in sorted_players]
            self.send_json({
                "ok": True,
                "prices": state["prices"],
                "price_history": hist,
                "last_tick": last_tick,
                "leaderboard": lb,
            })

        elif path == "/admin":
            if self.is_admin(): self.send_html(render_admin())
            else: self.redirect("/admin/login")

        elif path == "/admin/login":
            self.send_html(render_admin_login())

        elif path == "/admin/logout":
            tok = self.get_cookie("admin_token")
            state["admin_sessions"].discard(tok)
            self.send_response(302)
            self.send_header("Location", "/admin/login")
            self.send_header("Set-Cookie", "admin_token=; Path=/; Max-Age=0")
            self.end_headers()

        else:
            self.send_html("<h1 style='font-family:sans-serif;padding:40px'>404</h1>", 404)

    def log_message(self, fmt, *args): pass

    # ── POST ──────────────────────────────────────────────────────────────────

    def do_POST(self):
        path = self.path

        # Player registration
        if path == "/register":
            form = self.parse_form()
            name = form.get("name","").strip()
            team = form.get("team","").strip()
            if not name or not team:
                self.send_html(render_register("Please fill in both fields.","err")); return
            tok = generate_token()
            with state["lock"]:
                state["players"][tok] = {
                    "name": name, "team": team,
                    "balance": 100000.0,
                    "portfolio": {},
                    "trades": 0,
                    "joined_at": datetime.now().strftime("%H:%M:%S"),
                }
            self.send_response(302)
            self.send_header("Location", "/trade")
            self.set_cookie("player_token", tok)
            self.end_headers()

        # Trade
        elif path == "/api/trade":
            tok = self.player_token()
            player = get_player(tok) if tok else None
            if not player:
                self.send_json({"ok":False,"msg":"Not logged in."}); return
            if not state["game_active"]:
                self.send_json({"ok":False,"msg":"Game is paused. Wait for admin to start."}); return
            try:
                body   = json.loads(self.read_body())
                ticker = body["ticker"]
                action = body["action"]
                qty    = int(body.get("qty",1))
            except Exception:
                self.send_json({"ok":False,"msg":"Invalid request."}); return
            if ticker not in state["prices"] or qty < 1:
                self.send_json({"ok":False,"msg":"Invalid ticker or quantity."}); return
            price = state["prices"][ticker]["current"]
            with state["lock"]:
                if action == "buy":
                    cost = price * qty
                    if player["balance"] < cost:
                        self.send_json({"ok":False,"msg":f"Need ₹{cost:,.2f} but only ₹{player['balance']:,.2f} available."}); return
                    player["balance"] -= cost
                    player["portfolio"][ticker] = player["portfolio"].get(ticker,0) + qty
                    player["trades"] += 1
                    self.send_json({"ok":True,"msg":f"✓ Bought {qty}× {ticker} @ ₹{price:,.2f}"})
                elif action == "sell":
                    held = player["portfolio"].get(ticker,0)
                    if held < qty:
                        self.send_json({"ok":False,"msg":f"You only hold {held} units of {ticker}."}); return
                    player["balance"] += price * qty
                    player["portfolio"][ticker] = held - qty
                    player["trades"] += 1
                    self.send_json({"ok":True,"msg":f"✓ Sold {qty}× {ticker} @ ₹{price:,.2f}"})
                else:
                    self.send_json({"ok":False,"msg":"Unknown action."})

        # Admin login
        elif path == "/admin/login":
            form = self.parse_form()
            if form.get("password") == ADMIN_PASSWORD:
                tok = generate_token()
                state["admin_sessions"].add(tok)
                self.send_response(302)
                self.send_header("Location", "/admin")
                self.set_cookie("admin_token", tok)
                self.end_headers()
            else:
                self.send_html(render_admin_login("Wrong password."))

        # Toggle game
        elif path == "/admin/toggle":
            if not self.is_admin(): self.redirect("/admin/login"); return
            with state["lock"]:
                state["game_active"] = not state["game_active"]
            msg = "▶ Game started! Players can now trade." if state["game_active"] else "⏸ Game paused."
            self.send_html(render_admin(msg, "ok"))

        # Release news
        elif path == "/admin/release":
            if not self.is_admin(): self.redirect("/admin/login"); return
            form = self.parse_form()
            nid  = form.get("news_id")
            released_ids = {n["id"] for n in state["news_feed"]}
            item = next((n for n in state["news_pool"] if n["id"] == nid), None)
            if not item:
                self.send_html(render_admin("News item not found.","err")); return
            if nid in released_ids:
                self.send_html(render_admin("Already released.","err")); return
            with state["lock"]:
                entry = dict(item)
                entry["released_at"] = datetime.now().strftime("%H:%M:%S")
                state["news_feed"].append(entry)
                apply_news_impact(entry)
            self.send_html(render_admin(f"📢 Released: \"{item['title']}\" — prices updated!", "ok"))

        # Reset prices only
        elif path == "/admin/reset_prices":
            if not self.is_admin(): self.redirect("/admin/login"); return
            with state["lock"]:
                for p in state["prices"].values():
                    p["current"] = p["base"]
            self.send_html(render_admin("↺ Prices reset to base values.", "ok"))

        # ── Full game reset ───────────────────────────────────────────────────
        elif path == "/admin/full_reset":
            if not self.is_admin(): self.redirect("/admin/login"); return
            do_full_reset()
            self.send_html(render_admin("🔄 Full reset complete — all players cleared, prices back to base.", "ok"))

        else:
            self.send_html("<h1>404</h1>", 404)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
        base = f"http://localhost:{PORT}"
        print(f"""
╔══════════════════════════════════════════════════╗
║  STOCK EXCHANGE - THE ULTIMATE TRADING CHALLENGE ║
╠══════════════════════════════════════════════════╣
║  Player URL :  {base:<33} ║
║  Admin URL  :  {(base+'/admin'):<33} ║
║  Password   :  {ADMIN_PASSWORD:<33} ║
╚══════════════════════════════════════════════════╝
  Prices fluctuate every {TICK_INTERVAL}s when game is live.
  Press Ctrl+C to stop.
""")
        threading.Timer(0.8, lambda: webbrowser.open(base)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Server stopped.")

if __name__ == "__main__":
    main()
