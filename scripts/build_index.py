#!/usr/bin/env python3
"""Rebuild the mod cards in index.html from the repositories themselves.

The point of this script is that publishing a new mod should be the ONLY
step. Tag the repo `gen1recomp` + `mod` and it appears here on the next run;
nothing about this site has to be remembered or edited.

Where each field comes from, most authoritative first:

  version   the repo's own manifest.json, falling back to the latest release
            tag. The manifest is what the launcher reads, so it is what the
            site should quote -- a release tag can lag a version bump.
  games     manifest.json `games`. Absent means Gen 1 only, which is the
            engine's own default (ModTargets), not a missing value.
  blurb     copy.json in this repo if it has an entry, else the repo
            description. The override exists so a card can read better than
            a one-line GitHub description without making a new mod's card
            depend on remembering to write one.
  link      the repo URL.

Everything is written between the MODS:START / MODS:END markers. The rest of
index.html is never touched, so the design stays hand-authored.
"""
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

OWNER = "jramiresbrito"
NEEDS_TOPICS = {"gen1recomp", "mod"}
SKIP_TOPIC = "no-site"          # opt a repo out without untagging it
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = "<!-- MODS:START"
END = "<!-- MODS:END -->"

# manifest `games` -> the chip a player recognises
GAME_CHIPS = [("gen1", "R/B/Y"), ("gen2", "GOLD")]


def api(path, token=None):
    url = "https://api.github.com" + path
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "new-bark-mods-site",
    })
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def raw(repo, branch, path):
    url = "https://raw.githubusercontent.com/%s/%s/%s/%s" % (OWNER, repo, branch, path)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except (urllib.error.URLError, ValueError):
        return None


def wanted(repo):
    """The whole discovery rule, in one place.

    A repository is featured when it is tagged `gen1recomp` AND `mod`, is
    public, and is not archived. `no-site` opts one out without having to
    strip its topics. Nothing here looks at the repo NAME, so a mod called
    anything at all is found the moment it is tagged.
    """
    if repo.get("private") or repo.get("archived"):
        return False
    topics = set(repo.get("topics") or [])
    if SKIP_TOPIC in topics:
        return False
    return NEEDS_TOPICS.issubset(topics)


def collect(token=None):
    repos = []
    page = 1
    while True:
        batch = api("/users/%s/repos?per_page=100&page=%d" % (OWNER, page), token)
        if not batch:
            break
        repos.extend(batch)
        page += 1
        if page > 10:
            break

    mods = []
    for r in repos:
        if not wanted(r):
            continue
        branch = r.get("default_branch") or "main"
        manifest = raw(r["name"], branch, "manifest.json") or {}

        version = manifest.get("version")
        if not version:
            try:
                version = (api("/repos/%s/%s/releases/latest"
                               % (OWNER, r["name"]), token).get("tag_name") or "").lstrip("v")
            except urllib.error.HTTPError:
                version = None

        mods.append({
            "repo": r["name"],
            "name": manifest.get("name") or r["name"].replace("-", " ").title(),
            "version": version,
            # absent `games` means Gen 1 only -- the engine's own default
            "games": manifest.get("games") or ["gen1"],
            "desc": (r.get("description") or "").strip(),
            "url": r["html_url"],
            "pushed": r.get("pushed_at") or "",
        })

    # newest activity first, so the thing being worked on leads
    mods.sort(key=lambda m: m["pushed"], reverse=True)
    return mods


def card(mod, copy):
    over = copy.get(mod["repo"], {})
    title = over.get("name") or mod["name"]
    # A copy.json blurb is authored here and may carry markup on purpose
    # (<strong>, &eacute;). A GitHub description is plain text arriving from
    # outside this repo, so it is escaped -- an unescaped "<" in a
    # description would otherwise inject markup into the page.
    if over.get("blurb"):
        blurb = over["blurb"]
    elif mod["desc"]:
        blurb = html.escape(mod["desc"])
    else:
        blurb = "No description yet."

    chips = []
    if mod["version"]:
        chips.append('<span class="chip v">v%s</span>' % html.escape(mod["version"]))
    for key, label in GAME_CHIPS:
        if key in mod["games"]:
            chips.append('<span class="chip">%s</span>' % label)
    for extra in over.get("chips", []):
        chips.append('<span class="chip">%s</span>' % html.escape(extra))

    return (
        '      <article class="mod">\n'
        '        <h3>%s</h3>\n'
        '        <div class="chips">\n          %s\n        </div>\n'
        '        <p>%s</p>\n'
        '        <a class="go" href="%s">Get it</a>\n'
        '      </article>\n'
    ) % (html.escape(title), "\n          ".join(chips), blurb, html.escape(mod["url"]))


def main():
    token = os.environ.get("GITHUB_TOKEN") or None
    copy_path = os.path.join(ROOT, "copy.json")
    copy = {}
    if os.path.exists(copy_path):
        with open(copy_path, encoding="utf-8") as fh:
            copy = json.load(fh)

    mods = collect(token)
    if not mods:
        # Never blank the page because the API had a bad minute.
        print("no mods discovered - leaving index.html untouched", file=sys.stderr)
        return 1

    index = os.path.join(ROOT, "index.html")
    with open(index, encoding="utf-8") as fh:
        page = fh.read()

    body = "".join(card(m, copy) for m in mods)
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(page):
        print("markers not found in index.html", file=sys.stderr)
        return 1
    block = (START + " - generated by scripts/build_index.py, do not edit by hand -->\n"
             + body + "      " + END)
    page = pattern.sub(lambda _: block, page, count=1)

    page = re.sub(r'(<span class="stat" id="count">)[^<]*(</span>)',
                  r"\g<1>%d released\g<2>" % len(mods), page, count=1)

    with open(index, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)

    print("wrote %d mods:" % len(mods))
    for m in mods:
        print("  %-22s v%-8s %s" % (m["repo"], m["version"] or "?", ",".join(m["games"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
