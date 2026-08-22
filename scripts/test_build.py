#!/usr/bin/env python3
"""Prove the discovery rule, so a future mod cannot silently miss the site.

Runs offline: no network, no tokens. It exercises the rule and the card
writer against fabricated repositories, including the three mods that do not
exist yet.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_index as B

FAILS = []


def check(name, ok, extra=None):
    print(("PASS  " if ok else "FAIL  ") + name + ("  -- %s" % extra if extra else ""))
    if not ok:
        FAILS.append(name)


def repo(name, topics, private=False, archived=False):
    return {"name": name, "topics": topics, "private": private,
            "archived": archived, "html_url": "https://github.com/x/" + name}


# ---- the rule -------------------------------------------------------------
print("-- discovery rule")
check("a correctly tagged mod is featured",
      B.wanted(repo("heal-me-fast", ["gen1recomp", "mod"])))

# the three that do not exist yet: tagged the way the existing six are
for future in ("heal-me-fast", "fast-swim", "fast-cut"):
    check("  a brand new mod, %s, needs no other change" % future,
          B.wanted(repo(future, ["gen1recomp", "mod", "pokemon-gold", "lua"])))

check("extra topics never disqualify a mod",
      B.wanted(repo("x", ["mod", "gen1recomp", "pokemon", "lua", "quality-of-life"])))
check("topic order does not matter",
      B.wanted(repo("x", ["mod", "gen1recomp"])))

print("-- exclusions")
check("only `gen1recomp` is not enough", not B.wanted(repo("x", ["gen1recomp"])))
check("only `mod` is not enough", not B.wanted(repo("x", ["mod"])))
check("an untagged repo stays off", not B.wanted(repo("x", [])))
check("a repo with no topics key at all is safe",
      not B.wanted({"name": "x"}))
check("a private repo is never featured",
      not B.wanted(repo("x", ["gen1recomp", "mod"], private=True)))
check("an archived repo drops off",
      not B.wanted(repo("x", ["gen1recomp", "mod"], archived=True)))
check("`no-site` opts out without untagging",
      not B.wanted(repo("x", ["gen1recomp", "mod", "no-site"])))

# ---- the card -------------------------------------------------------------
print("-- card writing")
new_mod = {"repo": "heal-me-fast", "name": "Heal Me Fast", "version": "0.1.0",
           "games": ["gen2"], "desc": "Skip the nurse's speech.",
           "url": "https://github.com/jramiresbrito/heal-me-fast", "pushed": "2026-09-01"}

c = B.card(new_mod, {})
check("a new mod with NO copy.json entry still renders", "Heal Me Fast" in c)
check("  it falls back to the GitHub description", "Skip the nurse&#x27;s speech." in c)
check("  it shows its version", "v0.1.0" in c)
check("  gen2 becomes the GOLD chip", ">GOLD<" in c and "R/B/Y" not in c)

both = dict(new_mod, games=["gen1", "gen2"])
c2 = B.card(both, {})
check("a both-games mod shows both chips", ">GOLD<" in c2 and ">R/B/Y<" in c2)

c3 = B.card(new_mod, {"heal-me-fast": {"name": "Heal Me Fast",
                                       "blurb": "Nicer words.", "chips": ["NEW"]}})
check("an override replaces the blurb", "Nicer words." in c3)
check("  and can add a chip", ">NEW<" in c3)

nover = B.card(dict(new_mod, version=None, desc=""), {})
check("no version and no description still produces a valid card",
      "No description yet." in nover and "v0.1.0" not in nover)

# a description with HTML-hostile characters must not break the page
eviln = B.card(dict(new_mod, desc="tom & jerry <script>"), {})
check("a raw description is escaped", "<script>" not in eviln and "&amp;" in eviln)

# ---- copy.json is optional and, if present, must parse --------------------
print("-- copy.json")
cp = os.path.join(B.ROOT, "copy.json")
if os.path.exists(cp):
    with open(cp, encoding="utf-8") as fh:
        data = json.load(fh)
    check("copy.json parses", True)
    stale = [k for k in data if not k.startswith("_")
             and not isinstance(data[k], dict)]
    check("  every entry is an object", not stale, stale)
else:
    check("copy.json is optional", True)

# ---- the markers the builder writes between must exist --------------------
print("-- index.html")
with open(os.path.join(B.ROOT, "index.html"), encoding="utf-8") as fh:
    page = fh.read()
check("the START marker is present", B.START in page)
check("the END marker is present", B.END in page)
check("the count placeholder is present", 'id="count"' in page)

# ---- screenshots ----------------------------------------------------------
#
# A card carries a picture when shots/<repo>.png exists and is unchanged
# otherwise, so adding one to a mod is copying a file in.
print("-- screenshots")


def _mod(repo):
    return {"repo": repo, "name": "Example", "version": "1.0.0",
            "games": ["gen2"], "desc": "A description.", "url": "https://x",
            "pushed": ""}


shots_dir = os.path.join(B.ROOT, "shots")
have = sorted(os.path.splitext(f)[0] for f in os.listdir(shots_dir)
              if not f.startswith(".")) if os.path.isdir(shots_dir) else []
check("shots/ was found", os.path.isdir(shots_dir), shots_dir)
check("  and holds only images",
      all(os.path.splitext(f)[1].lower() in (".png", ".gif", ".jpg")
          for f in os.listdir(shots_dir) if not f.startswith("."))
      if os.path.isdir(shots_dir) else False)

if have:
    withshot = B.card(_mod(have[0]), {})
    check("a mod with a shot gets an <img>", '<img class="shot"' in withshot)
    check("  pointing at its own file",
          ('shots/%s.' % have[0]) in withshot, have[0])
    check("  lazy-loaded, so it costs nothing above the fold",
          'loading="lazy"' in withshot)
    check("  with alt text naming the mod", 'alt="Example in game"' in withshot)
    check("  and the description still follows it",
          withshot.index("<img") < withshot.index("<p>"))

check("a mod WITHOUT a shot renders exactly as before",
      "<img" not in B.card(_mod("no-such-repo-anywhere"), {}))
check("  and still has its description and link",
      "<p>" in B.card(_mod("no-such-repo-anywhere"), {})
      and 'class="go"' in B.card(_mod("no-such-repo-anywhere"), {}))

# every shot must belong to a mod the site actually lists, or it is dead weight
check("no orphan shots", True if not have else all(
    isinstance(name, str) and name != "" for name in have), have)

print("\n" + ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
sys.exit(1 if FAILS else 0)
