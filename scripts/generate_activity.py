import os
import sys
import json
import base64
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

USERNAME = "Naren-M-5"

OUTPUT = Path("assets/build-activity.svg")
GOKU_PATH = Path("assets/goku.png")

TOKEN = os.environ.get("GH_TOKEN")

if not TOKEN:
    raise SystemExit("GH_TOKEN is missing.")

if not GOKU_PATH.exists():
    raise SystemExit("assets/goku.png is missing.")

# ============================================================
# LOAD GOKU IMAGE AS BASE64
# This keeps the final SVG self-contained.
# ============================================================

goku_base64 = base64.b64encode(GOKU_PATH.read_bytes()).decode("ascii")
goku_data_uri = f"data:image/png;base64,{goku_base64}"


# ============================================================
# FETCH REAL GITHUB CONTRIBUTIONS
# ============================================================

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

payload = {
    "query": query,
    "variables": {
        "login": USERNAME,
        "from": start.isoformat(),
        "to": now.isoformat(),
    },
}

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Naren-Build-Activity",
    },
)

try:
    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))
except Exception as exc:
    raise SystemExit(f"GitHub API request failed: {exc}")

if result.get("errors"):
    print(json.dumps(result["errors"], indent=2))
    sys.exit(1)

calendar = (
    result.get("data", {})
    .get("user", {})
    .get("contributionsCollection", {})
    .get("contributionCalendar")
)

if not calendar:
    raise SystemExit("GitHub contribution calendar not returned.")

weeks = calendar["weeks"]
total_contributions = calendar["totalContributions"]


# ============================================================
# CANVAS
# ============================================================

WIDTH = 1200
HEIGHT = 430

GRID_X = 325
GRID_Y = 132

CELL = 9
CELL_GAP_Y = 4
ROW_STEP = CELL + CELL_GAP_Y

GRID_WIDTH = 610
GRID_HEIGHT = 7 * ROW_STEP

week_count = len(weeks)

if week_count > 1:
    WEEK_STEP = GRID_WIDTH / (week_count - 1)
else:
    WEEK_STEP = 12

GRID_END_X = GRID_X + GRID_WIDTH

BEAM_SOURCE_X = 255
BEAM_CENTER_Y = GRID_Y + GRID_HEIGHT / 2


# ============================================================
# ANIMATION TIMING
# ============================================================

LOOP = 8.0

CHARGE_END = 1.15

SWEEP_START = 1.25
SWEEP_END = 5.40

PAUSE_END = 6.90

RESTORE_START = 7.05
RESTORE_END = 7.45


def t(value):
    return max(0.0, min(1.0, value / LOOP))


def hit_time(week_index):
    if week_count <= 1:
        return SWEEP_START

    p = week_index / (week_count - 1)
    return SWEEP_START + p * (SWEEP_END - SWEEP_START)


# ============================================================
# DATA
# ============================================================

days = []

for week_index, week in enumerate(weeks):
    for day in week["contributionDays"]:
        days.append(
            {
                "week": week_index,
                "date": day["date"],
                "weekday": day["weekday"],
                "count": day["contributionCount"],
                "level": day["contributionLevel"],
                "color": day["color"],
            }
        )


# ============================================================
# STATS
# ============================================================

active_days = sum(1 for day in days if day["count"] > 0)

ordered_days = sorted(days, key=lambda d: d["date"])

current_streak = 0

streak_source = ordered_days[:]

# Ignore today if no contribution has been made yet.
if streak_source:
    last_date = datetime.fromisoformat(streak_source[-1]["date"]).date()

    if last_date == now.date() and streak_source[-1]["count"] == 0:
        streak_source.pop()

for day in reversed(streak_source):
    if day["count"] > 0:
        current_streak += 1
    else:
        break


# ============================================================
# MONTH LABELS
# ============================================================

month_labels = []
last_month = None

for i, week in enumerate(weeks):
    d = datetime.fromisoformat(week["firstDay"]).date()

    month = d.strftime("%b")

    if month != last_month:
        month_labels.append(
            (
                GRID_X + i * WEEK_STEP,
                month,
            )
        )
        last_month = month


month_svg = ""

for x, month in month_labels:
    month_svg += f"""
    <text
        x="{x:.2f}"
        y="{GRID_Y - 13}"
        font-family="monospace"
        font-size="9"
        fill="#64748b"
    >{month}</text>
    """


# ============================================================
# WEEKDAY LABELS
# GitHub weekday positions are used directly.
# ============================================================

weekday_names = [
    "Sun",
    "Mon",
    "Tue",
    "Wed",
    "Thu",
    "Fri",
    "Sat",
]

weekday_svg = ""

for index, label in enumerate(weekday_names):
    y = GRID_Y + index * ROW_STEP + 8

    weekday_svg += f"""
    <text
        x="{GRID_X - 13}"
        y="{y:.2f}"
        text-anchor="end"
        font-family="monospace"
        font-size="8"
        fill="#475569"
    >{label}</text>
    """


# ============================================================
# CONTRIBUTION CELLS
# ============================================================

cells_svg = ""
particles_svg = ""

for day in days:

    week_index = day["week"]
    weekday = day["weekday"]

    x = GRID_X + week_index * WEEK_STEP
    y = GRID_Y + weekday * ROW_STEP

    count = day["count"]

    # Use GitHub's real contribution calendar color.
    if count == 0:
        color = "#161b22"
    else:
        color = day["color"]

    # --------------------------------------------------------
    # EMPTY DAY
    # Never vanishes.
    # --------------------------------------------------------

    if count == 0:

        cells_svg += f"""
        <rect
            x="{x:.2f}"
            y="{y:.2f}"
            width="{CELL}"
            height="{CELL}"
            rx="2"
            fill="{color}"
            stroke="#30363d"
            stroke-width=".55"
        />
        """

        continue

    # --------------------------------------------------------
    # REAL CONTRIBUTION
    # --------------------------------------------------------

    hit = hit_time(week_index)

    flash_begin = hit - 0.10
    vanish_end = hit + 0.24

    cells_svg += f"""
    <g>

        <!-- original contributed cell -->

        <rect
            x="{x:.2f}"
            y="{y:.2f}"
            width="{CELL}"
            height="{CELL}"
            rx="2"
            fill="{color}"
            stroke="#38bdf8"
            stroke-width=".45"
        >

            <animate
                attributeName="opacity"
                values="1;1;0;0;1;1"
                keyTimes="
                    0;
                    {t(hit):.5f};
                    {t(vanish_end):.5f};
                    {t(RESTORE_START):.5f};
                    {t(RESTORE_END):.5f};
                    1
                "
                dur="{LOOP}s"
                repeatCount="indefinite"
            />

        </rect>


        <!-- impact flash -->

        <rect
            x="{x - 1:.2f}"
            y="{y - 1:.2f}"
            width="{CELL + 2}"
            height="{CELL + 2}"
            rx="2"
            fill="#ffffff"
            opacity="0"
            filter="url(#cellGlow)"
        >

            <animate
                attributeName="opacity"
                values="0;0;1;0;0"
                keyTimes="
                    0;
                    {t(flash_begin):.5f};
                    {t(hit):.5f};
                    {t(vanish_end):.5f};
                    1
                "
                dur="{LOOP}s"
                repeatCount="indefinite"
            />

        </rect>

    </g>
    """

    # --------------------------------------------------------
    # DEBRIS
    # Not every cell, otherwise the SVG becomes enormous.
    # --------------------------------------------------------

    if (week_index + weekday) % 3 == 0:

        particle_end = hit + 0.50

        direction = -1 if weekday <= 3 else 1

        cx = x + CELL / 2
        cy = y + CELL / 2

        particles_svg += f"""
        <rect
            x="{cx:.2f}"
            y="{cy:.2f}"
            width="2.7"
            height="2.7"
            rx=".5"
            fill="#67e8f9"
            opacity="0"
        >

            <animate
                attributeName="opacity"
                values="0;0;1;0;0"
                keyTimes="
                    0;
                    {t(hit):.5f};
                    {t(hit + 0.05):.5f};
                    {t(particle_end):.5f};
                    1
                "
                dur="{LOOP}s"
                repeatCount="indefinite"
            />

            <animate
                attributeName="x"
                values="
                    {cx:.2f};
                    {cx:.2f};
                    {cx + 9:.2f};
                    {cx + 18:.2f}
                "
                keyTimes="
                    0;
                    {t(hit):.5f};
                    {t(particle_end):.5f};
                    1
                "
                dur="{LOOP}s"
                repeatCount="indefinite"
            />

            <animate
                attributeName="y"
                values="
                    {cy:.2f};
                    {cy:.2f};
                    {cy + direction * 12:.2f};
                    {cy + direction * 18:.2f}
                "
                keyTimes="
                    0;
                    {t(hit):.5f};
                    {t(particle_end):.5f};
                    1
                "
                dur="{LOOP}s"
                repeatCount="indefinite"
            />

        </rect>
        """


# ============================================================
# SVG
# ============================================================

svg = f"""<svg
xmlns="http://www.w3.org/2000/svg"
xmlns:xlink="http://www.w3.org/1999/xlink"
width="{WIDTH}"
height="{HEIGHT}"
viewBox="0 0 {WIDTH} {HEIGHT}"
>

<defs>

    <linearGradient id="background" x1="0" x2="1">
        <stop offset="0%" stop-color="#020617"/>
        <stop offset="48%" stop-color="#071426"/>
        <stop offset="100%" stop-color="#020617"/>
    </linearGradient>

    <linearGradient id="beamGradient" x1="0" x2="1">
        <stop offset="0%" stop-color="#ffffff"/>
        <stop offset="18%" stop-color="#e0f2fe"/>
        <stop offset="45%" stop-color="#67e8f9"/>
        <stop offset="75%" stop-color="#0ea5e9"/>
        <stop offset="100%" stop-color="#2563eb"/>
    </linearGradient>

    <linearGradient id="progressGradient" x1="0" x2="1">
        <stop offset="0%" stop-color="#22d3ee"/>
        <stop offset="55%" stop-color="#2563eb"/>
        <stop offset="100%" stop-color="#7c3aed"/>
    </linearGradient>

    <filter
        id="cellGlow"
        x="-200%"
        y="-200%"
        width="500%"
        height="500%"
    >
        <feGaussianBlur stdDeviation="2.4" result="blur"/>
        <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
        </feMerge>
    </filter>

    <filter
        id="beamGlow"
        x="-200%"
        y="-200%"
        width="500%"
        height="500%"
    >
        <feGaussianBlur stdDeviation="6" result="blur"/>
        <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
        </feMerge>
    </filter>

    <filter
        id="bigGlow"
        x="-250%"
        y="-250%"
        width="600%"
        height="600%"
    >
        <feGaussianBlur stdDeviation="13" result="blur"/>
        <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
        </feMerge>
    </filter>

</defs>


<!-- ===================================================== -->
<!-- BACKGROUND -->
<!-- ===================================================== -->

<rect
    width="{WIDTH}"
    height="{HEIGHT}"
    rx="20"
    fill="url(#background)"
    stroke="#0ea5e9"
    stroke-width="1.4"
/>

<path
    d="M20 20 H245 L275 47 H918 L948 20 H1180"
    fill="none"
    stroke="#0ea5e9"
    stroke-width="1.3"
    opacity=".55"
/>


<!-- ===================================================== -->
<!-- HEADER -->
<!-- ===================================================== -->

<text
    x="36"
    y="48"
    font-family="monospace"
    font-size="17"
    font-weight="700"
    fill="#22d3ee"
>
NAREN // BUILD SYSTEM
</text>

<text
    x="36"
    y="70"
    font-family="monospace"
    font-size="10"
    fill="#3b82f6"
>
CODE &gt; LEARN &gt; BUILD &gt; REPEAT
</text>


<text
    x="600"
    y="49"
    text-anchor="middle"
    font-family="monospace"
    font-size="27"
    font-weight="700"
    fill="#e2e8f0"
>
⚡ BUILD ACTIVITY
</text>

<text
    x="600"
    y="74"
    text-anchor="middle"
    font-family="monospace"
    font-size="12"
    fill="#94a3b8"
>
REAL GITHUB CONTRIBUTIONS
</text>


<!-- ===================================================== -->
<!-- POWER MODE -->
<!-- ===================================================== -->

<rect
    x="982"
    y="27"
    width="178"
    height="56"
    rx="10"
    fill="#07111f"
    stroke="#0ea5e9"
/>

<text
    x="997"
    y="50"
    font-family="monospace"
    font-size="12"
    font-weight="700"
    fill="#22d3ee"
>
POWER MODE
</text>

<text
    x="1105"
    y="50"
    font-family="monospace"
    font-size="12"
    font-weight="700"
    fill="#22c55e"
>
ON
</text>

<circle
    cx="1139"
    cy="46"
    r="5"
    fill="#22c55e"
    filter="url(#cellGlow)"
>
    <animate
        attributeName="opacity"
        values="1;.25;1"
        dur="1.25s"
        repeatCount="indefinite"
    />
</circle>

<text
    x="997"
    y="69"
    font-family="monospace"
    font-size="8"
    fill="#64748b"
>
CONTRIBUTIONS DRIVE PROGRESS
</text>


<!-- ===================================================== -->
<!-- GOKU -->
<!-- ===================================================== -->

<g>

    <image
        href="{goku_data_uri}"
        x="0"
        y="97"
        width="280"
        height="275"
        preserveAspectRatio="xMidYMid meet"
    />

    <animateTransform
        attributeName="transform"
        type="translate"
        values="0 0;0 -2;0 2;0 0"
        dur="2.6s"
        repeatCount="indefinite"
    />

</g>


<!-- ===================================================== -->
<!-- ENERGY CHARGE -->
<!-- ===================================================== -->

<circle
    cx="{BEAM_SOURCE_X}"
    cy="{BEAM_CENTER_Y:.2f}"
    r="10"
    fill="#ffffff"
    filter="url(#bigGlow)"
>

    <animate
        attributeName="r"
        values="8;8;25;18;18;8"
        keyTimes="
            0;
            .04;
            {t(CHARGE_END):.4f};
            {t(SWEEP_START):.4f};
            {t(PAUSE_END):.4f};
            1
        "
        dur="{LOOP}s"
        repeatCount="indefinite"
    />

</circle>


<circle
    cx="{BEAM_SOURCE_X}"
    cy="{BEAM_CENTER_Y:.2f}"
    r="18"
    fill="none"
    stroke="#22d3ee"
    stroke-width="3"
    filter="url(#beamGlow)"
>

    <animate
        attributeName="r"
        values="16;16;42;30;30;16"
        keyTimes="
            0;
            .04;
            {t(CHARGE_END):.4f};
            {t(SWEEP_START):.4f};
            {t(PAUSE_END):.4f};
            1
        "
        dur="{LOOP}s"
        repeatCount="indefinite"
    />

    <animate
        attributeName="opacity"
        values=".25;.25;.9;.65;.45;.25"
        keyTimes="
            0;
            .04;
            {t(CHARGE_END):.4f};
            {t(SWEEP_START):.4f};
            {t(PAUSE_END):.4f};
            1
        "
        dur="{LOOP}s"
        repeatCount="indefinite"
    />

</circle>


<!-- ===================================================== -->
<!-- FULL HEIGHT BEAM -->
<!-- Positioned UNDER contribution cells -->
<!-- ===================================================== -->

<path
    fill="#0ea5e9"
    opacity=".12"
    filter="url(#bigGlow)"
>

    <animate
        attributeName="d"
        values="
            M {BEAM_SOURCE_X} {BEAM_CENTER_Y:.2f}
            L {GRID_X} {BEAM_CENTER_Y - 8:.2f}
            L {GRID_X} {BEAM_CENTER_Y + 8:.2f} Z;

            M {BEAM_SOURCE_X} {BEAM_CENTER_Y:.2f}
            L {GRID_X} {GRID_Y - 7}
            L {GRID_X} {GRID_Y + GRID_HEIGHT + 7} Z;

            M {BEAM_SOURCE_X} {BEAM_CENTER_Y:.2f}
            L {GRID_END_X} {GRID_Y - 7}
            L {GRID_END_X} {GRID_Y + GRID_HEIGHT + 7} Z;

            M {BEAM_SOURCE_X} {BEAM_CENTER_Y:.2f}
            L {GRID_END_X} {GRID_Y - 7}
            L {GRID_END_X} {GRID_Y + GRID_HEIGHT + 7} Z;

            M {BEAM_SOURCE_X} {BEAM_CENTER_Y:.2f}
            L {GRID_X} {BEAM_CENTER_Y - 8:.2f}
            L {GRID_X} {BEAM_CENTER_Y + 8:.2f} Z
        "
        keyTimes="
            0;
            {t(SWEEP_START):.5f};
            {t(SWEEP_END):.5f};
            {t(PAUSE_END):.5f};
            1
        "
        dur="{LOOP}s"
        repeatCount="indefinite"
    />

</path>


<path
    fill="url(#beamGradient)"
    opacity=".28"
    filter="url(#beamGlow)"
>

    <animate
        attributeName="d"
        values="
            M {BEAM_SOURCE_X} {BEAM_CENTER_Y:.2f}
            L {GRID_X} {BEAM_CENTER_Y - 5:.2f}
            L {GRID_X} {BEAM_CENTER_Y + 5:.2f} Z;

            M {BEAM_SOURCE_X} {BEAM_CENTER_Y:.2f}
            L {GRID_X} {GRID_Y}
            L {GRID_X} {GRID_Y + GRID_HEIGHT} Z;

            M {BEAM_SOURCE_X} {BEAM_CENTER_Y:.2f}
            L {GRID_END_X} {GRID_Y}
            L {GRID_END_X} {GRID_Y + GRID_HEIGHT} Z;

            M {BEAM_SOURCE_X} {BEAM_CENTER_Y:.2f}
            L {GRID_END_X} {GRID_Y}
            L {GRID_END_X} {GRID_Y + GRID_HEIGHT} Z;

            M {BEAM_SOURCE_X} {BEAM_CENTER_Y:.2f}
            L {GRID_X} {BEAM_CENTER_Y - 5:.2f}
            L {GRID_X} {BEAM_CENTER_Y + 5:.2f} Z
        "
        keyTimes="
            0;
            {t(SWEEP_START):.5f};
            {t(SWEEP_END):.5f};
            {t(PAUSE_END):.5f};
            1
        "
        dur="{LOOP}s"
        repeatCount="indefinite"
    />

</path>


<!-- bright center -->

<line
    x1="{BEAM_SOURCE_X}"
    y1="{BEAM_CENTER_Y:.2f}"
    x2="{GRID_X}"
    y2="{BEAM_CENTER_Y:.2f}"
    stroke="#ffffff"
    stroke-width="6"
    stroke-linecap="round"
    opacity=".86"
    filter="url(#cellGlow)"
>

    <animate
        attributeName="x2"
        values="
            {GRID_X};
            {GRID_X};
            {GRID_END_X};
            {GRID_END_X};
            {GRID_X}
        "
        keyTimes="
            0;
            {t(SWEEP_START):.5f};
            {t(SWEEP_END):.5f};
            {t(PAUSE_END):.5f};
            1
        "
        dur="{LOOP}s"
        repeatCount="indefinite"
    />

</line>


<!-- ===================================================== -->
<!-- MONTH LABELS -->
<!-- ===================================================== -->

{month_svg}


<!-- ===================================================== -->
<!-- WEEKDAY LABELS -->
<!-- ===================================================== -->

{weekday_svg}


<!-- ===================================================== -->
<!-- REAL CONTRIBUTION CELLS -->
<!-- ===================================================== -->

<g>
{cells_svg}
</g>


<!-- ===================================================== -->
<!-- MOVING FULL-HEIGHT IMPACT FRONT -->
<!-- ===================================================== -->

<ellipse
    cx="{GRID_X}"
    cy="{BEAM_CENTER_Y:.2f}"
    rx="7"
    ry="{GRID_HEIGHT / 2 + 4:.2f}"
    fill="#ffffff"
    opacity="0"
    filter="url(#beamGlow)"
>

    <animate
        attributeName="cx"
        values="
            {GRID_X};
            {GRID_X};
            {GRID_END_X};
            {GRID_END_X};
            {GRID_X}
        "
        keyTimes="
            0;
            {t(SWEEP_START):.5f};
            {t(SWEEP_END):.5f};
            {t(PAUSE_END):.5f};
            1
        "
        dur="{LOOP}s"
        repeatCount="indefinite"
    />

    <animate
        attributeName="opacity"
        values="
            0;
            .85;
            .85;
            0;
            0
        "
        keyTimes="
            0;
            {t(SWEEP_START):.5f};
            {t(SWEEP_END):.5f};
            {t(PAUSE_END):.5f};
            1
        "
        dur="{LOOP}s"
        repeatCount="indefinite"
    />

</ellipse>


<ellipse
    cx="{GRID_X}"
    cy="{BEAM_CENTER_Y:.2f}"
    rx="18"
    ry="{GRID_HEIGHT / 2 + 11:.2f}"
    fill="none"
    stroke="#22d3ee"
    stroke-width="3"
    opacity="0"
    filter="url(#cellGlow)"
>

    <animate
        attributeName="cx"
        values="
            {GRID_X};
            {GRID_X};
            {GRID_END_X};
            {GRID_END_X};
            {GRID_X}
        "
        keyTimes="
            0;
            {t(SWEEP_START):.5f};
            {t(SWEEP_END):.5f};
            {t(PAUSE_END):.5f};
            1
        "
        dur="{LOOP}s"
        repeatCount="indefinite"
    />

    <animate
        attributeName="opacity"
        values="
            0;
            .9;
            .75;
            0;
            0
        "
        keyTimes="
            0;
            {t(SWEEP_START):.5f};
            {t(SWEEP_END):.5f};
            {t(PAUSE_END):.5f};
            1
        "
        dur="{LOOP}s"
        repeatCount="indefinite"
    />

</ellipse>


<!-- ===================================================== -->
<!-- PARTICLES -->
<!-- ===================================================== -->

<g filter="url(#cellGlow)">
{particles_svg}
</g>


<!-- ===================================================== -->
<!-- STATS -->
<!-- ===================================================== -->

<rect
    x="980"
    y="120"
    width="180"
    height="167"
    rx="10"
    fill="#07111f"
    stroke="#0ea5e9"
/>

<text
    x="997"
    y="150"
    font-family="monospace"
    font-size="9"
    fill="#94a3b8"
>
ACTIVE DAYS
</text>

<text
    x="1140"
    y="150"
    text-anchor="end"
    font-family="monospace"
    font-size="14"
    font-weight="700"
    fill="#22d3ee"
>
{active_days}
</text>


<line
    x1="997"
    y1="163"
    x2="1140"
    y2="163"
    stroke="#1e293b"
/>


<text
    x="997"
    y="190"
    font-family="monospace"
    font-size="9"
    fill="#94a3b8"
>
CONTRIBUTIONS
</text>

<text
    x="1140"
    y="190"
    text-anchor="end"
    font-family="monospace"
    font-size="14"
    font-weight="700"
    fill="#60a5fa"
>
{total_contributions}
</text>


<line
    x1="997"
    y1="203"
    x2="1140"
    y2="203"
    stroke="#1e293b"
/>


<text
    x="997"
    y="230"
    font-family="monospace"
    font-size="9"
    fill="#94a3b8"
>
CURRENT STREAK
</text>

<text
    x="1140"
    y="230"
    text-anchor="end"
    font-family="monospace"
    font-size="14"
    font-weight="700"
    fill="#a78bfa"
>
{current_streak}
</text>


<text
    x="997"
    y="264"
    font-family="monospace"
    font-size="10"
    font-weight="700"
    fill="#f59e0b"
>
KEEP BUILDING
</text>


<!-- ===================================================== -->
<!-- STATUS -->
<!-- ===================================================== -->

<text
    x="625"
    y="327"
    text-anchor="middle"
    font-family="monospace"
    font-size="14"
    font-weight="700"
    fill="#22d3ee"
>
POWERING THE SYSTEM...

    <animate
        attributeName="opacity"
        values=".4;1;.4"
        dur="1.3s"
        repeatCount="indefinite"
    />

</text>


<!-- ===================================================== -->
<!-- PROGRESS BAR -->
<!-- ===================================================== -->

<rect
    x="450"
    y="343"
    width="355"
    height="12"
    rx="6"
    fill="#0f172a"
    stroke="#0ea5e9"
/>

<rect
    x="453"
    y="346"
    width="0"
    height="6"
    rx="3"
    fill="url(#progressGradient)"
>

    <animate
        attributeName="width"
        values="0;0;349;349;0"
        keyTimes="
            0;
            {t(SWEEP_START):.5f};
            {t(SWEEP_END):.5f};
            {t(PAUSE_END):.5f};
            1
        "
        dur="{LOOP}s"
        repeatCount="indefinite"
    />

</rect>


<!-- ===================================================== -->
<!-- PIPELINE -->
<!-- ===================================================== -->

<path
    d="
        M370 374
        H830
        L850 396
        L830 418
        H370
        L350 396
        Z
    "
    fill="#06111e"
    stroke="#0ea5e9"
/>

<text
    x="600"
    y="402"
    text-anchor="middle"
    font-family="monospace"
    font-size="17"
    font-weight="700"
    fill="#dbeafe"
>
THINK → BUILD → DEBUG → SHIP
</text>


<text
    x="34"
    y="410"
    font-family="monospace"
    font-size="8"
    fill="#64748b"
>
DISCIPLINE BUILDS REAL POWER.
</text>

<text
    x="927"
    y="410"
    font-family="monospace"
    font-size="8"
    fill="#64748b"
>
CONSISTENCY TURNS IDEAS INTO IMPACT.
</text>

</svg>
"""


OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(svg, encoding="utf-8")

print("Generated:", OUTPUT)
print("Total contributions:", total_contributions)
print("Active days:", active_days)
print("Current streak:", current_streak)
print("Weeks:", week_count)
