<p align="center">
  <img src="docs/gitlogo.png" alt="BaseCamp Linux" width="480"/>
</p>

# BaseCamp Linux

**Unofficial Linux companion app for Mountain peripherals.**

Mountain Base Camp is only available on Windows — this project brings full device control for the **Everest Max keyboard**, **Everest 60 keyboard**, **Makalu 67 mouse**, **Makalu Max mouse** and **DisplayPad** to Linux: display control, RGB lighting, button actions, monitor metrics, DPI, button remapping, multi-page display management and OBS integration.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Platform](https://img.shields.io/badge/Platform-Linux-black) ![License](https://img.shields.io/badge/License-GPL%20v3%20%2B%20Non--Commercial-red)

<p align="center">
  <a href="https://ko-fi.com/D1D61WIJRD"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support me on Ko-fi" /></a>
</p>

---

## Screenshot

<p align="center">
  <img src="docs/gitgui.png" alt="BaseCamp Linux GUI" width="320"/>
</p>

---

## DisplayPad

<p align="center">
  <img src="docs/Display.png" alt="DisplayPad — 12 Button Display" width="400"/>
</p>

The DisplayPad panel provides full control over all 12 display buttons (102×102 pixels each) with image upload, animated GIF support, multi-page navigation and button actions.

### Button Images (K1–K12)

- Assign individual images or animated GIFs to each of the 12 display buttons
- **Icon Library** with 39 bundled icons (Media, Social, System, Navigation, Numbers 1–12) plus all previously uploaded images — pick with one click instead of browsing the file system
- Images are automatically resized and converted to the device's BGR format

### Fullscreen Image & GIF

<p align="center">
  <img src="docs/fullscreengifmode.png" alt="DisplayPad — Fullscreen GIF Mode" width="400"/>
</p>

Upload a single image or animated GIF that is **automatically split across all 12 displays** as one seamless picture — no manual tile preparation needed. The app handles splitting, resizing and frame synchronisation. Fullscreen images and GIFs are saved to a dedicated library for quick reuse.

### Multi-Page System

- Create up to **12 sub-pages** — assign any button as a page folder with a customisable text label
- Pressing a folder button navigates to its sub-page, where all 12 buttons can be independently configured
- **K1 on sub-pages is always "Back"** — returns to the main page
- Fullscreen GIFs work on sub-pages with page navigation still functional underneath
- Page switching re-uploads all 12 button images to the device automatically

### Button Actions (K1–K12)

- **Action types:** Shell command, URL, Folder, App, Page navigation, OBS (Scene/Record/Stream), Macro, Keypress, Text
- The **Text** action types out any string when you press the button (great for Everest 60 owners who miss F-keys, or for snippets you find yourself typing all the time)
- Keypress and Text both work on X11 and Wayland (the app picks `xdotool` or `ydotool` automatically)
- Actions save immediately on change, no confirmation button needed
- Key events detected via HID with debounce, actions execute even during GIF animation

### Drag & Drop

You can drag a PNG, JPG, GIF or WebP straight from your file manager onto a button tile in the "Assign Images" dialog. The image is imported into the library and uploaded to the device, exactly as if you had clicked the slot and browsed for it.

### Icon Rotation

- Rotate all button icons by **0° / 90° / 180° / 270°** for mounting the pad in any orientation (e.g. SimRacing setups)
- Preview thumbnails rotate live in the GUI
- Rotation setting persists across restarts

---

## Macros

<p align="center">
  <img src="docs/macros.png" alt="Macro Editor" width="320"/>
</p>

Create custom macros and assign them to any button on your keyboard (D1–D4) or DisplayPad (K1–K12). Macros are software-executed sequences of actions that run when the assigned button is pressed.

### Macro Editor

Open the **Macros** tab in the switcher bar to create and manage macros.

- **Create / Delete / Duplicate** macros — each macro has a unique name (auto-numbered: Macro, Macro 1, Macro 2, …)
- **Reorder actions** with the ▲ / ▼ buttons, delete with ✕
- **Export / Import** macros as JSON files for sharing or backup
- **Auto-save** — changes are saved automatically when you leave a field

### Available Actions

| Action | Description | Value |
|--------|-------------|-------|
| **Key Tap** | Press and release a key | Key name (e.g. `ctrl`, `a`, `f1`) |
| **Key Down** | Press and hold a key | Key name |
| **Key Up** | Release a held key | Key name |
| **Mouse Click** | Click a mouse button | `left`, `right`, `middle`, `back`, `forward` |
| **Mouse Move** | Move cursor to an absolute position | `x, y` (e.g. `500, 300`) |
| **Mouse Path** | Play back a recorded mouse movement | Recording file (selected via picker) |
| **Mouse Scroll** | Scroll the mouse wheel | `up 3` or `down 5` (direction + amount) |
| **Delay** | Wait before the next action | Milliseconds (e.g. `200`) |
| **Type Text** | Type a string character by character | Any text |
| **Shell** | Run a shell command | Command (e.g. `firefox`) |
| **URL** | Open a URL in the default browser | URL |
| **Folder** | Open a folder in the file manager | Path |

For key actions, click the **Rec** button to capture the next keypress from your keyboard instead of typing the name manually. For mouse click, the **Rec** button opens a capture dialog (left/right/middle click on it, or use the quick-pick buttons for back/forward).

### Mouse Path Recording

Click **Rec Mouse** to record mouse movement:

1. A fullscreen overlay appears with a screenshot of your desktop as background — you can see where you're pointing
2. Press **Space** to start recording — move the mouse freely
3. Press **Space** again to stop — the movement is saved as a reusable recording file
4. An optional **"Add left click at end"** checkbox (enabled by default) appends a click at the final position

> **Privacy note:** The desktop screenshot is taken locally using your compositor's screenshot tool (Spectacle on KDE, grim on Sway, gnome-screenshot on GNOME, scrot on X11). It is used only as a visual background during recording, never sent anywhere, and automatically deleted when recording stops. This approach is required because Wayland does not allow applications to track the mouse cursor across the screen — the fullscreen overlay window receives mouse motion events while showing you where you are pointing.

Recordings are saved to `~/.config/mountain-time-sync/mouse_recordings/` and can be reused across multiple macros. Use the **"..."** button on a Mouse Path action to pick from saved recordings, or the **✕** button to delete them.

### Repeat Modes

| Mode | Description |
|------|-------------|
| **Once** | Execute the action sequence once |
| **N Times** | Repeat the sequence a configurable number of times |
| **Toggle** | First button press starts looping, second press stops |

### Assigning Macros to Buttons

In the **Keyboard** (Numpad Keys section) or **DisplayPad** (Button Actions), select **Macro** as the action type for any button. A dropdown shows all available macros by name — pick one and the macro UUID is saved. When the button is pressed, the macro executes in a background thread.

### Requirements

Macro execution requires **xdotool** (X11) or **ydotool** (Wayland) for keyboard and mouse simulation:

```bash
# Fedora / Nobara
sudo dnf install xdotool

# Debian / Ubuntu
sudo apt install xdotool

# Arch / CachyOS / Manjaro
sudo pacman -S xdotool
```

The app auto-detects which tool is available and uses it. If neither is installed, a warning message is shown with the install command.

---

## OBS Studio — Global Integration

OBS connection settings are managed in a dedicated **OBS Studio tab** — separate from any device panel. Once connected, OBS actions (Scene switch, Record, Stream) are available as an action type on **all devices**: D1–D4 (Keyboard) and K1–K12 (DisplayPad).

- Host, Port, Password configuration
- Connect & Load Scenes / Disconnect
- OBS switcher button turns **green** when connected (visible from any tab)
- Scene list auto-populated after connecting

---

## Plugins

BaseCamp Linux has a **plugin system** that lets you extend the app without modifying core files. Plugins are loaded from `~/.config/mountain-time-sync/plugins/` on startup.

### What plugins can do

- **Panel plugins** — Add a new tab to the switcher bar with custom GUI content
- **Action plugins** — Register new button action types for DisplayPad (K1-K12) and Everest Max (D1-D4)
- **Service plugins** — Run background tasks that start with the app and stop on shutdown
- **DisplayPad widgets** — Render live images onto DisplayPad buttons (e.g. live data, status indicators)
- **Combined** — A single plugin can be all of the above at once

### Plugin Manager

The **Plugins** tab in the app shows all installed plugins with status, type badges and an enable/disable toggle. No restart needed to disable a plugin.

The Plugin Manager also checks for updates. When a plugin you have installed has a newer version on GitHub, a green pill appears on its card (visible even when collapsed) and an explicit update button shows up when you expand it. One click downloads the new version and replaces the plugin folder. A small restart of the app is needed so the new code is actually loaded.

### Included: Now Playing

A bundled **Now Playing** plugin shows what's currently playing in your browser (YouTube, Spotify, etc.) via MPRIS:

- Panel with title, artist, progress bar, play/pause, volume/mute
- Live widget on any DisplayPad button
- Play/pause action type for button assignment
- Requires `playerctl` (`sudo dnf install playerctl` / `sudo apt install playerctl` / `sudo pacman -S playerctl`)

### Writing your own plugins

See **[PLUGINS.md](PLUGINS.md)** for the full plugin development guide with API reference, styling guide, thread safety rules, and complete example plugins.

---

## Settings

The cog icon in the top-right corner of the app opens a small settings dialog with three useful features.

### Backup and Restore

Export everything (keyboard buttons, DisplayPad pages, OBS config, macros, page names) into a single ZIP file. You can use it to migrate your setup to another machine, or just keep it around before you experiment with something new. Restoring asks for a confirmation first, and refuses any ZIP that tries to write outside the config folder.

Your image libraries and plugins stay separate so the backup file stays small. After restoring, restart the app so the new settings are loaded.

### Profiles

Save your current setup under a name like "Gaming", "Work" or "Streaming" and switch between them later. Each profile snapshots the keyboard actions, the entire DisplayPad layout (images, actions, pages), your OBS connection and your macros. Image libraries stay shared between profiles so you don't waste disk space.

Profiles are stored under `~/.config/mountain-time-sync/profiles/<name>/`. The active profile name is remembered between runs.

### Automatic updates

On startup the app quietly asks GitHub if there is a newer release. If there is, three things happen at once:

1. A popup appears with two buttons (Jetzt aktualisieren or Später) so you can decide on the spot.
2. The settings cog in the top-right corner turns green and gains a small up-arrow (⚙ ↑), so the hint stays visible even if you dismissed the popup.
3. The settings dialog itself shows a green line with the new version number.

Click "Jetzt aktualisieren" and the app downloads the new version in the background with live progress, installs it, and offers a Restart button that re-launches into the new build. Most updates between major releases are tiny source patches that ship as a 200 KB tarball, so the whole flow takes a couple of seconds. When native dependencies change the updater falls back to a full AppImage swap, with the right variant picked automatically based on your distribution.

Source updates are verified against a SHA-256 checksum that ships alongside the tarball on the GitHub release. A tarball without a published checksum is treated as suspect, and a checksum mismatch aborts the install before anything is extracted. The extraction itself uses Python's `tarfile.data_filter`, which refuses path-traversal entries, symlinks pointing outside the destination, and setuid bits.

If you installed via AUR or from source, the popup does not appear since those workflows have their own update mechanism (`yay -Syu basecamp-linux` and `git pull` respectively). The green cog still appears so you know there is something to pull.

### File picker

A small thing that still adds up: every file dialog now remembers the last folder you picked something from, per context (images, profiles, macros, backups). No more starting in your home directory every single time. If you have never picked anything yet, image pickers start at `$ICON_PATH` (set this environment variable to point at your own icon folder) and otherwise fall back to `/usr/share/icons` so you can use system icons straight away.

If you've wandered deep into some unrelated folder and want to go back to the default, open the settings dialog and hit **Reset remembered folders**. The next picker will start from `$ICON_PATH` or `/usr/share/icons` again.

### Autostart on Linux

To launch BaseCamp automatically when you log in, drop a `.desktop` file into `~/.config/autostart/`. Works on GNOME, KDE, XFCE, Cinnamon and most other DEs:

```ini
[Desktop Entry]
Type=Application
Name=BaseCamp Linux
Exec=basecamp-linux
Icon=basecamp-linux
X-GNOME-Autostart-enabled=true
```

Save that as `~/.config/autostart/basecamp-linux.desktop`. If you installed from the AppImage, replace `basecamp-linux` in the `Exec=` line with the full path to your AppImage (for example `/home/you/Applications/BaseCamp-Linux.AppImage`).

---

## Keyboard — Everest Max

The keyboard panel is split into a persistent **dashboard** at the top and collapsible sections below:

- **Dashboard** — Live clock display with 24H/12H toggle, language switcher (DE/EN + custom), Analog/Digital display style, splash screen and autostart toggles
- **Monitor Mode** — Start/stop live keyboard display with CPU%, GPU%, RAM%, HDD% and Network MB/s metrics
- **Main Display** — Switch between image and clock mode, upload any image to the keyboard's main display — automatically converted to the correct format
- **Numpad Keys** — Assign actions (Shell, URL, Folder, App, OBS, Macro, Keypress, Text) and custom button images (including GIF frame picker) to D1–D4 — automatically converted to the correct format
- **RGB Lighting** — Control keyboard RGB effects (Wave, Tornado, Reactive, Yeti, Matrix, and more) with speed, brightness, color and direction — settings saved automatically
- **Custom RGB Mode** — Per-key color editor: click or drag-select keys, assign colors, use the eyedropper (Alt+click), undo (Ctrl+Z), and save/load named presets — side LEDs fully selectable around both keyboard and numpad bezels (see [Custom RGB Mode — Keyboard](#custom-rgb-mode--keyboard) below)

### Features

- **Display styles** — Switch between Analog and Digital clock on the keyboard display
- **24H / 12H** — Toggle clock format
- **Monitor mode** — Live metrics on the keyboard display: CPU%, GPU%, RAM%, HDD%, Network MB/s
- **Button actions (D1–D4)** — Assign Shell commands, URLs, folders, installed apps, OBS actions, Macros, Keypresses or arbitrary Text to D1–D4 with a native folder picker, searchable app picker and OBS scene selector. Actions save immediately on change. Use **Reset Buttons Flash** after first setup or when switching from Mountain Base Camp. BaseCamp may have stored its own actions in the keyboard's flash memory, which can cause two actions to fire on a single button press. Reset Buttons Flash overwrites all four slots with your configured actions, clearing any leftover BaseCamp data.
- **Image upload (D1–D4)** — Upload images to D-buttons via the **Upload Images** dialog or individual per-slot upload buttons — automatically converted and resized (GIF frame picker included). Images are saved to the **Image Library** for quick reuse.
- **Image Library** — All uploaded images are stored locally as thumbnails. Pick from previously used images with one click instead of browsing the file system every time. Images can be deleted from the library individually.
- **Main display upload** — Upload any image to the keyboard's main display — with Image Library support for quick reuse
- **RGB Lighting** — Full RGB effect control: Wave, Tornado, Tornado Rainbow, Reactive, Yeti, Matrix, Off — with speed, brightness, color pickers and direction — settings saved to config
- **Custom RGB Mode** — Per-key color editor with rubber band selection, eyedropper, undo, and named presets — side LEDs selectable individually around keyboard and numpad — includes built-in Synthwave preset
- **System tray** — Minimize to tray, runs in the background
- **Internationalization** — UI language switchable at runtime via external JSON files (DE + EN included, add your own)

---

## Keyboard — Everest 60

The Everest 60 panel provides RGB lighting control for the Mountain Everest 60 (ANSI and ISO variants). The app detects which keyboard is connected and automatically switches the panel and layout.

### RGB Lighting

- Effects: Static, Breathing, Breathing Rainbow, Wave, Wave Rainbow, Tornado, Tornado Rainbow, Reactive, Yeti, Off
- Speed, brightness, dual-color and direction controls
- Settings saved to config and restored on next launch

### Custom RGB

- Per-key color editor with 60% ANSI layout (61 keys)
- Click, drag-select, eyedropper and undo — same controls as Everest Max
- Separate presets and config from Everest Max

---

## Mouse — Makalu 67 / Makalu Max

<p align="center">
  <img src="docs/gitguiMouse.png" alt="BaseCamp Linux — Mouse Panel" width="320"/>
</p>

The mouse panel supports both the **Makalu 67** (PID `0x0003`) and **Makalu Max** (PID `0x0002`). The app detects which mouse is connected and shows the model name in the switcher button and panel header. The Makalu Max supports 8 programmable buttons (vs 6 on the Makalu 67). All settings save to mouse flash and persist across reboots.

### RGB Lighting

- Effects: Static, Breathing, RGB Breathing, Rainbow, Responsive, Yeti, Off
- Dual-zone color support for Breathing and Yeti (Zone 1 + Zone 2)
- Speed: Slow / Medium / Fast
- Brightness: 0 / 25 / 50 / 75 / 100
- Rainbow direction: ← / →
- Color presets: 12 quick-select swatches

### Custom RGB

<p align="center">
  <img src="docs/customrgbMouse.png" alt="BaseCamp Linux — Mouse Custom RGB Editor" width="600"/>
</p>

Click **Open Key Color Editor** to open the per-LED editor. The Makalu 67 has 8 individually addressable LEDs arranged in a large ring on top of the mouse.

- Click an LED to select it, Ctrl+click to multi-select
- Pick a color from the HSV color wheel or quick swatches
- Undo (up to 20 steps)
- Save and load named presets — selected preset is remembered and restored on next open

### DPI

- 5 configurable DPI levels (50–19,000, step 50)
- Reads current values from the mouse on open, polls for profile changes every 1.5 s
- Cycle through levels with the DPI button on the mouse
- Reset to factory defaults (400 / 800 / 1600 / 3200 / 6400)

### Button Remap

- Remap any of the 6 physical buttons (Left, Right, Middle, Back, Forward, DPI+)
- **Categories:** Mouse, DPI, Scroll, Sniper
- **DPI Sniper** — hold a button to temporarily drop to a lower DPI (e.g. 400) for precision aim; profile DPI is restored automatically on release — no software running required, handled entirely by the mouse firmware
- Configurable Sniper DPI via slider + text field
- Left-button remap includes a 10-second safety confirmation dialog — automatically reverts if not confirmed
- Assignments saved to config and restored on next launch

### Settings

- **Polling Rate** — 125 / 250 / 500 / 1000 Hz
- **Button Response** — Debounce time: 2 / 4 / 6 / 8 / 10 / 12 ms
- **Angle Snapping** — On / Off
- **Lift-Off Distance** — Low / High

---

## Custom RGB Mode — Keyboard

<p align="center">
  <img src="docs/customrgb.png" alt="Custom RGB Mode Editor" width="600"/>
</p>

Click **Open Key Color Editor** in the Custom RGB Mode section to open the editor.

### Selecting keys
| Action | Result |
|--------|--------|
| Left-click a key | Select it (deselects others) |
| Ctrl+click | Add/remove key from selection |
| Right-click | Toggle key in/out of selection |
| Click + drag | Rubber band — selects all keys the band touches |
| **Select All** button | Select every key and side LED |
| **Deselect** button | Clear the selection |

Side LEDs are shown as small squares around the keyboard and numpad bezels and work exactly like keys.

### Coloring keys
| Action | Result |
|--------|--------|
| Click the color swatch (top-left) | Open the HSV color wheel picker |
| **Fill Selected** button | Apply the current color to all selected keys |
| **All White** / **All Black** buttons | Fill every key and side LED at once |
| Alt+click a key | Eyedropper — samples that key's color into the swatch |

### Applying to keyboard
| Button | What it does |
|--------|-------------|
| **Apply to Keyboard** | Sends the current colors to the keyboard over USB |
| **Persist to Slot** | Saves colors permanently to the keyboard's flash — survives power cycles and software restarts |

### Undo & Presets
| Action | Result |
|--------|--------|
| Ctrl+Z or **Undo** button | Undo the last color change (up to 20 steps) |
| **Save as…** | Save the current color layout as a named preset |
| **Load** | Apply a saved preset to the canvas |
| **Delete** | Remove a saved preset |

A built-in **Synthwave** preset is included as a starting point.

---

## Upload Images & Image Library

### Upload Images

<p align="center">
  <img src="docs/multiupload.png" alt="Upload Images Dialog" width="400"/>
</p>

Click **Upload Images** in the Numpad Keys section to open the multi-upload dialog.

| Element | Description |
|---------|-------------|
| **D1–D4 tiles** | Click a tile to open the Image Library and pick an image — the thumbnail is shown immediately as a preview |
| **↑ button** | Upload that single slot right away |
| **Upload All** | Upload all four slots sequentially — slots without a selected image are skipped |
| **Status rows** | Per-slot upload status and progress bar |
| **Skip detection** | If the same image is selected again (unchanged), the slot is skipped automatically — no unnecessary flash write |

The last image used per slot is remembered and shown as the tile preview next time you open the dialog.

---

### Image Library

<p align="center">
  <img src="docs/iconlibrary.png" alt="Image Library" width="320"/>
</p>

Every image you upload to D1–D4 or the main display is automatically saved to a local library (`~/.config/mountain-time-sync/icon_library/`). The library opens whenever you click a tile or the individual upload button.

| Element | Description |
|---------|-------------|
| **Browse new file…** | Open the file picker to choose a new image from disk (GIF frame picker included) |
| **Thumbnails** | Click any thumbnail to select it instantly — no file picker needed |
| **✕ button** | Delete an image from the library |

The main display has its own separate library (`main_library/`) with thumbnails that match the display's aspect ratio.

---

## Requirements

### Keyboard Firmware

> **Important:** This software requires keyboard firmware **57** (the first number in the version string).
> The full version `57.24.20` refers to three separate components:
> - `57` — Keyboard main firmware
> - `24` — Numpad firmware
> - `20` — Displaypad firmware
>
> If your version shows as `57.0.0`, your keyboard firmware is correct — the `.0.0` simply means the Numpad and Displaypad are not connected or not detected at that moment.
>
> If your keyboard firmware is not `57`, download and install it manually:
> **[Mountain_Everest_57.24.20.zip](https://mountain.gg/assets/Software/Mountain_Everest_57.24.20.zip)**

### Numpad / Displaypad not detected (version shows `57.0.0`)

If your Numpad or Displaypad firmware shows as `0`, the keyboard is not detecting them. Try the following steps:

1. **Unplug and reconnect** the Numpad and Displaypad cables to the keyboard.
2. **Power cycle** the keyboard by unplugging and replugging the main USB cable.
3. Run the Mountain Base Camp firmware updater on Windows with all components connected — it will detect and update the Numpad and Displaypad firmware automatically.
4. If a component is still not detected, try a different USB port or cable.

---

## Known Issues

### Main display stuck on Mountain logo (rare)

In rare cases the main display shows the original Mountain logo and cannot be overwritten with a new image — the upload appears to complete but the logo stays.

**Cause:** The keyboard's internal flash controller gets into a stuck state.

**Fix:** Click **Reset Dial Image** in the Main Display section of the app. This resets the flash controller and clears the stuck state.

---

## Usage

```bash
python3 gui.py
```

The GUI starts with a splash screen and auto-activates Monitor mode. The app minimizes to the system tray when closed.

---

## Installation

### AppImage (Debian, Ubuntu, Mint, Fedora, Nobara)

Self-contained AppImages are available in the [releases](../../releases). No Python installation required.

| File | Distro |
|------|--------|
| `BaseCamp-Linux-x86_64-debian.AppImage` | Debian, Ubuntu, Linux Mint |
| `BaseCamp-Linux-x86_64-fedora.AppImage` | Fedora, Nobara |

```bash
chmod +x BaseCamp-Linux-x86_64-*.AppImage
./BaseCamp-Linux-x86_64-debian.AppImage   # or -fedora
```

To add BaseCamp Linux to your app menu, run it once with `--install`:

```bash
./BaseCamp-Linux-x86_64-fedora.AppImage --install
```

This installs the icon and desktop entry to `~/.local/share/`. After that you can launch it directly from your application launcher.

USB permissions still need to be set up once (see below).

> If you get a FUSE error on startup, add `--appimage-extract-and-run`:
> ```bash
> ./BaseCamp-Linux-x86_64-fedora.AppImage --appimage-extract-and-run
> ```

---

### Arch / CachyOS / Manjaro — AUR

```bash
paru -S basecamp-linux
```

The udev rule is installed automatically. Just unplug and replug the keyboard after installation.

---

### From source

```bash
git clone https://github.com/ramisotti13-eng/BaseCamp-Linux.git
cd BaseCamp-Linux
pip install customtkinter pillow psutil obsws-python pystray hid pyusb
python3 gui.py
```

> **GPU monitoring** requires `nvidia-smi` (NVIDIA only).

---

### USB permissions (required once, AppImage + source installs)

All Mountain devices need USB access. The rules below cover every supported device:

| Device | PID |
|--------|-----|
| Everest Max | `0x0001` |
| Makalu Max | `0x0002` |
| Makalu 67 | `0x0003` |
| Everest 60 ANSI | `0x0005` |
| Everest 60 ISO | `0x0006` |
| DisplayPad | `0x0009` |

#### Debian / Ubuntu / Linux Mint

```bash
sudo tee /etc/udev/rules.d/99-mountain.rules <<EOF
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0001", MODE="0660", GROUP="plugdev", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0002", MODE="0660", GROUP="plugdev", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0003", MODE="0660", GROUP="plugdev", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0005", MODE="0660", GROUP="plugdev", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0006", MODE="0660", GROUP="plugdev", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0009", MODE="0660", GROUP="plugdev", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0001", MODE="0660", GROUP="plugdev", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0002", MODE="0660", GROUP="plugdev", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0003", MODE="0660", GROUP="plugdev", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0005", MODE="0660", GROUP="plugdev", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0006", MODE="0660", GROUP="plugdev", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0009", MODE="0660", GROUP="plugdev", TAG+="uaccess"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG plugdev $USER
```

> Log out and back in after adding the group, then unplug and replug all devices.

#### Fedora / Nobara

```bash
sudo tee /etc/udev/rules.d/99-mountain.rules <<EOF
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0001", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0002", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0003", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0005", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0006", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0009", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0001", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0002", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0003", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0005", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0006", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0009", MODE="0666", TAG+="uaccess"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
```

> Unplug and replug all devices. No group changes needed.

#### Arch / CachyOS / Manjaro

```bash
bash   # switch to bash if using Fish
sudo tee /etc/udev/rules.d/99-mountain.rules <<EOF
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0001", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0002", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0003", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0005", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0006", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="usb",    ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0009", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0001", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0002", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0003", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0005", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0006", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3282", ATTRS{idProduct}=="0009", MODE="0666", TAG+="uaccess"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
```

> Unplug and replug all devices. No group changes needed.

---

## Adding a language

Copy `lang/en.json` to `lang/xx.json` (e.g. `lang/fr.json`), translate the values, and it will appear automatically in the language dropdown.

---

## Device compatibility

| Device | VID | PID | Status |
|--------|-----|-----|--------|
| Mountain Everest Max (keyboard) | `0x3282` | `0x0001` | Fully supported |
| Mountain Everest 60 ANSI (keyboard) | `0x3282` | `0x0005` | RGB supported |
| Mountain Everest 60 ISO (keyboard) | `0x3282` | `0x0006` | RGB supported |
| Mountain Makalu 67 (mouse) | `0x3282` | `0x0003` | Fully supported |
| Mountain Makalu Max (mouse) | `0x3282` | `0x0002` | Fully supported |
| Mountain DisplayPad | `0x3282` | `0x0009` | Fully supported |

---

## Support

If you find this project useful, consider supporting its development:

<p align="center">
  <a href="https://ko-fi.com/D1D61WIJRD"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support me on Ko-fi" /></a>
</p>

---

## License

GPL v3 + Non-Commercial — free for personal and open-source use, commercial use prohibited. See [LICENSE](LICENSE) for details.
