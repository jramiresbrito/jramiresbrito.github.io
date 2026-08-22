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

print("\n" + ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
sys.exit(1 if FAILS else 0)
