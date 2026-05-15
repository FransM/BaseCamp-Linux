# Changelog

## [2.0.1] - 2026-05-15

First real source-overlay patch on top of 2.0, ships as a 200 KB tarball that the in-app updater installs in a couple of seconds. Touches one thing only:

- **Bundled plugins now refresh correctly when shipped through a source overlay.** The function that copies bundled plugins (now_playing, ...) into `~/.config/mountain-time-sync/plugins/` was resolving its source directory from PyInstaller's `_MEIPASS`, which always points at the AppImage's bundled location and silently skipped any updated plugin a source-overlay tarball was carrying. It now resolves from its own module path instead, so an overlay that ships a newer `plugins/now_playing/` is picked up like every other Python file in the overlay. User-installed third-party plugins are unaffected; they have always loaded from the user config directory and have nothing to do with this code path.

This is also the first end-to-end test of the source-update pipeline introduced in 2.0. If you are on 2.0 already, you should see the update popup on next startup and the whole thing should take about as long as it takes to read this paragraph.

## [2.0] - 2026-05-15

This release brings a proper in-app updater so you finally do not have to download a 250 MB AppImage every time something small needs to change. Underneath sits a source-overlay system that lets pure Python patches ship as tiny tarballs, typically around 200 KB instead of 250 MB, so updates between major releases happen in seconds instead of minutes. The popup that asks you whether to update is new too, and the settings cog in the header turns green with a small up-arrow the moment a new version is detected, so you actually notice that there is something to do.

### In-app updater

When the app starts it quietly asks GitHub if there is a newer release. If there is, a popup appears with two buttons (Update now or Later) so you can decide right away. The settings cog in the top-right corner also turns green with a "⚙ ↑" indicator that stays visible until you update or restart, so the hint is always there if you closed the popup.

Clicking the update button downloads the new version in the background with live progress, swaps it into place, and offers a Restart button. The restart re-launches the app via execv and stops the tray helper first so you do not end up with two tray icons.

All popup labels are translated, so users running the app in German will see "Update verfügbar / Jetzt aktualisieren / Später" instead.

### Two update paths, chosen automatically

The updater picks between two flavours behind the scenes:

- **Source overlay** is the small path used for most updates. When a release ships a `source-X.Y.Z.tar.gz` asset, the app downloads it (around 200 KB), unpacks it into `~/.local/share/basecamp-linux/source-overlay/`, and on the next start PyInstaller's runtime hook spots the overlay and prepends it to `sys.path`. All Python code then resolves to the overlay files instead of the bundled copies inside the AppImage. The AppImage itself is never touched, which means Debian and Fedora users get the exact same patch from the exact same tarball.
- **Full AppImage swap** is the bigger path, used when native dependencies change. The updater downloads the right AppImage variant for your distribution and atomically replaces the running file. Variant picking now reads `/etc/os-release`: Debian, Ubuntu and Mint get the debian build, everything else (Fedora, Nobara, Arch, Manjaro, openSUSE and friends) gets the fedora build, since rolling-release distributions handle the newer glibc without issues.

### Tamper protection for source updates

Source tarballs must come with a matching `source-X.Y.Z.tar.gz.sha256` sidecar on the GitHub release. The updater fetches the checksum before it even starts the download, computes SHA-256 of the bytes as they come in, and aborts with a clear error if the result does not match. A tarball published without a checksum is treated as suspect and the app silently falls back to the full AppImage path.

Extraction uses Python's `tarfile.data_filter`, which refuses path-traversal entries, absolute paths, symlinks pointing outside the destination, device nodes, named pipes and setuid bits. Even a compromised release pipeline cannot drop files outside the overlay directory or smuggle in a setuid binary.

### What this means for you as a user

For most patches the new flow is simply: see the popup, click "Update now", wait a couple of seconds, click "Restart now". No browser, no manual download, no chmod +x.

If you installed via AUR (`basecamp-linux` via yay) or from source, the popup does not appear since those workflows have their own update mechanism. You still get the green cog and the version line in settings, which points you to the right command for your install.

### Plugin compatibility

Nothing in the plugin API changed. Plugins continue to live in `~/.config/mountain-time-sync/plugins/` and are loaded exactly as before. The source overlay only contains bundled plugins from this repo, never user-installed ones, so third-party plugins are completely untouched by the update mechanism.

## [1.8.1.2] - 2026-05-15

Source-only patch on top of 1.8.1.1 — picks up another round of issue triage with @FransM (#3, #4, #5, #6, #12, #13, #14). Highlights:

- **Bundled plugins now auto-refresh on app upgrade.** The first-run copy step previously only fired if the destination didn't exist, so a fixed plugin in the host repo never reached `~/.config/mountain-time-sync/plugins/`. The app now compares versions and refreshes plugin source files in place (config.json / user state files are left alone). Fixes Frans' point in #13.
- **Plugin update count in the sidebar.** When the manager's background fetch finds newer versions in `basecamp-plugins`, the "Plugins" sidebar button picks up a green "↑N" counter — you no longer have to open the panel to see there's something to update.
- **Copy/paste in button-action fields.** Right-click menu (Cut / Copy / Paste / Select All) plus reliable Ctrl+C/X/V/A bindings on every DisplayPad action entry. Closes #14.
- **DisplayPad paging fixes.** Switching pages in the editor now also flips the live device to that page so the buttons you see in front of you always match the dialog. Setting a sub-page slot to "none" actually blanks the tile on the next upload. Addresses #5.
- **Disk Monitor: pick a mount-point from a dropdown.** New plugin-API hook (`value_options=` on `register_action_type`) lets plugins prefill the button-action editor with a list of suggestions. System Monitor uses it to show all mounted filesystems with size + fstype, so the user no longer has to remember the exact path. Closes #3.
- **System Monitor: CPU temperature caption.** Always shows "CPU" instead of falling back to whatever raw label the sensor exposed ("Package id 0", "Tctl", …). Closes #4 in the plugins repo.
- **Everest 60: unused effect controls now hide instead of grey out.** Rainbow modes no longer show empty Color 1 / Color 2 boxes; Static no longer shows a disabled speed slider. Closes #12.
- **Everest 60: side LEDs (44-LED perimeter ring) — initial support.** Reverse-engineered from @FransM's USB capture in #4. New "Side LEDs" panel section lights the whole ring in one colour; new `everest60-controller rgb side-static R G B [bri]` CLI; per-key controller path now accepts a `side` array in its JSON payload. Custom RGB editor integration still to come.

## [1.8.1.1] - 2026-05-14

A small patch release picking up things that came in from issue #2 (thanks @FransM):

- **`ICON_PATH` environment variable** — set it to your own icon library and every first-time file picker starts there. Lookup order is now: last folder you used → `$ICON_PATH` → `/usr/share/icons`.
- **Reset remembered folders** — new button in the settings dialog wipes the per-context "last folder" memory in one click. The next picker falls straight back to `$ICON_PATH` or `/usr/share/icons` again.
- **Autostart on Linux** — added a short README section with the XDG `.desktop` recipe under `~/.config/autostart/`, works on GNOME, KDE, XFCE and friends.
- **Plugin image colors fixed.** `push_plugin_image` was unpacking the channel tuple into variables named `b, g, r` while they actually held R, G, B, so the merge ended up doing nothing instead of swapping red and blue. Every plugin that pushes live images through the API (System Monitor, Now Playing) was rendering with inverted colors. Now it isn't.

No new binary release for this one — pull the source and run, or wait for the next AppImage build.

## [1.8.1] - 2026-05-14

This release is mainly about quality-of-life: a new settings dialog with backup/restore and profiles, a much better experience for everyone on Wayland, and a long list of bug fixes that came out of community reports and a thorough code review. Big thanks to everyone who opened GitHub issues — most of the fixes here exist because of you.

### New: Settings dialog (⚙ button in the header)

There is now a settings cog in the top-right corner that opens a small dialog with three useful things:

- **Backup & Restore.** Export everything (keyboard buttons, DisplayPad pages, OBS config, macros, page names, …) into a single ZIP file. Restore it on the same machine or move it to another one. Your image libraries and plugins stay separate so the backup stays small. Restoring asks for confirmation first, and refuses any ZIP that tries to write outside the config folder.
- **Profiles.** Save your current setup under a name like "Gaming", "Work" or "Streaming" and switch between them later. Each profile snapshots the keyboard actions, the entire DisplayPad layout (images, actions, pages), your OBS connection and your macros. Image libraries stay shared so you don't waste disk space.
- **Update check.** When you open the app it quietly asks GitHub whether there is a newer release, and if so shows a green "↑ v1.8.2 available" line. It also detects how you installed BaseCamp Linux and tells you exactly what to do: download the new AppImage, run `yay -Syu basecamp-linux`, `sudo apt upgrade`, or `git pull` — whichever is right for your install.

### Better file picker

- The app remembers the last folder you picked an image from — every dialog now opens where you were last time instead of dumping you in your home directory every single time.
- If you've never picked anything yet, it starts in `/usr/share/icons` so you can use system icons straight away.

### DisplayPad: Drag & Drop

You can now drag a PNG, JPG, GIF or WebP directly from your file manager onto a button tile in the "Assign Images" dialog. The image gets imported into the library and uploaded to the device — same as if you had clicked the slot and browsed for it.

### DisplayPad: Clear All clears more

"Clear All" used to leave button actions in place — so a button could still trigger a shell command even though its image was gone. Now Clear All also resets the actions to "None". Pages and the "Back" button on sub-pages are preserved so you can still navigate.

### Plugin Manager: spots updates on GitHub

The plugin manager now checks the version of every installed plugin against the central plugin index on GitHub. When a newer version is published you get a green **↑ v1.1** pill on the plugin card (visible even when the card is collapsed) plus an explicit **↑ Update to v1.1** button when you expand it. One click downloads and replaces the plugin. The "Available Plugins" list also shows a green **Update** button instead of the greyed-out "Installed" tag for plugins that have a newer version waiting.

### Fixes from GitHub issues

- **#3 — Deleting a DisplayPad image now actually clears the device.** Before, right-clicking a slot removed it from the GUI but the old image stayed visible on the pad until you restarted the app.
- **#5 — Page names finally show up everywhere.** If you renamed page 6 to "Stream", it used to keep showing "Page 6" in the dropdowns and on the folder icon. Now your custom name is used consistently: in both dialogs, in the page indicator, and on the folder icon on the device.
- **#6 — Apply no longer eats your typed text.** If you typed an action and clicked Apply without first clicking out of the field, your text was lost. Now Apply forces the field to commit before saving.
- **#7 — New "Text" action type.** Map a DisplayPad or D1-D4 button to a string of text — it gets typed out when you press the key. Great for Everest 60 owners who miss F-keys, or for anything you find yourself typing all the time.
- **#10 — DisplayPad keypress actions work on Wayland now.** The old code only used `xdotool`, which doesn't work on Wayland. Now the app auto-detects your session and uses `ydotool` instead when needed.

### Bug fixes

- **Switching language no longer crashes the keyboard panel.** Internal naming bug that took out the whole keyboard tab whenever you changed language. Fixed.
- **Hold a button during a GIF? No more spam.** When a fullscreen GIF was animating on the DisplayPad and you held down a key, the action used to fire on every frame. Now it fires once per press, like you'd expect.
- **Switching pages while a re-upload is retrying now works.** If the device was busy and the app was retrying the upload, switching to a different page would re-upload the old page's images. Fixed: the retry now picks up your current page.
- **Clear All on the DisplayPad no longer races with key events.** A race condition could cause a button press to be misinterpreted while Clear All was running. Fixed.
- **Big image uploads can't deadlock anymore.** Long uploads of the keyboard's main display could theoretically lock up if the controller printed enough error text. Replaced with a safer streaming approach.
- **The image dialog closes cleanly when you quit the app.** No more harmless-but-ugly `TclError` traceback on shutdown.
- A handful of smaller fixes around file handles and image-size validation that came out of a thorough code review.

### Security & robustness

- **SUDO_USER is now treated as untrusted input.** The app runs as root for USB access, and previously a poisoned environment variable could redirect root's file writes into another user's home directory. Now the value is validated against the password database and refused if it points at root or a non-existent account.
- **Your config directory belongs to you again.** When the app runs as root via sudo, the config folder is automatically chown'd back to your user so you can still edit files in `~/.config/mountain-time-sync/` without needing sudo.

## [1.8.0] - 2026-04-08

### Plugin System

- **Plugin architecture** — plugins can now extend the app without modifying core files; drop a folder into `~/.config/mountain-time-sync/plugins/` and restart
- **3 plugin types** — Panel (new GUI tab), Action (new button action type for DisplayPad/Everest Max), Service (background daemon thread); a single plugin can be multiple types at once
- **Plugin API (PluginContext)** — stable interface for plugins: i18n, config load/save, GUI scheduling, device access, DisplayPad image push, action registration
- **Auto-discovery** — `PluginManager` scans the plugins directory on startup, loads `plugin.json` manifests, imports and instantiates `Plugin` classes via `importlib`
- **Dynamic action types** — DisplayPad K1-K12 and Everest Max D1-D4 action type dropdowns now include plugin-registered types automatically
- **DisplayPad integration** — plugins can push live 102×102 images to any DisplayPad button via `ctx.push_plugin_image()`, with auto-detection of assigned buttons and GIF animation compatibility
- **Plugin action preview tiles** — DisplayPad panel grid shows blue-bordered tiles with action label text for plugin-assigned buttons
- **Plugin switcher buttons** — panel plugins get their own button in a new row of the device switcher bar
- **Service lifecycle** — service plugins are started after GUI init and stopped cleanly on app shutdown
- **Error isolation** — a failing plugin does not crash the app; errors are logged to console
- **`default_disabled` manifest field** — plugins can opt to start disabled on fresh installs

### Plugin Manager

- **New "Plugins" tab** in the switcher bar — shows all discovered plugins with status (Active / Disabled / Error), version, author, description, and type
- **Enable/Disable** — toggle plugins on or off; disabled state persists in `plugins_disabled.json`
- **Live enable** — enabling a plugin loads it immediately; panel plugins need an app restart to appear in the switcher
- **Active counter** — "2 / 3 active" display with restart hint for panel changes
- **Colored type badges** — "panel", "service", "action" shown as colored pills (blue, green, amber)
- **Accent border** — colored card border: green (active), gray (disabled), red (error)
- **Plugin icons** — optional `icon.png` in the plugin folder is displayed as 28x28 icon in the card
- **Collapsible cards** — plugin cards are compact by default (one line); click to expand for description, author, and error details

### Now Playing Plugin (Example)

- **Bundled example plugin** — shows what's playing in your browser (YouTube, Spotify, etc.) via MPRIS/playerctl
- **Panel**: thumbnail card with title, artist, progress bar, play/pause, mute, volume slider
- **DisplayPad widget**: live 102×102 image with title, artist, status bar, play/pause icon on the assigned button
- **Action type**: "Now Playing" action for DisplayPad/Everest Max buttons — press to toggle play/pause
- **Volume via pactl** — uses PulseAudio/PipeWire sink control (Chrome ignores MPRIS volume)
- **DejaVu Sans font** — full Unicode/Umlaut support across Linux distributions

### Documentation

- **PLUGINS.md** — comprehensive plugin development guide: API reference, DisplayPad integration (auto-detect button, GIF compatibility, preview tiles), UI styling, thread safety, debugging, 4 complete examples

### Everest 60 — Protocol overhaul (thanks to [@FransM](https://github.com/FransM) for reverse-engineering and testing!)

- **SetMode (0x16) fix:** buf[5]=0x01, effect code moved to buf[9] — sent before SendModeDetails now
- **SendModeDetails (0x17) fix:** Correct byte layout for colors, speed, brightness
- **Response verification:** Echo check now reads resp[1] (was resp[0]); retries up to 3× if device is busy
- **COLOR_RAINBOW = 0x02** (was 0x01), new **COLOR_DUAL = 0x10** for dual-color effects
- **Dual color support:** Breathing, Wave, Reactive, Yeti now use COLOR_DUAL — both colors sent correctly
- **Tornado direction fix:** CW=0x0A, CCW=0x09 with inversion formula; tornado is single-color only
- **Custom RGB: LEDIDX hardware mapping** — byte 4 is now the physical LED address (table by FransM)
- **Custom RGB: packet flag fix** — 0x0E = more packets, 0x0A = last packet (was inverted)
- **Custom RGB: mode activation** — `_send_mode(EFFECT_CUSTOM)` called before uploading per-key colors
- **Custom RGB: byte order fix** — color entries sent as IRGB (index, R, G, B) instead of RGBI
- **Custom RGB: header offset fix** — packet payload starts at byte 9, not byte 6
- **Custom RGB: buffer overflow fix** — `COLORS_PER_PKT` corrected from 56 to 14 (14 × 4 = 56 bytes in 65-byte report)
- **Arrow Up LED index** — corrected from 95 to 99
- **Timing fix:** Added 50ms sleep after `get_feature_report` for device stability

### Everest 60 — Layout & presets

- **Removed backtick/tilde key** — does not exist on the Everest 60 (64 keys)
- **Equal row widths** — all rows use proportional spacing, fixing rows 2+3 being shorter
- **Arrow key cluster** — row 4 has small right shift + ↑ + Del, row 5 has ← ↓ →
- **Default presets** — Synthwave, Ocean, Ember, Forest, Arctic, Galaxy (auto-loaded on first use)
- **"Shoreline" preset for Everest Max** — ocean wave gradient from deep navy to bright foam

### Custom RGB Editor

- **QWERTY / QWERTZ layout toggle** — switch keyboard label display between US and German layout
- **Live brightness** — brightness slider sends changes in real-time (300ms debounce, Everest 60 only)
- **Eyedropper shortcut** — changed from Alt+Click to Shift+Click (Alt conflicted with window managers)

### New features

- **DisplayPad Keypress action** — new "Keypress" action type for DisplayPad buttons; simulates keyboard input via `xdotool` (e.g. `grave`, `F12`, `ctrl+shift+a`) — useful for keys missing on compact keyboards like the Everest 60
- **Autostart minimized** — app starts in tray when launched via autostart (`--minimized` flag)
- **`--install` updates autostart** — running `--install` with a new AppImage also updates the autostart .desktop path
- **`--install` refreshes desktop cache** — runs `update-desktop-database` automatically

### i18n

- **Full translation coverage** — all CustomRGBWindow, Everest 60 panel, and color picker strings moved to lang files (~30+ keys)
- **Plugin UI** — all plugin manager labels translated (en + de)
- **Removed 14 duplicate keys** in en.json

### Bug fixes

- **Auto-detection fix** — device detection runs immediately on startup; Everest 60 auto-switches without manual change
- **Crash fix (`_rgb_apply_row`)** — reordered initialization to prevent `AttributeError` on startup
- **Display sleep recovery** — window restore forces full geometry cycle, re-packs active panel, refreshes switcher colors
- **Custom RGB button not updating on language switch** — now registered with `_reg()`
- **Direction not persisted** — RGB direction setting saved and restored on restart
- **Speed slider visual glitch** — slider position refreshes correctly when switching effects
- **Color picker going behind main window** — dialog stays on top with focus
- **SEGFAULT on exit** — HID background threads stopped before window destruction to prevent libusb crash
- **CTk widget rendering on panel switch** — buttons and other CTk widgets appeared broken until hovered; panel switcher now forces `_draw()` on all child widgets after switching, fixing incomplete rendering across all panels

### Security & stability

- **Command injection fix** — replaced `shell=True` with `["bash", "-c", action]` in button action execution (3 files) and macro shell runner
- **Path traversal fix** — mouse recording filenames sanitized with `os.path.basename()`
- **Tray helper path validation** — lang file argument validated to be inside `lang/`
- **Autostart/desktop entry path quoting** — Exec= paths now quoted, fixing paths with spaces
- **File descriptor leaks** — replaced ~20 `json.load(open(...))` with `_read_json()` helper using `with` statements; fixed fd leaks in gui.py, everest_max/panel.py, macros.py, CPU monitor
- **Upload pipe deadlock** — replaced `proc.stdout.read()` + `proc.wait()` with `proc.communicate()`
- **Debounce timer crash** — brightness timer cancelled on window close
- **Everest 60 controller** — `NUM_KEYS` corrected from 191 to 64, tornado direction bounds check
- **Preset consistency** — added missing `brightness: 100` to 6 default presets

### New files

- `shared/plugins.py` — PluginManager (discover, load, shutdown, action registry, enable/disable)
- `shared/plugin_api.py` — PluginContext (i18n, config, GUI, device access, action registration)
- `devices/plugins/panel.py` — Plugin Manager panel (view, enable, disable plugins)
- `PLUGINS.md` — Plugin development guide

### Changed files

- `shared/config.py` — added `PLUGINS_DIR` + `PLUGINS_DISABLED_FILE` path constants
- `gui.py` — PluginManager integration (init, panel registration, switcher buttons, shutdown)
- `devices/displaypad/panel.py` — dynamic action types, plugin action handler fallback, plugin image push, preview tiles
- `devices/everest_max/panel.py` — dynamic action types, plugin action labels
- `devices/everest60/controller.py` — protocol fixes, LEDIDX mapping, NUM_KEYS correction
- `devices/everest60/panel.py` — layout fix, QWERTZ toggle, live brightness, i18n
- `mountain-time-sync.py` — plugin action handler stub, autostart minimized
- `lang/en.json` + `lang/de.json` — plugin UI keys, Custom RGB keys, Everest 60 keys
- `default_presets.json` — Everest 60 presets, Shoreline preset, brightness field

---

## [1.7.0] - 2026-03-29

### Macro System — New Feature

- **New top-level Macros tab** in the switcher bar — create, edit, and manage macros independently from any device
- **Macro Editor**: Named macros with ordered action sequences, repeat modes (Once / N Times / Toggle), duplicate, delete, export/import as JSON
- **Auto-naming**: New macros get unique names automatically (Macro, Macro 1, Macro 2, …)

### Macro Actions

- **Key Down / Key Up / Key Tap**: Keyboard input simulation with **Rec button** — press Rec, then press any key on your keyboard to capture it
- **Mouse Click**: Left, right, middle, back, forward — with **Rec button** that opens a click-capture dialog (back/forward as quick-pick buttons for side mouse buttons)
- **Mouse Move**: Absolute screen position (x, y)
- **Mouse Path**: Saved mouse movement recordings — record once, reuse in any macro
- **Mouse Scroll**: Up/down with configurable scroll amount
- **Delay**: Configurable wait time in milliseconds
- **Type Text**: Type a string character by character
- **Shell / URL / Folder**: Run commands, open URLs, open folders

### Mouse Recording

- **Rec Mouse** button opens a fullscreen overlay with a screenshot of the desktop as background — see your screen while recording. This is needed because Wayland does not allow apps to track the mouse cursor across the screen; a fullscreen window with a desktop screenshot solves this by receiving mouse motion events while still showing you where you're pointing. The screenshot is taken locally, used only for the overlay background, never sent anywhere, and automatically deleted when recording stops
- **Space to start/stop** recording — no mouse click needed (avoids recording the stop-click position)
- Mouse movement captured via Motion events at ~50ms resolution — works on **X11 and Wayland**
- Recordings saved as reusable JSON files in `~/.config/mountain-time-sync/mouse_recordings/`
- **"Add left click at end"** checkbox (enabled by default) — automatically appends a click at the final position
- Recordings manageable: pick from saved recordings via **"..."** button, delete with **✕** in the picker
- Screenshot tools: `spectacle` (KDE), `grim` (Sway), `gnome-screenshot` (GNOME), `scrot` (X11)

### Macro Assignment

- New **"Macro"** action type available on **D1–D4** (Everest Max) and **K1–K12** (DisplayPad)
- Macro picker dropdown shows all saved macros by name
- Macros execute in a background thread when the assigned button is pressed

### Input Tool Support

- **Auto-detection**: Finds `xdotool` (X11) or `ydotool` (Wayland) automatically
- **ydotool key mapping**: Full Linux input-event-codes mapping for all keys
- **Clear error message** if no input tool is installed — shows install command for Fedora, Debian, and Arch

### Internationalisation

- Full DE/EN support for all Macro features (20+ new translation keys)

---

## [1.6.3-beta] - 2026-03-29

### Mountain Everest 60 Keyboard — Full Support

- **Automatic detection**: Everest 60 ANSI (PID `0x0005`) and ISO (PID `0x0006`) detected automatically on startup — dedicated panel with RGB controls
- **RGB Lighting**: Full effect control — Static, Breathing, Breathing Rainbow, Wave, Wave Rainbow, Tornado, Tornado Rainbow, Reactive, Yeti, Off — with speed, brightness, color pickers and direction
- **Custom RGB Mode**: Per-key color editor with 60% ANSI layout (61 keys) — separate config and presets from Everest Max
- **Keyboard switcher label**: Shows "Everest Max" or "Everest 60" depending on which keyboard is detected (like "Makalu 67" / "Makalu Max" for mouse)
- **Protocol**: Interface 2, magic bytes `0x46 0x23 0xEA`, 65-byte HID Feature Reports — based on OpenRGB reverse-engineering

### Custom RGB Window — Layout Adaptability

- `CustomRGBWindow` now accepts layout parameters — automatically adapts to the connected keyboard:
  - **Everest Max**: Full layout with numpad, nav cluster, and 45 side LEDs
  - **Everest 60**: Compact 60% layout (61 keys, no numpad, no side LEDs, no "Persist to Slot")
- Separate per-key config and presets per keyboard model — settings don't interfere

### USB Access / udev Rules

- Updated `99-mountain.rules` with all supported devices: Everest Max (`0x0001`), Makalu Max (`0x0002`), Makalu 67 (`0x0003`), Everest 60 ANSI (`0x0005`), Everest 60 ISO (`0x0006`), DisplayPad (`0x0009`)
- Added `hidraw` rules for all devices (previously only DisplayPad had hidraw access)
- Updated README installation instructions with complete udev rules

### Build

- Added `everest60-controller` binary to AppImage
- Added `everest60-controller.spec` for PyInstaller builds

---

## [1.6.2-beta] - 2026-03-28

### Makalu Max (PID 0x0002) — Full Support

- **Automatic detection**: App detects Makalu Max and Makalu 67 automatically on startup — same panel, same controls
- **8-button remapping**: Makalu Max supports 8 programmable buttons (vs 6 on Makalu 67); remap and sniper assignments extended accordingly
- **Model name display**: Switcher button and RGB Lighting section header show the detected model name ("Makalu 67" or "Makalu Max")

### DisplayPad — Brightness Control

- **Brightness dropdown** (☀ 0%/25%/50%/75%/100%) added next to the rotation menu — reverse-engineered from USB capture (`12 03 00 00 [%]`)
- Brightness is saved to config and automatically restored on device reconnect or app restart

### UI / UX

- **Device switcher buttons** now turn **green** when the device is connected (instead of always staying gray when not active). Active device stays blue, disconnected stays gray — applies to Keyboard, Mouse, DisplayPad, and OBS
- **DisplayPad busy-at-boot retry**: If the DisplayPad is busy when the app starts (e.g. after autostart), the app retries up to 5× with increasing delays (2 s, 4 s, 6 s, 8 s, 10 s) before giving up

### Build

- Added `makalu-controller` binary to AppImage (was missing — caused errno 2 on Custom RGB in frozen builds)
- Added `build.sh` for reproducible AppImage builds

---

## [1.6.1-beta] - 2026-03-25

### Makalu Max (PID 0x0002) — Initial Support

- Device constants and `detect_model()` added to controller
- Default button layout for Makalu Max defined (`REMAP_DEFAULTS_MAX`)

---

## [1.6.0] - 2026-03-25

### Mountain DisplayPad — Full Support

- **Button Images (K1–K12)**: Assign individual 102×102 images or animated GIFs to each of the 12 display buttons
- **Fullscreen Image/GIF**: Upload a single image or animated GIF that spans across all 12 displays as one seamless picture
- **Icon Library**: Built-in library with 39 bundled icons (Media, Social, System, Navigation, Numbers 1–12) plus user-uploaded images — all accessible via a grid picker
- **Fullscreen Library**: Separate library for fullscreen images and GIFs, auto-saves uploaded files for quick reuse
- **Button Actions (K1–K12)**: Assign actions to each button — Shell command, URL, Folder, App, OBS, or Page navigation
- **Multi-Page System**: Create up to 12 sub-pages with customisable folder icons and text labels (DPFolder.png). K1 on sub-pages is always "Back". Fullscreen GIFs work on sub-pages with page navigation still functional underneath
- **Key Event Detection**: Hardware button presses detected via HID (data[0]==0x01 filter, 0.8s debounce). Actions execute during GIF animation by reading key events between frame uploads
- **Icon Rotation**: Rotate all button icons by 0°/90°/180°/270° for mounting the pad in any orientation (e.g. SimRacing setups). Preview thumbnails rotate live in the GUI
- **Device Reconnect**: Automatically re-uploads saved images when the DisplayPad is reconnected or the app restarts
- **Clear All**: Uploads blank (black) images to all buttons on the device, preserving page folder icons
- **Auto-Upload**: Images upload automatically when assigned or when the image dialog is closed — no manual upload button needed
- **GIF Animation**: Supports animated GIFs on individual buttons and fullscreen, with configurable minimum frame time (ms/frame)

### OBS Studio — Global Integration

- **New top-level OBS tab** in the switcher bar (alongside Keyboard, Mouse, DisplayPad)
- OBS connection settings (Host, Port, Password) moved from Keyboard panel to dedicated OBS panel
- Connect & Load Scenes / Disconnect with status indicator
- **OBS switcher button turns green** when connected (visible from any tab)
- **OBS actions available on all devices**: D1–D4 (Keyboard) and K1–K12 (DisplayPad) can be set to OBS type with Scene/Record/Stream selector
- OBS actions execute via `obsws_python` in background threads

### Keyboard (Everest Max) — Improvements

- **OBS section removed** from Keyboard panel (moved to global OBS tab)
- **D1–D4 actions**: Added "OBS" action type with scene/record/stream dropdown
- **Auto-save**: D1–D4 action changes save immediately on type change, browse, or entry edit — green checkmark buttons removed

### UI / UX

- **Simplified DisplayPad layout**: Single scrollable panel (no accordion) with all controls directly visible
- **Simplified OBS layout**: Direct content display without accordion
- **Two-row switcher bar**: Keyboard/Mouse/DisplayPad on top, OBS Studio centered below
- **Emoji-free switcher buttons**: Text-only buttons for better compatibility across platforms
- **Window width** increased to 480px to accommodate 4 tabs
- **Scroll speed** capped in all Library Picker dialogs (consistent with panel scroll behaviour)
- **GIF frame picker skipped** for DisplayPad (device supports animation natively)

### Internationalisation

- Full DE/EN support for all new DisplayPad features (29+ new keys)
- OBS panel and action type labels in both languages
- Page system labels: Page selector, Back button, page name hints

---

## [1.5.1] - 2026-03-22

### Internal

- `mountain-time-sync.py`: fixed slow memory growth in the controller loop — `_handle_btn_resp` was redefined on every iteration (5×/s), creating constant function-object churn; moved to a single definition before the loop
- `mountain-time-sync.py`: RAM and HDD metrics now polled every 2 s instead of every 0.2 s — values change slowly and the reduction in `virtual_memory()` / `disk_usage()` allocation pressure stops Python's memory allocator from retaining freed arenas

---

## [1.5.0] - 2026-03-22

### Makalu 67 Mouse — Button Remap

- New **Button Remap** section in the Makalu 67 panel
- Remap any of the 6 physical buttons (Left, Right, Middle, Back, Forward, DPI+) to a different function
- Categories: Mouse, DPI, Scroll, Sniper
- New **DPI Sniper** function: assign a button to temporarily switch to a lower DPI while held — profile DPI is restored automatically on release (no software polling required, handled by mouse firmware)
- DPI Sniper value is configurable via slider + input field (50–19,000, step 50)
- Left button remap includes a 10-second safety confirmation dialog — automatically reverts if not confirmed
- Assignments are saved to config and restored on next launch

### Makalu 67 Mouse — DPI

- DPI settings panel: 5 configurable DPI levels, cycle through them with the DPI button on the mouse
- Reads current DPI values from the mouse on panel open and polls for profile changes every 1.5 seconds
- Reset button restores factory defaults

### Makalu 67 Mouse — Settings

- Mouse settings panel: Polling Rate (125 / 250 / 500 / 1000 Hz), Button Response (debounce 2–12 ms), Angle Snapping (on/off), Lift-Off Distance (Low/High)

### Internationalisation

- Full DE/EN language support for the entire Makalu 67 panel (RGB, Custom RGB, DPI, Settings, Button Remap)
- All section titles, labels, dropdowns, status messages and button grid update live when switching language

### Presets

- 6 built-in color presets ship with the app for both the **keyboard** (Custom RGB) and the **Makalu 67** (Custom RGB): Synthwave, Ocean, Ember, Forest, Arctic, Galaxy
- Presets load automatically on first launch — no setup required

### Internal

- `controller.py`: extracted `_run_cmd()` helper — all HID commands now share a single open/send/get/close pattern instead of duplicating it per function
- `panel.py`: extracted `_fetch_dpi()` helper — `_dpi_load_from_device` and `_dpi_poll` no longer duplicate the subprocess/parse logic
- `panel.py`: removed dead `_REMAP_LABELS` / `_REMAP_LABEL_TO_KEY` class attributes (superseded by i18n translation maps)
- Fixed `rgb code` / `rgb code2` CLI commands in controller.py that would crash at runtime after the `_send_lighting` refactor

---

## [1.4.2] - 2026-03-21 (Beta)

### Makalu 67 Mouse — RGB Control (New Device)
- Full RGB control panel for the Mountain Makalu 67 gaming mouse (VID 0x3282, PID 0x0003)
- Effects: Static, Breathing, RGB Breathing, Rainbow, Responsive, Yeti, Off
- Dual-zone color support for Breathing and Yeti (Zone 1 + Zone 2 colors)
- Speed control: Slow / Medium / Fast (confirmed via USB capture)
- Brightness: 5 levels — 0 / 25 / 50 / 75 / 100 (dropdown, confirmed via USB capture)
- Rainbow direction: ← / → (confirmed via USB capture)
- 12 color presets (standard gaming colors) — click to apply instantly
- All controls push to the mouse immediately without a separate Apply button
- UI shows only the controls relevant to the selected effect

### Keyboard Main Display
- Added **Volume** mode to the display mode selector

### D1–D4 Image Upload
- Fixed upload checksum: was hardcoded `0x6be9`, now correctly computed from pixel data
- Added debug log file at `/tmp/basecamp_d1d4_upload.log` for troubleshooting upload issues

### Internal
- Device code restructured into `devices/everest_max/` and `devices/makalu67/`
- Shared utilities extracted to `shared/` (config, image_utils, ui_helpers)
- Protocol documentation moved to `protocol/`
- README screenshots moved to `docs/`

---

## [1.4.1] - 2026-03-19

### Upload Images & Image Library
- New **Upload Images** dialog (Numpad Keys section): shows D1–D4 as four tiles with thumbnail previews, select images per slot and upload all at once with **Upload All**
- Per-slot **↑** button inside the dialog for uploading a single slot without affecting others
- **Image Library**: every uploaded image is automatically saved as a thumbnail locally — pick previously used images with one click instead of browsing the file system every time
- Library images can be deleted individually via the ✕ button
- The last uploaded image per D-slot is remembered and shown as the tile preview on next open
- **Skip detection**: if the same image is selected again (content unchanged), the slot is skipped — no unnecessary flash write, both in single and multi upload
- **Main display Image Library**: the main display upload now also uses the library picker with thumbnails in the correct 240×204 aspect ratio (stored in `main_library/`)
- Image Library picker opens at the mouse cursor position

---

## [1.4.0] - 2026-03-19

### Custom RGB Mode
- Completely redesigned: new per-key color editor with a full keyboard canvas in a popup window
- Click individual keys to select and color them
- Rubber band (drag) selection across multiple keys
- Ctrl+click and right-click for toggle selection
- Alt+click eyedropper to sample a key's current color
- Ctrl+Z / Undo button (up to 20 steps)
- Side LEDs shown as individual clickable squares around both keyboard and numpad bezels (11 top, 4 right, 12 bottom, 4 left; numpad: 3 top, 4 right, 3 bottom, 4 left)
- Fill selected, fill all, select all, deselect all controls
- Preset system: save, load and delete named color presets
- Built-in **Synthwave** sample preset included
- Section renamed from "Custom RGB Mode (Beta)" to "Custom RGB Mode"

### Color Picker
- Replaced the system color dialog with a custom HSV color wheel
- Circular picker: hue as angle, saturation as radius, brightness as slider
- Before/after preview swatches and hex input field
- Used everywhere colors are picked: Key Color Editor, RGB Lighting, Custom RGB zones

### Bug Fixes
- Fixed: Direction dropdown visible on startup when Static effect was selected
- Fixed: Custom RGB colors not applying to keyboard in AppImage — `basecamp-controller` was not rebuilt with `per-key-rgb` support
- Fixed: Synthwave preset not loading side LED colors — wrong JSON key (`side_leds` → `side`)

---

## [1.3.1] - 2026-03-18

### Numpad Keys — Action Types
- Added action type selector per D-button: Shell, URL, Folder, App, None
- New folder picker: opens native file manager dialog to browse for a folder
- New app picker: searchable list of installed `.desktop` applications
- Actions are saved immediately to config when ✓ is pressed — no restart required
- New **Reset Buttons Flash** button: overwrites all 4 keyboard flash slots with your configured actions — use this after first setup or when switching from Windows Mountain Base Camp, as BaseCamp may have stored its own actions in flash that cause two actions to fire on a single button press

### OBS Integration
- Removed per-button ✓ save button — type and scene changes now save automatically

### Bug Fixes
- Fixed: D4 button press not detected (Write 2/3 in `_write_action` was disabling the flash slot before byte42 could activate)
- Fixed: `XDG_RUNTIME_DIR` not set when launching apps/folders from D-button press as sudo user
- Fixed: Folder/App actions not working on Arch/CachyOS/KDE — controller now auto-detects Wayland vs X11 and sets the correct display environment (`WAYLAND_DISPLAY` or `DISPLAY`)

### Code Quality
- All CLI error messages changed from German to English

---

## [1.3.0] - 2026-03-17

### RGB Lighting
- Fully implemented RGB effects: Wave, Tornado, Tornado Rainbow, Reactive, Yeti, Matrix, Off
- Fixed inverted speed slider (hardware uses 1=fast, 100=slow — now correctly mapped)
- Fixed Tornado and Tornado Rainbow effects not working
- Direction dropdown is now context-sensitive: arrow directions (L→R, T→B, …) for Wave effects, CW/CCW for Tornado effects
- RGB settings (effect, speed, brightness, colors, direction) are now saved to config and restored on next launch

### Custom RGB Mode (Beta)
- New section: zone-based RGB colors for 7 keyboard zones (F Keys, Number Row, QWERTY, Home Row, Shift Row, Bottom Row, Numpad)
- Side ring LED color control (30 LEDs on keyboard, 14 on numpad)
- Brightness slider for all LEDs
- Reset button to restore all zones to default colors
- Zone colors and brightness are saved to config and restored on next launch

### GUI
- Reordered accordion sections: Monitor → Main Display → Numpad Keys → RGB Lighting → Custom RGB Mode → OBS Integration
- OBS Integration moved to the bottom
- All red buttons now have bold black text for better readability
- All colored buttons (blue, green) now use white text instead of near-black
- GIF frame picker cancel button text changed from muted gray to white

### Bug Fixes
- Fixed: switching back to Clock mode after a main display image upload now works correctly
- Fixed: main display stuck on Mountain logo can now be resolved directly in the app via the **Reset Dial Image** button — no Windows required

### Config Persistence
- RGB settings saved to `~/.config/mountain-time-sync/rgb_settings.json`
- Zone colors saved to `~/.config/mountain-time-sync/zone_colors.json`

---

## [1.2.0]

- AUR package for Arch / CachyOS / Manjaro
- Two AppImages: Debian/Ubuntu and Fedora/Nobara builds
- Fixed udev rule: use `MODE=0666` for Arch/CachyOS compatibility

## [1.1.0]

- Main display upload (240×204 image)
- Main display mode switch (Image / Clock)
- Reset Dial Image button
- GIF frame picker for D1–D4 image upload

## [1.0.0]

- Initial release
- Time sync (analog / digital clock)
- Monitor mode: CPU, GPU, RAM, HDD, Network metrics
- D1–D4 button actions and image upload (72×72)
- OBS WebSocket integration
- System tray support
- DE / EN language support
