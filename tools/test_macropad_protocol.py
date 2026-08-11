#!/usr/bin/env python3
"""
Checks the MacroPad packet builders against the bytes read out of
MacroPadSDK.dll. No hardware and no hidapi needed.

    python3 tools/test_macropad_protocol.py

Every expectation here is a fact taken from the disassembly, written down so
that a later refactor cannot quietly change what goes on the wire. Two of them
are cross-checks rather than MacroPad facts: the INIT handshake and the
DisplayPad brightness packet, which our shipping DisplayPad driver sends to
real hardware. They are the reason to believe the rest.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devices.macropad import controller as mp   # noqa: E402

failures = []


def check(name, actual, expected_prefix, length=64):
    """Compare the leading bytes and the total length."""
    problems = []
    if len(actual) != length:
        problems.append("length %d, expected %d" % (len(actual), length))
    got = actual[:len(expected_prefix)]
    if bytes(got) != bytes(expected_prefix):
        problems.append("bytes %s, expected %s" % (got.hex(" "), bytes(expected_prefix).hex(" ")))
    if problems:
        failures.append("%s: %s" % (name, "; ".join(problems)))
        print("FAIL  %s" % name)
        for problem in problems:
            print("      %s" % problem)
    else:
        print("ok    %-28s %s" % (name, got.hex(" ")))


# ── The handshake, cross-checked against the shipping DisplayPad driver ───────
# devices/displaypad/panel.py sends INIT_MSG = 00 11 80 00 00 01 ... to real
# hardware. Ours must be the same 64 bytes without the report ID.
check("init", mp.pkt_init(True), bytes([0x11, 0x80, 0x00, 0x00, 0x01]))
check("init disable", mp.pkt_init(False), bytes([0x11, 0x80, 0x00, 0x00, 0x00]))

# ── Reads ────────────────────────────────────────────────────────────────────
check("firmware_info", mp.pkt_firmware_info(), bytes([0x11, 0x00]))
check("firmware_layout", mp.pkt_firmware_layout(), bytes([0x11, 0x12]))

# ── Settings, resets, flash ──────────────────────────────────────────────────
check("led on", mp.pkt_led(True), bytes([0x12, 0x03]))
check("led off", mp.pkt_led(False), bytes([0x12, 0x02]))
check("reset keys", mp.pkt_reset_keys(), bytes([0x13, 0x60]))
check("reset effects", mp.pkt_reset_effects(), bytes([0x13, 0x61]))
check("save slot 3", mp.pkt_save(3), bytes([0x13, 0x55, 0x00, 0x00, 0x03]))

# ── Profiles ─────────────────────────────────────────────────────────────────
check("switch profile 2/4", mp.pkt_switch_profile(2, 4),
      bytes([0x14, 0x00, 0x00, 0x00, 0x02, 0x04]))

# The SDK validates before building; so do we.
for bad in (0, 6, -1):
    try:
        mp.pkt_switch_profile(bad)
        failures.append("switch profile %r was accepted" % bad)
        print("FAIL  profile %r accepted" % bad)
    except ValueError:
        print("ok    profile %-22r rejected" % bad)

# ── Key remapping ────────────────────────────────────────────────────────────
# 14 20, source as uint16 little endian in [2:4], target in [4:6].
check("remap key 3 -> 0x1234", mp.pkt_remap_key(3, 0x1234),
      bytes([0x14, 0x20, 0x03, 0x00, 0x34, 0x12]))
check("shortcut 5 + ctrl", mp.pkt_shortcut(5, 0x2C, 0x01),
      bytes([0x14, 0x21, 0x05, 0x00, 0x2C, 0x01]))

# ── Lighting ─────────────────────────────────────────────────────────────────
# Static: speed goes out as 0xFF, direction and width likewise, colour 1 at [9].
static = mp.pkt_effect(mp.EFFECT_STATIC, brightness=75, color1=(0x00, 0x44, 0xFF))
check("static effect", static,
      bytes([0x14, 0x2C, 0x00, 0x00, 0xFF, 75, 0x00, 0xFF, 0xFF,
             0x00, 0x44, 0xFF]))

# Wave: a real speed value, dual colour raises byRandColor to 16.
wave = mp.pkt_effect(mp.EFFECT_WAVE, brightness=50, speed=60,
                     color1=(1, 2, 3), color2=(4, 5, 6))
check("wave dual colour", wave,
      bytes([0x14, 0x2C, 0x04, 0x00, 60, 50, 0x10, 0xFF, 0xFF,
             1, 2, 3, 4, 5, 6]))

# Off carries no colour at all.
check("off", mp.pkt_effect(mp.EFFECT_OFF),
      bytes([0x14, 0x2C, 0x0C, 0x00, 0xFF, mp.DEFAULT_BRIGHTNESS, 0x00,
             0xFF, 0xFF, 0x00, 0x00, 0x00]))

# Custom activation is the odd one: the SDK fills the buffer with 0xFF first.
custom = mp.pkt_custom_activate(80)
check("custom activate", custom,
      bytes([0x14, 0x2C, 0x0A, 0x00, 0xFF, 80, 0xFF, 0xFF]))
if custom[-1] != 0xFF:
    failures.append("custom activate: tail should stay 0xFF")
    print("FAIL  custom activate tail is 0x%02x, expected 0xff" % custom[-1])
else:
    print("ok    custom activate tail        ff")

# Per-key colours: 14 2C 00 01 <chunk> 4B 00, then 12 RGB triples at offset 7.
colors = [(i, i + 1, i + 2) for i in range(0, 36, 3)]
packet = mp.pkt_custom_colors(colors)
check("custom colours header", packet,
      bytes([0x14, 0x2C, 0x00, 0x01, 0x00, 0x4B, 0x00]))
expected_body = bytes(b for color in colors for b in color)
if packet[7:7 + 36] != expected_body:
    failures.append("custom colours: body at offset 7 does not match")
    print("FAIL  custom colours body")
else:
    print("ok    custom colours body        %s ..." % packet[7:13].hex(" "))
if any(packet[7 + 36:]):
    failures.append("custom colours: bytes after the 36 colour bytes are not zero")
    print("FAIL  custom colours tail not zero")
else:
    print("ok    custom colours tail        zero")

try:
    mp.pkt_custom_colors(colors[:5])
    failures.append("custom colours accepted a short list")
    print("FAIL  short colour list accepted")
except ValueError:
    print("ok    short colour list          rejected")

# ── Response helpers ─────────────────────────────────────────────────────────
if not mp.is_ack(bytes([0xFF, 0xAA] + [0] * 62)):
    failures.append("is_ack rejected FF AA")
if mp.is_ack(bytes([0x14, 0x2C] + [0] * 62)):
    failures.append("is_ack accepted a non-ack")
print("ok    ack detection")

# decode_key_event is the unverified part; check it is at least self-consistent.
event = bytearray(64)
event[0] = 0x01
event[1] = 0b00000101   # keys 0 and 2
event[2] = 0b00001000   # key 11
decoded = mp.decode_key_event(bytes(event))
if decoded != {0, 2, 11}:
    failures.append("decode_key_event returned %r, expected {0, 2, 11}" % decoded)
    print("FAIL  decode_key_event %r" % decoded)
else:
    print("ok    decode_key_event (hypothesis, not verified on hardware)")

# ── The probe script must agree with the driver ──────────────────────────────
# tools/macropad_probe.py is deliberately standalone so testers can download
# one file, which means it carries its own copy of the packet layout. That is
# the kind of duplication that drifts, so pin the two together here.
import macropad_probe as probe   # noqa: E402

pairs = [
    ("probe init", probe.INIT_PACKET, mp.pkt_init(True)),
    ("probe firmware info", probe.FW_INFO_PACKET, mp.pkt_firmware_info()),
    ("probe firmware layout", probe.FW_LAYOUT_PACKET, mp.pkt_firmware_layout()),
    ("probe static red", probe.effect_packet(0, brightness=60, color=(255, 0, 0)),
     mp.pkt_effect(mp.EFFECT_STATIC, brightness=60, color1=(255, 0, 0))),
    ("probe wave", probe.effect_packet(4, brightness=60, speed=60),
     mp.pkt_effect(mp.EFFECT_WAVE, brightness=60, speed=60, color1=(255, 0, 0))),
    ("probe custom activate", probe.custom_activate_packet(70),
     mp.pkt_custom_activate(70)),
]
for name, from_probe, from_driver in pairs:
    if bytes(from_probe) == bytes(from_driver):
        print("ok    %-28s matches driver" % name)
    else:
        failures.append("%s differs from the driver" % name)
        print("FAIL  %s" % name)
        print("      probe  %s" % bytes(from_probe)[:14].hex(" "))
        print("      driver %s" % bytes(from_driver)[:14].hex(" "))

palette = [(255, 0, 0), (255, 128, 0), (255, 255, 0), (128, 255, 0),
           (0, 255, 0), (0, 255, 128), (0, 255, 255), (0, 128, 255),
           (0, 0, 255), (128, 0, 255), (255, 0, 255), (255, 255, 255)]
if bytes(probe.per_key_packet()) == bytes(mp.pkt_custom_colors(palette)):
    print("ok    probe per-key colours       matches driver")
else:
    failures.append("probe per-key colour packet differs from the driver")
    print("FAIL  probe per-key colours")

# ── The capture analysis, on synthetic reports ───────────────────────────────
# The real run needs hardware; this at least proves the analysis does not throw
# and picks the right bits out of a DisplayPad-shaped report.
probe.report["key_capture"] = {}
idle = [bytes(64)]
captured = {
    "M1": [bytes([0x01, 0x01] + [0] * 62).hex(" ")],
    "M9": [bytes([0x01, 0x00, 0x01] + [0] * 61).hex(" ")],
    "M5": [bytes(64).hex(" ")],          # nothing but idle, must not crash
}
probe.analyse_capture(idle, captured)
analysis = probe.report["key_capture"].get("analysis", {})
if analysis.get("M1") == [{"byte": 0, "bit": 0}, {"byte": 1, "bit": 0}] and \
        analysis.get("M9") == [{"byte": 0, "bit": 0}, {"byte": 2, "bit": 0}] and \
        analysis.get("M5") == []:
    print("ok    capture analysis")
else:
    failures.append("capture analysis returned %r" % analysis)
    print("FAIL  capture analysis %r" % analysis)

if probe.report["key_capture"].get("first_bytes") != [0x01]:
    failures.append("capture analysis did not report the leading 0x01")
    print("FAIL  capture analysis first_bytes")
else:
    print("ok    capture analysis first byte")

# ── The report descriptor summary, on a real descriptor ──────────────────────
# Taken from this machine's DisplayPad (interface 3): a vendor collection with
# one 64 byte report in each direction. Same shape the MacroPad should show.
descriptor = bytes.fromhex(
    "06 00 ff 09 01 a1 01 09 01 15 00 26 ff 00 75 08 95 40 81 02 09 01 "
    "15 00 26 ff 00 75 08 95 40 91 02 c0".replace(" ", ""))
summary = probe.summarise_descriptor(descriptor)
if summary["usage_page"] == "0xFF00" and summary["usage"] == "0x01" and \
        summary["reports"].get("0", {}).get("input") == 64 and \
        summary["reports"].get("0", {}).get("output") == 64:
    print("ok    descriptor summary          %s" % summary["reports"])
else:
    failures.append("descriptor summary returned %r" % summary)
    print("FAIL  descriptor summary %r" % summary)

print()
if failures:
    print("%d check(s) failed:" % len(failures))
    for failure in failures:
        print("  - %s" % failure)
    sys.exit(1)
print("all checks passed")
