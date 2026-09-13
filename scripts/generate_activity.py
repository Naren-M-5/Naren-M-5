import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

USERNAME = "Naren-M-5"
OUTPUT = Path("assets/build-activity.svg")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
GOKU_URI = "data:image/jpeg;base64,__PLACEHOLDER__"

if not TOKEN:
    raise SystemExit("ERROR: GH_TOKEN is missing")

now = datetime.now(timezone.utc)
start = now - timedelta(days=364)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          firstDay
          contributionDays {
            date
            contributionCount
            contributionLevel
            color
            weekday
          }
        }
      }
    }
  }
}
"""

payload = json.dumps({
    "query": query,
    "variables": {
        "login": USERNAME,
        "from": start.isoformat(),
        "to": now.isoformat(),
    },
}).encode("utf-8")

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Naren-Build-Activity",
    },
)

try:
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
except Exception as exc:
    raise SystemExit(f"ERROR: GitHub API request failed: {exc}")

if data.get("errors"):
    raise SystemExit(json.dumps(data["errors"], indent=2))

user = data.get("data", {}).get("user")
if not user:
    raise SystemExit(f"ERROR: GitHub user {USERNAME} not found")

calendar = user["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]
total_contributions = calendar["totalContributions"]

WIDTH = 1200
HEIGHT = 430
GRID_X = 320
GRID_Y = 130
GRID_WIDTH = 610
CELL = 9
ROW_GAP = 4
ROW_STEP = CELL + ROW_GAP
GRID_HEIGHT = 7 * ROW_STEP
WEEK_COUNT = max(1, len(weeks))
WEEK_STEP = GRID_WIDTH / max(1, WEEK_COUNT - 1)
GRID_END = GRID_X + GRID_WIDTH
SOURCE_X = 255
CENTER_Y = GRID_Y + GRID_HEIGHT / 2

LOOP = 8.0
SWEEP_START = 1.30
SWEEP_END = 5.35
RESTORE_START = 7.05
RESTORE_END = 7.45


def kt(seconds: float) -> str:
    return f"{max(0.0, min(1.0, seconds / LOOP)):.5f}"


def hit_time(week_index: int) -> float:
    progress = week_index / max(1, WEEK_COUNT - 1)
    return SWEEP_START + progress * (SWEEP_END - SWEEP_START)

month_svg = []
last_month = None
for index, week in enumerate(weeks):
    date = datetime.fromisoformat(week["firstDay"]).date()
    month = date.strftime("%b")
    if month != last_month:
        x = GRID_X + index * WEEK_STEP
        month_svg.append(f'<text x="{x:.2f}" y="{GRID_Y - 13}" font-family="monospace" font-size="9" fill="#64748b">{month}</text>')
        last_month = month

day_svg = []
for index, label in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
    y = GRID_Y + index * ROW_STEP + 8
    day_svg.append(f'<text x="{GRID_X - 12}" y="{y:.2f}" text-anchor="end" font-family="monospace" font-size="8" fill="#64748b">{label}</text>')

cells = []
particles = []
all_days = []
active_days = 0

for week_index, week in enumerate(weeks):
    for day in week["contributionDays"]:
        all_days.append(day)
        count = day["contributionCount"]
        x = GRID_X + week_index * WEEK_STEP
        y = GRID_Y + day["weekday"] * ROW_STEP

        if count == 0:
            cells.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{CELL}" height="{CELL}" rx="2" fill="#161b22" stroke="#30363d" stroke-width=".5"/>')
            continue

        active_days += 1
        color = day["color"]
        hit = hit_time(week_index)
        flash_start = max(SWEEP_START, hit - 0.08)
        disappear = min(hit + 0.22, RESTORE_START - 0.05)

        cells.append(f'''
<g>
  <rect x="{x:.2f}" y="{y:.2f}" width="{CELL}" height="{CELL}" rx="2" fill="{color}" stroke="#38bdf8" stroke-width=".45">
    <animate attributeName="opacity" values="1;1;0;0;1;1" keyTimes="0;{kt(hit)};{kt(disappear)};{kt(RESTORE_START)};{kt(RESTORE_END)};1" dur="{LOOP}s" repeatCount="indefinite"/>
  </rect>
  <rect x="{x - 1:.2f}" y="{y - 1:.2f}" width="{CELL + 2}" height="{CELL + 2}" rx="2" fill="#ffffff" opacity="0" filter="url(#cellGlow)">
    <animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;{kt(flash_start)};{kt(hit)};{kt(disappear)};1" dur="{LOOP}s" repeatCount="indefinite"/>
  </rect>
</g>''')

        if (week_index + day["weekday"]) % 3 == 0:
            cx = x + CELL / 2
            cy = y + CELL / 2
            end = min(hit + 0.42, RESTORE_START - 0.05)
            direction = -1 if day["weekday"] <= 3 else 1
            particles.append(f'''
<circle cx="{cx:.2f}" cy="{cy:.2f}" r="1.7" fill="#67e8f9" opacity="0">
  <animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;{kt(hit)};{kt(hit + .04)};{kt(end)};1" dur="{LOOP}s" repeatCount="indefinite"/>
  <animate attributeName="cx" values="{cx:.2f};{cx:.2f};{cx + 16:.2f};{cx + 23:.2f}" keyTimes="0;{kt(hit)};{kt(end)};1" dur="{LOOP}s" repeatCount="indefinite"/>
  <animate attributeName="cy" values="{cy:.2f};{cy:.2f};{cy + direction * 12:.2f};{cy + direction * 18:.2f}" keyTimes="0;{kt(hit)};{kt(end)};1" dur="{LOOP}s" repeatCount="indefinite"/>
</circle>''')

valid_days = [d for d in sorted(all_days, key=lambda item: item["date"]) if d["date"] <= now.date().isoformat()]
if valid_days and valid_days[-1]["date"] == now.date().isoformat() and valid_days[-1]["contributionCount"] == 0:
    valid_days = valid_days[:-1]

current_streak = 0
for day in reversed(valid_days):
    if day["contributionCount"] > 0:
        current_streak += 1
    else:
        break

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
<defs>
  <linearGradient id="bg" x1="0" x2="1"><stop offset="0%" stop-color="#020617"/><stop offset="48%" stop-color="#071426"/><stop offset="100%" stop-color="#020617"/></linearGradient>
  <linearGradient id="beam" x1="0" x2="1"><stop offset="0%" stop-color="#ffffff"/><stop offset="20%" stop-color="#e0f2fe"/><stop offset="45%" stop-color="#67e8f9"/><stop offset="72%" stop-color="#0ea5e9"/><stop offset="100%" stop-color="#2563eb"/></linearGradient>
  <linearGradient id="progress" x1="0" x2="1"><stop offset="0%" stop-color="#22d3ee"/><stop offset="55%" stop-color="#2563eb"/><stop offset="100%" stop-color="#7c3aed"/></linearGradient>
  <filter id="cellGlow" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="2.5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="beamGlow" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="6" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="bigGlow" x="-250%" y="-250%" width="600%" height="600%"><feGaussianBlur stdDeviation="12" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>

<rect width="1200" height="430" rx="20" fill="url(#bg)" stroke="#0ea5e9" stroke-width="1.3"/>
<path d="M20 20 H245 L275 47 H918 L948 20 H1180" fill="none" stroke="#0ea5e9" stroke-width="1.2" opacity=".55"/>

<text x="35" y="48" font-family="monospace" font-size="17" font-weight="700" fill="#22d3ee">NAREN // BUILD SYSTEM</text>
<text x="35" y="70" font-family="monospace" font-size="10" fill="#3b82f6">CODE &gt; LEARN &gt; BUILD &gt; REPEAT</text>
<text x="600" y="49" text-anchor="middle" font-family="monospace" font-size="27" font-weight="700" fill="#e2e8f0">⚡ BUILD ACTIVITY</text>
<text x="600" y="74" text-anchor="middle" font-family="monospace" font-size="12" fill="#94a3b8">REAL GITHUB CONTRIBUTIONS</text>

<rect x="982" y="27" width="178" height="56" rx="10" fill="#07111f" stroke="#0ea5e9"/>
<text x="997" y="50" font-family="monospace" font-size="12" font-weight="700" fill="#22d3ee">POWER MODE</text>
<text x="1105" y="50" font-family="monospace" font-size="12" font-weight="700" fill="#22c55e">ON</text>
<circle cx="1139" cy="46" r="5" fill="#22c55e" filter="url(#cellGlow)"><animate attributeName="opacity" values="1;.25;1" dur="1.25s" repeatCount="indefinite"/></circle>

<g>
  <image href="{GOKU_URI}" x="0" y="96" width="280" height="275" preserveAspectRatio="xMidYMid meet"/>
  <animateTransform attributeName="transform" type="translate" values="0 0;0 -2;0 2;0 0" dur="2.6s" repeatCount="indefinite"/>
</g>

<circle cx="{SOURCE_X}" cy="{CENTER_Y}" r="10" fill="#ffffff" filter="url(#bigGlow)">
  <animate attributeName="r" values="8;8;25;18;18;8" keyTimes="0;.04;{kt(1.20)};{kt(SWEEP_START)};{kt(RESTORE_START)};1" dur="{LOOP}s" repeatCount="indefinite"/>
</circle>

<path fill="url(#beam)" opacity=".16" filter="url(#bigGlow)">
  <animate attributeName="d" values="M {SOURCE_X} {CENTER_Y} L {GRID_X} {CENTER_Y - 5} L {GRID_X} {CENTER_Y + 5} Z;M {SOURCE_X} {CENTER_Y} L {GRID_X} {GRID_Y - 5} L {GRID_X} {GRID_Y + GRID_HEIGHT + 5} Z;M {SOURCE_X} {CENTER_Y} L {GRID_END} {GRID_Y - 5} L {GRID_END} {GRID_Y + GRID_HEIGHT + 5} Z;M {SOURCE_X} {CENTER_Y} L {GRID_END} {GRID_Y - 5} L {GRID_END} {GRID_Y + GRID_HEIGHT + 5} Z;M {SOURCE_X} {CENTER_Y} L {GRID_X} {CENTER_Y - 5} L {GRID_X} {CENTER_Y + 5} Z" keyTimes="0;{kt(SWEEP_START)};{kt(SWEEP_END)};{kt(RESTORE_START)};1" dur="{LOOP}s" repeatCount="indefinite"/>
</path>

<line x1="{SOURCE_X}" y1="{CENTER_Y}" x2="{GRID_X}" y2="{CENTER_Y}" stroke="#ffffff" stroke-width="5" stroke-linecap="round" opacity=".85" filter="url(#cellGlow)">
  <animate attributeName="x2" values="{GRID_X};{GRID_X};{GRID_END};{GRID_END};{GRID_X}" keyTimes="0;{kt(SWEEP_START)};{kt(SWEEP_END)};{kt(RESTORE_START)};1" dur="{LOOP}s" repeatCount="indefinite"/>
</line>

{''.join(month_svg)}
{''.join(day_svg)}
<g>{''.join(cells)}</g>

<ellipse cx="{GRID_X}" cy="{CENTER_Y}" rx="7" ry="{GRID_HEIGHT / 2 + 5}" fill="#ffffff" opacity="0" filter="url(#beamGlow)">
  <animate attributeName="cx" values="{GRID_X};{GRID_X};{GRID_END};{GRID_END};{GRID_X}" keyTimes="0;{kt(SWEEP_START)};{kt(SWEEP_END)};{kt(RESTORE_START)};1" dur="{LOOP}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0;.9;.9;0;0" keyTimes="0;{kt(SWEEP_START)};{kt(SWEEP_END)};{kt(RESTORE_START)};1" dur="{LOOP}s" repeatCount="indefinite"/>
</ellipse>
<ellipse cx="{GRID_X}" cy="{CENTER_Y}" rx="18" ry="{GRID_HEIGHT / 2 + 12}" fill="none" stroke="#22d3ee" stroke-width="3" opacity="0" filter="url(#cellGlow)">
  <animate attributeName="cx" values="{GRID_X};{GRID_X};{GRID_END};{GRID_END};{GRID_X}" keyTimes="0;{kt(SWEEP_START)};{kt(SWEEP_END)};{kt(RESTORE_START)};1" dur="{LOOP}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0;.9;.75;0;0" keyTimes="0;{kt(SWEEP_START)};{kt(SWEEP_END)};{kt(RESTORE_START)};1" dur="{LOOP}s" repeatCount="indefinite"/>
</ellipse>
<g filter="url(#cellGlow)">{''.join(particles)}</g>

<rect x="980" y="120" width="180" height="167" rx="10" fill="#07111f" stroke="#0ea5e9"/>
<text x="997" y="150" font-family="monospace" font-size="9" fill="#94a3b8">ACTIVE DAYS</text>
<text x="1140" y="150" text-anchor="end" font-family="monospace" font-size="14" font-weight="700" fill="#22d3ee">{active_days}</text>
<text x="997" y="190" font-family="monospace" font-size="9" fill="#94a3b8">CONTRIBUTIONS</text>
<text x="1140" y="190" text-anchor="end" font-family="monospace" font-size="14" font-weight="700" fill="#60a5fa">{total_contributions}</text>
<text x="997" y="230" font-family="monospace" font-size="9" fill="#94a3b8">CURRENT STREAK</text>
<text x="1140" y="230" text-anchor="end" font-family="monospace" font-size="14" font-weight="700" fill="#a78bfa">{current_streak}</text>
<text x="997" y="264" font-family="monospace" font-size="10" font-weight="700" fill="#f59e0b">KEEP BUILDING</text>

<text x="625" y="327" text-anchor="middle" font-family="monospace" font-size="14" font-weight="700" fill="#22d3ee">POWERING THE SYSTEM...<animate attributeName="opacity" values=".4;1;.4" dur="1.3s" repeatCount="indefinite"/></text>
<rect x="450" y="343" width="355" height="12" rx="6" fill="#0f172a" stroke="#0ea5e9"/>
<rect x="453" y="346" width="0" height="6" rx="3" fill="url(#progress)"><animate attributeName="width" values="0;0;349;349;0" keyTimes="0;{kt(SWEEP_START)};{kt(SWEEP_END)};{kt(RESTORE_START)};1" dur="{LOOP}s" repeatCount="indefinite"/></rect>
<path d="M370 374 H830 L850 396 L830 418 H370 L350 396 Z" fill="#06111e" stroke="#0ea5e9"/>
<text x="600" y="402" text-anchor="middle" font-family="monospace" font-size="17" font-weight="700" fill="#dbeafe">THINK → BUILD → DEBUG → SHIP</text>
</svg>'''

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(svg, encoding="utf-8")
print(f"Generated {OUTPUT}")
print(f"Active days: {active_days}")
print(f"Total contributions: {total_contributions}")
print(f"Current streak: {current_streak}")
