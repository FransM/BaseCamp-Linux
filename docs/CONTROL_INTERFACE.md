# Control Interface & Action Chains

This covers driving BaseCamp from outside the GUI, chaining several actions onto
one key, switching pages and redefining keys (GitHub issues **#16**, **#17**,
**#18**, **#20** and **#63**).

## Callable interface (#20)

While the GUI is running it hosts a small **Unix-domain socket** server. Any
program can connect and send one line of JSON to drive the keyboard or the
DisplayPad, e.g. turn the board red when an appointment approaches, push an icon
to a DisplayPad key when an email arrives, or flip the pad to a page of snippets
when your editor starts.

- **Socket path:** `$XDG_RUNTIME_DIR/basecamp-control.sock`
  (falls back to `/tmp/basecamp-control-<uid>.sock`).
- **Protocol:** one JSON object per line in, one JSON reply line out
  (`{"ok": true, ...}` or `{"ok": false, "error": "..."}`).
- The GUI does not have to be visible. Minimized to tray works the same.

### From the command line

```sh
# Health check
basecamp --ctl '{"cmd":"ping"}'

# Set the Everest 60 side ring to red
basecamp --ctl '{"cmd":"rgb","device":"everest60","args":["side-static","255","0","0"]}'

# Switch the GUI to the DisplayPad tab
basecamp --ctl '{"cmd":"page","page":"displaypad"}'

# Switch the DisplayPad itself to one of your key pages
basecamp --ctl '{"cmd":"dp_page","page":"Editor"}'

# Push an image to Everest Max macro key D3 (button index 2)
basecamp --ctl '{"cmd":"image","device":"everest_max","button":2,"path":"/home/me/icon.png"}'

# Redefine Everest Max key D1 to launch a terminal
basecamp --ctl '{"cmd":"set_key","button":0,"type":"shell","action":"kitty"}'

# Discover tabs, connected devices, DisplayPad pages and the page it is on
basecamp --ctl '{"cmd":"list"}'
```

(`basecamp` = the AppImage / installed launcher. With a source checkout use
`python gui.py --ctl '<json>'`.) The reply is printed to stdout and the exit
code is 0 on `"ok": true`, 1 otherwise, so shell scripts can just test `$?`.

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
| `ping`    | none                                                | health / version |
| `list`    | none                                                | GUI tabs, active tab, device presence, DisplayPad pages + current page |
| `page`    | `page`                                              | switch GUI tab (`everest_max`, `everest60`, `makalu67`, `displaypad`, `obs`, `macros`, `plugins`, plugin ids) |
| `dp_page` | `page`                                              | switch the DisplayPad's active key page, by name, by id, or `"prev"` |
| `rgb`     | `device`, `args[]`                                  | run the device's `rgb …` verb |
| `run`     | `device`, `args[]`                                  | run any device-controller verb (e.g. `["upload","2","/p.png"]`) |
| `image`   | `device`, `button`, `path`                          | upload an image to a key |
| `set_key` | `button` (0-3), `type`, `action`                    | redefine an Everest Max macro key |

`page` and `dp_page` are different things: `page` decides which panel the GUI
shows, `dp_page` decides which twelve keys the physical pad shows.

### Switching DisplayPad pages from a script (#63)

`dp_page` takes the page **name** you gave the page in the app, the same name
buttons, chain steps and timeouts point at:

```sh
basecamp --ctl '{"cmd":"dp_page","page":"Editor"}'
{"ok": true, "page": 2, "name": "Editor", "changed": true}
```

- `"prev"` goes back to the page you came from, exactly like the `Previous page`
  timeout target.
- A raw page id (`{"cmd":"dp_page","page":2}`) also works. A name always wins
  over an id, so a page literally named "3" stays reachable by its name.
- `changed: false` means the pad was already on that page and nothing was done.
  Re-sending the same page is not an error, so a script that fires on every
  window focus does not have to track state.
- An unknown name is rejected and the reply lists the names that do exist:
  `{"ok": false, "error": "dp_page: no page named 'Edtior'", "pages": ["Main", "Editor", "OBS"]}`
- The switch is queued onto the GUI thread and, like a page action on a key,
  waits for a running upload or GIF animation to finish first. `ok` means
  accepted, not "already on screen". Discover the outcome with `list` if you
  need it.

Wrap an application so the pad follows it:

```sh
#!/bin/sh
# ~/bin/code-with-pad
basecamp --ctl '{"cmd":"dp_page","page":"Editor"}'
code --wait "$@"
basecamp --ctl '{"cmd":"dp_page","page":"prev"}'
```

To find the page names a script can use:

```sh
basecamp --ctl '{"cmd":"list"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["displaypad"])'
{'pages': {'0': 'Main', '1': 'Media', '2': 'Editor'}, 'current': 0}
```

## Action chains, multiple actions per key (#17)

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

This is honoured by both dispatchers, the in-process DisplayPad handler and the
Everest Max action daemon.

## Redefine-key action (#18)

A **`set_key`** action type changes another key on press (modal / layered
layouts).

- **Everest Max** (`action` is JSON): `{"button":1,"type":"shell","action":"firefox"}`,
  sent to the GUI over the control socket.
- **DisplayPad** (`action` is JSON): `{"page":0,"key":3,"type":"url","action":"https://…"}`,
  where `page`/`key` default to the current page and the pressed key.

## Actions on plugin / monitor keys, and page hops (#16)

- Plugin-registered action types dispatch on both DisplayPad and Everest Max, so
  a key showing a plugin or monitor widget can also carry a press action.
- The **`page`** action type lets any key jump to another tab/page (e.g. a
  System-Monitor key that opens a details page).
- **F1-F12 on the Everest 60:** not implemented. The 60 has no app-assignable
  keys; remapping its real keys to function keys requires the keyboard's
  firmware remap protocol, which isn't reverse-engineered yet (a USB capture of
  Windows BaseCamp doing the remap would be needed, same approach as the side
  LEDs).

## Testing checklist (needs hardware / running GUI)

- [x] `basecamp --ctl '{"cmd":"ping"}'` returns `{"ok": true, ...}` while the GUI runs.
- [x] `dp_page` switches the pad between named pages and re-uploads all twelve
      key images, including the plugin services bound to the target page.
- [ ] `rgb` / `image` / `page` / `set_key` over the socket take effect.
- [ ] An Everest Max key with `type:"page"` switches tabs; `type:"set_key"` redefines another key.
- [ ] A DisplayPad key with an `actions` chain runs every step in order.
- [ ] Existing single-action keys still behave exactly as before (backward compatibility).
