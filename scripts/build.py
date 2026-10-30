#!/usr/bin/env python3
"""Render the terminal-style profile card (dark_mode.svg / light_mode.svg).

Run locally:   python3 scripts/build.py
With stats:    GH_TOKEN=<token> python3 scripts/build.py

Stdlib only. When no token is available the last fetched stats in
cache/stats.json are reused so the card still renders.
"""

import datetime as dt
import json
import os
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "stats.json"

# --------------------------------------------------------------------------
# Edit this block to change what the card says.
# --------------------------------------------------------------------------
USER = "viswabnath"
PROMPT_USER = "viswa"
HANDLE = "viswanath@onemark"

INFO = [
    ("OS", "Web, macOS, anything with a browser"),
    ("Uptime", "{uptime}"),
    ("Host", "OneMark"),
    ("Kernel", "Creative Frontend Developer"),
    None,
    ("Languages.Core", "JavaScript, HTML, CSS"),
    ("Frameworks", "React, Vite"),
    ("Graphics", "Three.js, GSAP"),
    ("Backend", "Firebase, Git"),
    None,
    ("Focus", "Interactive 3D web, UI animation"),
]

CONTACT = [
    ("Portfolio", "viswabnath.github.io/portfolio"),
    ("LinkedIn", "in/viswabnath"),
    ("GitHub", "@viswabnath"),
]

PLAN = [
    ("x", "build immersive, interactive 3D web experiences"),
    ("x", "craft refined UI animations"),
    ("~", "push web performance & modern rendering further"),
]

THEMES = {
    "dark": {
        "bg": "#0d1117", "bar": "#161b22", "border": "#30363d",
        "text": "#c9d1d9", "dim": "#6e7681", "key": "#ffa657",
        "value": "#a5d6ff", "user": "#3fb950", "path": "#79c0ff",
        "cursor": "#58a6ff", "warn": "#e3b341",
        "grad": ("#58a6ff", "#bc8cff"), "scan": 0.025,
        "blocks": ["#ff7b72", "#ffa657", "#e3b341", "#3fb950",
                   "#56d4dd", "#79c0ff", "#d2a8ff", "#c9d1d9"],
    },
    "light": {
        "bg": "#ffffff", "bar": "#f6f8fa", "border": "#d0d7de",
        "text": "#24292f", "dim": "#8c959f", "key": "#bc4c00",
        "value": "#0a3069", "user": "#1a7f37", "path": "#0550ae",
        "cursor": "#0969da", "warn": "#9a6700",
        "grad": ("#0969da", "#8250df"), "scan": 0,
        "blocks": ["#cf222e", "#bc4c00", "#9a6700", "#1a7f37",
                   "#1b7c83", "#0969da", "#8250df", "#24292f"],
    },
}

# --------------------------------------------------------------------------
# Layout constants
# --------------------------------------------------------------------------
W = 860
CW = 8.4          # monospace glyph advance at 14px
LH = 20           # line height
PAD = 24
BAR = 34
INFO_X = 280      # left edge of the neofetch text column
COLS = 62         # width of a key/value row in characters

# 5x7 pixel monogram "VB"
GLYPHS = [
    "1...1.1111.",
    "1...1.1...1",
    "1...1.1...1",
    "1...1.1111.",
    ".1.1..1...1",
    ".1.1..1...1",
    "..1...1111.",
]
PX = 20

CUBE = [
    "      +----------+",
    "     /          /|",
    "    /          / |",
    "   +----------+  |",
    "   |          |  +",
    "   |  onemark | / ",
    "   |          |/  ",
    "   +----------+   ",
]


# --------------------------------------------------------------------------
# GitHub stats
# --------------------------------------------------------------------------
def gql(token, query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": USER},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


def fetch_stats(token):
    base = gql(token, """
      query($login: String!) {
        user(login: $login) {
          createdAt
          followers { totalCount }
          pullRequests { totalCount }
          repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) { totalCount }
          contributionsCollection { contributionYears }
        }
      }""", {"login": USER})["user"]

    stars, repos, cursor = 0, 0, None
    while True:
        page = gql(token, """
          query($login: String!, $cursor: String) {
            user(login: $login) {
              repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, privacy: PUBLIC) {
                totalCount
                pageInfo { hasNextPage endCursor }
                nodes { stargazerCount }
              }
            }
          }""", {"login": USER, "cursor": cursor})["user"]["repositories"]
        repos = page["totalCount"]
        stars += sum(n["stargazerCount"] for n in page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    commits = 0
    for year in base["contributionsCollection"]["contributionYears"]:
        cc = gql(token, """
          query($login: String!, $from: DateTime!, $to: DateTime!) {
            user(login: $login) {
              contributionsCollection(from: $from, to: $to) {
                totalCommitContributions
                restrictedContributionsCount
              }
            }
          }""", {"login": USER, "from": f"{year}-01-01T00:00:00Z",
                 "to": f"{year}-12-31T23:59:59Z"})["user"]["contributionsCollection"]
        commits += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]

    return {
        "created_at": base["createdAt"],
        "repos": repos,
        "stars": stars,
        "commits": commits,
        "followers": base["followers"]["totalCount"],
        "contributed": base["repositoriesContributedTo"]["totalCount"],
        "prs": base["pullRequests"]["totalCount"],
    }


def load_stats():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        stats = fetch_stats(token)
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps(stats, indent=2) + "\n")
        return stats
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    return {"created_at": None, "repos": 0, "stars": 0, "commits": 0,
            "followers": 0, "contributed": 0, "prs": 0}


def uptime(created_at):
    if not created_at:
        return "booting..."
    start = dt.date.fromisoformat(created_at[:10])
    today = dt.date.today()
    y, m, d = today.year - start.year, today.month - start.month, today.day - start.day
    if d < 0:
        m -= 1
        d += (today.replace(day=1) - dt.timedelta(days=1)).day
    if m < 0:
        y -= 1
        m += 12

    def unit(n, word):
        return f"{n} {word}{'' if n == 1 else 's'}"
    return f"{unit(y, 'year')}, {unit(m, 'month')}, {unit(d, 'day')}"


# --------------------------------------------------------------------------
# SVG building
# --------------------------------------------------------------------------
class Card:
    def __init__(self, t):
        self.t = t
        self.out = []
        self.defs = []
        self.clips = 0

    def span(self, text, color, bold=False):
        weight = ' font-weight="700"' if bold else ""
        return f'<tspan fill="{color}"{weight}>{escape(text)}</tspan>'

    def line(self, x, y, spans, at):
        self.out.append(
            f'<text x="{x}" y="{y}" visibility="hidden">{"".join(spans)}'
            f'<set attributeName="visibility" to="visible" begin="{at:.3f}s" fill="freeze"/></text>')

    def prompt(self, y, cmd, at):
        """Draw a prompt, type `cmd` into it, return the time typing ends."""
        t = self.t
        spans = [self.span(PROMPT_USER, t["user"], True), self.span("@", t["dim"]),
                 self.span("github", t["user"], True), self.span(":", t["dim"]),
                 self.span("~", t["path"], True), self.span("$ ", t["dim"])]
        self.line(PAD, y, spans, at)
        x0 = PAD + CW * (len(PROMPT_USER) + len("@github:~$ "))
        if not cmd:
            self.out.append(
                f'<rect x="{x0:.1f}" y="{y - 13}" width="{CW}" height="17" fill="{t["cursor"]}" visibility="hidden">'
                f'<set attributeName="visibility" to="visible" begin="{at:.3f}s" fill="freeze"/>'
                f'<animate attributeName="opacity" values="1;0" dur="1.1s" calcMode="discrete" '
                f'begin="{at:.3f}s" repeatCount="indefinite"/></rect>')
            return at

        start, step = at + 0.5, 0.075
        n = len(cmd)
        dur = step * n
        widths = ";".join(f"{CW * (i + 1):.1f}" for i in range(n))
        xs = ";".join(f"{x0 + CW * (i + 1):.1f}" for i in range(n))
        keys = ";".join(f"{i / n:.3f}" for i in range(n))
        cid = f"type{self.clips}"
        self.clips += 1
        self.defs.append(
            f'<clipPath id="{cid}"><rect x="{x0:.1f}" y="{y - 16}" width="0" height="22">'
            f'<animate attributeName="width" values="{widths}" keyTimes="{keys}" calcMode="discrete" '
            f'begin="{start:.3f}s" dur="{dur:.3f}s" fill="freeze"/></rect></clipPath>')
        self.out.append(
            f'<text x="{x0:.1f}" y="{y}" clip-path="url(#{cid})">{self.span(cmd, t["text"])}</text>')
        end = start + dur
        self.out.append(
            f'<rect x="{x0:.1f}" y="{y - 13}" width="{CW}" height="17" fill="{t["cursor"]}" visibility="hidden">'
            f'<set attributeName="visibility" to="visible" begin="{at:.3f}s" fill="freeze"/>'
            f'<animate attributeName="x" values="{xs}" keyTimes="{keys}" calcMode="discrete" '
            f'begin="{start:.3f}s" dur="{dur:.3f}s" fill="freeze"/>'
            f'<set attributeName="visibility" to="hidden" begin="{end + 0.25:.3f}s" fill="freeze"/></rect>')
        return end + 0.3

    def kv(self, y, key, value, at, width=COLS):
        t = self.t
        parts = key.split(".")
        key_len = len(key) + 1
        dots = max(width - 2 - key_len - 2 - len(value), 1)
        spans = [self.span(". ", t["dim"])]
        for i, p in enumerate(parts):
            if i:
                spans.append(self.span(".", t["text"]))
            spans.append(self.span(p, t["key"]))
        spans += [self.span(":", t["text"]), self.span(" " + "." * dots + " ", t["dim"]),
                  self.span(value, t["value"])]
        self.line(INFO_X, y, spans, at)

    def kv_pair(self, y, left, right, at):
        t = self.t
        half = (COLS - 1) // 2
        spans = [self.span(". ", t["dim"])]
        for i, (k, v) in enumerate((left, right)):
            w = half - 2 if i == 0 else COLS - 5 - (half - 2)
            dots = max(w - len(k) - 1 - 2 - len(v), 1)
            if i:
                spans.append(self.span(" | ", t["dim"]))
            spans += [self.span(k, t["key"]), self.span(":", t["text"]),
                      self.span(" " + "." * dots + " ", t["dim"]), self.span(v, t["value"])]
        self.line(INFO_X, y, spans, at)

    def header(self, y, label, at):
        t = self.t
        rule = "─" * (COLS - len(label) - 1)
        self.line(INFO_X, y, [self.span(label, t["user"], True), self.span(" " + rule, t["dim"])], at)


def render(theme, stats):
    t = THEMES[theme]
    c = Card(t)
    y = BAR + 26

    at = c.prompt(y, "neofetch", 0.4)
    at += 0.15
    y += LH * 1.5
    top = y

    # Left column: pixel monogram + wireframe cube
    art_x, art_y = PAD + 6, top - 12
    g0, g1 = t["grad"]
    c.defs.append(
        f'<linearGradient id="grad" gradientUnits="userSpaceOnUse" x1="{art_x}" y1="{art_y}" '
        f'x2="{art_x + PX * 11}" y2="{art_y + PX * 7}"><stop offset="0" stop-color="{g0}"/>'
        f'<stop offset="1" stop-color="{g1}"/></linearGradient>')
    rows = []
    for r, row in enumerate(GLYPHS):
        rects = "".join(
            f'<rect x="{art_x + col * PX}" y="{art_y + r * PX}" width="{PX - 2}" height="{PX - 2}" rx="3"/>'
            for col, ch in enumerate(row) if ch == "1")
        rows.append(f'<g visibility="hidden">{rects}<set attributeName="visibility" to="visible" '
                    f'begin="{at + r * 0.04:.3f}s" fill="freeze"/></g>')
    c.out.append(f'<g class="pulse" fill="url(#grad)" filter="url(#glow)">{"".join(rows)}</g>')
    cy = art_y + PX * 7 + 44
    for i, row in enumerate(CUBE):
        # Position by indent: some renderers drop leading whitespace.
        indent = len(row) - len(row.lstrip())
        c.line(f"{art_x - 6 + indent * CW:.1f}", cy + i * 18, [c.span(row.strip(), t["dim"])],
               at + 0.3 + i * 0.03)

    # Right column: neofetch info
    step = 0.04
    c.line(INFO_X, y, [c.span(HANDLE, t["user"], True), c.span(" " + "─" * (COLS - len(HANDLE) - 1), t["dim"])], at)
    for item in INFO:
        y += LH
        at += step
        if item is None:
            c.line(INFO_X, y, [c.span(".", t["dim"])], at)
            continue
        key, value = item
        c.kv(y, key, value.format(uptime=uptime(stats["created_at"])), at)

    y += LH * 2
    at += step
    c.header(y, "- Contact", at)
    for key, value in CONTACT:
        y += LH
        at += step
        c.kv(y, key, value, at)

    y += LH * 2
    at += step
    c.header(y, "- GitHub Stats", at)
    fmt = "{:,}".format
    for left, right in (
        (("Repos", fmt(stats["repos"])), ("Stars", fmt(stats["stars"]))),
        (("Commits", fmt(stats["commits"])), ("Followers", fmt(stats["followers"]))),
        (("Contributed", fmt(stats["contributed"])), ("Pull Requests", fmt(stats["prs"]))),
    ):
        y += LH
        at += step
        c.kv_pair(y, left, right, at)

    y += LH + 6
    at += step
    blocks = "".join(
        f'<rect x="{INFO_X + i * CW * 3:.1f}" y="{y}" width="{CW * 3:.1f}" height="16" fill="{col}"/>'
        for i, col in enumerate(t["blocks"]))
    c.out.append(f'<g visibility="hidden">{blocks}<set attributeName="visibility" to="visible" '
                 f'begin="{at:.3f}s" fill="freeze"/></g>')

    # cat ~/.plan
    y += LH * 2 + 14
    at = c.prompt(y, "cat ~/.plan", at + 0.5)
    for mark, task in PLAN:
        y += LH
        at += 0.12
        color = t["user"] if mark == "x" else t["warn"]
        c.line(PAD, y, [c.span("[", t["dim"]), c.span(mark, color, True),
                        c.span("] ", t["dim"]), c.span(task, t["text"])], at)

    y += LH
    c.prompt(y, "", at + 0.6)

    h = int(y + PAD)
    scan = (f'<rect y="{BAR}" width="{W}" height="{h - BAR}" fill="url(#scan)"/>'
            if t["scan"] else "")
    title = f"{PROMPT_USER}@github: ~ — zsh"
    summary = (f"{HANDLE}: Creative Frontend Developer building interactive 3D web "
               f"experiences with React, Three.js and GSAP under the OneMark brand.")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" role="img" aria-labelledby="title">
<title id="title">{escape(summary)}</title>
<style>
text {{ font: 14px ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace; white-space: pre; }}
.title {{ font-size: 12px; fill: {t["dim"]}; }}
.pulse {{ animation: pulse 3.2s ease-in-out infinite; }}
@keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.72; }} }}
@media (prefers-reduced-motion: reduce) {{ .pulse {{ animation: none; }} }}
</style>
<defs>
<filter id="glow" x="-10%" y="-10%" width="120%" height="120%">
<feGaussianBlur stdDeviation="2.4" result="blur"/>
<feComponentTransfer in="blur" result="soft"><feFuncA type="linear" slope="0.5"/></feComponentTransfer>
<feMerge><feMergeNode in="soft"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#ffffff" fill-opacity="{t["scan"]}"/></pattern>
<clipPath id="window"><rect width="{W}" height="{h}" rx="10"/></clipPath>
{chr(10).join(c.defs)}
</defs>
<g clip-path="url(#window)">
<rect width="{W}" height="{h}" fill="{t["bg"]}"/>
<rect width="{W}" height="{BAR}" fill="{t["bar"]}"/>
<line x1="0" y1="{BAR}" x2="{W}" y2="{BAR}" stroke="{t["border"]}"/>
<circle cx="20" cy="17" r="6" fill="#ff5f56"/><circle cx="40" cy="17" r="6" fill="#ffbd2e"/><circle cx="60" cy="17" r="6" fill="#27c93f"/>
<text class="title" x="{W / 2}" y="21" text-anchor="middle">{escape(title)}</text>
<g xml:space="preserve">
{chr(10).join(c.out)}
</g>
{scan}
</g>
<rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="10" fill="none" stroke="{t["border"]}"/>
</svg>
'''


def main():
    stats = load_stats()
    for theme in THEMES:
        (ROOT / f"{theme}_mode.svg").write_text(render(theme, stats))
    print("rendered with", stats)


if __name__ == "__main__":
    main()
