import os
import sys
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

USERNAME = "Naren-M-5"
OUTPUT = Path("assets/build-activity.svg")

TOKEN = os.environ.get("GH_TOKEN")

if not TOKEN:
    raise SystemExit("GH_TOKEN is missing.")

# ---------------------------------------------------------
# Fetch the last ~1 year of GitHub contribution data
# ---------------------------------------------------------

today = datetime.now(timezone.utc)
start = today - timedelta(days=364)

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
            weekday
          }
        }
      }
    }
  }
}
"""

payload = {
    "query": query,
    "variables": {
        "login": USERNAME,
        "from": start.isoformat(),
        "to": today.isoformat(),
    },
}

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Naren-GitHub-Profile",
    },
)

try:
    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))
except Exception as exc:
    raise SystemExit(f"GitHub GraphQL request failed: {exc}")

if "errors" in result:
    print(json.dumps(result["errors"], indent=2))
    sys.exit(1)

calendar = (
    result.get("data", {})
    .get("user", {})
    .get("contributionsCollection", {})
    .get("contributionCalendar")
)

if not calendar:
    raise SystemExit("Contribution calendar was not returned.")

weeks = calendar["weeks"]
total_contributions = calendar["totalContributions"]

# ---------------------------------------------------------
# Geometry
# ---------------------------------------------------------

WIDTH = 1200
HEIGHT = 450

GRID_X = 330
GRID_Y = 132

CELL = 10
GAP = 3
STEP = CELL + GAP

week_count = len(weeks)

# Keep all weeks inside the panel.
max_grid_width = 600

if week_count > 1:
    STEP_X = max_grid_width / (week_count - 1)
else:
    STEP_X = STEP

GRID_W = max_grid_width
GRID_H = 7 * STEP

BEAM_START_X = 255
BEAM_Y = GRID_Y + GRID_H / 2

LOOP = 8.0
CHARGE_END = 1.25
SWEEP_START = 1.25
SWEEP_END = 5.7
RESET_START = 7.35

# ---------------------------------------------------------
# Colors
# ---------------------------------------------------------

COLORS = {
    "NONE": "#111827",
    "FIRST_QUARTILE": "#164e63",
    "SECOND_QUARTILE": "#0369a1",
    "THIRD_QUARTILE": "#0284c7",
    "FOURTH_QUARTILE": "#38bdf8",
}

# ---------------------------------------------------------
# Stats
# ---------------------------------------------------------

all_days = []

for week_index, week in enumerate(weeks):
    for day in week["contributionDays"]:
        all_days.append(
            {
                "week": week_index,
                "date": day["date"],
                "weekday": day["weekday"],
                "count": day["contributionCount"],
                "level": day["contributionLevel"],
            }
        )

active_days = sum(1 for day in all_days if day["count"] > 0)

sorted_days = sorted(all_days, key=lambda d: d["date"])

# Current streak:
# If today has no contribution yet, allow yesterday to be the streak endpoint.
streak = 0
days_for_streak = sorted_days[:]

if days_for_streak:
    latest = datetime.fromisoformat(days_for_streak[-1]["date"]).date()
    today_date = today.date()

    if latest == today_date and days_for_streak[-1]["count"] == 0:
        days_for_streak = days_for_streak[:-1]

    for day in reversed(days_for_streak):
        if day["count"] > 0:
            streak += 1
        else:
            break

# ---------------------------------------------------------
# Month labels
# ---------------------------------------------------------

month_labels = []
last_month = None

for week_index, week in enumerate(weeks):
    first_day = datetime.fromisoformat(week["firstDay"]).date()
    month_name = first_day.strftime("%b")

    if month_name != last_month:
        x = GRID_X + week_index * STEP_X
        month_labels.append((x, month_name))
        last_month = month_name

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def hit_time_for_week(week_index):
    if week_count <= 1:
        return SWEEP_START

    progress = week_index / (week_count - 1)
    return SWEEP_START + progress * (SWEEP_END - SWEEP_START)


def normalized(value):
    return max(0.0, min(1.0, value / LOOP))


# ---------------------------------------------------------
# SVG pieces
# ---------------------------------------------------------

month_svg = []

for x, label in month_labels:
    month_svg.append(
        f"""
        <text x="{x:.1f}" y="{GRID_Y - 12}"
              font-family="monospace"
              font-size="9"
              fill="#64748b">
          {label}
        </text>
        """
    )

day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

days_svg = []

for i, name in enumerate(day_labels):
    y = GRID_Y + i * STEP + CELL - 1

    days_svg.append(
        f"""
        <text x="{GRID_X - 12}" y="{y:.1f}"
              text-anchor="end"
              font-family="monospace"
              font-size="8"
              fill="#475569">
          {name}
        </text>
        """
    )

cells_svg = []
particles_svg = []

for day in all_days:
    week_index = day["week"]
    weekday = day["weekday"]
    count = day["count"]
    level = day["level"]

    x = GRID_X + week_index * STEP_X
    y = GRID_Y + weekday * STEP

    color = COLORS.get(level, "#111827")

    # Empty days remain visible and never disappear.
    if count == 0:
        cells_svg.append(
            f"""
            <rect x="{x:.2f}" y="{y:.2f}"
                  width="{CELL}" height="{CELL}"
                  rx="2"
                  fill="{color}"
                  stroke="#1f2937"
                  stroke-width=".5"/>
            """
        )
        continue

    # Beam reaches this week's x coordinate.
    hit = hit_time_for_week(week_index)

    flash_start = hit - 0.08
    fade_end = hit + 0.30

    k1 = normalized(flash_start)
    k2 = normalized(hit)
    k3 = normalized(fade_end)
    k4 = normalized(RESET_START)

    # Real contributed cell:
    # visible -> flash -> disappear -> remain gone -> restore at reset
    cells_svg.append(
        f"""
        <g>
          <rect x="{x:.2f}" y="{y:.2f}"
                width="{CELL}" height="{CELL}"
                rx="2"
                fill="{color}"
                stroke="#38bdf8"
                stroke-width=".55">

            <animate attributeName="opacity"
                     values="1;1;0;0;1"
                     keyTimes="0;{k2:.4f};{k3:.4f};{k4:.4f};1"
                     dur="{LOOP}s"
                     repeatCount="indefinite"/>

          </rect>

          <rect x="{x:.2f}" y="{y:.2f}"
                width="{CELL}" height="{CELL}"
                rx="2"
                fill="#ffffff"
                opacity="0"
                filter="url(#smallGlow)">

            <animate attributeName="opacity"
                     values="0;0;1;0;0"
                     keyTimes="0;{k1:.4f};{k2:.4f};{k3:.4f};1"
                     dur="{LOOP}s"
                     repeatCount="indefinite"/>

          </rect>
        </g>
        """
    )

    # Only add some debris so the SVG does not become excessively heavy.
    if count > 0 and (week_index + weekday) % 3 == 0:
        px = x + CELL / 2
        py = y + CELL / 2

        particle_end = min(hit + 0.45, RESET_START)

        p1 = normalized(hit)
        p2 = normalized(particle_end)

        direction = 1 if weekday % 2 == 0 else -1

        particles_svg.append(
            f"""
            <circle cx="{px:.2f}" cy="{py:.2f}" r="1.8"
                    fill="#67e8f9"
                    opacity="0">

              <animate attributeName="opacity"
                       values="0;0;1;0;0"
                       keyTimes="0;{p1:.4f};{min(p1 + 0.015, 0.99):.4f};{p2:.4f};1"
                       dur="{LOOP}s"
                       repeatCount="indefinite"/>

              <animate attributeName="cx"
                       values="{px:.2f};{px:.2f};{px + 14:.2f};{px + 22:.2f}"
                       keyTimes="0;{p1:.4f};{p2:.4f};1"
                       dur="{LOOP}s"
                       repeatCount="indefinite"/>

              <animate attributeName="cy"
                       values="{py:.2f};{py:.2f};{py + direction * 15:.2f};{py:.2f}"
                       keyTimes="0;{p1:.4f};{p2:.4f};1"
                       dur="{LOOP}s"
                       repeatCount="indefinite"/>

            </circle>
            """
        )

GRID_END_X = GRID_X + GRID_W

svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{WIDTH}"
     height="{HEIGHT}"
     viewBox="0 0 {WIDTH} {HEIGHT}">

<defs>

  <linearGradient id="bg" x1="0" x2="1">
    <stop offset="0%" stop-color="#020617"/>
    <stop offset="50%" stop-color="#071426"/>
    <stop offset="100%" stop-color="#020617"/>
  </linearGradient>

  <linearGradient id="beam" x1="0" x2="1">
    <stop offset="0%" stop-color="#ffffff"/>
    <stop offset="22%" stop-color="#e0f2fe"/>
    <stop offset="48%" stop-color="#67e8f9"/>
    <stop offset="75%" stop-color="#0ea5e9"/>
    <stop offset="100%" stop-color="#2563eb"/>
  </linearGradient>

  <linearGradient id="progress" x1="0" x2="1">
    <stop offset="0%" stop-color="#22d3ee"/>
    <stop offset="55%" stop-color="#2563eb"/>
    <stop offset="100%" stop-color="#7c3aed"/>
  </linearGradient>

  <filter id="smallGlow"
          x="-150%" y="-150%"
          width="400%" height="400%">
    <feGaussianBlur stdDeviation="2.5" result="blur"/>
    <feMerge>
      <feMergeNode in="blur"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>

  <filter id="glow"
          x="-200%" y="-200%"
          width="500%" height="500%">
    <feGaussianBlur stdDeviation="5" result="blur"/>
    <feMerge>
      <feMergeNode in="blur"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>

  <filter id="bigGlow"
          x="-200%" y="-200%"
          width="500%" height="500%">
    <feGaussianBlur stdDeviation="11" result="blur"/>
    <feMerge>
      <feMergeNode in="blur"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>

</defs>


<!-- ================================================= -->
<!-- BACKGROUND -->
<!-- ================================================= -->

<rect width="{WIDTH}"
      height="{HEIGHT}"
      rx="20"
      fill="url(#bg)"
      stroke="#0ea5e9"
      stroke-width="1.4"/>

<path d="M20 20 H255 L285 48 H915 L945 20 H1180"
      fill="none"
      stroke="#0ea5e9"
      stroke-width="1.2"
      opacity=".6"/>


<!-- ================================================= -->
<!-- HEADER -->
<!-- ================================================= -->

<text x="35" y="49"
      font-family="monospace"
      font-size="17"
      font-weight="700"
      fill="#22d3ee">
  NAREN // BUILD SYSTEM
</text>

<text x="35" y="72"
      font-family="monospace"
      font-size="10"
      fill="#3b82f6">
  CODE &gt; LEARN &gt; BUILD &gt; REPEAT
</text>

<text x="600" y="50"
      text-anchor="middle"
      font-family="monospace"
      font-size="27"
      font-weight="700"
      fill="#e2e8f0">
  BUILD ACTIVITY
</text>

<text x="600" y="76"
      text-anchor="middle"
      font-family="monospace"
      font-size="12"
      fill="#94a3b8">
  REAL GITHUB CONTRIBUTIONS // LIVE BUILD DATA
</text>


<!-- ================================================= -->
<!-- POWER MODE -->
<!-- ================================================= -->

<rect x="972" y="27"
      width="190" height="57"
      rx="10"
      fill="#07111f"
      stroke="#0ea5e9"/>

<text x="990" y="51"
      font-family="monospace"
      font-size="13"
      font-weight="700"
      fill="#22d3ee">
  POWER MODE
</text>

<text x="1106" y="51"
      font-family="monospace"
      font-size="13"
      font-weight="700"
      fill="#22c55e">
  ON
</text>

<circle cx="1142" cy="47"
        r="5"
        fill="#22c55e"
        filter="url(#smallGlow)">
  <animate attributeName="opacity"
           values="1;.25;1"
           dur="1.3s"
           repeatCount="indefinite"/>
</circle>

<text x="990" y="70"
      font-family="monospace"
      font-size="8"
      fill="#64748b">
  CONTRIBUTIONS DRIVE PROGRESS
</text>


<!-- ================================================= -->
<!-- GOKU -->
<!-- ================================================= -->

<g>

  <image
    href="https://raw.githubusercontent.com/{USERNAME}/{USERNAME}/main/assets/goku.png"
    x="5"
    y="105"
    width="270"
    height="265"
    preserveAspectRatio="xMidYMid meet"/>

  <animateTransform
    attributeName="transform"
    type="translate"
    values="0 0;0 -2;0 2;0 0"
    dur="2.5s"
    repeatCount="indefinite"/>

</g>


<!-- ================================================= -->
<!-- ENERGY ORB -->
<!-- ================================================= -->

<circle cx="{BEAM_START_X}"
        cy="{BEAM_Y:.2f}"
        r="13"
        fill="#ffffff"
        filter="url(#bigGlow)">

  <animate attributeName="r"
           values="9;9;23;17;17;9"
           keyTimes="0;.05;.14;.20;.84;1"
           dur="{LOOP}s"
           repeatCount="indefinite"/>

</circle>

<circle cx="{BEAM_START_X}"
        cy="{BEAM_Y:.2f}"
        r="22"
        fill="none"
        stroke="#22d3ee"
        stroke-width="3"
        filter="url(#glow)">

  <animate attributeName="r"
           values="15;15;39;28;28;15"
           keyTimes="0;.05;.14;.20;.84;1"
           dur="{LOOP}s"
           repeatCount="indefinite"/>

  <animate attributeName="opacity"
           values=".25;.25;.9;.55;.55;.25"
           keyTimes="0;.05;.14;.20;.84;1"
           dur="{LOOP}s"
           repeatCount="indefinite"/>

</circle>


<!-- ================================================= -->
<!-- BEAM UNDER THE CONTRIBUTION CELLS -->
<!-- ================================================= -->

<line x1="{BEAM_START_X}"
      y1="{BEAM_Y:.2f}"
      x2="{GRID_X}"
      y2="{BEAM_Y:.2f}"
      stroke="#0ea5e9"
      stroke-width="{GRID_H + 12}"
      stroke-linecap="round"
      opacity=".08"
      filter="url(#bigGlow)">

  <animate attributeName="x2"
           values="{GRID_X};{GRID_X};{GRID_END_X};{GRID_END_X};{GRID_X}"
           keyTimes="0;{SWEEP_START / LOOP:.4f};{SWEEP_END / LOOP:.4f};{RESET_START / LOOP:.4f};1"
           dur="{LOOP}s"
           repeatCount="indefinite"/>

</line>

<line x1="{BEAM_START_X}"
      y1="{BEAM_Y:.2f}"
      x2="{GRID_X}"
      y2="{BEAM_Y:.2f}"
      stroke="url(#beam)"
      stroke-width="30"
      stroke-linecap="round"
      opacity=".68"
      filter="url(#glow)">

  <animate attributeName="x2"
           values="{GRID_X};{GRID_X};{GRID_END_X};{GRID_END_X};{GRID_X}"
           keyTimes="0;{SWEEP_START / LOOP:.4f};{SWEEP_END / LOOP:.4f};{RESET_START / LOOP:.4f};1"
           dur="{LOOP}s"
           repeatCount="indefinite"/>

</line>

<line x1="{BEAM_START_X}"
      y1="{BEAM_Y:.2f}"
      x2="{GRID_X}"
      y2="{BEAM_Y:.2f}"
      stroke="#ffffff"
      stroke-width="7"
      stroke-linecap="round"
      opacity=".92">

  <animate attributeName="x2"
           values="{GRID_X};{GRID_X};{GRID_END_X};{GRID_END_X};{GRID_X}"
           keyTimes="0;{SWEEP_START / LOOP:.4f};{SWEEP_END / LOOP:.4f};{RESET_START / LOOP:.4f};1"
           dur="{LOOP}s"
           repeatCount="indefinite"/>

</line>


<!-- ================================================= -->
<!-- MONTHS -->
<!-- ================================================= -->

{''.join(month_svg)}


<!-- ================================================= -->
<!-- DAYS -->
<!-- ================================================= -->

{''.join(days_svg)}


<!-- ================================================= -->
<!-- REAL CONTRIBUTION CELLS -->
<!-- ================================================= -->

<g>

{''.join(cells_svg)}

</g>


<!-- ================================================= -->
<!-- MOVING IMPACT FRONT -->
<!-- ================================================= -->

<g filter="url(#glow)">

  <ellipse cx="{GRID_X}"
           cy="{BEAM_Y:.2f}"
           rx="7"
           ry="{GRID_H / 2 + 4:.2f}"
           fill="#ffffff"
           opacity="0">

    <animate attributeName="cx"
             values="{GRID_X};{GRID_X};{GRID_END_X};{GRID_END_X};{GRID_X}"
             keyTimes="0;{SWEEP_START / LOOP:.4f};{SWEEP_END / LOOP:.4f};{RESET_START / LOOP:.4f};1"
             dur="{LOOP}s"
             repeatCount="indefinite"/>

    <animate attributeName="opacity"
             values="0;1;1;0;0"
             keyTimes="0;{SWEEP_START / LOOP:.4f};{SWEEP_END / LOOP:.4f};{RESET_START / LOOP:.4f};1"
             dur="{LOOP}s"
             repeatCount="indefinite"/>

  </ellipse>

  <ellipse cx="{GRID_X}"
           cy="{BEAM_Y:.2f}"
           rx="17"
           ry="{GRID_H / 2 + 11:.2f}"
           fill="none"
           stroke="#22d3ee"
           stroke-width="3"
           opacity="0">

    <animate attributeName="cx"
             values="{GRID_X};{GRID_X};{GRID_END_X};{GRID_END_X};{GRID_X}"
             keyTimes="0;{SWEEP_START / LOOP:.4f};{SWEEP_END / LOOP:.4f};{RESET_START / LOOP:.4f};1"
             dur="{LOOP}s"
             repeatCount="indefinite"/>

    <animate attributeName="opacity"
             values="0;.8;.8;0;0"
             keyTimes="0;{SWEEP_START / LOOP:.4f};{SWEEP_END / LOOP:.4f};{RESET_START / LOOP:.4f};1"
             dur="{LOOP}s"
             repeatCount="indefinite"/>

  </ellipse>

</g>


<!-- ================================================= -->
<!-- DEBRIS FROM REAL CONTRIBUTION CELLS -->
<!-- ================================================= -->

<g filter="url(#smallGlow)">

{''.join(particles_svg)}

</g>


<!-- ================================================= -->
<!-- STATS -->
<!-- ================================================= -->

<rect x="970"
      y="118"
      width="195"
      height="176"
      rx="11"
      fill="#07111f"
      stroke="#0ea5e9"
      opacity=".96"/>

<text x="990" y="148"
      font-family="monospace"
      font-size="10"
      fill="#94a3b8">
  ACTIVE DAYS
</text>

<text x="1145" y="148"
      text-anchor="end"
      font-family="monospace"
      font-size="15"
      font-weight="700"
      fill="#22d3ee">
  {active_days}
</text>

<line x1="990" y1="162"
      x2="1145" y2="162"
      stroke="#1e293b"/>

<text x="990" y="190"
      font-family="monospace"
      font-size="10"
      fill="#94a3b8">
  CONTRIBUTIONS
</text>

<text x="1145" y="190"
      text-anchor="end"
      font-family="monospace"
      font-size="15"
      font-weight="700"
      fill="#60a5fa">
  {total_contributions}
</text>

<line x1="990" y1="204"
      x2="1145" y2="204"
      stroke="#1e293b"/>

<text x="990" y="232"
      font-family="monospace"
      font-size="10"
      fill="#94a3b8">
  CURRENT STREAK
</text>

<text x="1145" y="232"
      text-anchor="end"
      font-family="monospace"
      font-size="15"
      font-weight="700"
      fill="#a78bfa">
  {streak}
</text>

<text x="990" y="270"
      font-family="monospace"
      font-size="11"
      font-weight="700"
      fill="#f59e0b">
  KEEP BUILDING
</text>


<!-- ================================================= -->
<!-- STATUS -->
<!-- ================================================= -->

<text x="625"
      y="330"
      text-anchor="middle"
      font-family="monospace"
      font-size="14"
      font-weight="700"
      fill="#22d3ee">

  POWERING THE SYSTEM...

  <animate attributeName="opacity"
           values=".45;1;.45"
           dur="1.3s"
           repeatCount="indefinite"/>

</text>


<!-- ================================================= -->
<!-- PROGRESS -->
<!-- ================================================= -->

<rect x="455"
      y="346"
      width="350"
      height="12"
      rx="6"
      fill="#0f172a"
      stroke="#0ea5e9"/>

<rect x="458"
      y="349"
      width="0"
      height="6"
      rx="3"
      fill="url(#progress)">

  <animate attributeName="width"
           values="0;0;344;344;0"
           keyTimes="0;{SWEEP_START / LOOP:.4f};{SWEEP_END / LOOP:.4f};{RESET_START / LOOP:.4f};1"
           dur="{LOOP}s"
           repeatCount="indefinite"/>

</rect>


<!-- ================================================= -->
<!-- FOOTER -->
<!-- ================================================= -->

<path d="M370 380 H830 L850 402 L830 424 H370 L350 402 Z"
      fill="#06111e"
      stroke="#0ea5e9"/>

<text x="600"
      y="408"
      text-anchor="middle"
      font-family="monospace"
      font-size="17"
      font-weight="700"
      fill="#dbeafe">
  THINK → BUILD → DEBUG → SHIP
</text>

<text x="35"
      y="421"
      font-family="monospace"
      font-size="9"
      fill="#64748b">
  DISCIPLINE BUILDS REAL POWER.
</text>

<text x="930"
      y="421"
      font-family="monospace"
      font-size="8"
      fill="#64748b">
  CONSISTENCY TURNS IDEAS INTO IMPACT.
</text>

</svg>
"""

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(svg, encoding="utf-8")

print(f"Generated {OUTPUT}")
print(f"Weeks: {week_count}")
print(f"Active days: {active_days}")
print(f"Total contributions: {total_contributions}")
print(f"Current streak: {streak}")
