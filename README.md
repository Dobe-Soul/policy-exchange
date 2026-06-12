# 🏦 Policy Exchange — The Insurance Trading Challenge

A fast-paced, browser-based trading simulation where participants buy and sell insurance policies that fluctuate in real time based on news events released by the game admin.

Built with **pure Python** (zero dependencies) — no pip installs, no frameworks.

---

## 🚀 Quick Start

```bash
python policy_exchange.py
```

Then open:

| URL | Who uses it |
|-----|-------------|
| `http://localhost:8080` | Players — register & trade |
| `http://localhost:8080/admin` | Admin — game controls |

Default admin password: `admin123`  
*(Change it by editing `ADMIN_PASSWORD` at the top of the file)*

---

## 🎮 How the Game Works

1. **Players** visit the link, register with their name and team, and receive ₹1,00,000 in virtual capital
2. **Admin** starts the game from the admin panel
3. Prices fluctuate automatically every 4 seconds using a mean-reverting random walk
4. Admin releases **news clippings** (e.g. cyclone alerts, regulatory changes) that cause real price swings
5. Players buy and sell policies to maximise their portfolio value
6. The leaderboard updates live — highest portfolio value wins

---

## ⚙️ Configuration

At the top of `policy_exchange.py`:

```python
PORT           = 8080        # Change if 8080 is in use
ADMIN_PASSWORD = "admin123"  # Change before running publicly
TICK_INTERVAL  = 4           # Seconds between automatic price ticks
```

Volatility per policy (how wildly each price moves):

```python
VOLATILITY = {
    "HLTH": 0.004,   # Health      — calm
    "LIFE": 0.003,   # Life        — very calm
    "PROP": 0.006,   # Property    — moderate
    "MRIN": 0.005,   # Marine      — moderate
    "MOTO": 0.004,   # Motor       — calm
    "CATA": 0.009,   # Catastrophe — most volatile
}
```

---

## 🌐 Sharing With Players (Online)

### Option A — ngrok (quickest)
```bash
# Terminal 1
python policy_exchange.py

# Terminal 2
ngrok http 8080
```
Share the `https://xxxx.ngrok-free.app` URL. The ngrok warning page is already bypassed in this build.

### Option B — Cloudflare Tunnel (no warning page, no time limit)
```bash
# Terminal 1
python policy_exchange.py

# Terminal 2
cloudflared tunnel --url http://localhost:8080
```
Share the `https://xxxx.trycloudflare.com` URL.

---

## 🛠 Admin Panel Features

| Feature | Description |
|---------|-------------|
| ▶ Start / ⏸ Pause | Enable or disable trading for all players |
| 📢 Release news | Push one of 12 scenario cards — instantly moves prices |
| ↺ Reset prices | Restore all prices to base values |
| 🔄 Full Game Reset | Wipe all players, trades, and news (new round) |
| 🏆 Leaderboard | Live rankings by portfolio value, auto-refreshes |
| 💹 Live prices | Price table with sparkline trend charts |

---

## 📰 News Scenarios Included

| # | Event | Category | Impact |
|---|-------|----------|--------|
| N01 | Cyclone Alert — Eastern Coast | Natural Disaster | MRIN +22%, PROP +18%, CATA +30% |
| N02 | IRDAI Imposes Premium Cap | Regulatory | HLTH −12%, LIFE −10% |
| N03 | Aging Population Report | Demographic | HLTH +10%, LIFE +8% |
| N04 | GDP Growth Revised to 7.8% | Economic | MOTO +7%, MRIN +6% |
| N05 | Urban Flood Risk Reclassification | Regulatory | PROP +14%, CATA +20% |
| N06 | Tech IPO Boom | Market Event | All +3–5% |
| N07 | Monsoon Deficit 40% Below Normal | Natural Disaster | PROP −8%, CATA −5% |
| N08 | Road Safety Bill Passes | Regulatory | MOTO −11% |
| N09 | Pandemic Preparedness Fund | Policy | HLTH +18% |
| N10 | Shipping Lane Disruptions | Geopolitical | MRIN +25% |
| N11 | EV Adoption Surges | Technology | MOTO −6% |
| N12 | SC Raises Motor Liability Limits | Legal | MOTO +16% |

---

## 🗂 Project Structure

```
policy_exchange/
├── policy_exchange.py   # Entire application — server, game logic, all HTML
└── README.md
```

Everything is self-contained in one file. No templates, no static folder, no database.

---

## 📋 Requirements

- Python 3.7 or higher
- No external packages needed

---

## 📄 License

MIT — free to use, modify, and share.
