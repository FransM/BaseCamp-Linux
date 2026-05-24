# Control Interface & Action Chains

This covers the features added for GitHub issues **#16, #17, #18 and #20** —
driving BaseCamp from outside the GUI, chaining several actions onto one key,
switching pages and redefining keys.

> Status: backend + IPC + CLI are implemented and unit-tested. The GUI editor
> bits (new action types in the dropdown) are wired but need testing on real
> hardware — see the checklist at the end.

## Callable interface (#20)

While the GUI is running it hosts a small **Unix-domain socket** server. Any
program can connect and send one line of JSON to drive the keyboard / DisplayPad
— e.g. turn the board red when an appointment approaches, or push an icon to a
DisplayPad key when an email arrives.

- **Socket path:** `$XDG_RUNTIME_DIR/basecamp-control.sock`
  (falls back to `/tmp/basecamp-control-<uid>.sock`).
- **Protocol:** one JSON object per line in, one JSON reply line out
  (`{"ok": true, ...}` or `{"ok": false, "error": "..."}`).

### From the command line

```sh
# Health check
basecamp --ctl '{"cmd":"ping"}'

# Set the Everest 60 side ring to red
basecamp --ctl '{"cmd":"rgb","device":"everest60","args":["side-static","255","0","0"]}'

# Switch the GUI to the DisplayPad tab
basecamp --ctl '{"cmd":"page","page":"displaypad"}'

# Push an image to Everest Max macro key D3 (button index 2)
basecamp --ctl '{"cmd":"image","device":"everest_max","button":2,"path":"/home/me/icon.png"}'

# Redefine Everest Max key D1 to launch a terminal
basecamp --ctl '{"cmd":"set_key","button":0,"type":"shell","action":"kitty"}'

# Discover available pages and connected devices
basecamp --ctl '{"cmd":"list"}'
```

(`basecamp` = the AppImage / installed launcher. With a source checkout use
`python gui.py --ctl '<json>'`.)

### From any language

Connect to the socket, send a JSON line, read a JSON line. Python:

```python
from shared.ipc import send_command
send_command({"cmd": "rgb", "device": "everest60",
              "args": ["side-static", "0", "255", "0"]})
```

### Commands

| cmd       | fields                                              | effect |
|-----------|-----------------------------------------------------|--------|
| `ping`    | —                                                   | health / version |
| `list`    | —                                                   | pages, active page, device presence |
| `page`    | `page`                                              | switch GUI tab (`everest_max`, `everest60`, `makalu67`, `displaypad`, `obs`, `macros`, `plugins`, plugin ids) |
| `rgb`     | `device`, `args[]`                                  | run the device's `rgb …` verb |
| `run`     | `device`, `args[]`                                  | run any device-controller verb (e.g. `["upload","2","/p.png"]`) |
| `image`   | `device`, `button`, `path`                          | upload an image to a key |
| `set_key` | `button` (0–3), `type`, `action`                    | redefine an Everest Max macro key |

## Action chains — multiple actions per key (#17)

A key can run several actions in sequence. Each button's stored action dict may
carry an `actions` list of extra `{ "type": ..., "action": ... }` steps that run
in order right after the primary action, e.g. launch a command **and** switch to
a page:

```json
{
  "type": "shell", "action": "obs --startrecording",
  "actions": [ { "type": "page", "action": "displaypad" } ]
}
```

This is honoured by both dispatchers — the in-process DisplayPad handler and the
Everest Max action daemon.

## Redefine-key action (#18)

A new **`set_key`** action type changes another key on press (modal / layered
layouts).

- **Everest Max** (`action` is JSON): `{"button":1,"type":"shell","action":"firefox"}`
  — sent to the GUI over the control socket.
- **DisplayPad** (`action` is JSON): `{"page":0,"key":3,"type":"url","action":"https://…"}`
  — `page`/`key` default to the current page and the pressed key.

## Actions on plugin / monitor keys, and page hops (#16)

- Plugin-registered action types already dispatch on both DisplayPad and Everest
  Max, so a key showing a plugin/monitor can also carry a press action.
- The new **`page`** action type lets any key jump to another tab/page (e.g. a
  System-Monitor key that opens a details page).
- **F1–F12 on the Everest 60:** not implemented. The 60 has no app-assignable
  keys; remapping its real keys to function keys requires the keyboard's
  firmware remap protocol, which isn't reverse-engineered yet (a USB capture of
  Windows BaseCamp doing the remap would be needed — same approach as the side
  LEDs).

## Testing checklist (needs hardware / running GUI)

- [ ] `basecamp --ctl '{"cmd":"ping"}'` returns `{"ok": true, ...}` while the GUI runs.
- [ ] `rgb` / `image` / `page` / `set_key` over the socket take effect.
- [ ] An Everest Max key with `type:"page"` switches tabs; `type:"set_key"` redefines another key.
- [ ] A DisplayPad key with an `actions` chain runs every step in order.
- [ ] Existing single-action keys still behave exactly as before (backward compatibility).
