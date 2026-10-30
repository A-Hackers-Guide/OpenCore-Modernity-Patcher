"""
gui_icons.py: Draw the app's icons at runtime

OCLP ships .icns artwork that carries its branding, so we draw our own:
rounded tiles with a simple glyph, rendered at whatever size is asked for.
"""

import math

import wx

PALETTE = {
    "app":       ((88, 86, 214), (175, 82, 222)),
    "build":     ((0, 122, 255), (90, 200, 250)),
    "installer": ((52, 199, 89), (48, 176, 199)),
    "hardware":  ((255, 149, 0), (255, 204, 0)),
    "support":   ((142, 142, 147), (99, 99, 102)),
}

_cache = {}


def bitmap(name: str, size: int) -> wx.Bitmap:
    key = (name, size)
    if key not in _cache:
        _cache[key] = _draw(name, size)
    return _cache[key]


def _draw(name: str, size: int) -> wx.Bitmap:
    scale = 2
    s = size * scale
    bmp = wx.Bitmap.FromRGBA(s, s, 0, 0, 0, 0)
    dc = wx.MemoryDC(bmp)
    gc = wx.GraphicsContext.Create(dc)

    top, bottom = PALETTE.get(name, PALETTE["app"])
    pad = s * 0.08
    brush = gc.CreateLinearGradientBrush(0, pad, 0, s - pad, wx.Colour(*top), wx.Colour(*bottom))
    gc.SetBrush(brush)
    gc.SetPen(wx.TRANSPARENT_PEN)
    gc.DrawRoundedRectangle(pad, pad, s - 2 * pad, s - 2 * pad, s * 0.22)

    gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(wx.WHITE).Width(max(2, s * 0.06)).Cap(wx.CAP_ROUND).Join(wx.JOIN_ROUND)))
    gc.SetBrush(wx.TRANSPARENT_BRUSH)
    c = s / 2
    r = s * 0.24
    if name == "app":
        _ring(gc, c, c, r)
        gc.StrokeLine(c, c - r * 1.25, c, c - r * 0.35)
    elif name == "build":
        # boot drive with a key slot
        gc.DrawRoundedRectangle(c - r * 1.3, c - r * 0.8, r * 2.6, r * 1.6, r * 0.3)
        gc.StrokeLine(c - r * 0.7, c, c + r * 0.4, c)
        gc.DrawEllipse(c + r * 0.5, c - r * 0.2, r * 0.4, r * 0.4)
    elif name == "installer":
        gc.StrokeLine(c, c - r * 1.2, c, c + r * 0.6)
        gc.StrokeLines([(c - r * 0.7, c - r * 0.1), (c, c + r * 0.6), (c + r * 0.7, c - r * 0.1)])
        gc.StrokeLine(c - r * 1.1, c + r * 1.1, c + r * 1.1, c + r * 1.1)
    elif name == "hardware":
        gc.DrawRoundedRectangle(c - r * 0.9, c - r * 0.9, r * 1.8, r * 1.8, r * 0.25)
        for i in (-0.5, 0, 0.5):
            for (x1, y1, x2, y2) in ((c + r * i, c - r * 0.9, c + r * i, c - r * 1.35),
                                     (c + r * i, c + r * 0.9, c + r * i, c + r * 1.35),
                                     (c - r * 0.9, c + r * i, c - r * 1.35, c + r * i),
                                     (c + r * 0.9, c + r * i, c + r * 1.35, c + r * i)):
                gc.StrokeLine(x1, y1, x2, y2)
    elif name == "support":
        path = gc.CreatePath()
        path.AddArc(c, c - r * 0.35, r * 0.6, math.pi, math.pi * 2.25, True)
        path.AddLineToPoint(c, c + r * 0.45)
        gc.StrokePath(path)
        gc.SetBrush(wx.WHITE_BRUSH)
        gc.DrawEllipse(c - s * 0.035, c + r * 0.85, s * 0.07, s * 0.07)
    del gc
    dc.SelectObject(wx.NullBitmap)
    return wx.Bitmap(bmp.ConvertToImage().Scale(size, size, wx.IMAGE_QUALITY_HIGH))


def _ring(gc, cx, cy, r) -> None:
    path = gc.CreatePath()
    path.AddArc(cx, cy, r, math.radians(-60), math.radians(240), True)
    gc.StrokePath(path)


def app_icon() -> wx.IconBundle:
    bundle = wx.IconBundle()
    for size in (16, 32, 48, 64, 128, 256):
        icon = wx.Icon()
        icon.CopyFromBitmap(bitmap("app", size))
        bundle.AddIcon(icon)
    return bundle
