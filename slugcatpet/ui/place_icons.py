"""Shared tabbar placement icon rendering."""
from __future__ import annotations
import math
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (QColor, QPainter, QPen, QPolygonF, QPainterPath,
                           QPixmap, QLinearGradient, QRadialGradient)
from ..cats import get as get_cat_def

# Icons use the Saint palette and sprite frames.
_SAINT = get_cat_def("saint")
_HEAD_ATLAS, _HEAD_FAM = _SAINT.frames["head"]
_FACE_ATLAS, _FACE_FAM = _SAINT.frames["face"]

COLLAPSED_W, COLLAPSED_H = 24, 48
EXPANDED_W = 120
EXPANDED_H = 250
# Olive-tinted icon palette matching the tabbar panel.
_ICON_GREY = QColor(192, 199, 183)
_POLE_EDGE = QColor(20, 22, 26)
_POLE_SHEEN = QColor(104, 112, 126)
_POLE_CORE = QColor(40, 42, 47)
_POLE_TILE = QColor(255, 255, 255, 12)
_ICON_SAINT = QColor(*_SAINT.body_color)
_ICON_EYE = QColor(*_SAINT.eye_color)
_ICON_AMBER = QColor(233, 203, 138)
_ICON_FACET = QColor(70, 76, 66, 160)
_ICON_RED = QColor(210, 96, 84)
_FRUIT_TOP = QColor(140, 185, 255)
_FRUIT_BOT = QColor(28, 64, 210)
_FRUIT_OUTLINE = QColor(22, 26, 44)
_LAMP_OUTLINE = QColor(255, 70, 20)
_LAMP_FLESH = QColor(255, 248, 230)
_SLIME_BODY = QColor(255, 122, 26)
_SLIME_TENDRIL = QColor(204, 92, 16)
_SLIME_GLOW = QColor(255, 150, 50, 90)
_BAT_BODY = QColor(24, 26, 30)
_BAT_EYE = QColor(232, 236, 226)


def _pen(c, w, cap=True):
    p = QPen(c, w)
    p.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    if cap:
        p.setCapStyle(Qt.PenCapStyle.RoundCap)
    return p


_CAT_HEAD = "Kill_Slugcat"             # solid cat-head UI frame


def _cat_ready(atlas):
    """Return whether the atlas has the frames needed for cat pole icons."""
    if atlas is None:
        return False
    base = atlas.get("base")
    return (base.has("BodyA") and base.has("LegsAVerticalPole") and base.has("PlayerArm0")
            and atlas.get(_FACE_ATLAS).has(_FACE_FAM + "1") and base.has("OnTopOfTerrainHand")
            and atlas.get(_HEAD_ATLAS).has(_HEAD_FAM + "0") and atlas.get("ui").has(_CAT_HEAD))


def _blit(p, atlas, key, frame, center, k, w, rot=0.0, tint=None):
    """Draw one tinted atlas frame centered in the icon."""
    pm = atlas.sprite(key, frame, tint or _ICON_SAINT, padded=False)
    sc = k * w / 22.0
    pw, ph = pm.width() * sc, pm.height() * sc
    p.save()
    p.translate(center.x(), center.y())
    if rot:
        p.rotate(rot)
    p.drawPixmap(QRectF(-pw / 2, -ph / 2, pw, ph), pm, QRectF(pm.rect()))
    p.restore()


def _pole_rod(p, r, vertical):
    """Draw a dark cylindrical pole with a subtle highlight."""
    cx, cy = r.center().x(), r.center().y()
    w, h = r.width(), r.height()
    if vertical:
        bw = w * 0.22
        rod = QRectF(cx - bw / 2, r.top() + h * 0.04, bw, h * 0.92)
        g = QLinearGradient(rod.left(), 0.0, rod.right(), 0.0)   # horizontal highlight
        rad = bw / 2
    else:
        bh = h * 0.24
        rod = QRectF(r.left() + w * 0.04, cy - bh / 2, w * 0.92, bh)
        g = QLinearGradient(0.0, rod.top(), 0.0, rod.bottom())   # vertical highlight
        rad = bh / 2
    g.setColorAt(0.0, _POLE_EDGE)
    g.setColorAt(0.30, _POLE_SHEEN)
    g.setColorAt(0.55, _POLE_CORE)
    g.setColorAt(1.0, _POLE_EDGE)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(g)
    p.drawRoundedRect(rod, rad, rad)


def _paint_pole_icon(p, r, vertical, atlas=None):
    """Draw a pole icon, optionally with a small Saint sprite."""
    w = r.width()
    L, T = r.left(), r.top()

    def Pt(fx, fy):
        return QPointF(L + fx * w, T + fy * r.height())

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_POLE_TILE)
    p.drawRoundedRect(r, w * 0.24, w * 0.24)

    if not _cat_ready(atlas):
        _pole_rod(p, r, vertical)
        return

    if vertical:
        # Draw most of the cat behind the pole, then the front hand.
        _blit(p, atlas, "base", "LegsAVerticalPole", Pt(0.60, 0.66), 0.95, w)
        _blit(p, atlas, "base", "BodyA", Pt(0.64, 0.48), 0.50, w)
        _blit(p, atlas, "base", "PlayerArm0", Pt(0.56, 0.47), 0.36, w, rot=16.0)
        _blit(p, atlas, _HEAD_ATLAS, _HEAD_FAM + "0", Pt(0.64, 0.30), 0.46, w)
        _blit(p, atlas, _FACE_ATLAS, _FACE_FAM + "1", Pt(0.64, 0.28), 0.46, w, tint=_ICON_EYE)
        _blit(p, atlas, "base", "OnTopOfTerrainHand", Pt(0.39, 0.35), 0.37, w)  # back hand
        _pole_rod(p, r, vertical)                           # pole on top
        _blit(p, atlas, "base", "OnTopOfTerrainHand", Pt(0.575, 0.47), 0.37, w)  # front hand
    else:
        # Draw the cat first, then cover the arm middles with the pole.
        p.setPen(_pen(_ICON_SAINT, 0.11 * w))
        p.drawLine(Pt(0.5, 0.78), Pt(0.5, 0.88))            # body
        p.setPen(_pen(_ICON_SAINT, 0.045 * w))
        p.drawLine(Pt(0.5, 0.88), Pt(0.44, 0.97))           # dangling legs
        p.drawLine(Pt(0.5, 0.88), Pt(0.56, 0.97))
        _blit(p, atlas, "ui", _CAT_HEAD, Pt(0.5, 0.82), 0.60, w)   # head
        p.setPen(_pen(_ICON_SAINT, 0.055 * w))              # raised arms
        p.drawLine(Pt(0.45, 0.74), Pt(0.415, 0.325))
        p.drawLine(Pt(0.55, 0.74), Pt(0.585, 0.325))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_ICON_SAINT)
        rr = 0.033 * w
        for hx in (0.415, 0.585):                           # hands
            p.drawEllipse(Pt(hx, 0.325), rr, rr)
        _pole_rod(p, r, vertical)                           # pole on top


def _paint_place_icon(p, kind, r, atlas=None):
    """Draw a placeable item icon inside rect r."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    cx, cy = r.center().x(), r.center().y()
    w, h = r.width(), r.height()

    if kind == "vpole":
        _paint_pole_icon(p, r, vertical=True, atlas=atlas)
    elif kind == "hpole":
        _paint_pole_icon(p, r, vertical=False, atlas=atlas)
    elif kind == "fruit":
        # Fruit sprite with a blue gradient, or vector fallback.
        if atlas is not None and atlas.get("base").has("DangleFruit0A"):
            _paint_fruit_sprite(p, r, atlas)
        else:
            _paint_fruit_fallback(p, r)
    elif kind == "stone":
        # Irregular pebble with a small facet line.
        ox, oy = cx, cy + h * 0.04
        pts = [(-0.54, 0.12), (-0.30, -0.40), (0.10, -0.46),
               (0.54, -0.12), (0.46, 0.34), (-0.12, 0.46)]
        poly = [QPointF(ox + dx * w * 0.56, oy + dy * h * 0.50) for dx, dy in pts]
        p.setPen(_pen(_ICON_GREY, max(1.8, w * 0.13), cap=False))
        p.setBrush(_ICON_GREY)
        p.drawPolygon(QPolygonF(poly))
        p.setPen(_pen(_ICON_FACET, max(1.2, w * 0.07)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(ox - w * 0.20, oy - h * 0.16),
                   QPointF(ox + w * 0.08, oy - h * 0.24))
    elif kind == "lamp":
        # Lantern sprite with warm glow, or vector fallback.
        if atlas is not None and atlas.get("base").has("DangleFruit0A"):
            _paint_lamp_sprite(p, r, atlas)
        else:
            d = w * 0.42
            bulb = QRectF(0, 0, d, d)
            bulb.moveCenter(QPointF(cx, cy))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(_ICON_AMBER)
            p.drawEllipse(bulb)
            p.setPen(_pen(_ICON_AMBER, max(1.4, w * 0.08)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            bc, rad = bulb.center(), d / 2
            for k in range(8):
                a = math.radians(22.5 + 45 * k)
                p.drawLine(
                    QPointF(bc.x() + math.cos(a) * (rad + w * 0.05),
                            bc.y() - math.sin(a) * (rad + w * 0.05)),
                    QPointF(bc.x() + math.cos(a) * (rad + w * 0.18),
                            bc.y() - math.sin(a) * (rad + w * 0.18)))
    elif kind == "slimemold":
        _paint_slimemold_icon(p, r, atlas)
    elif kind == "batfly":
        # Batfly silhouette: wings, body, bright eye.
        bx, by = cx, cy + h * 0.06
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_BAT_BODY)
        for sgn in (-1, 1):                                    # mirrored wings
            wing = [QPointF(bx + sgn * w * 0.02, by - h * 0.16),
                    QPointF(bx + sgn * w * 0.46, by - h * 0.34),
                    QPointF(bx + sgn * w * 0.30, by + h * 0.06),
                    QPointF(bx + sgn * w * 0.02, by + h * 0.10)]
            p.drawPolygon(QPolygonF(wing))
        body = QRectF(0, 0, w * 0.26, h * 0.40)
        body.moveCenter(QPointF(bx, by))
        p.drawEllipse(body)
        p.setBrush(_BAT_EYE)
        p.drawEllipse(QPointF(bx, by - h * 0.09), w * 0.035, w * 0.035)
    elif kind == "clear":
        # clear/no symbol
        d = min(w, h) * 0.90
        ring = QRectF(0, 0, d, d)
        ring.moveCenter(QPointF(cx, cy))
        p.setPen(_pen(_ICON_RED, max(1.8, w * 0.13)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(ring)
        a, rr = math.radians(45), d / 2
        p.drawLine(QPointF(cx - math.cos(a) * rr, cy + math.sin(a) * rr),
                   QPointF(cx + math.cos(a) * rr, cy - math.sin(a) * rr))


def _paint_lamp_sprite(p, r, atlas):
    """Draw a tinted lantern sprite with a warm glow."""
    cx, cy = r.center().x(), r.center().y()
    w, h = r.width(), r.height()
    glow_r = min(w, h) * 0.52
    grad = QRadialGradient(QPointF(cx, cy), glow_r)
    grad.setColorAt(0.0, QColor(255, 150, 70, 165))
    grad.setColorAt(0.45, QColor(255, 100, 35, 80))
    grad.setColorAt(1.0, QColor(255, 70, 0, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(grad)
    p.drawEllipse(QPointF(cx, cy), glow_r, glow_r)
    sw, sh = atlas.source_size("base", "DangleFruit0A")
    s = min(w / sw, h / sh) * 0.58                                 # leave room for the glow
    dw, dh = sw * s, sh * s
    dst = QRectF(cx - dw / 2, cy - dh / 2, dw, dh)
    outline = atlas.sprite("base", "DangleFruit0A", _LAMP_OUTLINE)
    flesh = atlas.sprite("base", "DangleFruit0B", _LAMP_FLESH)
    p.save()                                                      # flip so the wide end points upward
    p.translate(cx, cy)
    p.scale(1.0, -1.0)
    local = QRectF(-dw / 2, -dh / 2, dw, dh)
    p.drawPixmap(local, outline, QRectF(outline.rect()))
    p.drawPixmap(local, flesh, QRectF(flesh.rect()))
    p.restore()


def _paint_fruit_sprite(p, r, atlas):
    """Draw a fruit sprite with a blue gradient fill."""
    sw, sh = atlas.source_size("base", "DangleFruit0A")
    s = min(r.width() / sw, r.height() / sh) * 0.8
    dw, dh = sw * s, sh * s
    dst = QRectF(r.center().x() - dw / 2, r.center().y() - dh / 2, dw, dh)
    outline = atlas.sprite("base", "DangleFruit0A", _FRUIT_OUTLINE)
    flesh = atlas.sprite("base", "DangleFruit0B")                  # white mask, colored by the gradient below
    ss = 4                                                          # supersample to reduce aliasing
    lw, lh = max(1, int(dw * ss)), max(1, int(dh * ss))
    layer = QPixmap(lw, lh)
    layer.fill(Qt.GlobalColor.transparent)
    lp = QPainter(layer)
    lp.drawPixmap(QRectF(0, 0, lw, lh), flesh, QRectF(flesh.rect()))
    lp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    g = QLinearGradient(QPointF(0, 0), QPointF(0, lh))
    g.setColorAt(0.0, _FRUIT_TOP)
    g.setColorAt(1.0, _FRUIT_BOT)
    lp.fillRect(layer.rect(), g)
    lp.end()
    p.drawPixmap(dst, outline, QRectF(outline.rect()))
    p.drawPixmap(dst, layer, QRectF(layer.rect()))


def _paint_slimemold_icon(p, r, atlas=None):
    """Draw an orange slime mold sprite, or vector fallback."""
    if atlas is not None and atlas.get("ui").has("Symbol_SlimeMold"):
        sw, sh = atlas.source_size("ui", "Symbol_SlimeMold")
        s = min(r.width() / sw, r.height() / sh) * 0.92
        dw, dh = sw * s, sh * s
        pm = atlas.sprite("ui", "Symbol_SlimeMold", _SLIME_BODY)
        p.drawPixmap(QRectF(r.center().x() - dw / 2, r.center().y() - dh / 2, dw, dh),
                     pm, QRectF(pm.rect()))
        return
    cx, cy = r.center().x(), r.center().y()
    w, h = r.width(), r.height()
    bx, by = cx, cy - h * 0.14
    glow_r = min(w, h) * 0.42
    grad = QRadialGradient(QPointF(bx, by), glow_r)
    grad.setColorAt(0.0, _SLIME_GLOW)
    grad.setColorAt(1.0, QColor(255, 150, 50, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(grad)
    p.drawEllipse(QPointF(bx, by), glow_r, glow_r)
    p.setPen(_pen(_SLIME_TENDRIL, max(1.6, w * 0.09)))
    for dx in (-0.22, -0.05, 0.12, 0.28):
        sx = bx + dx * w
        p.drawLine(QPointF(sx, by + h * 0.06),
                   QPointF(sx + dx * w * 0.25, by + h * 0.42))
    d = min(w, h) * 0.34
    bulb = QRectF(0, 0, d, d)
    bulb.moveCenter(QPointF(bx, by))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_SLIME_BODY)
    p.drawEllipse(bulb)


def _paint_fruit_fallback(p, r):
    """Vector fallback for fruit icons when the atlas is unavailable."""
    cx, cy = r.center().x(), r.center().y()
    w, h = r.width(), r.height()
    path = QPainterPath()
    path.moveTo(QPointF(cx, r.top()))
    path.cubicTo(QPointF(cx + w * 0.50, cy - h * 0.10),
                 QPointF(cx + w * 0.42, r.bottom()), QPointF(cx, r.bottom()))
    path.cubicTo(QPointF(cx - w * 0.42, r.bottom()),
                 QPointF(cx - w * 0.50, cy - h * 0.10), QPointF(cx, r.top()))
    g = QLinearGradient(QPointF(0, r.top()), QPointF(0, r.bottom()))
    g.setColorAt(0.0, _FRUIT_TOP)
    g.setColorAt(1.0, _FRUIT_BOT)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(g)
    p.drawPath(path)


def make_place_icon(kind, size, dpr, atlas=None):
    """Render an item icon to an offscreen QPixmap."""
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.fill(Qt.GlobalColor.transparent)
    pm.setDevicePixelRatio(dpr)
    r = QRectF(0, 0, size, size)
    r.adjust(size * 0.10, size * 0.10, -size * 0.10, -size * 0.10)
    p = QPainter(pm)
    _paint_place_icon(p, kind, r, atlas)
    p.end()
    return pm
