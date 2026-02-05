import json
import os
import sys
import urllib.parse
import urllib.request
from collections import defaultdict


def gh_get(url: str, token: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-actions",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_repos(username: str, token: str):
    page = 1
    repos = []
    while True:
        q = urllib.parse.urlencode(
            {
                "per_page": 100,
                "type": "owner",
                "sort": "updated",
                "page": page,
            }
        )
        data = gh_get(f"https://api.github.com/users/{username}/repos?{q}", token)
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos


def aggregate_languages(username: str, repos, token: str):
    totals = defaultdict(int)
    for repo in repos:
        if repo.get("fork"):
            continue
        name = repo.get("name")
        if not name:
            continue
        try:
            data = gh_get(f"https://api.github.com/repos/{username}/{name}/languages", token)
        except Exception:
            continue
        for lang, count in data.items():
            totals[lang] += int(count)
    return totals


def render_svg(output_path: str, totals):
    if not totals:
        fallback = (
            "<svg xmlns='http://www.w3.org/2000/svg' width='600' height='220' viewBox='0 0 600 220'>"
            "<rect width='100%' height='100%' fill='#0d1117'/>"
            "<text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle' fill='#c9d1d9' "
            "font-family='Segoe UI, Arial, sans-serif' font-size='24'>Most used languages unavailable</text>"
            "</svg>"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(fallback)
        return

    palette = [
        "#f1e05a",
        "#3572A5",
        "#e34c26",
        "#563d7c",
        "#b07219",
        "#00ADD8",
        "#f34b7d",
        "#89e051",
        "#555555",
        "#701516",
    ]

    items = sorted(totals.items(), key=lambda it: it[1], reverse=True)[:10]
    total = sum(v for _, v in items) or 1

    bar_width = 540.0
    x = 30.0
    segments = []
    legend = []
    for i, (lang, value) in enumerate(items):
        pct = (value / total) * 100.0
        width = max(8.0, (value / total) * bar_width)
        color = palette[i % len(palette)]
        segments.append((x, width, color))

        col = 0 if i < 5 else 1
        row = i if i < 5 else i - 5
        lx = 40 + (col * 280)
        ly = 120 + (row * 24)
        legend.append((lx, ly, color, lang, pct))
        x += width

    parts = [
        "<svg xmlns='http://www.w3.org/2000/svg' width='600' height='250' viewBox='0 0 600 250' role='img' aria-label='Most Used Languages'>",
        "  <rect width='100%' height='100%' rx='8' fill='#0d1117'/>",
        "  <rect x='1' y='1' width='598' height='248' rx='7' fill='none' stroke='#ffffff' stroke-width='2'/>",
        "  <text x='30' y='48' fill='#ffffff' font-family='Segoe UI, Arial, sans-serif' font-size='20' font-weight='700'>Most Used Languages</text>",
    ]

    for sx, sw, color in segments:
        parts.append(f"  <rect x='{sx:.2f}' y='64' width='{sw:.2f}' height='14' rx='7' fill='{color}'/>")

    for lx, ly, color, lang, pct in legend:
        parts.append(f"  <circle cx='{lx}' cy='{ly}' r='7' fill='{color}'/>")
        parts.append(
            f"  <text x='{lx + 14}' y='{ly + 5}' fill='#ffffff' font-family='Segoe UI, Arial, sans-serif' font-size='14'>{lang} {pct:.1f}%</text>"
        )

    parts.append("</svg>")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


def main():
    if len(sys.argv) != 3:
        print("Usage: generate_top_langs_svg.py <username> <output_file>", file=sys.stderr)
        sys.exit(2)

    username = sys.argv[1]
    output_file = sys.argv[2]
    token = os.environ.get("GH_TOKEN", "")

    repos = fetch_repos(username, token)
    totals = aggregate_languages(username, repos, token)
    render_svg(output_file, totals)


if __name__ == "__main__":
    main()
