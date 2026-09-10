"""Deterministic RGB choice frames.

A frame shows two candidate cards of equal size at mirrored positions. Every
pixel outside the two card interiors is identical between a trial and its
mirrored trial, so swapping the pair changes nothing but which side each
candidate is on. Rendering is pure numpy: same manifest, same candidates,
same variant => byte-identical frame on every machine.
"""

import numpy as np

from . import font
from .manifest import LOGO_SIZE

WIDTH, HEIGHT = 320, 180
CARD_Y0, CARD_Y1 = 28, 166
LEFT_CARD = (8, 152)
RIGHT_CARD = (168, 312)

VARIANT_STYLE = {
    "standard": {
        "background": (235, 240, 249),
        "card": (255, 255, 255),
        "border": (19, 36, 71),
        "ink": (19, 36, 71),
        "header": (19, 36, 71),
        "header_ink": (219, 229, 249),
        "scale_bonus": 0,
    },
    "high_contrast": {
        "background": (0, 0, 0),
        "card": (255, 255, 255),
        "border": (255, 255, 255),
        "ink": (0, 0, 0),
        "header": (255, 255, 255),
        "header_ink": (0, 0, 0),
        "scale_bonus": 0,
    },
    "large": {
        "background": (245, 245, 235),
        "card": (255, 255, 255),
        "border": (40, 40, 40),
        "ink": (20, 20, 20),
        "header": (40, 40, 40),
        "header_ink": (245, 245, 235),
        "scale_bonus": 1,
    },
}


def hex_rgb(value: str):
    return tuple(int(value[i : i + 2], 16) for i in (1, 3, 5))


def _rect(frame, x0, y0, x1, y1, color):
    frame[y0:y1, x0:x1] = np.asarray(color, dtype=np.uint8)


def _centered_text(frame, cx, y, text, color, scale):
    font.draw_text(frame, cx - font.text_width(text, scale) // 2, y, text, color, scale)


def _draw_card(frame, x0, x1, candidate, category, style):
    ink = style["ink"]
    bonus = style["scale_bonus"]
    _rect(frame, x0, CARD_Y0, x1, CARD_Y1, style["border"])
    _rect(frame, x0 + 2, CARD_Y0 + 2, x1 - 2, CARD_Y1 - 2, style["card"])
    cx = (x0 + x1) // 2
    inner_w = x1 - x0 - 12
    if category == "ticker":
        scale = 4 + bonus
        text = "$" + candidate["text"]
        while font.text_width(text, scale) > inner_w and scale > 1:
            scale -= 1
        _centered_text(frame, cx, 78, text, ink, scale)
    elif category == "name":
        scale = 3 + bonus
        text = candidate["text"]
        while font.text_width(text, scale) > inner_w and scale > 1:
            scale -= 1
        lines = [text]
        if font.text_width(text, scale) > inner_w:
            lines = font.wrap(text, inner_w // ((font.GLYPH_W + font.SPACING) * scale))
        y = 96 - (len(lines) * (font.text_height(scale) + 4)) // 2
        for line in lines:
            _centered_text(frame, cx, y, line, ink, scale)
            y += font.text_height(scale) + 4
    elif category in ("launch_action", "launch_venue"):
        scale = 3 + bonus
        text = candidate["text"]
        while font.text_width(text, scale) > inner_w and scale > 1:
            scale -= 1
        _centered_text(frame, cx, 88, text, ink, scale)
    elif category == "description":
        scale = 1 + bonus
        per_line = inner_w // ((font.GLYPH_W + font.SPACING) * scale)
        lines = font.wrap(candidate["text"], per_line)[:8]
        y = 96 - (len(lines) * (font.text_height(scale) + 3)) // 2
        for line in lines:
            _centered_text(frame, cx, y, line, ink, scale)
            y += font.text_height(scale) + 3
    elif category == "logo":
        cell = 12 + 2 * bonus
        size = LOGO_SIZE * cell
        lx, ly = cx - size // 2, 97 - size // 2
        fg, bg = hex_rgb(candidate["fg"]), hex_rgb(candidate["bg"])
        _rect(frame, lx, ly, lx + size, ly + size, bg)
        for r, row in enumerate(candidate["pixels"]):
            for c, bit in enumerate(row):
                if bit == "#":
                    _rect(frame, lx + c * cell, ly + r * cell, lx + (c + 1) * cell, ly + (r + 1) * cell, fg)
    elif category == "palette":
        colors = [hex_rgb(c) for c in candidate["colors"]]
        band_h = 100 // len(colors)
        top = 97 - (band_h * len(colors)) // 2
        bx0, bx1 = x0 + 10, x1 - 10
        for i, color in enumerate(colors):
            _rect(frame, bx0, top + i * band_h, bx1, top + (i + 1) * band_h, color)
    else:
        raise ValueError(f"Unknown category {category}")


def render(manifest: dict, category: str, left: dict, right: dict, variant: str, header_extra: str = "") -> np.ndarray:
    if variant not in VARIANT_STYLE:
        raise ValueError(f"Unknown variant {variant}")
    style = VARIANT_STYLE[variant]
    w, h = manifest["frame"]["width"], manifest["frame"]["height"]
    if (w, h) != (WIDTH, HEIGHT):
        raise ValueError("Unsupported frame size")
    frame = np.empty((h, w, 3), dtype=np.uint8)
    frame[:] = np.asarray(style["background"], dtype=np.uint8)
    _rect(frame, 0, 0, w, 22, style["header"])
    header = category.replace("_", " ").upper()
    if header_extra:
        header = f"{header} {header_extra}"
    _centered_text(frame, w // 2, 7, header, style["header_ink"], 1)
    _draw_card(frame, *LEFT_CARD, left, category, style)
    _draw_card(frame, *RIGHT_CARD, right, category, style)
    return frame


def save_png(frame: np.ndarray, path):
    from PIL import Image

    Image.fromarray(frame, "RGB").save(path, format="PNG", optimize=False)


def load_png(path) -> np.ndarray:
    from PIL import Image

    with Image.open(path) as im:
        return np.array(im.convert("RGB"), dtype=np.uint8, copy=True)
