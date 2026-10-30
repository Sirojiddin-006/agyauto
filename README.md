# agyauto

[English](README.md) · [Oʻzbekcha](README.uz.md)

Stop babysitting permission prompts. `agyauto` wraps a command (`agy`, or `ssh` into a server where you run `agy`) in its own
pseudo-terminal and answers agy's "Run this command? / Accept this file edit? / Allow creation of this file?" prompts for you,
with a [btop](https://github.com/aristocratos/btop)-style dashboard to watch, pause and audit every session.

```
curl -fsSL https://raw.githubusercontent.com/Sirojiddin-006/agyauto/main/install.sh | sh
```

Linux and macOS, Python 3.8+ (standard library only). Windows: use WSL for now.

## Use

```sh
agyauto agy                    # local agy
agyauto ssh user@server        # then start agy on the server
agyauto --name build ssh ci    # give the session a name
agyauto                        # open the dashboard (from any other terminal / workspace)
```

The keystroke is written straight into the wrapped command's pty. It never touches window focus, your keyboard or other
workspaces, so you can keep working elsewhere. Run as many sessions as you like; each is independent.

### Dashboard

| Key | |
|---|---|
| `1`-`5` / Tab | Sessions · Live · History · Stats · Settings |
| `j` `k` | select session / row |
| `p` | pause / resume the selected session |
| `d` | **dangermode** on/off for the selected session |
| `r` | rename session |
| `f` `/` `Enter` | History: kind filter, search, details |
| `L` | English ⇄ Oʻzbekcha |
| `q` | quit |

Changes made in the dashboard reach running sessions within about a second. No restart, the wrapped ssh is never interrupted.

### Safety

* Only option **1** (Enter, or `1` with `--key 1`) is ever sent. The "always allow (persist to settings.json)" options are never chosen.
* **Deleting `/` or `~` (`rm -rf /`, `--no-preserve-root`, ...) is never approved**, not even in dangermode. The prompt stays on
  screen, the terminal bell rings, a desktop notification is sent and the event is logged as `BLOCKED`.
* Add your own deny rules (regex) in Settings or `agyauto config set deny 'rm -rf|DROP TABLE'`.
* **Dangermode** approves *everything* else, including unknown prompts such as `press ctrl+j to approve` or `(y/n)`. It is off by default
  and enabled per session after a confirmation.
* Nothing is sent while you are typing in that terminal.
* Tokens, passwords and keys are redacted before anything is written to history or shown in the live view. The state
  directory is private (`0700`/`0600`).

Prompts agyauto does not recognise are recorded as `STALLED` (with a redacted screen snapshot) so the pattern can be added. Open an
issue with that snapshot.

## Commands

```
agyauto status [--json]          running sessions
agyauto history [-n N] [--kind APPROVED|BLOCKED|STALLED] [-s TEXT]
agyauto config [get|set KEY VALUE]   lang, key, delay, notify, retention_days, danger_default, deny
agyauto lang en|uz
agyauto doctor
agyauto update
agyauto uninstall [--purge]
```

Files: `~/.config/agyauto/config.json`, `~/.local/state/agyauto/` (history.db, live session files), program in `~/.local/share/agyauto/`.
History is kept 90 days by default.

## Development

```sh
python3 -m unittest discover -s tests -v
```

MIT licensed.
