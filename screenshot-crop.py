#!/usr/bin/env python3
"""
Screenshot with Post-Capture Crop - Captures screen after delay, then lets you crop
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
import os
import sys
import json
from datetime import datetime

class ScreenshotCropTool(Gtk.Window):
    def __init__(self):
        super().__init__(title="Screenshot Tool")
        self.set_default_size(500, 320)
        self.set_border_width(15)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        
        self.countdown_active = False
        self.remaining_seconds = 0
        self.captured_pixbuf = None
        self.selected_monitor = None
        self.monitor_geometries = []
        self.updating_combo = False  # Flag to prevent recursion
        
        # Load config for persistent storage
        self.config_file = os.path.expanduser("~/.config/screenshot-crop/config.json")
        self.load_config()
        self.save_folder = self.config.get('last_folder', os.path.expanduser("~/Pictures"))
        
        # Main container
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup("<b><big>Screenshot with Crop</big></b>")
        vbox.pack_start(title_label, False, False, 0)
        
        # Separator
        vbox.pack_start(Gtk.Separator(), False, False, 0)
        
        # Info label
        info_label = Gtk.Label()
        info_label.set_markup(
            "<i>Captures all monitors after delay,\n"
            "then lets you select the area to keep</i>"
        )
        vbox.pack_start(info_label, False, False, 0)
        
        # Capture options frame
        options_frame = Gtk.Frame(label="Capture Options")
        options_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        options_vbox.set_border_width(10)
        options_frame.add(options_vbox)
        vbox.pack_start(options_frame, False, False, 0)
        
        # Monitor selection
        monitor_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        monitor_label = Gtk.Label(label="Select Monitor:")
        monitor_box.pack_start(monitor_label, False, False, 0)
        
        self.monitor_combo = Gtk.ComboBoxText()
        self.populate_monitor_list()
        self.monitor_combo.set_active(0)  # Select first monitor by default
        monitor_box.pack_start(self.monitor_combo, True, True, 0)
        
        # Identify button
        identify_button = Gtk.Button(label="Identify")
        identify_button.connect("clicked", self.identify_monitors)
        monitor_box.pack_start(identify_button, False, False, 0)
        
        options_vbox.pack_start(monitor_box, False, False, 0)
        
        # Delay setting
        delay_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        delay_label = Gtk.Label(label="Delay before capture (seconds):")
        delay_box.pack_start(delay_label, False, False, 0)
        
        self.delay_adjustment = Gtk.Adjustment(value=3, lower=0, upper=10, step_increment=1)
        self.delay_spin = Gtk.SpinButton(adjustment=self.delay_adjustment, climb_rate=1, digits=0)
        self.delay_spin.set_value(3)  # Default 3 seconds
        delay_box.pack_start(self.delay_spin, False, False, 0)
        
        options_vbox.pack_start(delay_box, False, False, 0)
        
        # Folder selection with recent folders dropdown
        folder_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        folder_label = Gtk.Label(label="Save to:")
        folder_box.pack_start(folder_label, False, False, 0)
        
        # ComboBox for recent folders
        self.folder_combo = Gtk.ComboBoxText.new_with_entry()
        self.folder_entry = self.folder_combo.get_child()
        self.update_folder_combo()
        self.folder_combo.connect("changed", self.on_folder_combo_changed)
        folder_box.pack_start(self.folder_combo, True, True, 0)
        
        browse_button = Gtk.Button(label="Browse...")
        browse_button.connect("clicked", self.on_browse_folder)
        folder_box.pack_start(browse_button, False, False, 0)
        
        options_vbox.pack_start(folder_box, False, False, 0)
        
        # Help text
        help_label = Gtk.Label()
        help_label.set_markup(
            f"<small>1. Select monitor to capture\n"
            f"2. Set delay and click capture\n"
            f"3. Open menus/dialogs during countdown\n"
            f"4. After capture, select area to save</small>"
        )
        options_vbox.pack_start(help_label, False, False, 0)
        
        # Countdown display
        self.countdown_label = Gtk.Label(label="")
        vbox.pack_start(self.countdown_label, False, False, 5)
        
        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_margin_top(10)
        vbox.pack_end(button_box, False, False, 0)
        
        # Help button
        help_button = Gtk.Button(label="Help")
        help_button.connect("clicked", self.show_help)
        button_box.pack_start(help_button, False, False, 0)
        
        # Cancel button
        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.connect("clicked", self.on_cancel)
        button_box.pack_start(self.cancel_button, True, True, 0)
        
        # Capture button
        self.capture_button = Gtk.Button(label="Capture Screen")
        self.capture_button.get_style_context().add_class("suggested-action")
        self.capture_button.connect("clicked", self.on_capture)
        button_box.pack_start(self.capture_button, True, True, 0)
        
        # Connect destroy signal
        self.connect("destroy", self.on_destroy)
    
    def load_config(self):
        """Load configuration from file"""
        self.config = {
            'last_folder': os.path.expanduser("~/Pictures"),
            'recent_folders': []
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                    # Validate folders still exist
                    self.config['recent_folders'] = [
                        f for f in self.config['recent_folders'] 
                        if os.path.exists(f)
                    ][:10]  # Keep max 10 recent folders
        except Exception as e:
            print(f"Could not load config: {e}")
    
    def save_config(self):
        """Save configuration to file"""
        try:
            # Validate config before saving
            if not isinstance(self.config.get('recent_folders'), list):
                self.config['recent_folders'] = []
            
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except RecursionError:
            print("Recursion error while saving config - skipping save")
        except Exception as e:
            print(f"Could not save config: {e}")
    
    def add_recent_folder(self, folder):
        """Add folder to recent folders list"""
        if folder in self.config['recent_folders']:
            self.config['recent_folders'].remove(folder)
        self.config['recent_folders'].insert(0, folder)
        self.config['recent_folders'] = self.config['recent_folders'][:10]
        self.config['last_folder'] = folder
        self.save_config()
        self.update_folder_combo()
    
    def update_folder_combo(self):
        """Update the folder combo box with recent folders"""
        self.updating_combo = True  # Set flag to prevent recursion
        
        self.folder_combo.remove_all()
        
        # Add current folder first
        self.folder_combo.append_text(self.save_folder)
        
        # Add recent folders
        for folder in self.config['recent_folders']:
            if folder != self.save_folder:
                # Show shortened path for display
                display_path = folder.replace(os.path.expanduser("~"), "~")
                self.folder_combo.append_text(folder)
        
        self.folder_combo.set_active(0)
        self.updating_combo = False  # Clear flag
    
    def on_folder_combo_changed(self, combo):
        """Handle folder selection from dropdown"""
        if self.updating_combo:  # Skip if we're updating the combo
            return
            
        text = combo.get_active_text()
        if text and os.path.exists(os.path.expanduser(text)):
            self.save_folder = os.path.expanduser(text)
            self.add_recent_folder(self.save_folder)
    
    def on_destroy(self, widget):
        """Save config before closing"""
        self.save_config()
        Gtk.main_quit()
    
    def show_help(self, widget):
        """Show help/about dialog"""
        dialog = Gtk.AboutDialog()
        dialog.set_transient_for(self)
        dialog.set_program_name("Screenshot Crop Tool")
        dialog.set_version("1.0.1")
        dialog.set_copyright("© 2024 Screenshot Crop Tool Contributors")
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_website("https://github.com/rjeffmyers/screenshot-crop")
        dialog.set_website_label("GitHub Repository")
        dialog.set_comments("A powerful screenshot tool for Linux with monitor selection,\ncropping capabilities, and project folder management.")
        
        dialog.set_authors(["Screenshot Crop Tool Contributors"])
        
        # Add keyboard shortcuts info
        dialog.set_wrap_license(True)
        
        # Custom secondary text with usage info
        usage_text = """
Keyboard Shortcuts:
• Enter - Save selected area
• Escape - Cancel crop operation  
• Ctrl+S - Save full capture without cropping
• Escape (3x) - Force close if unresponsive

Tips:
• Use delay to capture menus and tooltips
• Set project folder for batch screenshots
• Click "Continue" after save for rapid workflow
        """
        
        # Create a custom content area for additional info
        content_area = dialog.get_content_area()
        
        expander = Gtk.Expander(label="Usage Tips & Shortcuts")
        expander_label = Gtk.Label(label=usage_text)
        expander_label.set_alignment(0, 0)
        expander.add(expander_label)
        content_area.pack_end(expander, False, False, 10)
        
        dialog.show_all()
        dialog.run()
        dialog.destroy()
    
    def on_browse_folder(self, widget):
        """Open folder selection dialog"""
        dialog = Gtk.FileChooserDialog(
            title="Select Screenshot Folder",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        dialog.set_current_folder(self.save_folder)
        dialog.set_create_folders(True)  # Allow creating folders
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_folder = dialog.get_filename()
            if new_folder and os.path.exists(new_folder):
                self.save_folder = new_folder
                self.updating_combo = True  # Prevent recursion
                self.folder_entry.set_text(self.save_folder)
                self.updating_combo = False
                self.add_recent_folder(self.save_folder)
        
        dialog.destroy()
    
    def populate_monitor_list(self):
        """Populate the monitor dropdown with available monitors"""
        self.monitor_combo.remove_all()
        self.monitor_geometries = []
        
        display = Gdk.Display.get_default()
        n_monitors = display.get_n_monitors()
        
        for i in range(n_monitors):
            monitor = display.get_monitor(i)
            geometry = monitor.get_geometry()
            is_primary = display.get_primary_monitor() == monitor
            model = monitor.get_model() or f"Display {i+1}"
            
            # Store geometry for later use
            self.monitor_geometries.append({
                'index': i,
                'geometry': geometry,
                'monitor': monitor
            })
            
            # Add to combo box
            label = f"Monitor {i+1}: {model} ({geometry.width}x{geometry.height})"
            if is_primary:
                label += " [Primary]"
            self.monitor_combo.append_text(label)
            
    
    def identify_monitors(self, widget):
        """Show monitor identification numbers on each screen"""
        display = Gdk.Display.get_default()
        n_monitors = display.get_n_monitors()
        
        identify_windows = []
        
        for i in range(n_monitors):
            monitor = display.get_monitor(i)
            geometry = monitor.get_geometry()
            
            # Create a window for this monitor
            identify_win = Gtk.Window(type=Gtk.WindowType.POPUP)
            identify_win.set_decorated(False)
            identify_win.set_skip_taskbar_hint(True)
            identify_win.set_keep_above(True)
            identify_win.set_app_paintable(True)
            
            # Set window size and position
            window_size = 300
            x = geometry.x + (geometry.width - window_size) // 2
            y = geometry.y + (geometry.height - window_size) // 2
            
            identify_win.move(x, y)
            identify_win.set_default_size(window_size, window_size)
            
            # Create container with background
            frame = Gtk.Frame()
            frame.set_shadow_type(Gtk.ShadowType.NONE)
            
            # Create event box for background color
            event_box = Gtk.EventBox()
            event_box.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(0.1, 0.1, 0.1, 0.9))
            
            # Create label with large text
            label = Gtk.Label()
            label.set_markup(f'<span font="120" color="white"><b>{i + 1}</b></span>')
            label.set_margin_top(50)
            label.set_margin_bottom(50)
            label.set_margin_left(50)
            label.set_margin_right(50)
            
            # Add secondary info
            model = monitor.get_model() or f"Display {i+1}"
            is_primary = display.get_primary_monitor() == monitor
            
            info_label = Gtk.Label()
            info_text = f'<span font="16" color="white">{model}\n{geometry.width}x{geometry.height}'
            if is_primary:
                info_text += '\n<b>PRIMARY</b>'
            info_text += '</span>'
            info_label.set_markup(info_text)
            
            # Pack everything
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            vbox.pack_start(label, True, False, 0)
            vbox.pack_start(info_label, False, False, 0)
            
            event_box.add(vbox)
            frame.add(event_box)
            identify_win.add(frame)
            
            identify_win.show_all()
            identify_windows.append(identify_win)
        
        # Auto-close after 2 seconds
        GLib.timeout_add_seconds(2, lambda: self.close_identify_windows(identify_windows))
    
    def close_identify_windows(self, windows):
        """Close all identify windows"""
        for window in windows:
            window.destroy()
        return False
    
    def on_cancel(self, widget):
        if self.countdown_active:
            self.countdown_active = False
            self.reset_ui()
        else:
            self.destroy()
    
    def reset_ui(self):
        """Reset UI after canceling countdown"""
        self.countdown_label.set_markup("")
        self.capture_button.set_sensitive(True)
        self.delay_spin.set_sensitive(True)
        self.cancel_button.set_label("Cancel")
        
    def on_capture(self, widget):
        """Handle capture button click"""
        delay = int(self.delay_spin.get_value())
        
        # Get selected monitor
        selected_index = self.monitor_combo.get_active()
        if selected_index >= 0 and selected_index < len(self.monitor_geometries):
            self.selected_monitor = self.monitor_geometries[selected_index]
        else:
            self.show_error("Please select a monitor")
            return
        
        # Disable controls during countdown
        self.capture_button.set_sensitive(False)
        self.delay_spin.set_sensitive(False)
        self.cancel_button.set_label("Stop")
        
        if delay > 0:
            self.countdown_active = True
            self.remaining_seconds = delay
            self.update_countdown()
        else:
            self.hide()
            while Gtk.events_pending():
                Gtk.main_iteration()
            GLib.timeout_add(200, self.capture_full_screen)
    
    def update_countdown(self):
        """Update countdown display"""
        if not self.countdown_active:
            self.reset_ui()
            return False
            
        if self.remaining_seconds > 0:
            self.countdown_label.set_markup(
                f"<big><b>Capturing in {self.remaining_seconds} seconds...</b></big>\n"
                f"<i>Prepare your screen now!</i>"
            )
            self.remaining_seconds -= 1
            GLib.timeout_add_seconds(1, self.update_countdown)
        else:
            self.countdown_label.set_markup("<big><b>Capturing...</b></big>")
            self.countdown_active = False
            
            # Hide window and capture
            self.hide()
            while Gtk.events_pending():
                Gtk.main_iteration()
            
            # Small delay to ensure window is hidden
            GLib.timeout_add(200, self.capture_full_screen)
        
        return False
    
    def capture_full_screen(self):
        """Capture the selected monitor"""
        try:
            if not self.selected_monitor:
                self.show_error("No monitor selected")
                return False
            
            screen = Gdk.Screen.get_default()
            root_window = screen.get_root_window()
            
            # Get the selected monitor's geometry
            geometry = self.selected_monitor['geometry']
            x = geometry.x
            y = geometry.y
            width = geometry.width
            height = geometry.height
            
            
            # Capture just this monitor
            self.captured_pixbuf = Gdk.pixbuf_get_from_window(
                root_window,
                x, y,
                width, height
            )
            
            if self.captured_pixbuf:
                # Show crop interface
                self.show_crop_interface()
            else:
                self.show_error("Failed to capture screen")
                
        except Exception as e:
            self.show_error(f"Error capturing screen: {str(e)}")
            
        return False
    
    def show_crop_interface(self):
        """Show interface to crop the captured screenshot on the selected monitor"""
        # Create overlay window
        crop_window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        crop_window.set_decorated(False)
        crop_window.set_skip_taskbar_hint(True)
        crop_window.set_keep_above(True)
        crop_window.set_app_paintable(True)
        
        # Get the selected monitor's geometry
        geometry = self.selected_monitor['geometry']
        mon_x = geometry.x
        mon_y = geometry.y
        mon_width = geometry.width
        mon_height = geometry.height
        
        
        # Position window on the selected monitor
        crop_window.move(mon_x, mon_y)
        crop_window.set_default_size(mon_width, mon_height)
        
        # Use the captured pixbuf dimensions (same as monitor)
        screen_width = self.captured_pixbuf.get_width()
        screen_height = self.captured_pixbuf.get_height()
        
        # Make window handle transparency
        screen = Gdk.Screen.get_default()
        visual = screen.get_rgba_visual()
        if visual:
            crop_window.set_visual(visual)
        
        # Selection state
        selection = {"start": None, "end": None, "dragging": False}
        
        # Track escape key presses for failsafe
        escape_count = {"count": 0, "last_time": 0}
        
        def on_draw(widget, cr):
            # Draw the captured screenshot
            Gdk.cairo_set_source_pixbuf(cr, self.captured_pixbuf, 0, 0)
            cr.paint()
            
            # Darken overlay
            cr.set_source_rgba(0, 0, 0, 0.3)
            cr.paint()
            
            # Draw selection area if we have valid coordinates
            if selection["start"] and selection["end"]:
                x = min(selection["start"][0], selection["end"][0])
                y = min(selection["start"][1], selection["end"][1])
                w = abs(selection["end"][0] - selection["start"][0])
                h = abs(selection["end"][1] - selection["start"][1])
                
                # Only process if we have a valid selection area
                if w > 1 and h > 1:
                    # Clear the darkening in selected area
                    cr.save()
                    cr.rectangle(x, y, w, h)
                    cr.clip()
                    
                    # Redraw just the selected portion from pixbuf
                    Gdk.cairo_set_source_pixbuf(cr, self.captured_pixbuf, 0, 0)
                    cr.paint()
                    cr.restore()
                    
                    # Draw selection border
                    cr.set_source_rgba(0, 0.5, 1, 1)
                    cr.set_line_width(2)
                    cr.rectangle(x, y, w, h)
                    cr.stroke()
                    
                    # Draw dimensions and help text
                    if w > 100 and h > 60:
                        cr.set_source_rgba(1, 1, 1, 1)
                        cr.select_font_face("Sans", 0, 0)
                        cr.set_font_size(14)
                        
                        # Draw background box for text
                        cr.set_source_rgba(0, 0, 0, 0.7)
                        cr.rectangle(x + 2, y + 2, 150, 60)
                        cr.fill()
                        
                        # Draw text
                        cr.set_source_rgba(1, 1, 1, 1)
                        cr.set_font_size(14)
                        dim_text = f"{int(w)} × {int(h)}"
                        cr.move_to(x + 8, y + 20)
                        cr.show_text(dim_text)
                        
                        cr.set_font_size(12)
                        cr.move_to(x + 8, y + 40)
                        cr.show_text("Enter: Save")
                        cr.move_to(x + 8, y + 55)
                        cr.show_text("Escape: Cancel")
            else:
                # Show instructions centered on the monitor
                text_x = screen_width / 2
                
                cr.set_source_rgba(1, 1, 1, 0.9)
                cr.select_font_face("Sans", 0, 1)
                cr.set_font_size(24)
                text = "Drag to select area to save"
                extents = cr.text_extents(text)
                cr.move_to(text_x - extents.width/2, 60)
                cr.show_text(text)
                
                cr.set_font_size(16)
                cr.select_font_face("Sans", 0, 0)
                text2 = "Press Escape to cancel"
                extents2 = cr.text_extents(text2)
                cr.move_to(text_x - extents2.width/2, 90)
                cr.show_text(text2)
        
        def on_key_press(widget, event):
            if event.keyval == Gdk.KEY_Escape:
                # Failsafe: press Escape 3 times quickly to force close
                current_time = GLib.get_monotonic_time() / 1000000  # Convert to seconds
                if current_time - escape_count["last_time"] < 1:  # Within 1 second
                    escape_count["count"] += 1
                else:
                    escape_count["count"] = 1
                escape_count["last_time"] = current_time
                
                if escape_count["count"] >= 3:
                    # Force immediate close
                    crop_window.destroy()
                    self.reset_ui()
                    self.show()
                    return True
                
                # Normal single Escape
                crop_window.destroy()
                self.reset_ui()
                self.show()
                return True
            elif event.keyval == Gdk.KEY_Return or event.keyval == Gdk.KEY_KP_Enter:
                if selection["start"] and selection["end"]:
                    # Save the selected area
                    x = int(min(selection["start"][0], selection["end"][0]))
                    y = int(min(selection["start"][1], selection["end"][1]))
                    w = int(abs(selection["end"][0] - selection["start"][0]))
                    h = int(abs(selection["end"][1] - selection["start"][1]))
                    
                    if w > 5 and h > 5:
                        crop_window.destroy()
                        self.save_cropped_area(x, y, w, h)
                return True
            elif event.keyval == Gdk.KEY_s and event.state & Gdk.ModifierType.CONTROL_MASK:
                # Ctrl+S to save full screen
                crop_window.destroy()
                self.save_full_screenshot()
                return True
            return False
        
        def on_button_press(widget, event):
            selection["start"] = (event.x, event.y)
            selection["end"] = (event.x, event.y)  # Initialize to same point
            selection["dragging"] = True
            widget.queue_draw()
            return True
            
        def on_motion(widget, event):
            if selection["dragging"]:
                selection["end"] = (event.x, event.y)
                widget.queue_draw()
            return True
                
        def on_button_release(widget, event):
            if selection["dragging"]:
                selection["dragging"] = False
                selection["end"] = (event.x, event.y)
                widget.queue_draw()
            return True
        
        crop_window.connect("draw", on_draw)
        crop_window.connect("button-press-event", on_button_press)
        crop_window.connect("motion-notify-event", on_motion)
        crop_window.connect("button-release-event", on_button_release)
        crop_window.connect("key-press-event", on_key_press)
        
        crop_window.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.KEY_PRESS_MASK
        )
        
        crop_window.show_all()
        crop_window.present()
        
        # Set cursor to crosshair after window is shown
        if crop_window.get_window():
            cursor = Gdk.Cursor.new_for_display(Gdk.Display.get_default(), Gdk.CursorType.CROSSHAIR)
            crop_window.get_window().set_cursor(cursor)
        
        # Make sure keyboard events work without using grab_add which can cause issues
        crop_window.set_can_focus(True)
        crop_window.grab_focus()
    
    def save_cropped_area(self, x, y, width, height):
        """Save the cropped area"""
        try:
            # Ensure we don't go out of bounds
            pixbuf_width = self.captured_pixbuf.get_width()
            pixbuf_height = self.captured_pixbuf.get_height()
            
            # Clamp values to pixbuf dimensions
            x = max(0, min(x, pixbuf_width - 1))
            y = max(0, min(y, pixbuf_height - 1))
            width = min(width, pixbuf_width - x)
            height = min(height, pixbuf_height - y)
            
            if width <= 0 or height <= 0:
                self.show_error("Invalid selection area")
                return
            
            # Create cropped pixbuf
            cropped = self.captured_pixbuf.new_subpixbuf(x, y, width, height)
            
            # Prompt for filename
            filepath = self.prompt_for_filename()
            if filepath:
                # Save
                cropped.savev(filepath, "png", [], [])
                self.show_success(filepath)
            else:
                # User cancelled, go back to main window
                self.reset_ui()
                self.show()
            
        except Exception as e:
            self.show_error(f"Error saving screenshot: {str(e)}")
    
    def prompt_for_filename(self):
        """Prompt user for filename"""
        dialog = Gtk.FileChooserDialog(
            title="Save Screenshot As",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        
        # Set current folder
        os.makedirs(self.save_folder, exist_ok=True)
        dialog.set_current_folder(self.save_folder)
        
        # Suggest a default filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dialog.set_current_name(f"Screenshot_{timestamp}.png")
        
        # Add file filter for PNG
        filter_png = Gtk.FileFilter()
        filter_png.set_name("PNG images")
        filter_png.add_mime_type("image/png")
        filter_png.add_pattern("*.png")
        dialog.add_filter(filter_png)
        
        # Set overwrite confirmation
        dialog.set_do_overwrite_confirmation(True)
        
        response = dialog.run()
        filepath = None
        
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            # Ensure .png extension
            if not filepath.endswith('.png'):
                filepath += '.png'
            # Update save folder to remember location
            new_folder = os.path.dirname(filepath)
            if new_folder != self.save_folder:
                self.save_folder = new_folder
                self.folder_entry.set_text(self.save_folder)
                self.add_recent_folder(self.save_folder)
        
        dialog.destroy()
        return filepath
    
    def save_full_screenshot(self):
        """Save the full screenshot without cropping"""
        try:
            filepath = self.prompt_for_filename()
            if filepath:
                self.captured_pixbuf.savev(filepath, "png", [], [])
                self.show_success(filepath)
            else:
                # User cancelled
                self.reset_ui()
                self.show()
            
        except Exception as e:
            self.show_error(f"Error saving screenshot: {str(e)}")
    
    def show_success(self, filepath):
        """Show success dialog"""
        self.reset_ui()
        
        # Get just the filename for display
        filename = os.path.basename(filepath)
        
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.NONE,
            text="Screenshot Saved"
        )
        dialog.format_secondary_text(f"Saved: {filename}\nFolder: {self.save_folder}")
        
        dialog.add_button("Continue (New Screenshot)", 1)
        dialog.add_button("Open Folder", 2)
        dialog.add_button("Open Image", 3)
        dialog.add_button("Exit", 4)
        
        # Set Continue as default
        dialog.set_default_response(1)
        
        response = dialog.run()
        dialog.destroy()
        
        if response == 1:
            # Continue with new screenshot
            self.captured_pixbuf = None
            self.show()
        elif response == 2:
            # Open folder
            os.system(f'xdg-open "{self.save_folder}"')
            self.captured_pixbuf = None
            self.show()
        elif response == 3:
            # Open image
            os.system(f'xdg-open "{filepath}"')
            self.captured_pixbuf = None
            self.show()
        else:
            # Exit
            Gtk.main_quit()
    
    def show_error(self, message):
        """Show error dialog"""
        self.reset_ui()
        
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Screenshot Failed"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
        self.show()


def main():
    # Initialize GTK properly
    Gtk.init(sys.argv)
    
    win = ScreenshotCropTool()
    win.show_all()
    
    # Connect delete event to ensure proper cleanup
    win.connect("delete-event", lambda w, e: Gtk.main_quit())
    
    try:
        Gtk.main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        Gtk.main_quit()


if __name__ == "__main__":
    main()