"""Generate profile cards from the GitHub public API, without external card hosts."""
import collections
import concurrent.futures
import datetime
import html
import json
import os
import pathlib
import urllib.parse
import urllib.request

LOGIN = "Barretomen"
ROOT = pathlib.Path(__file__).resolve().parents[1]


def get(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "barretomen-profile"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    request = urllib.request.Request("https://api.github.com/" + path, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def collect():
    now = datetime.datetime.now(datetime.timezone.utc)
    profile = get(f"users/{LOGIN}")
    repos = []
    page = 1
    while True:
        batch = get(f"users/{LOGIN}/repos?type=owner&per_page=100&page={page}")
        repos.extend(repo for repo in batch if not repo["private"])
        if len(batch) < 100:
            break
        page += 1

    original = [repo for repo in repos if not repo["fork"]]
    language_repos = [repo for repo in original if not repo["archived"]]
    language_paths = [
        f"repos/{LOGIN}/{urllib.parse.quote(repo['name'], safe='')}/languages"
        for repo in language_repos
    ]
    language_bytes = collections.Counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for languages in executor.map(get, language_paths):
            language_bytes.update(languages)

    primary_languages = collections.Counter(
        repo["language"] for repo in original if repo.get("language")
    )
    pushed = [repo["pushed_at"] for repo in original if repo.get("pushed_at")]
    return {
        "updated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "public_repositories": len(repos),
        "stars_on_original_public_repositories": sum(repo["stargazers_count"] for repo in original),
        "forks_on_original_public_repositories": sum(repo["forks_count"] for repo in original),
        "followers": profile["followers"],
        "following": profile["following"],
        "last_public_push": max(pushed, default="")[:10],
        "primary_languages_by_original_repository": dict(primary_languages.most_common()),
        "language_bytes": dict(language_bytes.most_common()),
    }


def palette(theme):
    if theme == "light":
        return {"background": "#FFFFFF", "border": "#D0D7DE", "text": "#1F2328",
                "muted": "#59636E", "accent": "#087F78", "track": "#E6EDF3"}
    return {"background": "#0D1117", "border": "#30363D", "text": "#F0F6FC",
            "muted": "#8B949E", "accent": "#17D6C5", "track": "#21262D"}


def card(title, description, body, stats, theme):
    colors = palette(theme)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="330" viewBox="0 0 420 330" role="img" aria-labelledby="title description">
<title id="title">{html.escape(title)}</title>
<desc id="description">{html.escape(description)}</desc>
<style>text{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;fill:{colors["text"]}}}.heading{{font-size:19px;font-weight:600;fill:{colors["accent"]}}}.label{{font-size:13px;fill:{colors["muted"]}}}.value{{font-size:32px;font-weight:600}}.foot{{font-size:10px;fill:{colors["muted"]}}}</style>
<rect x=".5" y=".5" width="419" height="329" rx="10" fill="{colors["background"]}" stroke="{colors["border"]}"/>
<text x="26" y="37" class="heading">{html.escape(title)}</text>
<path d="M26 56H394" stroke="{colors["border"]}"/>
{body}
<path d="M26 289H394" stroke="{colors["border"]}"/>
<text x="26" y="312" class="foot">GitHub public API · {html.escape(stats["updated_at"])}</text>
</svg>
'''


def render(stats, theme="dark"):
    colors = palette(theme)
    values = [
        ("Public repositories", stats["public_repositories"]),
        ("Stars earned", stats["stars_on_original_public_repositories"]),
        ("Repository forks", stats["forks_on_original_public_repositories"]),
        ("Followers", stats["followers"]),
    ]
    rows = []
    for index, (label, value) in enumerate(values):
        x = 26 + (index % 2) * 194
        y = 112 + (index // 2) * 87
        rows.append(
            f'<text x="{x}" y="{y}" class="value">{value:,}</text>'
            f'<text x="{x}" y="{y + 24}" class="label">{label}</text>'
        )
    last_push = stats["last_public_push"] or "No public pushes yet"
    rows.append(f'<circle cx="30" cy="267" r="3" fill="{colors["accent"]}"/>')
    rows.append(f'<text x="42" y="271" class="label">Last public push · {html.escape(last_push)}</text>')
    description = ", ".join(f"{label}: {value}" for label, value in values)
    return card("João’s GitHub activity", description, "\n".join(rows), stats, theme)


def render_languages(stats, theme="dark"):
    colors = palette(theme)
    total = sum(stats["language_bytes"].values())
    swatches = ["#17D6C5", "#56C7F3", "#F7B42C", "#9CBBF9", "#52B788", "#D7BDE2"]
    rows = []
    for index, (name, size) in enumerate(list(stats["language_bytes"].items())[:6]):
        share = size * 100 / total
        y = 83 + index * 33
        rows.append(
            f'<text x="26" y="{y}" font-size="12">{html.escape(name)}</text>'
            f'<text x="394" y="{y}" text-anchor="end" class="label">{share:.1f}%</text>'
            f'<rect x="26" y="{y + 8}" width="368" height="5" rx="2.5" fill="{colors["track"]}"/>'
            f'<rect x="26" y="{y + 8}" width="{368 * share / 100:.2f}" height="5" rx="2.5" fill="{swatches[index]}"/>'
        )
    if not total:
        rows.append('<text x="26" y="110" class="label">No public language data yet.</text>')
    rows.append('<text x="26" y="275" class="foot">Code size across original, unarchived public repos</text>')
    description = "Language shares by GitHub Linguist code size. " + ", ".join(
        f"{name}: {size} bytes" for name, size in stats["language_bytes"].items()
    )
    return card("Most used languages", description, "\n".join(rows), stats, theme)


if __name__ == "__main__":
    stats = collect()
    output = pathlib.Path(os.environ.get("PROFILE_ASSET_DIR", ROOT / "assets"))
    output.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        suffix = "" if theme == "dark" else "-light"
        (output / f"github-stats{suffix}.svg").write_text(render(stats, theme), encoding="utf-8")
        (output / f"top-languages{suffix}.svg").write_text(render_languages(stats, theme), encoding="utf-8")
    (output / "github-stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(stats, ensure_ascii=False))
