#!/usr/bin/env python3
"""
Mountain MacroPad probe for BaseCamp-Linux.

We reverse-engineered the MacroPad (VID 0x3282, PID 0x0008) from the Windows
software, but nobody on the project owns one. This script collects the last
missing piece from someone who does: the exact shape of the report the pad
sends when a key is pressed. Everything else about the protocol is already
known and does not need your hardware.

    python3 macropad_probe.py

It writes macropad-probe-<timestamp>.json next to itself. Attach that file to
https://github.com/ramisotti13-eng/BaseCamp-Linux/issues and we can finish the
driver.

What it does:
  * lists the USB/HID interfaces of the pad and dumps its report descriptors
  * sends the vendor handshake (11 80 00 00 01) and asks for firmware info
  * records the raw reports while you press each key M1 to M12 in turn
  * with --lighting, tries a few colours so you can see whether they land

What it never does: write to flash, change your key bindings, touch firmware,
or save anything on the device. The lighting test is opt-in and is not
persisted, so unplugging the pad restores it.

This file is standalone on purpose. Copy it anywhere, no other project files
needed. Python 3.8 or newer plus the hidapi binding.
"""
import argparse
import binascii
import json
import os
import platform
import sys
import time

VID = 0x3282
PID = 0x0008
PAYLOAD_LEN = 64
NUM_KEYS = 12

INIT_PACKET = bytes([0x11, 0x80, 0x00, 0x00, 0x01]) + bytes(PAYLOAD_LEN - 5)
FW_INFO_PACKET = bytes([0x11, 0x00]) + bytes(PAYLOAD_LEN - 2)
FW_LAYOUT_PACKET = bytes([0x11, 0x12]) + bytes(PAYLOAD_LEN - 2)

KNOWN_MOUNTAIN_PIDS = {
    0x0001: "Everest Keyboard",
    0x0002: "Makalu mouse",
    0x0003: "Makalu 67 mouse",
    0x0005: "Everest 60 (ANSI)",
    0x0006: "Everest 60 (ISO)",
    0x0008: "MacroPad",
    0x0009: "DisplayPad",
}

report = {
    "probe_version": 1,
    "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "environment": {},
    "mountain_devices": [],
    "interfaces": [],
    "handshake": [],
    "firmware": {},
    "key_capture": {},
    "lighting": {},
    "notes": [],
}


# ── output helpers ────────────────────────────────────────────────────────────

def section(title):
    print()
    print(title)
    print("-" * len(title))


def note(text):
    report["notes"].append(text)
    print("  note: %s" % text)


def hexs(data):
    if data is None:
        return None
    return binascii.hexlify(bytes(data), " ").decode()


# ── HID report descriptor ─────────────────────────────────────────────────────

def read_report_descriptor(hid_path):
    """Read the raw report descriptor from sysfs. Linux and hidraw only.

    hidapi paths look like /dev/hidraw3 on the hidraw backend; the descriptor
    sits next to the device node in sysfs."""
    if isinstance(hid_path, bytes):
        hid_path = hid_path.decode(errors="replace")
    name = os.path.basename(hid_path)
    if not name.startswith("hidraw"):
        return None
    sysfs = "/sys/class/hidraw/%s/device/report_descriptor" % name
    try:
        with open(sysfs, "rb") as handle:
            return handle.read()
    except OSError:
        return None


def walk_descriptor(data):
    """Minimal HID item walker. Enough to see usage pages and report sizes."""
    items = []
    index = 0
    while index < len(data):
        prefix = data[index]
        index += 1
        if prefix == 0xFE:                       # long item, skip it
            if index >= len(data):
                break
            size = data[index]
            index += 2 + size
            continue
        size = prefix & 0x03
        size = 4 if size == 3 else size
        item_type = (prefix >> 2) & 0x03         # 0 main, 1 global, 2 local
        tag = (prefix >> 4) & 0x0F
        value = int.from_bytes(data[index:index + size], "little")
        index += size
        items.append((item_type, tag, value))
    return items


def summarise_descriptor(data):
    """Report IDs with their input/output/feature payload sizes, in bytes."""
    usage_page = usage = report_id = 0
    report_size = report_count = 0
    sizes = {}
    for item_type, tag, value in walk_descriptor(data):
        if item_type == 1:                       # global
            if tag == 0x0:
                usage_page = value
            elif tag == 0x7:
                report_size = value
            elif tag == 0x9:
                report_count = value
            elif tag == 0x8:
                report_id = value
        elif item_type == 2 and tag == 0x0:      # local usage
            usage = usage or value
        elif item_type == 0 and tag in (0x8, 0x9, 0xB):
            kind = {0x8: "input", 0x9: "output", 0xB: "feature"}[tag]
            entry = sizes.setdefault(report_id, {})
            entry[kind] = entry.get(kind, 0) + (report_size * report_count) // 8
    return {
        "usage_page": "0x%04X" % usage_page,
        "usage": "0x%02X" % usage,
        "reports": {str(k): v for k, v in sorted(sizes.items())},
    }


# ── enumeration ───────────────────────────────────────────────────────────────

def import_hid():
    try:
        import hid
        return hid
    except ImportError:
        print("The hidapi Python binding is missing. Install it with one of:")
        print("    pip install --user hid")
        print("    sudo dnf install python3-hidapi        # Fedora")
        print("    sudo apt install python3-hid           # Debian, Ubuntu")
        print("    sudo pacman -S python-hidapi           # Arch")
        return None


def scan(hid, vid, pid):
    section("Mountain devices on this machine")
    everything = []
    try:
        everything = list(hid.enumerate(vid if vid else 0, 0))
    except Exception as exc:
        print("  enumerate failed: %s" % exc)
    seen = {}
    for entry in everything:
        seen.setdefault(entry.get("product_id"), entry)
    if not seen:
        print("  none found")
    for product_id, entry in sorted(seen.items()):
        name = KNOWN_MOUNTAIN_PIDS.get(product_id, "unknown")
        mark = "  <= target" if product_id == pid else ""
        print("  0x%04X  %-20s %s%s" % (product_id, name,
                                        entry.get("product_string") or "", mark))
        report["mountain_devices"].append({
            "pid": "0x%04X" % product_id,
            "guess": name,
            "product_string": entry.get("product_string"),
            "manufacturer": entry.get("manufacturer_string"),
        })

    section("Interfaces of 0x%04X:0x%04X" % (vid, pid))
    entries = [e for e in everything if e.get("product_id") == pid]
    if not entries:
        print("  not connected")
        return []
    entries.sort(key=lambda e: e.get("interface_number") or 0)
    for entry in entries:
        path = entry.get("path")
        path_text = path.decode(errors="replace") if isinstance(path, bytes) else str(path)
        info = {
            "interface_number": entry.get("interface_number"),
            "usage_page": "0x%04X" % (entry.get("usage_page") or 0),
            "usage": "0x%02X" % (entry.get("usage") or 0),
            "path": path_text,
            "release": entry.get("release_number"),
        }
        descriptor = read_report_descriptor(path_text)
        if descriptor:
            info["descriptor"] = hexs(descriptor)
            info["descriptor_summary"] = summarise_descriptor(descriptor)
        readable = os.access(path_text, os.R_OK | os.W_OK) if path_text.startswith("/dev/") else None
        info["writable"] = readable
        report["interfaces"].append(info)
        print("  interface %-3s usage page %s usage %s  %s%s" % (
            info["interface_number"], info["usage_page"], info["usage"],
            path_text, "" if readable is not False else "   (no permission)"))
        if "descriptor_summary" in info:
            summary = info["descriptor_summary"]
            print("      descriptor: usage page %s usage %s, reports %s" % (
                summary["usage_page"], summary["usage"], summary["reports"] or "{}"))
    if any(i.get("writable") is False for i in report["interfaces"]):
        note("No write permission on at least one hidraw node. Either run this "
             "with sudo or install the udev rule 99-mountain.rules from the "
             "BaseCamp-Linux repository and replug the pad.")
    return entries


# ── device conversation ───────────────────────────────────────────────────────

class Link:
    """One open HID interface, with reads that keep what they cannot use."""

    def __init__(self, hid, entry):
        self.entry = entry
        self.dev = hid.Device(path=entry["path"])
        self.dev.nonblocking = False
        self.spare = []

    def close(self):
        try:
            self.dev.close()
        except Exception:
            pass

    def write(self, payload):
        self.dev.write(b"\x00" + bytes(payload))

    def read(self, timeout_ms):
        try:
            data = self.dev.read(PAYLOAD_LEN, timeout=timeout_ms)
        except Exception:
            return None
        return bytes(data) if data else None

    def ask(self, payload, timeout_ms=700):
        """Send, then collect replies until the timeout. Returns them all,
        because we do not yet know which reports are answers and which are
        key state, and that distinction is exactly what we are here to find."""
        self.write(payload)
        deadline = time.monotonic() + timeout_ms / 1000.0
        replies = []
        while time.monotonic() < deadline:
            remaining = int((deadline - time.monotonic()) * 1000)
            if remaining <= 0:
                break
            data = self.read(remaining)
            if data:
                replies.append(data)
        return replies


def try_handshake(hid, entries, forced_interface=None):
    """Send the handshake to each candidate interface, see which one answers.

    On the DisplayPad this exact packet is answered with an echo of its first
    five bytes, so that is what we look for first, but anything at all coming
    back is worth recording."""
    section("Handshake")
    winner = None
    for entry in entries:
        number = entry.get("interface_number")
        if forced_interface is not None and number != forced_interface:
            continue
        path = entry.get("path")
        path_text = path.decode(errors="replace") if isinstance(path, bytes) else str(path)
        result = {"interface_number": number, "path": path_text}
        try:
            link = Link(hid, entry)
        except Exception as exc:
            result["error"] = str(exc)
            print("  interface %-3s cannot open: %s" % (number, exc))
            report["handshake"].append(result)
            continue
        try:
            replies = link.ask(INIT_PACKET)
            result["replies"] = [hexs(r) for r in replies]
            if replies:
                echo = replies[0][:5] == INIT_PACKET[:5]
                result["echoes_init"] = echo
                print("  interface %-3s answered %s%s" % (
                    number, hexs(replies[0][:8]),
                    "  (echoes the handshake)" if echo else ""))
                if winner is None:
                    winner = (entry, link)
                else:
                    link.close()
            else:
                print("  interface %-3s silent" % number)
                link.close()
        except Exception as exc:
            result["error"] = str(exc)
            print("  interface %-3s error: %s" % (number, exc))
            link.close()
        report["handshake"].append(result)
    if winner is None:
        print("  no interface answered. The pad may need a replug, or another")
        print("  program (Base Camp under Wine, an earlier run of this script)")
        print("  may still hold it.")
    return winner


def read_firmware(link):
    section("Firmware")
    for name, packet in (("info", FW_INFO_PACKET), ("layout", FW_LAYOUT_PACKET)):
        replies = link.ask(packet)
        report["firmware"][name] = [hexs(r) for r in replies]
        if replies:
            print("  %-7s %s" % (name, hexs(replies[0][:16])))
        else:
            print("  %-7s no answer" % name)


# ── the part we actually need ─────────────────────────────────────────────────

def capture_keys(link, seconds_per_key):
    """Record raw reports while the user presses each key in turn."""
    section("Key capture")
    print("This is the measurement we cannot do without you.")
    print("Press the key the prompt asks for, hold it about a second, release.")
    print("Do not press anything else while a key is being recorded.")
    print()

    input("First a baseline with nothing pressed. Press ENTER, then hands off. ")
    baseline = collect(link, 2.0)
    report["key_capture"]["baseline"] = [hexs(r) for r in baseline]
    print("  %d report(s) while idle" % len(baseline))

    per_key = {}
    for index in range(1, NUM_KEYS + 1):
        try:
            input("Press ENTER, then press and release key M%-2d " % index)
        except (EOFError, KeyboardInterrupt):
            print()
            note("Key capture stopped early at M%d." % index)
            break
        captured = collect(link, seconds_per_key)
        per_key["M%d" % index] = [hexs(r) for r in captured]
        print("  M%-2d %d report(s)%s" % (
            index, len(captured), "" if captured else "   nothing arrived"))
    report["key_capture"]["keys"] = per_key
    analyse_capture(baseline, per_key)


def collect(link, seconds):
    """Drain every report that arrives in the next `seconds`."""
    deadline = time.monotonic() + seconds
    out = []
    while time.monotonic() < deadline:
        remaining = int((deadline - time.monotonic()) * 1000)
        if remaining <= 0:
            break
        data = link.read(min(remaining, 200))
        if data:
            out.append(data)
    return out


def analyse_capture(baseline, per_key):
    """Say what changed per key, so the result is readable without a decoder."""
    section("What the reports say")
    idle = set()
    for row in baseline:
        idle.add(bytes(row))
    if not per_key:
        print("  nothing captured")
        return

    first_bytes = set()
    findings = {}
    for name, rows in per_key.items():
        bits = set()
        for hex_row in rows:
            row = bytes.fromhex(hex_row.replace(" ", ""))
            if row in idle:
                continue
            first_bytes.add(row[0])
            for position, value in enumerate(row):
                if not value:
                    continue
                for bit in range(8):
                    if value & (1 << bit):
                        bits.add((position, bit))
        findings[name] = sorted(bits)
        if bits:
            print("  %-4s %s" % (name, ", ".join("byte %d bit %d" % b for b in sorted(bits)[:6])))
        else:
            print("  %-4s no report differed from idle" % name)
    report["key_capture"]["analysis"] = {
        k: [{"byte": b, "bit": i} for b, i in v] for k, v in findings.items()}
    if first_bytes:
        report["key_capture"]["first_bytes"] = sorted(first_bytes)
        print()
        print("  first byte of key reports: %s" % ", ".join(
            "0x%02X" % b for b in sorted(first_bytes)))
        if first_bytes == {0x01}:
            print("  that matches the DisplayPad, which is what we hoped for")


# ── optional lighting check ───────────────────────────────────────────────────

def effect_packet(effect, brightness=60, speed=60, color=(255, 0, 0)):
    packet = bytearray(PAYLOAD_LEN)
    packet[0] = 0x14
    packet[1] = 0x2C
    packet[2] = effect
    packet[4] = 0xFF if effect in (0, 12) else speed
    packet[5] = brightness
    packet[6] = 0x00
    packet[7] = 0xFF
    packet[8] = 0xFF
    packet[9], packet[10], packet[11] = color
    return bytes(packet)


def test_lighting(link):
    section("Lighting")
    print("Nothing here is written to flash. Unplug the pad to undo it.")
    steps = [
        ("backlight on", bytes([0x12, 0x03]) + bytes(PAYLOAD_LEN - 2)),
        ("static red", effect_packet(0, color=(255, 0, 0))),
        ("static green", effect_packet(0, color=(0, 255, 0))),
        ("static blue", effect_packet(0, color=(0, 0, 255))),
        ("wave", effect_packet(4)),
        ("per-key colours", per_key_packet()),
        ("custom effect on", custom_activate_packet()),
    ]
    results = {}
    for name, packet in steps:
        replies = link.ask(packet, timeout_ms=400)
        results[name] = [hexs(r) for r in replies]
        print("  %-16s sent, %d reply/replies" % (name, len(replies)))
        time.sleep(1.2)
    report["lighting"] = results
    print()
    answer = ask_yes_no("Did the lighting actually change while that ran?")
    report["lighting"]["visible_change"] = answer
    answer2 = ask_yes_no("Did the last step light the 12 keys in different colours?")
    report["lighting"]["per_key_worked"] = answer2


def per_key_packet():
    """Twelve visibly different colours, one per key."""
    palette = [(255, 0, 0), (255, 128, 0), (255, 255, 0), (128, 255, 0),
               (0, 255, 0), (0, 255, 128), (0, 255, 255), (0, 128, 255),
               (0, 0, 255), (128, 0, 255), (255, 0, 255), (255, 255, 255)]
    packet = bytearray(PAYLOAD_LEN)
    packet[0] = 0x14
    packet[1] = 0x2C
    packet[2] = 0x00
    packet[3] = 0x01
    packet[4] = 0x00
    packet[5] = 0x4B
    offset = 7
    for red, green, blue in palette:
        packet[offset], packet[offset + 1], packet[offset + 2] = red, green, blue
        offset += 3
    return bytes(packet)


def custom_activate_packet(brightness=70):
    packet = bytearray([0xFF]) * PAYLOAD_LEN
    packet[0] = 0x14
    packet[1] = 0x2C
    packet[2] = 0x0A
    packet[3] = 0x00
    packet[5] = brightness
    return bytes(packet)


def ask_yes_no(question):
    try:
        answer = input("%s [y/n] " % question).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if answer.startswith("y"):
        return True
    if answer.startswith("n"):
        return False
    return None


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Collect what BaseCamp-Linux still needs to support the "
                    "Mountain MacroPad.")
    parser.add_argument("--vid", type=lambda v: int(v, 0), default=VID)
    parser.add_argument("--pid", type=lambda v: int(v, 0), default=PID,
                        help="default 0x0008 (MacroPad)")
    parser.add_argument("--interface", type=int, default=None,
                        help="only talk to this interface number")
    parser.add_argument("--seconds", type=float, default=3.0,
                        help="recording window per key, default 3")
    parser.add_argument("--lighting", action="store_true",
                        help="also try the lighting commands (not saved to flash)")
    parser.add_argument("--no-keys", action="store_true",
                        help="skip the key capture")
    parser.add_argument("--dry-run", action="store_true",
                        help="list interfaces only, never open or write")
    parser.add_argument("--out", default=None, help="where to write the report")
    args = parser.parse_args()

    print(__doc__.strip().split("\n\n")[0])
    report["environment"] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "vid": "0x%04X" % args.vid,
        "pid": "0x%04X" % args.pid,
        "euid": os.geteuid() if hasattr(os, "geteuid") else None,
    }

    hid = import_hid()
    if hid is None:
        return 2

    entries = scan(hid, args.vid, args.pid)
    if not entries:
        print()
        print("No device with PID 0x%04X found. Plug the pad in and try again." % args.pid)
        print("If it is plugged in, run this with sudo once to rule out permissions.")
        save(args.out)
        return 1

    if args.dry_run:
        print()
        print("Dry run, nothing was sent to the device.")
        save(args.out)
        return 0

    winner = try_handshake(hid, entries, args.interface)
    if winner is None:
        save(args.out)
        return 1
    entry, link = winner
    report["command_interface"] = entry.get("interface_number")

    try:
        read_firmware(link)
        if not args.no_keys:
            capture_keys(link, args.seconds)
        if args.lighting:
            test_lighting(link)
    finally:
        link.close()

    path = save(args.out)
    print()
    print("Written: %s" % path)
    print("Please attach that file to the MacroPad issue at")
    print("https://github.com/ramisotti13-eng/BaseCamp-Linux/issues")
    print("It contains device identifiers and raw HID reports, nothing else.")
    return 0


def save(out):
    path = out or ("macropad-probe-%s.json" % time.strftime("%Y%m%d-%H%M%S"))
    with open(path, "w") as handle:
        json.dump(report, handle, indent=1)
    return os.path.abspath(path)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)
