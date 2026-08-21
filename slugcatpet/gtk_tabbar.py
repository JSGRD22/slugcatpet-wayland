"""使用GTK layer-shell制作的侧边 Tab：收起态可拖动箭头，展开态图标盘+动作列。"""
from __future__ import annotations

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, GtkLayerShell
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QGuiApplication

from .i18n import t
from .ui.tabbar import COLLAPSED_H, COLLAPSED_W, EXPANDED_H, EXPANDED_W, _make_place_icon

_CSS = b"""
window, .slugcat-root {
    background-color: transparent;
}
.slugcat-panel {
    background-color: rgba(30,34,40,0.92);
    border-radius: 0;
    padding: 6px;
}
.slugcat-arrow {
    color: #cfe8b8;
    background-color: rgba(40,46,40,0.70);
    border: 0;
    border-top-left-radius: 8px;
    border-bottom-left-radius: 8px;
    font-size: 18px;
}
.slugcat-arrow:hover {
    background-color: rgba(60,72,55,1.0);
}
.slugcat-button {
    color: #e8f5d8;
    background-color: rgba(60,70,55,1.0);
    border: 1px solid #4a5a3a;
    border-radius: 5px;
    min-height: 28px;
    padding: 4px 8px;
    font-size: 12px;
}
.slugcat-button:hover {
    background-color: rgba(80,100,70,1.0);
}
.slugcat-toast {
    color: #ffffff;
    background-color: rgba(20,22,26,0.92);
    border-radius: 6px;
    padding: 5px 9px;
    font-size: 12px;
}
"""


def _place_pixbuf(kind, size, atlas):
    """Render the existing Qt tabbar icon into a GTK pixbuf."""
    qpix = _make_place_icon(kind, size, 1.0, atlas)
    data = QByteArray()
    buf = QBuffer(data)
    if not buf.open(QIODevice.OpenModeFlag.WriteOnly):
        return None
    try:
        if not qpix.save(buf, "PNG"):
            return None
    finally:
        buf.close()

    loader = GdkPixbuf.PixbufLoader.new_with_type("png")
    try:
        loader.write(bytes(data))
        loader.close()
    except Exception:
        try:
            loader.close()
        except Exception:
            pass
        return None
    return loader.get_pixbuf()


class GtkLayerTabBar:
    def __init__(self, pet, app, params=None):
        self.pet = pet
        self.app = app
        self.params = params or {}
        self.expanded = bool(self.params.get("tab_expanded", False))
        self._visible = False
        self._dragging = False
        self._moved = False
        self._toast_source = None
        self._last_margin_top = None
        self._root = None
        self._content = None

        screen = QGuiApplication.primaryScreen().availableGeometry()
        self._screen_y = screen.y()
        self._screen_h = screen.height()
        default_y = screen.y() + (screen.height() - EXPANDED_H) // 2
        self._y = int(self.params.get("tab_y", default_y))

        self.gtk_win = Gtk.Window()
        self.gtk_win.set_title("slugcatpet-tabbar")
        self.gtk_win.set_app_paintable(True)
        self.gtk_win.set_decorated(False)
        self.gtk_win.connect("delete-event", self._on_delete)
        self._init_layer_window(self.gtk_win, full_height=True)

        provider = Gtk.CssProvider()
        provider.load_from_data(_CSS)
        Gtk.StyleContext.add_provider_for_screen(
            self.gtk_win.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self._toast_win = Gtk.Window()
        self._toast_win.set_title("slugcatpet-tabbar-toast")
        self._toast_win.set_decorated(False)
        self._toast_win.set_app_paintable(True)
        self._init_layer_window(self._toast_win, layer=GtkLayerShell.Layer.OVERLAY)
        self._toast_label = Gtk.Label()
        self._toast_label.get_style_context().add_class("slugcat-toast")
        self._toast_win.add(self._toast_label)

        self._rebuild()

    def _init_layer_window(self, win, layer=GtkLayerShell.Layer.TOP, full_height=False):
        GtkLayerShell.init_for_window(win)
        try:
            GtkLayerShell.set_namespace(win, "slugcatpet-tabbar")
        except Exception:
            pass
        GtkLayerShell.set_layer(win, layer)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.LEFT, False)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.BOTTOM, full_height)
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.TOP, 0)
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.BOTTOM, 0)
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.RIGHT, 0)

    def _top_margin(self, refresh=True):
        if refresh:
            self._refresh_screen()
        height = self._height()
        low = self._screen_y
        high = self._screen_y + max(0, self._screen_h - height)
        self._y = max(low, min(high, int(self._y)))
        return max(0, self._y - self._screen_y)

    def _refresh_screen(self):
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self._screen_y = area.y()
        self._screen_h = area.height()

    def _width(self):
        base = EXPANDED_W if self.expanded else COLLAPSED_W
        if self._content is None:
            return base
        try:
            _minimum, natural = self._content.get_preferred_width()
        except Exception:
            return base
        return max(base, int(natural))

    def _height(self):
        return EXPANDED_H if self.expanded else COLLAPSED_H

    def _surface_width(self):
        width = self._width()
        try:
            allocated = self.gtk_win.get_allocated_width()
        except Exception:
            allocated = 0
        return max(width, int(allocated)) if allocated > 1 else width

    def _content_x(self):
        return max(0, self._surface_width() - self._width())

    def _sync_layer(self):
        self._refresh_screen()
        try:
            GtkLayerShell.set_exclusive_zone(self.gtk_win, 0)
        except Exception:
            pass
        self.gtk_win.set_default_size(self._width(), self._screen_h)
        if self._root is not None:
            self._root.set_size_request(self._width(), self._screen_h)
        self._sync_position(refresh=False)

    def _sync_position(self, refresh=True):
        margin = self._top_margin(refresh=refresh)
        self._last_margin_top = margin
        if self._root is not None and self._content is not None:
            self._root.move(self._content, self._content_x(), margin)
        self._sync_input_shape(margin)

    def _sync_input_shape(self, margin=None):
        if margin is None:
            margin = self._top_margin(refresh=False)
        region = cairo.Region()
        if self._visible:
            rect = cairo.RectangleInt(self._content_x(), int(margin), self._width(), self._height())
            region.union(cairo.Region(rect))
        try:
            self.gtk_win.input_shape_combine_region(region)
        except Exception:
            pass

    def _sync_after_allocate(self):
        self._sync_layer()
        return False

    def _rebuild(self):
        child = self.gtk_win.get_child()
        if child is not None:
            self.gtk_win.remove(child)
        self._root = Gtk.Fixed()
        self._root.get_style_context().add_class("slugcat-root")
        self._content = self._expanded_widget() if self.expanded else self._collapsed_widget()
        self._root.put(self._content, 0, self._top_margin())
        self.gtk_win.add(self._root)
        self._sync_layer()
        if self._visible:
            self.gtk_win.show_all()
            self._sync_position(refresh=False)
            GLib.idle_add(self._sync_after_allocate)

    def _collapsed_widget(self):
        event = Gtk.EventBox()
        event.get_style_context().add_class("slugcat-root")
        event.set_size_request(COLLAPSED_W, COLLAPSED_H)
        event.add_events(Gdk.EventMask.BUTTON_PRESS_MASK
                         | Gdk.EventMask.BUTTON_RELEASE_MASK
                         | Gdk.EventMask.POINTER_MOTION_MASK)
        event.connect("button-press-event", self._on_arrow_press)
        event.connect("motion-notify-event", self._on_arrow_motion)
        event.connect("button-release-event", self._on_arrow_release)
        label = Gtk.Label(label="\u2039")
        label.get_style_context().add_class("slugcat-arrow")
        event.add(label)
        return event

    def _expanded_widget(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        arrow = Gtk.Button(label="\u203a")
        arrow.get_style_context().add_class("slugcat-arrow")
        arrow.set_size_request(16, EXPANDED_H)
        arrow.connect("clicked", lambda _btn: self.toggle())
        outer.pack_start(arrow, False, False, 0)

        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        panel.get_style_context().add_class("slugcat-panel")
        outer.pack_start(panel, True, True, 0)

        grid = Gtk.Grid()
        grid.set_row_spacing(4)
        grid.set_column_spacing(4)
        panel.pack_start(grid, False, False, 0)
        atlas = getattr(self.pet, "atlas", None)
        place_items = [
            ("vpole", t("tip_vpole"), self._place_vpole),
            ("hpole", t("tip_hpole"), self._place_hpole),
            ("fruit", t("tip_fruit"), self._place_fruit),
            ("stone", t("tip_stone"), self._place_stone),
            ("lamp", t("tip_lamp"), self._place_lamp),
            ("slimemold", t("tip_slimemold"), self._place_slimemold),
            ("batfly", t("tip_batfly"), self._place_batfly),
            ("clear", t("tip_clear"), self._clear_all),
        ]
        for i, (kind, tip, cb) in enumerate(place_items):
            btn = self._icon_button(kind, tip, cb, atlas)
            btn.set_size_request(30, 32)
            grid.attach(btn, i % 3, i // 3, 1, 1)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        panel.pack_start(sep, False, False, 2)
        panel.pack_start(self._button(t("btn_open_settings"), None, self._open_settings),
                         False, False, 0)
        panel.pack_start(self._button(t("btn_quit_app"), None, self._quit), False, False, 0)
        return outer

    def _button(self, label, tip, callback):
        btn = Gtk.Button(label=label)
        btn.get_style_context().add_class("slugcat-button")
        if tip:
            btn.set_tooltip_text(tip)
        btn.connect("clicked", lambda _btn: callback())
        return btn

    def _icon_button(self, kind, tip, callback, atlas):
        btn = self._button("", tip, callback)
        pixbuf = _place_pixbuf(kind, 22, atlas)
        if pixbuf is not None:
            btn.set_image(Gtk.Image.new_from_pixbuf(pixbuf))
            btn.set_always_show_image(True)
        else:
            btn.set_label(kind[:1].upper())
        return btn

    def show(self):
        self._visible = True
        self._sync_layer()
        self.gtk_win.show_all()
        GLib.idle_add(self._sync_after_allocate)

    def hide(self):
        self._visible = False
        self._sync_layer()
        self.gtk_win.hide()
        self._toast_win.hide()

    def isVisible(self):
        return bool(self._visible and self.gtk_win.get_visible())

    def winId(self):
        return 0

    def toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.expanded = True
            self.show()
            self._rebuild()

    def toggle(self):
        self.expanded = not self.expanded
        self._rebuild()

    def _on_delete(self, *_args):
        self.hide()
        return True

    def _on_arrow_press(self, _widget, event):
        if event.button != 1:
            return False
        self._dragging = True
        self._moved = False
        self._drag_accum = 0.0
        self._drag_start_y = self._y
        self._drag_start_root = self._event_surface_y(event)
        return True

    def _on_arrow_motion(self, _widget, event):
        if not self._dragging:
            return False
        dy = self._event_surface_y(event) - self._drag_start_root
        if abs(dy) < 0.5:
            return True
        self._drag_accum = max(self._drag_accum, abs(dy))
        if self._drag_accum > 2.0:
            self._moved = True
        self._y = int(round(self._drag_start_y + dy))
        self.params["tab_y"] = self._y
        self._sync_position(refresh=False)
        return True

    def _event_surface_y(self, event):
        margin = self._last_margin_top
        if margin is None:
            margin = self._top_margin(refresh=False)
        return float(margin) + float(event.y)

    def _on_arrow_release(self, _widget, event):
        if event.button != 1 or not self._dragging:
            return False
        moved = self._moved
        self._dragging = False
        self._moved = False
        if not moved:
            self.toggle()
        return True

    def _toast(self, msg):
        self._toast_label.set_text(msg)
        self._toast_label.show()
        width = self._width()
        GtkLayerShell.set_margin(self._toast_win, GtkLayerShell.Edge.TOP, self._top_margin() + 10)
        GtkLayerShell.set_margin(self._toast_win, GtkLayerShell.Edge.RIGHT, width + 8)
        self._toast_win.show_all()
        if self._toast_source is not None:
            GLib.source_remove(self._toast_source)
        self._toast_source = GLib.timeout_add(1600, self._hide_toast)

    def _hide_toast(self):
        self._toast_win.hide()
        self._toast_source = None
        return False

    def _collapse(self):
        if self.expanded:
            self.toggle()

    def _place_fruit(self):
        if self.pet.can_place_fruit():
            self.pet.enter_place_fruit_mode()
            self._collapse()
        else:
            self._toast(t("toast_max_fruit"))

    def _place_stone(self):
        if self.pet.can_place_stone():
            self.pet.enter_place_stone_mode()
            self._collapse()
        else:
            self._toast(t("toast_max_stone"))

    def _place_lamp(self):
        self.pet.enter_place_lamp_mode()
        self._collapse()

    def _place_slimemold(self):
        if self.pet.can_place_slimemold():
            self.pet.enter_place_slimemold_mode()
            self._collapse()
        else:
            self._toast(t("toast_max_slimemold"))

    def _place_batfly(self):
        if self.pet.can_place_batfly():
            self.pet.enter_place_batfly_mode()
            self._collapse()
        else:
            self._toast(t("toast_max_batfly"))

    def _place_vpole(self):
        if self.pet.can_place_pole("vertical"):
            self.pet.enter_place_vpole_mode()
            self._collapse()
        else:
            self._toast(t("toast_max_vpole"))

    def _place_hpole(self):
        if self.pet.can_place_pole("horizontal"):
            self.pet.enter_place_hpole_mode()
            self._collapse()
        else:
            self._toast(t("toast_max_hpole"))

    def _clear_all(self):
        if (self.pet.fruits or self.pet.stones or self.pet.slimemolds
                or self.pet.batflies or self.pet.poles or self.pet.lamp is not None):
            self.pet.clear_all_items()
        else:
            self._toast(t("toast_no_object"))

    def _open_settings(self):
        self.pet.open_settings()

    def _quit(self):
        try:
            from .platform.cursorfx import abort_all
            abort_all()
        except Exception:
            pass
        self.app.quit()
