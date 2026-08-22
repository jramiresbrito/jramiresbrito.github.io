# New Bark Town Mods

The site at <https://jramiresbrito.github.io> that lists my Gen1Recomp mods.

## Adding a mod

Tag the mod's repository with **both** topics:

    gen1recomp    mod

That is the whole procedure. Nothing in this repository has to be edited.
Within six hours the card appears, with its name, version and supported
games read from the mod's own `manifest.json`.

Want it live immediately? Actions -> **Refresh mod list** -> Run workflow.

## What decides whether a mod is listed

`scripts/build_index.py`, in `wanted()`:

| Condition | Result |
|---|---|
| tagged `gen1recomp` **and** `mod` | listed |
| tagged only one of them | not listed |
| private, or archived | not listed |
| tagged `no-site` | not listed, without untagging it |

The repository **name** is never consulted, so a mod can be called anything.

## Where each field comes from

| Shown | Source |
|---|---|
| Name | `copy.json` override, else the mod's `manifest.json` `name`, else the repo name |
| Version | the mod's `manifest.json` `version`, else its latest release tag |
| GOLD / R/B/Y chips | the mod's `manifest.json` `games` (absent means Gen 1 only) |
| Description | `copy.json` override, else the GitHub repo description |

`copy.json` is **optional polish, not the list.** A mod with no entry there is
still listed in full, using its GitHub description. Add an entry only when a
card deserves better words than one line of description. Overrides may contain
HTML; GitHub descriptions are escaped.

## Running it locally

    python3 scripts/test_build.py     # offline, no token needed
    python3 scripts/build_index.py    # hits the GitHub API

Everything the builder writes sits between the `MODS:START` / `MODS:END`
markers in `index.html`. The rest of that file is hand-authored.
