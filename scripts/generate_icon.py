#!/usr/bin/env python3
"""Generate AppIcon.icns for Razer Battery menu bar app.

Uses AppKit (pyobjc) to draw a Razer-green battery icon at all required
sizes, then calls iconutil to produce the final .icns file.

Design: dark rounded-rect background, green circle outline, vertical
battery inside with green charge segments.

Usage: python scripts/generate_icon.py
"""

import os
import subprocess
import sys

from AppKit import (
    NSBitmapImageRep, NSGraphicsContext, NSColor,
    NSBezierPath, NSMakeRect, NSPNGFileType, NSCalibratedRGBColorSpace,
)
from Foundation import NSPoint


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
ICONSET_DIR = os.path.join(PROJECT_ROOT, "resources", "AppIcon.iconset")
ICNS_PATH = os.path.join(PROJECT_ROOT, "resources", "AppIcon.icns")

# macOS .iconset required sizes
ICON_SIZES = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]

# Colors
RAZER_GREEN = (0.0, 0.85, 0.0)  # slightly less neon for app icon clarity
DARK_BG = (0.08, 0.08, 0.10)


def draw_icon(size):
    """Draw the Razer battery icon at the given pixel size and return PNG data."""
    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, size, size, 8, 4, True, False, NSCalibratedRGBColorSpace, 0, 0
    )
    ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    NSGraphicsContext.setCurrentContext_(ctx)

    s = float(size)
    pad = s * 0.04

    # --- Background: dark rounded rectangle ---
    corner = s * 0.20
    bg_rect = NSMakeRect(pad, pad, s - 2 * pad, s - 2 * pad)
    bg_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(bg_rect, corner, corner)
    NSColor.colorWithCalibratedRed_green_blue_alpha_(DARK_BG[0], DARK_BG[1], DARK_BG[2], 1.0).setFill()
    bg_path.fill()

    # --- Green circle outline ---
    cx = s * 0.5
    cy = s * 0.5
    circle_r = s * 0.36
    circle_lw = s * 0.035

    circle_rect = NSMakeRect(cx - circle_r, cy - circle_r, circle_r * 2, circle_r * 2)
    circle_path = NSBezierPath.bezierPathWithOvalInRect_(circle_rect)
    NSColor.colorWithCalibratedRed_green_blue_alpha_(RAZER_GREEN[0], RAZER_GREEN[1], RAZER_GREEN[2], 1.0).setStroke()
    circle_path.setLineWidth_(circle_lw)
    circle_path.stroke()

    # --- Vertical battery ---
    # Battery body: centered, vertical orientation
    bw = s * 0.26   # battery width
    bh = s * 0.38   # battery height
    bx = cx - bw / 2
    by = cy - bh / 2 - s * 0.03  # shift down slightly to make room for terminal
    bcorner = s * 0.03

    body_rect = NSMakeRect(bx, by, bw, bh)
    body_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(body_rect, bcorner, bcorner)
    NSColor.colorWithCalibratedRed_green_blue_alpha_(RAZER_GREEN[0], RAZER_GREEN[1], RAZER_GREEN[2], 1.0).setStroke()
    body_path.setLineWidth_(s * 0.022)
    body_path.stroke()

    # --- Battery terminal (top nub) ---
    tw = bw * 0.40
    th = s * 0.05
    tx = cx - tw / 2
    ty = by + bh  # sits on top of the body
    tcorner = s * 0.015

    term_rect = NSMakeRect(tx, ty, tw, th)
    term_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(term_rect, tcorner, tcorner)
    NSColor.colorWithCalibratedRed_green_blue_alpha_(RAZER_GREEN[0], RAZER_GREEN[1], RAZER_GREEN[2], 1.0).setFill()
    term_path.fill()

    # --- Charge segments (3 green bars inside battery) ---
    seg_pad = s * 0.035  # padding inside battery body
    seg_gap = s * 0.02   # gap between segments
    num_segments = 3

    seg_area_x = bx + seg_pad
    seg_area_y = by + seg_pad
    seg_area_w = bw - 2 * seg_pad
    seg_area_h = bh - 2 * seg_pad

    total_gaps = seg_gap * (num_segments - 1)
    seg_h = (seg_area_h - total_gaps) / num_segments
    seg_corner = s * 0.015

    for i in range(num_segments):
        sy = seg_area_y + i * (seg_h + seg_gap)
        seg_rect = NSMakeRect(seg_area_x, sy, seg_area_w, seg_h)
        seg_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(seg_rect, seg_corner, seg_corner)
        NSColor.colorWithCalibratedRed_green_blue_alpha_(RAZER_GREEN[0], RAZER_GREEN[1], RAZER_GREEN[2], 0.9).setFill()
        seg_path.fill()

    ctx.flushGraphics()
    NSGraphicsContext.setCurrentContext_(None)

    png_data = rep.representationUsingType_properties_(NSPNGFileType, None)
    return png_data


def main():
    os.makedirs(ICONSET_DIR, exist_ok=True)

    for filename, px in ICON_SIZES:
        print(f"  Generating {filename} ({px}x{px})...")
        png_data = draw_icon(px)
        path = os.path.join(ICONSET_DIR, filename)
        png_data.writeToFile_atomically_(path, True)

    print("  Converting to .icns...")
    result = subprocess.run(
        ["iconutil", "--convert", "icns", ICONSET_DIR, "--output", ICNS_PATH],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  ERROR: iconutil failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    print(f"  Done: {ICNS_PATH}")


if __name__ == "__main__":
    main()
