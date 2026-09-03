#!/usr/bin/env python3
"""Generate battery state icons for the macOS menu bar.

Produces 7 PNG icons (44x44 px for @2x Retina) with a segmented
vertical battery design matching common battery icon conventions:

  - battery_critical.png    (0-10%, red)
  - battery_low.png         (11-30%, orange)
  - battery_medium.png      (31-60%, orange + yellow-green)
  - battery_full.png        (61-100%, green)
  - battery_charging_low.png  (charging + ≤30%, bolt)
  - battery_charging.png      (charging + >30%, green + bolt)
  - battery_disconnected.png  (gray outline, no fill)

Usage: python scripts/generate_battery_icons.py
"""

import os

from AppKit import (
    NSBitmapImageRep, NSGraphicsContext, NSColor,
    NSBezierPath, NSMakeRect, NSPNGFileType, NSCalibratedRGBColorSpace,
)
from Foundation import NSPoint

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "resources", "battery_icons")

SIZE = 44  # px (22pt @2x)

# --- Colors (r, g, b, a) ---
OUTLINE_DARK = (0.20, 0.20, 0.22, 1.0)
OUTLINE_GRAY = (0.55, 0.55, 0.55, 1.0)
RED = (0.80, 0.18, 0.15, 1.0)
ORANGE = (0.90, 0.49, 0.13, 1.0)
YELLOW_GREEN = (0.75, 0.83, 0.22, 1.0)
GREEN = (0.30, 0.69, 0.31, 1.0)
WHITE = (1.0, 1.0, 1.0, 0.95)

# --- Layout (all in pixels for 44x44 canvas) ---
# Battery body (rounded rect outline)
BODY = dict(x=9, y=3, w=26, h=33, r=5)
STROKE_W = 2.5

# Cap / positive terminal on top
CAP = dict(x=17, y=36, w=10, h=5, r=2)

# Three fill segments inside body (bottom to top)
SEG_INSET = 4  # inset from body edges
SEG_GAP = 3    # gap between segments
SEG_R = 2      # corner radius

def _calc_segments():
    """Calculate segment rects from body dimensions."""
    ix = BODY["x"] + SEG_INSET
    iw = BODY["w"] - 2 * SEG_INSET
    iy = BODY["y"] + SEG_INSET
    ih = BODY["h"] - 2 * SEG_INSET
    seg_h = (ih - 2 * SEG_GAP) / 3.0
    return [
        (ix, iy + i * (seg_h + SEG_GAP), iw, seg_h)
        for i in range(3)
    ]

SEGMENTS = _calc_segments()


def _color(r, g, b, a=1.0):
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)


def _draw_outline(color=OUTLINE_DARK):
    """Draw battery body outline and cap."""
    b = BODY
    body = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
        NSMakeRect(b["x"], b["y"], b["w"], b["h"]), b["r"], b["r"],
    )
    _color(*color).setStroke()
    body.setLineWidth_(STROKE_W)
    body.stroke()

    c = CAP
    cap = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
        NSMakeRect(c["x"], c["y"], c["w"], c["h"]), c["r"], c["r"],
    )
    _color(*color).setFill()
    cap.fill()


def _draw_segment(index, color):
    """Fill segment 0 (bottom), 1 (middle), or 2 (top)."""
    x, y, w, h = SEGMENTS[index]
    seg = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
        NSMakeRect(x, y, w, h), SEG_R, SEG_R,
    )
    _color(*color).setFill()
    seg.fill()


def _draw_partial_segment(index, color, fraction):
    """Fill a segment partially (fraction 0.0–1.0, from bottom up)."""
    x, y, w, h = SEGMENTS[index]
    ph = max(h * fraction, 3)
    seg = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
        NSMakeRect(x, y, w, ph), SEG_R, SEG_R,
    )
    _color(*color).setFill()
    seg.fill()


def _draw_bolt(color=WHITE):
    """Draw a lightning bolt centered in the battery body."""
    cx = BODY["x"] + BODY["w"] / 2.0
    cy = BODY["y"] + BODY["h"] * 0.12
    s = BODY["h"] * 0.14

    bolt = NSBezierPath.bezierPath()
    # 6-point zigzag bolt
    bolt.moveToPoint_(NSPoint(cx + s * 0.35, cy + s * 5.6))   # top
    bolt.lineToPoint_(NSPoint(cx - s * 0.55, cy + s * 3.0))   # mid-left
    bolt.lineToPoint_(NSPoint(cx + s * 0.10, cy + s * 3.2))   # notch
    bolt.lineToPoint_(NSPoint(cx - s * 0.35, cy + s * 0.2))   # bottom
    bolt.lineToPoint_(NSPoint(cx + s * 0.55, cy + s * 2.8))   # mid-right
    bolt.lineToPoint_(NSPoint(cx - s * 0.10, cy + s * 2.6))   # notch
    bolt.closePath()

    _color(*color).setFill()
    bolt.fill()


def _create_icon(draw_func):
    """Render a 44x44 PNG using the given draw function."""
    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, SIZE, SIZE, 8, 4, True, False, NSCalibratedRGBColorSpace, 0, 0,
    )
    ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    NSGraphicsContext.setCurrentContext_(ctx)

    draw_func()

    ctx.flushGraphics()
    NSGraphicsContext.setCurrentContext_(None)
    return rep.representationUsingType_properties_(NSPNGFileType, None)


# --- Icon draw functions ---

def draw_critical():
    _draw_outline()
    _draw_partial_segment(0, RED, 0.45)

def draw_low():
    _draw_outline()
    _draw_segment(0, ORANGE)

def draw_medium():
    _draw_outline()
    _draw_segment(0, ORANGE)
    _draw_segment(1, YELLOW_GREEN)

def draw_full():
    _draw_outline()
    _draw_segment(0, GREEN)
    _draw_segment(1, GREEN)
    _draw_segment(2, GREEN)

def draw_charging_low():
    _draw_outline()
    _draw_bolt(ORANGE)

def draw_charging():
    _draw_outline()
    _draw_segment(0, GREEN)
    _draw_segment(1, GREEN)
    _draw_segment(2, GREEN)
    _draw_bolt(WHITE)

def draw_disconnected():
    _draw_outline(OUTLINE_GRAY)


ICONS = {
    "battery_critical": draw_critical,
    "battery_low": draw_low,
    "battery_medium": draw_medium,
    "battery_full": draw_full,
    "battery_charging_low": draw_charging_low,
    "battery_charging": draw_charging,
    "battery_disconnected": draw_disconnected,
}


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for name, draw_func in ICONS.items():
        filename = f"{name}.png"
        print(f"  Generating {filename}...")
        png_data = _create_icon(draw_func)
        path = os.path.join(OUTPUT_DIR, filename)
        png_data.writeToFile_atomically_(path, True)
    print(f"  Done — {len(ICONS)} icons written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
