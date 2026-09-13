import os, json, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

USER = "Naren-M-5"
OUT = Path("assets/build-activity.svg")
TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
if not TOKEN:
    raise SystemExit("Missing GH_TOKEN")

now = datetime.now(timezone.utc)
start = now - timedelta(days=364)
query = """
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){contributionsCollection(from:$from,to:$to){contributionCalendar{
    totalContributions weeks{firstDay contributionDays{date contributionCount color weekday}}
  }}}
}
"""
body = json.dumps({"query": query, "variables": {"login": USER, "from": start.isoformat(), "to": now.isoformat()}}).encode()
req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as r:
    data = json.loads(r.read().decode())
if data.get("errors"):
    raise SystemExit(json.dumps(data["errors"], indent=2))
cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks, total = cal["weeks"], cal["totalContributions"]

W, H = 1200, 430
GX, GY, GW = 320, 130, 610
CELL, STEP = 9, 13
GH = STEP * 7
WC = max(1, len(weeks))
WS = GW / max(1, WC - 1)
GE, SX, CY = GX + GW, 250, GY + GH / 2
LOOP, A, B, R1, R2 = 8.0, 1.30, 5.35, 7.05, 7.45

def k(t): return f"{max(0, min(1, t / LOOP)):.5f}"
def hit(i): return A + (i / max(1, WC - 1)) * (B - A)

months, lm = [], None
for i, w in enumerate(weeks):
    m = datetime.fromisoformat(w["firstDay"]).strftime("%b")
    if m != lm:
        months.append(f'<text x="{GX+i*WS:.1f}" y="{GY-13}" font-family="monospace" font-size="9" fill="#64748b">{m}</text>')
        lm = m

days = [f'<text x="{GX-12}" y="{GY+i*STEP+8}" text-anchor="end" font-family="monospace" font-size="8" fill="#64748b">{d}</text>' for i, d in enumerate(["Sun","Mon","Tue","Wed","Thu","Fri","Sat"])]

cells, bits, all_days, active = [], [], [], 0
for wi, w in enumerate(weeks):
    for d in w["contributionDays"]:
        all_days.append(d)
        x, y, c = GX + wi * WS, GY + d["weekday"] * STEP, d["contributionCount"]
        if c == 0:
            cells.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="2" fill="#161b22" stroke="#30363d" stroke-width=".5"/>')
            continue
        active += 1
        ht, gone = hit(wi), min(hit(wi) + .22, R1 - .05)
        cells.append(f'<g><rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="2" fill="{d["color"]}" stroke="#38bdf8" stroke-width=".45"><animate attributeName="opacity" values="1;1;0;0;1;1" keyTimes="0;{k(ht)};{k(gone)};{k(R1)};{k(R2)};1" dur="{LOOP}s" repeatCount="indefinite"/></rect><rect x="{x-1:.1f}" y="{y-1:.1f}" width="{CELL+2}" height="{CELL+2}" rx="2" fill="#fff" opacity="0" filter="url(#glow)"><animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;{k(max(A,ht-.08))};{k(ht)};{k(gone)};1" dur="{LOOP}s" repeatCount="indefinite"/></rect></g>')
        if (wi + d["weekday"]) % 3 == 0:
            cx, cy, end = x + CELL/2, y + CELL/2, min(ht + .42, R1 - .05)
            dy = -14 if d["weekday"] <= 3 else 14
            bits.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.7" fill="#67e8f9" opacity="0"><animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;{k(ht)};{k(ht+.04)};{k(end)};1" dur="{LOOP}s" repeatCount="indefinite"/><animate attributeName="cx" values="{cx:.1f};{cx:.1f};{cx+16:.1f};{cx+23:.1f}" keyTimes="0;{k(ht)};{k(end)};1" dur="{LOOP}s" repeatCount="indefinite"/><animate attributeName="cy" values="{cy:.1f};{cy:.1f};{cy+dy:.1f};{cy+dy*1.4:.1f}" keyTimes="0;{k(ht)};{k(end)};1" dur="{LOOP}s" repeatCount="indefinite"/></circle>')

valid = [d for d in sorted(all_days, key=lambda x: x["date"]) if d["date"] <= now.date().isoformat()]
if valid and valid[-1]["date"] == now.date().isoformat() and valid[-1]["contributionCount"] == 0:
    valid.pop()
streak = 0
for d in reversed(valid):
    if d["contributionCount"]: streak += 1
    else: break

character = '''<g transform="translate(45 95)"><animateTransform attributeName="transform" type="translate" values="45 95;45 92;45 98;45 95" dur="2.6s" repeatCount="indefinite"/><ellipse cx="92" cy="154" rx="70" ry="80" fill="#f97316"/><path d="M55 88 L20 48 L72 68 L52 15 L105 58 L119 20 L137 72 L178 42 L150 92 Z" fill="#facc15" stroke="#fde047" stroke-width="3" filter="url(#big)"/><circle cx="101" cy="100" r="37" fill="#fde68a" stroke="#111827" stroke-width="3"/><path d="M71 90 L111 76 L101 104 Z M111 76 L145 90 L114 104 Z" fill="#facc15"/><circle cx="88" cy="103" r="4" fill="#38bdf8"/><circle cx="116" cy="103" r="4" fill="#38bdf8"/><path d="M91 124 Q105 136 123 122" fill="none" stroke="#111827" stroke-width="4" stroke-linecap="round"/><path d="M92 146 L176 157 L177 177 L87 171 Z" fill="#fca5a5" stroke="#111827" stroke-width="3"/><path d="M174 151 L215 135 L226 154 L183 179 Z" fill="#fde68a" stroke="#111827" stroke-width="3"/><circle cx="220" cy="146" r="20" fill="#e0f2fe" filter="url(#big)"/></g>'''

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><defs><linearGradient id="bg" x1="0" x2="1"><stop offset="0%" stop-color="#020617"/><stop offset="48%" stop-color="#071426"/><stop offset="100%" stop-color="#020617"/></linearGradient><linearGradient id="beam" x1="0" x2="1"><stop offset="0%" stop-color="#fff"/><stop offset="35%" stop-color="#67e8f9"/><stop offset="100%" stop-color="#2563eb"/></linearGradient><linearGradient id="bar" x1="0" x2="1"><stop offset="0%" stop-color="#22d3ee"/><stop offset="55%" stop-color="#2563eb"/><stop offset="100%" stop-color="#7c3aed"/></linearGradient><filter id="glow" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="big" x="-250%" y="-250%" width="600%" height="600%"><feGaussianBlur stdDeviation="12" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><rect width="1200" height="430" rx="20" fill="url(#bg)" stroke="#0ea5e9"/><path d="M20 20 H245 L275 47 H918 L948 20 H1180" fill="none" stroke="#0ea5e9" opacity=".55"/><text x="35" y="48" font-family="monospace" font-size="17" font-weight="700" fill="#22d3ee">NAREN // BUILD SYSTEM</text><text x="35" y="70" font-family="monospace" font-size="10" fill="#3b82f6">CODE &gt; LEARN &gt; BUILD &gt; REPEAT</text><text x="600" y="49" text-anchor="middle" font-family="monospace" font-size="27" font-weight="700" fill="#e2e8f0">⚡ BUILD ACTIVITY</text><text x="600" y="74" text-anchor="middle" font-family="monospace" font-size="12" fill="#94a3b8">REAL GITHUB CONTRIBUTIONS</text><rect x="982" y="27" width="178" height="56" rx="10" fill="#07111f" stroke="#0ea5e9"/><text x="997" y="50" font-family="monospace" font-size="12" font-weight="700" fill="#22d3ee">POWER MODE</text><text x="1105" y="50" font-family="monospace" font-size="12" font-weight="700" fill="#22c55e">ON</text><circle cx="1139" cy="46" r="5" fill="#22c55e" filter="url(#glow)"><animate attributeName="opacity" values="1;.25;1" dur="1.25s" repeatCount="indefinite"/></circle>{character}<circle cx="{SX}" cy="{CY}" r="10" fill="#fff" filter="url(#big)"><animate attributeName="r" values="8;8;25;18;18;8" keyTimes="0;.04;{k(1.20)};{k(A)};{k(R1)};1" dur="{LOOP}s" repeatCount="indefinite"/></circle><path fill="url(#beam)" opacity=".16" filter="url(#big)"><animate attributeName="d" values="M {SX} {CY} L {GX} {CY-5} L {GX} {CY+5} Z;M {SX} {CY} L {GX} {GY-5} L {GX} {GY+GH+5} Z;M {SX} {CY} L {GE} {GY-5} L {GE} {GY+GH+5} Z;M {SX} {CY} L {GE} {GY-5} L {GE} {GY+GH+5} Z;M {SX} {CY} L {GX} {CY-5} L {GX} {CY+5} Z" keyTimes="0;{k(A)};{k(B)};{k(R1)};1" dur="{LOOP}s" repeatCount="indefinite"/></path><line x1="{SX}" y1="{CY}" x2="{GX}" y2="{CY}" stroke="#fff" stroke-width="5" stroke-linecap="round" opacity=".85" filter="url(#glow)"><animate attributeName="x2" values="{GX};{GX};{GE};{GE};{GX}" keyTimes="0;{k(A)};{k(B)};{k(R1)};1" dur="{LOOP}s" repeatCount="indefinite"/></line>{''.join(months)}{''.join(days)}<g>{''.join(cells)}</g><ellipse cx="{GX}" cy="{CY}" rx="7" ry="{GH/2+5}" fill="#fff" opacity="0" filter="url(#big)"><animate attributeName="cx" values="{GX};{GX};{GE};{GE};{GX}" keyTimes="0;{k(A)};{k(B)};{k(R1)};1" dur="{LOOP}s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;.9;.9;0;0" keyTimes="0;{k(A)};{k(B)};{k(R1)};1" dur="{LOOP}s" repeatCount="indefinite"/></ellipse><g filter="url(#glow)">{''.join(bits)}</g><rect x="980" y="120" width="180" height="167" rx="10" fill="#07111f" stroke="#0ea5e9"/><text x="997" y="150" font-family="monospace" font-size="9" fill="#94a3b8">ACTIVE DAYS</text><text x="1140" y="150" text-anchor="end" font-family="monospace" font-size="14" font-weight="700" fill="#22d3ee">{active}</text><text x="997" y="190" font-family="monospace" font-size="9" fill="#94a3b8">CONTRIBUTIONS</text><text x="1140" y="190" text-anchor="end" font-family="monospace" font-size="14" font-weight="700" fill="#60a5fa">{total}</text><text x="997" y="230" font-family="monospace" font-size="9" fill="#94a3b8">CURRENT STREAK</text><text x="1140" y="230" text-anchor="end" font-family="monospace" font-size="14" font-weight="700" fill="#a78bfa">{streak}</text><text x="997" y="264" font-family="monospace" font-size="10" font-weight="700" fill="#f59e0b">KEEP BUILDING</text><text x="625" y="327" text-anchor="middle" font-family="monospace" font-size="14" font-weight="700" fill="#22d3ee">POWERING THE SYSTEM...<animate attributeName="opacity" values=".4;1;.4" dur="1.3s" repeatCount="indefinite"/></text><rect x="450" y="343" width="355" height="12" rx="6" fill="#0f172a" stroke="#0ea5e9"/><rect x="453" y="346" width="0" height="6" rx="3" fill="url(#bar)"><animate attributeName="width" values="0;0;349;349;0" keyTimes="0;{k(A)};{k(B)};{k(R1)};1" dur="{LOOP}s" repeatCount="indefinite"/></rect><path d="M370 374 H830 L850 396 L830 418 H370 L350 396 Z" fill="#06111e" stroke="#0ea5e9"/><text x="600" y="402" text-anchor="middle" font-family="monospace" font-size="17" font-weight="700" fill="#dbeafe">THINK → BUILD → DEBUG → SHIP</text></svg>'''

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg, encoding="utf-8")
print(f"Generated {OUT}")
print(f"Active days: {active}")
print(f"Total contributions: {total}")
print(f"Current streak: {streak}")
