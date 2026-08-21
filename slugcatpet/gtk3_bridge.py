import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, GtkLayerShell, Gdk, GLib
import cairo

from PySide6.QtGui import QImage, QPainter, QColor, QMouseEvent, QCursor, QGuiApplication
from PySide6.QtCore import Qt, QPoint, QPointF, QEvent

FRAME_MS = 16
BODY_INPUT_RADIUS = 30
ITEM_INPUT_RADIUS = 15


class GTK3Bridge:
    def __init__(self, pet_window):
        self.pet = pet_window
        self.width = 0
        self.height = 0
        self.qimg = None
        self.buffer = None
        self.stride = 0
        self.cairo_surface = None
        
        self.gtk_win = Gtk.Window()
        self.gtk_win.set_title("Slugcat Pet")
        GtkLayerShell.init_for_window(self.gtk_win)
        GtkLayerShell.set_layer(self.gtk_win, GtkLayerShell.Layer.OVERLAY)

        GtkLayerShell.set_anchor(self.gtk_win, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self.gtk_win, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_anchor(self.gtk_win, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self.gtk_win, GtkLayerShell.Edge.RIGHT, True)
        self._sync_geometry(force=True)
        
        self.gtk_win.set_app_paintable(True)
        screen = self.gtk_win.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.gtk_win.set_visual(visual)
            
        css = Gtk.CssProvider()
        css.load_from_data(b"window { background-color: rgba(0,0,0,0); }")
        self.gtk_win.get_style_context().add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        self.gtk_win.connect("draw", self.on_draw)
        self.gtk_win.add_events(Gdk.EventMask.POINTER_MOTION_MASK | 
                                Gdk.EventMask.BUTTON_PRESS_MASK | 
                                Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.gtk_win.connect("button-press-event", self.on_mouse_press)
        self.gtk_win.connect("button-release-event", self.on_mouse_release)
        self.gtk_win.connect("motion-notify-event", self.on_mouse_motion)
        
        self.last_global_pos = QPoint(0, 0)
        self.original_cursor_pos = QCursor.pos
        self.original_update = self.pet.update
        QCursor.pos = self.mock_cursor_pos
        
        # Override update to prevent QWidget from repainting itself natively
        self.pet.update = self.queue_render
        
        self._render_source = GLib.timeout_add(FRAME_MS, self.render_frame)
        self.gtk_win.show_all()

    def close(self):
        if self._render_source is not None:
            GLib.source_remove(self._render_source)
            self._render_source = None
        QCursor.pos = self.original_cursor_pos
        self.pet.update = self.original_update
        if hasattr(self.pet, "_cursor_logical_override"):
            delattr(self.pet, "_cursor_logical_override")
        self.gtk_win.hide()

    def _reset_surface(self, width, height):
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        self.qimg = QImage(self.width, self.height, QImage.Format_ARGB32_Premultiplied)
        self.buffer = self.qimg.bits()
        self.stride = self.qimg.bytesPerLine()
        self.cairo_surface = cairo.ImageSurface.create_for_data(
            self.buffer, cairo.FORMAT_ARGB32, self.width, self.height, self.stride
        )

    def _sync_geometry(self, force=False):
        width = self.pet.width()
        height = self.pet.height()
        if force or width != self.width or height != self.height:
            self._reset_surface(width, height)

        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.geometry()
        margin_top = self.pet.y() - geo.y()
        margin_left = self.pet.x() - geo.x()
        margin_bottom = geo.height() - margin_top - self.height
        margin_right = geo.width() - margin_left - self.width

        GtkLayerShell.set_margin(self.gtk_win, GtkLayerShell.Edge.TOP, margin_top)
        GtkLayerShell.set_margin(self.gtk_win, GtkLayerShell.Edge.BOTTOM, margin_bottom)
        GtkLayerShell.set_margin(self.gtk_win, GtkLayerShell.Edge.LEFT, margin_left)
        GtkLayerShell.set_margin(self.gtk_win, GtkLayerShell.Edge.RIGHT, margin_right)
        
    def mock_cursor_pos(self):
        return self.last_global_pos

    def _event_global_pos(self, e):
        x = getattr(e, "x_root", None)
        y = getattr(e, "y_root", None)
        if x is None or y is None:
            x = self.pet.x() + getattr(e, "x", 0)
            y = self.pet.y() + getattr(e, "y", 0)
        return QPoint(int(x), int(y))

    def _sync_cursor_from_event(self, e):
        self.last_global_pos = self._event_global_pos(e)
        self.pet._cursor_logical_override = self.pet.to_logical(e.x, e.y)
        
    def queue_render(self, *args, **kwargs):
        return None

    @staticmethod
    def _qt_button(button):
        if button == 1:
            return Qt.MouseButton.LeftButton
        if button == 3:
            return Qt.MouseButton.RightButton
        return Qt.MouseButton.NoButton

    def _mouse_event(self, event_type, e):
        button = self._qt_button(e.button)
        return QMouseEvent(event_type, QPointF(e.x, e.y), button, button,
                           Qt.KeyboardModifier.NoModifier)

    def on_mouse_press(self, w, e):
        self._sync_cursor_from_event(e)
        self.pet.mousePressEvent(self._mouse_event(QEvent.Type.MouseButtonPress, e))
        return False
        
    def on_mouse_release(self, w, e):
        self._sync_cursor_from_event(e)
        self.pet.mouseReleaseEvent(self._mouse_event(QEvent.Type.MouseButtonRelease, e))
        return False
        
    def on_mouse_motion(self, w, e):
        self._sync_cursor_from_event(e)
        return False

    @staticmethod
    def _union_rect(region, x, y, radius):
        rect = cairo.RectangleInt(int(x - radius), int(y - radius),
                                  int(radius * 2), int(radius * 2))
        region.union(cairo.Region(rect))

    def _item_iter(self):
        for name in ("fruits", "stones", "slimemolds", "batflies"):
            yield from getattr(self.pet, name, [])
        
    def update_region(self):
        region = cairo.Region()
        
        if self.pet._place_mode:
            rect = cairo.RectangleInt(0, 0, self.width, self.height)
            region.union(cairo.Region(rect))
        else:
            scale = self.pet._scale
            for pet in self.pet.pets:
                x = pet.body.chunk0.x * scale
                y = pet.body.chunk0.y * scale
                self._union_rect(region, x, y, BODY_INPUT_RADIUS * scale)

            for item in self._item_iter():
                x = item.x * scale
                y = item.y * scale
                self._union_rect(region, x, y, ITEM_INPUT_RADIUS * scale)
                
        self.gtk_win.input_shape_combine_region(region)

    def render_frame(self):
        self._sync_geometry()
        self.update_region()
        self.qimg.fill(QColor(0, 0, 0, 0))
        
        p = QPainter(self.qimg)
        self.pet.customPaint(p)
        
        self.gtk_win.queue_draw()
        return True

    def on_draw(self, widget, cr):
        cr.set_source_surface(self.cairo_surface, 0, 0)
        cr.paint()
        return False
