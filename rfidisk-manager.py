#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import os
import subprocess
import sys
import socket
import psutil
import time
import threading
from PIL import Image, ImageTk
import webbrowser

TAGS_FILE = "rfidisk_tags.json"
CONFIG_FILE = "rfidisk_config.json"
THEME_FILE = "rfidisk_theme.json"
LOCK_PORT = 47821
VERSION = "0.95"
GITHUB_URL = "https://github.com/ItsDanik/rfidisk"

# Default fallback theme with semantic UI element names
COLORS = {
    # Background colors
    "bg_primary": "#1e1e2e",
    "bg_secondary": "#181825",
    "bg_tertiary": "#11111b",
    
    # Text colors
    "text_primary": "#cdd6f4",
    "text_secondary": "#bac2de",
    "text_tertiary": "#a6adc8",
    "text_warning": "#f38ba8",
    "text_success": "#a6e3a1",
    
    # Surface colors
    "surface_primary": "#313244",
    "surface_secondary": "#45475a",
    "surface_tertiary": "#585b70",
    
    # Border colors
    "border_primary": "#313244",
    "border_secondary": "#45475a",
    
    # Accent colors
    "accent_primary": "#89b4fa",
    "accent_secondary": "#74c7ec",
    "accent_success": "#a6e3a1",
    "accent_warning": "#f9e2af",
    "accent_error": "#f38ba8",
    "accent_highlight": "#fab387"
}

class SingletonApp:
    """Prevent multiple instances and handle inter-process communication"""
    def __init__(self):
        self.socket = None
        self.is_primary = False
        self.listening = False
        
    def acquire_lock(self):
        """Try to bind to a socket - if successful, we're the first instance"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('localhost', LOCK_PORT))
            self.socket.listen(1)
            self.socket.setblocking(False)
            self.is_primary = True
            return True
        except socket.error:
            return False
    
    def send_to_primary(self, tag_id=None):
        """Send a message to the primary instance"""
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(1.0)
            client_socket.connect(('localhost', LOCK_PORT))
            if tag_id:
                client_socket.send(f"EDIT:{tag_id}".encode())
            else:
                client_socket.send("FOCUS".encode())
            client_socket.close()
            return True
        except socket.error:
            return False
    
    def check_for_messages(self):
        """Check for incoming messages from other instances"""
        if not self.is_primary or not self.socket or not self.listening:
            return None
            
        try:
            client, addr = self.socket.accept()
            client.setblocking(True)
            data = client.recv(1024).decode().strip()
            client.close()
            return data
        except BlockingIOError:
            return None
        except socket.error:
            return None
    
    def start_listening(self):
        """Start listening for messages"""
        self.listening = True
    
    def stop_listening(self):
        """Stop listening for messages"""
        self.listening = False
    
    def cleanup(self):
        """Clean up socket resources"""
        self.stop_listening()
        if self.socket:
            self.socket.close()
            self.socket = None

class TagManager:
    def __init__(self, root):
        self.root = root
        self.root.title(f"RFIDisk Tag Manager v{VERSION}")
        self.root.geometry("740x720")
        
        # Load theme configuration
        self.themes = {}
        self.current_theme_name = "Catppuccin Mocha"
        self.load_theme_config()
        
        # Singleton management
        self.singleton = SingletonApp()
        self.setup_singleton()
        
        self.tags = self.load_tags()
        self.config = self.load_config()
        self.current_tag = None
        self.display_mode = "line1"
        
        # Load logo image
        self.logo_image = None
        self.load_logo()
        
        self.create_widgets()
        self.refresh_tag_list()
        
        # Start IPC handler after UI is fully set up
        self.root.after(100, self.setup_ipc_handler)
    
    def load_theme_config(self):
        """Load theme configuration from file"""
        global COLORS
        
        try:
            with open(THEME_FILE, 'r') as f:
                theme_config = json.load(f)
            
            # Load available themes
            self.themes = theme_config.get("themes", {})
            
            # Get current theme name
            self.current_theme_name = theme_config.get("current_theme", "Catppuccin Mocha")
            
            # Load current theme colors
            if self.current_theme_name in self.themes:
                COLORS = self.themes[self.current_theme_name].copy()
                print(f"Loaded theme: {self.current_theme_name}")

                # Apply the color scheme
                self.configure_theme()

            else:
                print(f"Theme '{self.current_theme_name}' not found in theme file")
                
        except Exception as e:
            print(f"Failed to load theme config: {e}")
    
    def save_theme_config(self, theme_name):
        """Save current theme to configuration file"""
        try:
            with open(THEME_FILE, 'r') as f:
                theme_config = json.load(f)
            
            theme_config["current_theme"] = theme_name
            
            with open(THEME_FILE, 'w') as f:
                json.dump(theme_config, f, indent=2)
            
            print(f"Theme saved: {theme_name}")
            return True
        except Exception as e:
            print(f"Failed to save theme config: {e}")
            return False
    
    def change_theme(self, theme_name):
        """Change the current theme"""
        global COLORS
        
        if theme_name in self.themes:
            # Update global colors
            COLORS = self.themes[theme_name].copy()
            self.current_theme_name = theme_name
            
            # Save theme selection
            self.save_theme_config(theme_name)
            
            # Reconfigure theme
            self.configure_theme()
            
            # Update UI elements that need manual color updates
            self.update_theme_colors()
            
            return True
        else:
            return False
    
    def update_theme_colors(self):
        """Update UI elements that need manual color updates after theme change"""
        # Update root window background
        self.root.configure(bg=COLORS["bg_primary"])
        
        # Update warning labels and other non-ttk widgets
        for widget in self.root.winfo_children():
            self._update_widget_colors(widget)
    
    def _update_widget_colors(self, widget):
        """Recursively update widget colors"""
        try:
            if isinstance(widget, tk.Label):
                # Update background
                if widget.cget('bg') in [COLORS["bg_primary"], COLORS["bg_secondary"], COLORS["bg_tertiary"]]:
                    widget.configure(bg=COLORS["bg_primary"])
                
                # Update text colors
                current_fg = widget.cget('fg')
                if current_fg == COLORS.get("text_warning", "#f38ba8"):
                    widget.configure(fg=COLORS["text_warning"])
                elif current_fg == COLORS.get("accent_highlight", "#fab387"):
                    widget.configure(fg=COLORS["accent_highlight"])
                else:
                    widget.configure(fg=COLORS["text_primary"])
                    
        except tk.TclError:
            pass
        
        # Recursively update child widgets
        for child in widget.winfo_children():
            self._update_widget_colors(child)
    
    def load_logo(self):
        """Load the RFIDisk logo image"""
        logo_path = "./rfidisk.png"
        if os.path.exists(logo_path):
            try:
                image = Image.open(logo_path)
                if image.size != (400, 100):
                    image = image.resize((400, 100), Image.Resampling.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(image)
            except Exception as e:
                print(f"Failed to load logo: {e}")
                self.logo_image = None
        else:
            print(f"Logo file not found: {logo_path}")
            self.logo_image = None
    
    def open_github(self):
        """Open the GitHub repository in the default web browser"""
        webbrowser.open(GITHUB_URL)
    
    def create_clickable_logo(self, parent):
        """Create a clickable logo that opens the GitHub repository"""
        if self.logo_image:
            logo_label = tk.Label(parent, image=self.logo_image, bg=COLORS["bg_primary"], cursor="hand2")
            logo_label.pack(pady=(0, 10))
            
            logo_label.bind("<Button-1>", lambda e: self.open_github())
            
            def on_enter(e):
                logo_label.config(bg=COLORS["surface_primary"])
            
            def on_leave(e):
                logo_label.config(bg=COLORS["bg_primary"])
            
            logo_label.bind("<Enter>", on_enter)
            logo_label.bind("<Leave>", on_leave)
            
            return logo_label
        return None

    def get_installed_version(self):
        """Check if RFIDisk is installed via autostart entry"""
        autostart_path = os.path.expanduser("~/.config/autostart/rfidisk.desktop")
        if os.path.exists(autostart_path):
            return VERSION
        else:
            return "Not Installed"
    
    def configure_theme(self):
        """Configure theme with current colors"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure base styles
        style.configure('.', 
                       background=COLORS["bg_primary"],
                       foreground=COLORS["text_primary"],
                       fieldbackground=COLORS["surface_primary"],
                       selectbackground=COLORS["accent_primary"],
                       selectforeground=COLORS["bg_primary"],
                       insertcolor=COLORS["text_primary"],
                       troughcolor=COLORS["surface_secondary"],
                       bordercolor=COLORS["border_primary"],
                       darkcolor=COLORS["bg_tertiary"],
                       lightcolor=COLORS["border_primary"])
        
        # Configure specific widgets
        style.configure('TFrame', 
                       background=COLORS["bg_primary"],
                       relief='flat',
                       borderwidth=1)
        
        style.configure('TLabel', 
                       background=COLORS["bg_primary"],
                       foreground=COLORS["text_primary"],
                       font=('Segoe UI', 9),
                       borderwidth=0,
                       relief='flat')
        
        style.configure('TButton', 
                       background=COLORS["surface_primary"],
                       foreground=COLORS["text_primary"],
                       borderwidth=1,
                       focuscolor=COLORS["surface_secondary"],
                       relief='raised',
                       bordercolor=COLORS["border_primary"])
        
        style.map('TButton',
                 background=[('active', COLORS["surface_secondary"]),
                           ('pressed', COLORS["surface_tertiary"])],
                 relief=[('pressed', 'sunken')],
                 bordercolor=[('active', COLORS["border_secondary"]),
                             ('pressed', COLORS["border_primary"])])
        
        style.configure('TEntry', 
                       fieldbackground=COLORS["surface_primary"],
                       foreground=COLORS["text_primary"],
                       borderwidth=1,
                       relief='solid',
                       bordercolor=COLORS["border_primary"],
                       focuscolor=COLORS["accent_primary"])
        
        style.configure('TCheckbutton', 
                       background=COLORS["bg_primary"],
                       foreground=COLORS["text_primary"],
                       indicatorcolor=COLORS["surface_primary"],
                       bordercolor=COLORS["border_primary"],
                       indicatorrelief='solid')
        
        style.map('TCheckbutton',
                 indicatorcolor=[('selected', COLORS["accent_success"]),
                               ('active', COLORS["surface_secondary"])],
                 bordercolor=[('active', COLORS["border_secondary"]),
                             ('selected', COLORS["accent_success"])])
        
        style.configure('TNotebook', 
                       background=COLORS["bg_primary"],
                       borderwidth=1,
                       bordercolor=COLORS["border_primary"])
        
        style.configure('TNotebook.Tab', 
                       background=COLORS["surface_primary"],
                       foreground=COLORS["text_secondary"],
                       padding=[15, 5],
                       borderwidth=1,
                       relief='raised',
                       bordercolor=COLORS["border_primary"])
        
        style.map('TNotebook.Tab',
                 background=[('selected', COLORS["accent_primary"]),
                           ('active', COLORS["surface_secondary"])],
                 foreground=[('selected', COLORS["bg_primary"]),
                           ('active', COLORS["text_primary"])],
                 bordercolor=[('selected', COLORS["accent_primary"]),
                             ('active', COLORS["border_secondary"])])
        
        style.configure('TSpinbox', 
                       fieldbackground=COLORS["surface_primary"],
                       foreground=COLORS["text_primary"],
                       background=COLORS["surface_primary"],
                       arrowcolor=COLORS["text_primary"],
                       borderwidth=1,
                       bordercolor=COLORS["border_primary"],
                       relief='solid',
                       focuscolor=COLORS["accent_primary"])
        
        # Combobox styling
        style.configure('TCombobox',
                       fieldbackground=COLORS["surface_primary"],
                       background=COLORS["surface_primary"],
                       foreground=COLORS["text_primary"],
                       borderwidth=1,
                       bordercolor=COLORS["border_primary"],
                       relief='solid',
                       focuscolor=COLORS["accent_primary"])
        
        style.map('TCombobox',
                 fieldbackground=[('readonly', COLORS["surface_primary"])],
                 background=[('readonly', COLORS["surface_primary"])],
                 bordercolor=[('focus', COLORS["accent_primary"]),
                            ('active', COLORS["border_secondary"])])
        
        style.configure('NoBorder.TFrame', 
                       background=COLORS["bg_primary"],
                       relief='flat',
                       borderwidth=0)
        
        # Configure root window
        self.root.configure(bg=COLORS["bg_primary"], highlightbackground=COLORS["border_primary"])
        
        # Configure non-ttk widgets
        self.root.option_add('*Listbox*Background', COLORS["surface_primary"])
        self.root.option_add('*Listbox*Foreground', COLORS["text_primary"])
        self.root.option_add('*Listbox*selectBackground', COLORS["accent_primary"])
        self.root.option_add('*Listbox*selectForeground', COLORS["bg_primary"])
        self.root.option_add('*Listbox*font', ('Segoe UI', 9))
        self.root.option_add('*Listbox*highlightBackground', COLORS["border_primary"])
        self.root.option_add('*Listbox*highlightColor', COLORS["border_primary"])
        self.root.option_add('*Listbox*borderWidth', 1)
        
        self.root.option_add('*BorderWidth', 1)
        self.root.option_add('*highlightThickness', 1)
        self.root.option_add('*highlightBackground', COLORS["border_primary"])
        self.root.option_add('*highlightColor', COLORS["border_primary"])
    
    def setup_singleton(self):
        """Handle singleton instance logic"""
        edit_tag_id = None
        if len(sys.argv) > 2 and sys.argv[1] == "--edit":
            edit_tag_id = sys.argv[2]
        
        if not self.singleton.acquire_lock():
            if edit_tag_id:
                print(f"Another instance detected, requesting to edit tag: {edit_tag_id}")
                if self.singleton.send_to_primary(edit_tag_id):
                    print("Request sent to existing instance")
                else:
                    print("Failed to communicate with existing instance")
            else:
                print("Another instance detected, bringing it to focus")
                self.singleton.send_to_primary()
            
            sys.exit(0)
        
        if edit_tag_id:
            self.root.after(500, lambda: self.focus_and_edit_tag(edit_tag_id))
    
    def setup_ipc_handler(self):
        """Set up periodic check for inter-process communication"""
        self.singleton.start_listening()
        
        def check_ipc():
            if self.singleton.listening:
                message = self.singleton.check_for_messages()
                if message:
                    self.handle_ipc_message(message)
            self.root.after(100, check_ipc)
        
        check_ipc()
    
    def handle_ipc_message(self, message):
        """Handle messages from other instances"""
        print(f"Received IPC message: {message}")
        
        if message.startswith("EDIT:"):
            tag_id = message[5:]
            self.focus_and_edit_tag(tag_id)
        elif message == "FOCUS":
            self.bring_to_front()
    
    def focus_and_edit_tag(self, tag_id):
        """Bring window to front and edit specified tag"""
        self.bring_to_front()
        
        if tag_id not in self.tags:
            self.tags[tag_id] = {
                'command': '',
                'line1': 'new entry',
                'line2': 'configure me',
                'line3': 'edit rfidisk_tags.json',
                'line4': tag_id,
                'terminate': ''
            }
            self.save_tags()
            self.refresh_tag_list()
        
        self.notebook.select(0)
        
        display_items = self.get_display_items()
        for i, (current_tag_id, _) in enumerate(display_items):
            if current_tag_id == tag_id:
                self.tag_listbox.selection_clear(0, tk.END)
                self.tag_listbox.selection_set(i)
                self.tag_listbox.see(i)
                self.load_tag_data(tag_id)
                break
        
        self.flash_window()
        
        messagebox.showinfo("New Tag Detected", 
                          f"Tag {tag_id} detected and ready for configuration!\n\n"
                          f"Please configure the launch command and display settings.")
    
    def bring_to_front(self):
        """Bring the window to the front and give it focus"""
        self.root.lift()
        self.root.focus_force()
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))
    
    def flash_window(self):
        """Flash the window to get user's attention"""
        original_color = self.root.cget('background')
        
        def flash(count=0):
            if count < 6:
                if count % 2 == 0:
                    self.root.configure(background=COLORS["accent_error"])
                else:
                    self.root.configure(background=original_color)
                self.root.after(200, lambda: flash(count + 1))
            else:
                self.root.configure(background=original_color)
        
        flash()
    
    def create_warning_label(self, parent):
        """Create warning label with current theme colors and no borders"""
        warning_frame = ttk.Frame(parent, style='NoBorder.TFrame')
        warning_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.create_clickable_logo(warning_frame)
        
        warning_text = [
            "This software can automatically launch applications.",
            "Make sure your configuration only contains",
            "trusted commands to avoid potential security risks.",
            "",
            "WARNING! USE AT YOUR OWN RISK!!!"
        ]
        
        for line in warning_text:
            if line == "WARNING! USE AT YOUR OWN RISK!!!":
                label = tk.Label(warning_frame, text=line, 
                               fg=COLORS["text_warning"], 
                               bg=COLORS["bg_primary"],
                               font=('Segoe UI', 9, 'bold'), 
                               justify=tk.CENTER,
                               borderwidth=0,
                               highlightthickness=0)
            elif line == "":
                label = tk.Label(warning_frame, text=" ", 
                               fg=COLORS["text_primary"], 
                               bg=COLORS["bg_primary"],
                               font=('Segoe UI', 9), 
                               justify=tk.CENTER,
                               borderwidth=0,
                               highlightthickness=0)
            else:
                label = tk.Label(warning_frame, text=line, 
                               fg=COLORS["accent_highlight"], 
                               bg=COLORS["bg_primary"],
                               font=('Segoe UI', 9), 
                               justify=tk.CENTER,
                               borderwidth=0,
                               highlightthickness=0)
            label.pack(fill=tk.X)
    
    def load_tags(self):
        """Load tags from JSON file"""
        if os.path.exists(TAGS_FILE):
            try:
                with open(TAGS_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load tags: {e}")
                return {}
        return {}
    
    def load_config(self):
        """Load configuration from JSON file"""
        default_config = {
            "settings": {
                "serial_port": "/dev/ttyACM0",
                "removal_delay": 0.0,
                "desktop_notifications": True,
                "notification_timeout": 8000,
                "auto_launch_manager": True,
                "disable_autolaunch": False
            }
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    user_config = json.load(f)
                    if "settings" in user_config:
                        default_config["settings"].update(user_config["settings"])
                print(f"Loaded config from {CONFIG_FILE}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load config: {e}")
        else:
            self.save_config(default_config)
            print(f"Created default config file: {CONFIG_FILE}")
        
        return default_config
    
    def save_tags(self):
        """Save tags to JSON file"""
        try:
            with open(TAGS_FILE, 'w') as f:
                json.dump(self.tags, f, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save tags: {e}")
            return False
    
    def save_config(self, config=None):
        """Save configuration to JSON file"""
        if config is None:
            config = self.config
            
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")
            return False
    
    def create_widgets(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tags tab
        self.tags_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tags_frame, text="Tag Management")
        
        # Settings tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Configuration")
        
        # Quit tab
        self.quit_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.quit_frame, text="About/Quit")
        
        self.setup_tags_tab()
        self.setup_settings_tab()
        self.setup_quit_tab()
        
        # Add version label at bottom right
        self.create_version_label()
    
    def create_version_label(self):
        """Create version label at bottom right of window"""
        version_frame = ttk.Frame(self.root)
        version_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)
        
        installed_version = self.get_installed_version()
        version_text = f"RFIDisk Version: {installed_version}"
        
        version_label = ttk.Label(version_frame, text=version_text, 
                                font=('Segoe UI', 8), 
                                foreground=COLORS["text_tertiary"])
        version_label.pack(side=tk.RIGHT)
    
    def setup_quit_tab(self):
        """Setup the quit tab with confirmation"""
        main_container = ttk.Frame(self.quit_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        message_frame = ttk.Frame(main_container)
        message_frame.pack(fill=tk.X, pady=(20, 10))
        
        ttk.Label(message_frame, text="RFIDisk",
                 font=('Segoe UI', 16, 'bold'), foreground=COLORS["accent_secondary"]).pack(pady=0)

        ttk.Label(message_frame, text="Project by danik 2025\n",
                 font=('Segoe UI', 12, 'bold'), foreground=COLORS["accent_highlight"]).pack(pady=0)
        
        ttk.Label(message_frame, text="Click the logo banner below to visit the GitHub repository.",
                 font=('Segoe UI', 11)).pack(pady=0)

        ttk.Label(message_frame, text="Check the README.md for complete documentation.",
                 font=('Segoe UI', 11)).pack(pady=0)

        ttk.Label(message_frame, text=" ",
                 font=('Segoe UI', 20), foreground=COLORS["accent_highlight"]).pack(pady=0)
        
        ttk.Label(message_frame, text="Exit RFIDisk Manager", 
                 font=('Segoe UI', 16, 'bold')).pack(pady=5)
        
        ttk.Label(message_frame, text="Are you sure you want to quit?",
                 font=('Segoe UI', 11)).pack(pady=0)
        
        ttk.Label(message_frame, text="All unsaved changes will be lost.",
                 font=('Segoe UI', 9), foreground=COLORS["accent_highlight"]).pack(pady=0)
        
        button_frame = ttk.Frame(main_container)
        button_frame.pack(pady=10)
        
        quit_btn = ttk.Button(button_frame, text="Quit Application", 
                             command=self.quit_app)
        quit_btn.pack(pady=10, ipadx=20, ipady=10)
        
        self.create_warning_label(main_container)
    
    def setup_tags_tab(self):
        """Setup the tag management tab"""
        # Main container for the entire tab
        main_container = ttk.Frame(self.tags_frame)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Container for the content (tag list + editor)
        content_container = ttk.Frame(main_container)
        content_container.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - tag list
        left_frame = ttk.Frame(content_container)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Display mode toggle
        display_frame = ttk.Frame(left_frame)
        display_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(display_frame, text="Display:").pack(side=tk.LEFT)
        self.display_btn = ttk.Button(display_frame, text="Show Tag IDs", command=self.toggle_display_mode)
        self.display_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(left_frame, text="Configured Tags:").pack(anchor=tk.W)
        
        self.tag_listbox = tk.Listbox(left_frame, width=25, height=20)
        self.tag_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.tag_listbox.bind('<<ListboxSelect>>', self.on_tag_select)
        
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="New Tag", command=self.new_tag).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(button_frame, text="Delete Tag", command=self.delete_tag).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Right panel - tag editor (this will expand to fill remaining space)
        editor_container = ttk.Frame(content_container)
        editor_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a frame for the editor content that can have the warning below it
        editor_content = ttk.Frame(editor_container)
        editor_content.pack(fill=tk.BOTH, expand=True)
        
        # Tag ID
        ttk.Label(editor_content, text="Tag ID:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.tag_id_var = tk.StringVar()
        self.tag_id_entry = ttk.Entry(editor_content, textvariable=self.tag_id_var, width=30)
        self.tag_id_entry.grid(row=0, column=1, sticky=tk.W+tk.E, pady=2)
        
        # Command
        ttk.Label(editor_content, text="Launch Command:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.command_var = tk.StringVar()
        self.command_entry = ttk.Entry(editor_content, textvariable=self.command_var, width=30)
        self.command_entry.grid(row=1, column=1, sticky=tk.W+tk.E, pady=2)
        ttk.Button(editor_content, text="Browse", command=self.browse_command).grid(row=1, column=2, padx=5)
        
        # Display lines
        ttk.Label(editor_content, text="Display Line 1:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.line1_var = tk.StringVar()
        self.line1_entry = ttk.Entry(editor_content, textvariable=self.line1_var, width=30)
        self.line1_entry.grid(row=2, column=1, sticky=tk.W+tk.E, pady=2)
        
        ttk.Label(editor_content, text="Display Line 2:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.line2_var = tk.StringVar()
        ttk.Entry(editor_content, textvariable=self.line2_var, width=30).grid(row=3, column=1, sticky=tk.W+tk.E, pady=2)
        
        ttk.Label(editor_content, text="Display Line 3:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.line3_var = tk.StringVar()
        ttk.Entry(editor_content, textvariable=self.line3_var, width=30).grid(row=4, column=1, sticky=tk.W+tk.E, pady=2)
        
        ttk.Label(editor_content, text="Display Line 4:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.line4_var = tk.StringVar()
        ttk.Entry(editor_content, textvariable=self.line4_var, width=30).grid(row=5, column=1, sticky=tk.W+tk.E, pady=2)
        
        # Terminate command
        ttk.Label(editor_content, text="Terminate Command:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.terminate_var = tk.StringVar()
        ttk.Entry(editor_content, textvariable=self.terminate_var, width=30).grid(row=6, column=1, sticky=tk.W+tk.E, pady=2)
        
        # Save button
        ttk.Button(editor_content, text="Save Changes", command=self.save_current_tag).grid(row=7, column=1, pady=10)
        
        # Test buttons
        test_frame = ttk.Frame(editor_content)
        test_frame.grid(row=8, column=0, columnspan=3, pady=10)
        ttk.Button(test_frame, text="Test Launch", command=self.test_launch).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_frame, text="Test Terminate", command=self.test_terminate).pack(side=tk.LEFT, padx=5)
        
        editor_content.columnconfigure(1, weight=1)
        
        # Now add the warning to the editor_container (below the editor content)
        self.create_warning_label(editor_container)
    
    def setup_settings_tab(self):
        """Setup the configuration settings tab"""
        # Create a main container that uses pack for the warning
        main_container = ttk.Frame(self.settings_frame)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create a frame for the grid-based settings
        settings_container = ttk.Frame(main_container)
        settings_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Theme selection (NEW - added at the top)
        ttk.Label(settings_container, text="Theme:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.theme_var = tk.StringVar()
        self.theme_combobox = ttk.Combobox(settings_container, 
                                          textvariable=self.theme_var,
                                          values=list(self.themes.keys()),
                                          state="readonly",
                                          width=20)
        self.theme_combobox.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Set current theme from loaded configuration
        self.theme_var.set(self.current_theme_name)
        
        # Serial port setting
        ttk.Label(settings_container, text="Serial Port:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.serial_port_var = tk.StringVar(value=self.config["settings"].get("serial_port", "/dev/ttyACM0"))
        self.serial_port_entry = ttk.Entry(settings_container, textvariable=self.serial_port_var, width=30)
        self.serial_port_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Removal delay
        ttk.Label(settings_container, text="Removal Delay (seconds):").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.removal_delay_var = tk.DoubleVar(value=self.config["settings"].get("removal_delay", 0.0))
        self.removal_delay_spinbox = ttk.Spinbox(settings_container, from_=0.0, to=10.0, increment=0.1, 
                                                textvariable=self.removal_delay_var, width=10)
        self.removal_delay_spinbox.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Disable Autolaunch setting
        ttk.Label(settings_container, text="Disable Autolaunch:").grid(row=3, column=0, sticky=tk.W, pady=5, padx=5)
        self.disable_autolaunch_var = tk.BooleanVar(value=self.config["settings"].get("disable_autolaunch", False))
        self.disable_autolaunch_check = ttk.Checkbutton(settings_container, variable=self.disable_autolaunch_var)
        self.disable_autolaunch_check.grid(row=3, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Desktop notifications
        ttk.Label(settings_container, text="Desktop Notifications:").grid(row=4, column=0, sticky=tk.W, pady=5, padx=5)
        self.notifications_var = tk.BooleanVar(value=self.config["settings"].get("desktop_notifications", True))
        self.notifications_check = ttk.Checkbutton(settings_container, variable=self.notifications_var, 
                                                  command=self.toggle_notification_settings)
        self.notifications_check.grid(row=4, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Notification timeout
        ttk.Label(settings_container, text="Notification Timeout (ms):").grid(row=5, column=0, sticky=tk.W, pady=5, padx=5)
        self.notification_timeout_var = tk.IntVar(value=self.config["settings"].get("notification_timeout", 8000))
        self.notification_timeout_spinbox = ttk.Spinbox(settings_container, from_=1000, to=30000, increment=1000, 
                                                       textvariable=self.notification_timeout_var, width=10)
        self.notification_timeout_spinbox.grid(row=5, column=1, sticky=tk.W, pady=5, padx=5)
                
        # Auto launch manager
        ttk.Label(settings_container, text="Auto Launch Manager:").grid(row=6, column=0, sticky=tk.W, pady=5, padx=5)
        self.auto_launch_var = tk.BooleanVar(value=self.config["settings"].get("auto_launch_manager", True))
        ttk.Checkbutton(settings_container, variable=self.auto_launch_var).grid(row=6, column=1, sticky=tk.W, pady=5, padx=5)
                
        # Save & Apply button (UPDATED)
        ttk.Button(settings_container, text="Save & Apply", command=self.save_and_apply_settings).grid(row=7, column=0, columnspan=3, pady=20)
        
        # Status label
        self.settings_status_var = tk.StringVar(value="Settings loaded")
        ttk.Label(settings_container, textvariable=self.settings_status_var).grid(row=8, column=0, columnspan=3, pady=5)
        
        # Set initial state for notification timeout
        self.toggle_notification_settings()
        
        settings_container.columnconfigure(1, weight=1)
        
        # Add warning label after main content
        self.create_warning_label(main_container)
    
    def save_and_apply_settings(self):
        """Save configuration settings and apply theme"""
        try:
            # Update config with current values
            self.config["settings"]["serial_port"] = self.serial_port_var.get().strip()
            self.config["settings"]["removal_delay"] = float(self.removal_delay_var.get())
            self.config["settings"]["disable_autolaunch"] = bool(self.disable_autolaunch_var.get())
            self.config["settings"]["desktop_notifications"] = bool(self.notifications_var.get())
            self.config["settings"]["notification_timeout"] = int(self.notification_timeout_var.get())
            self.config["settings"]["auto_launch_manager"] = bool(self.auto_launch_var.get())
            
            # Save to file
            if self.save_config():
                # Apply theme if changed
                if self.theme_var.get() != self.current_theme_name:
                    theme_success = self.change_theme(self.theme_var.get())
                    
                    if theme_success:
                        self.settings_status_var.set("Settings saved and theme applied!")
                        messagebox.showinfo("Success", "Configuration saved and theme applied!")
                    else:
                        self.settings_status_var.set("Settings saved but theme failed")
                        messagebox.showwarning("Warning", "Configuration saved but theme change failed!")
                else:
                    self.settings_status_var.set("Settings saved successfully!")
                    messagebox.showinfo("Success", "Configuration saved!")
            else:
                self.settings_status_var.set("Failed to save settings")
                
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value: {e}")
            self.settings_status_var.set("Error: Invalid values")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
            self.settings_status_var.set("Error saving settings")
    
    def toggle_notification_settings(self):
        """Enable/disable notification timeout based on notifications checkbox"""
        if self.notifications_var.get():
            self.notification_timeout_spinbox.config(state="normal")
        else:
            self.notification_timeout_spinbox.config(state="disabled")
    
    def save_settings(self):
        """Save configuration settings (legacy method, now using save_and_apply_settings)"""
        self.save_and_apply_settings()
    
    def toggle_display_mode(self):
        """Switch between displaying Tag IDs and Line1 names"""
        if self.display_mode == "tag_id":
            self.display_mode = "line1"
            self.display_btn.config(text="Show Tag IDs")
        else:
            self.display_mode = "tag_id"
            self.display_btn.config(text="Show Names")
        
        self.refresh_tag_list()
    
    def get_display_items(self):
        """Get items for display in the listbox based on current mode"""
        items = []
        
        if self.display_mode == "tag_id":
            # Display Tag IDs, sorted alphabetically
            for tag_id in sorted(self.tags.keys()):
                items.append((tag_id, tag_id))
        else:
            # Display Line1 names, sorted alphabetically by line1
            sorted_items = []
            for tag_id, tag_data in self.tags.items():
                line1 = tag_data.get('line1', 'Unnamed').strip()
                if not line1:
                    line1 = "Unnamed"
                sorted_items.append((line1.lower(), tag_id, line1))
            
            # Sort by line1 (case-insensitive)
            sorted_items.sort(key=lambda x: x[0])
            
            for _, tag_id, line1 in sorted_items:
                items.append((tag_id, line1))
        
        return items
    
    def refresh_tag_list(self):
        """Refresh the tag list with current display mode"""
        self.tag_listbox.delete(0, tk.END)
        display_items = self.get_display_items()
        
        for tag_id, display_text in display_items:
            self.tag_listbox.insert(tk.END, display_text)
    
    def get_selected_tag_id(self):
        """Get the actual tag ID from the current selection"""
        selection = self.tag_listbox.curselection()
        if selection:
            display_items = self.get_display_items()
            if selection[0] < len(display_items):
                return display_items[selection[0]][0]  # Return the tag_id
        return None
    
    def on_tag_select(self, event):
        """Handle tag selection in the listbox"""
        tag_id = self.get_selected_tag_id()
        if tag_id:
            self.load_tag_data(tag_id)
    
    def load_tag_data(self, tag_id):
        """Load tag data into the editor fields"""
        self.current_tag = tag_id
        tag_data = self.tags[tag_id]
        
        self.tag_id_var.set(tag_id)
        self.command_var.set(tag_data.get('command', ''))
        self.line1_var.set(tag_data.get('line1', ''))
        self.line2_var.set(tag_data.get('line2', ''))
        self.line3_var.set(tag_data.get('line3', ''))
        self.line4_var.set(tag_data.get('line4', ''))
        self.terminate_var.set(tag_data.get('terminate', ''))
    
    def new_tag(self):
        """Create a new tag entry"""
        tag_id = simpledialog.askstring("New Tag", "Enter Tag ID:")
        if tag_id and tag_id not in self.tags:
            self.tags[tag_id] = {
                'command': '',
                'line1': 'New Tag',
                'line2': 'Configure me',
                'line3': '',
                'line4': tag_id,
                'terminate': ''
            }
            self.save_tags()
            self.refresh_tag_list()
            
            # Select the new tag
            display_items = self.get_display_items()
            for i, (tid, _) in enumerate(display_items):
                if tid == tag_id:
                    self.tag_listbox.selection_set(i)
                    self.load_tag_data(tag_id)
                    break
    
    def delete_tag(self):
        """Delete the currently selected tag"""
        tag_id = self.get_selected_tag_id()
        if tag_id:
            if messagebox.askyesno("Delete Tag", f"Delete tag '{tag_id}'?"):
                del self.tags[tag_id]
                self.save_tags()
                self.refresh_tag_list()
                self.clear_editor()
    
    def save_current_tag(self):
        """Save changes to the current tag"""
        if self.current_tag:
            # If tag ID changed, create new entry and delete old
            new_tag_id = self.tag_id_var.get().strip()
            if new_tag_id != self.current_tag:
                if new_tag_id in self.tags and new_tag_id != self.current_tag:
                    messagebox.showerror("Error", "Tag ID already exists!")
                    return
                # Move to new ID
                self.tags[new_tag_id] = self.tags[self.current_tag]
                del self.tags[self.current_tag]
                self.current_tag = new_tag_id
            
            # Update data
            self.tags[self.current_tag] = {
                'command': self.command_var.get(),
                'line1': self.line1_var.get(),
                'line2': self.line2_var.get(),
                'line3': self.line3_var.get(),
                'line4': self.line4_var.get(),
                'terminate': self.terminate_var.get()
            }
            
            self.save_tags()
            self.refresh_tag_list()
            messagebox.showinfo("Success", "Tag saved successfully!")
    
    def clear_editor(self):
        """Clear the editor fields"""
        self.current_tag = None
        self.tag_id_var.set('')
        self.command_var.set('')
        self.line1_var.set('')
        self.line2_var.set('')
        self.line3_var.set('')
        self.line4_var.set('')
        self.terminate_var.set('')
    
    def browse_command(self):
        """Browse for an executable file"""
        filename = filedialog.askopenfilename(
            title="Select Application",
            filetypes=[("Executable files", "*.sh *.py *.desktop"), ("All files", "*.*")]
        )
        if filename:
            self.command_var.set(filename)
    
    def test_launch(self):
        """Test the launch command"""
        command = self.command_var.get()
        if command:
            try:
                subprocess.Popen(command, shell=True)
                messagebox.showinfo("Test", "Launch command executed!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to execute: {e}")
        else:
            messagebox.showwarning("Warning", "No launch command specified")
    
    def test_terminate(self):
        """Test the terminate command (placeholder)"""
        command = self.terminate_var.get()
        if command:
            messagebox.showinfo("Info", f"Terminate command would execute: {command}")
        else:
            messagebox.showinfo("Info", "No custom terminate command - would use standard termination")
    
    def quit_app(self):
        """Quit the application"""
        self.singleton.cleanup()
        self.root.quit()

def main():
    root = tk.Tk()
    app = TagManager(root)
    
    # Start on tags tab by default
    if len(sys.argv) == 1 and app.singleton.is_primary:
        app.notebook.select(0)  # Switch to tags tab (index 0)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nShutting down RFIDisk Manager...")
    finally:
        app.singleton.cleanup()

if __name__ == "__main__":
    main()
