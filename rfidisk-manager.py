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

TAGS_FILE = "rfidisk_tags.json"
CONFIG_FILE = "rfidisk_config.json"
LOCK_PORT = 47821  # Arbitrary port for instance checking
VERSION = "0.92"  # Version number

class SingletonApp:
    """Prevent multiple instances and handle inter-process communication"""
    def __init__(self):
        self.socket = None
        self.is_primary = False
        
    def acquire_lock(self):
        """Try to bind to a socket - if successful, we're the first instance"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('localhost', LOCK_PORT))
            self.socket.listen(1)
            self.is_primary = True
            return True
        except socket.error:
            # Another instance is already running
            return False
    
    def send_to_primary(self, tag_id=None):
        """Send a message to the primary instance"""
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
        """Check for incoming messages from other instances (non-blocking)"""
        if not self.is_primary or not self.socket:
            return None
            
        try:
            self.socket.settimeout(0.1)  # Non-blocking
            client, addr = self.socket.accept()
            data = client.recv(1024).decode().strip()
            client.close()
            return data
        except socket.timeout:
            return None
        except socket.error:
            return None
    
    def cleanup(self):
        """Clean up socket resources"""
        if self.socket:
            self.socket.close()
            self.socket = None

class TagManager:
    def __init__(self, root):
        self.root = root
        self.root.title(f"RFIDisk Tag Manager v{VERSION}")
        self.root.geometry("900x750")  # Increased height for warning message
        
        # Singleton management
        self.singleton = SingletonApp()
        self.setup_singleton()
        
        self.tags = self.load_tags()
        self.config = self.load_config()
        self.current_tag = None
        self.display_mode = "line1"  # Changed default to "Show Names"
        
        self.create_widgets()
        self.refresh_tag_list()
        self.setup_ipc_handler()
    
    def setup_singleton(self):
        """Handle singleton instance logic"""
        # Check command line arguments
        edit_tag_id = None
        if len(sys.argv) > 2 and sys.argv[1] == "--edit":
            edit_tag_id = sys.argv[2]
        
        # Try to acquire lock - if we can't, send message to primary instance and exit
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
            
            # Always exit if we're not the primary instance
            sys.exit(0)
        
        # We are the primary instance - process command line args if any
        if edit_tag_id:
            # Schedule the tag edit after the UI is fully loaded
            self.root.after(500, lambda: self.focus_and_edit_tag(edit_tag_id))
    
    def setup_ipc_handler(self):
        """Set up periodic check for inter-process communication"""
        def check_ipc():
            message = self.singleton.check_for_messages()
            if message:
                self.handle_ipc_message(message)
            self.root.after(100, check_ipc)  # Check every 100ms
        
        self.root.after(100, check_ipc)
    
    def handle_ipc_message(self, message):
        """Handle messages from other instances"""
        print(f"Received IPC message: {message}")
        
        if message.startswith("EDIT:"):
            tag_id = message[5:]  # Remove "EDIT:" prefix
            self.focus_and_edit_tag(tag_id)
        elif message == "FOCUS":
            self.bring_to_front()
    
    def focus_and_edit_tag(self, tag_id):
        """Bring window to front and edit specified tag"""
        self.bring_to_front()
        
        # Ensure the tag exists or create it
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
        
        # Switch to tags tab and select the tag
        self.notebook.select(0)  # Switch to tags tab
        
        # Find and select the tag in the list
        display_items = self.get_display_items()
        for i, (current_tag_id, _) in enumerate(display_items):
            if current_tag_id == tag_id:
                self.tag_listbox.selection_clear(0, tk.END)
                self.tag_listbox.selection_set(i)
                self.tag_listbox.see(i)
                self.load_tag_data(tag_id)
                break
        
        # Flash the window to get user's attention
        self.flash_window()
        
        # Show notification
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
            if count < 6:  # Flash 3 times
                if count % 2 == 0:
                    self.root.configure(background='#ff4444')  # Red flash
                else:
                    self.root.configure(background=original_color)
                self.root.after(200, lambda: flash(count + 1))
            else:
                self.root.configure(background=original_color)
        
        flash()
    
    def create_warning_label(self, parent):
        """Create warning label with red bold text"""
        warning_frame = ttk.Frame(parent)
        warning_frame.pack(fill=tk.X, padx=5, pady=10)
        
        warning_text = [
            "This software can automatically launch applications.",
            "Make sure your configuration only contains",
            "trusted commands to avoid potential security risks.",
            "",
            "WARNING! USE AT YOUR OWN RISK!!!"
        ]
        
        for line in warning_text:
            if line == "WARNING! USE AT YOUR OWN RISK!!!":
                # Make the last line extra prominent
                label = tk.Label(warning_frame, text=line, fg='red', font=('TkDefaultFont', 9, 'bold'), justify=tk.CENTER)
            elif line == "":
                # Empty line for spacing
                label = tk.Label(warning_frame, text=" ", fg='red', font=('TkDefaultFont', 9, 'bold'), justify=tk.CENTER)
            else:
                label = tk.Label(warning_frame, text=line, fg='red', font=('TkDefaultFont', 9, 'bold'), justify=tk.CENTER)
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
                "auto_launch_manager": True
            }
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    if "settings" in user_config:
                        default_config["settings"].update(user_config["settings"])
                print(f"Loaded config from {CONFIG_FILE}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load config: {e}")
        else:
            # Create default config file
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
        
        self.setup_tags_tab()
        self.setup_settings_tab()
    
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
        
        # Quit button at bottom of left panel
        ttk.Button(left_frame, text="Quit", command=self.quit_app).pack(fill=tk.X, pady=(10, 0))
        
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
        
        # Serial port setting
        ttk.Label(settings_container, text="Serial Port:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.serial_port_var = tk.StringVar(value=self.config["settings"].get("serial_port", "/dev/ttyACM0"))
        self.serial_port_entry = ttk.Entry(settings_container, textvariable=self.serial_port_var, width=30)
        self.serial_port_entry.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5, padx=5)
        ttk.Button(settings_container, text="Detect", command=self.detect_serial_ports).grid(row=0, column=2, padx=5)
        
        # Removal delay
        ttk.Label(settings_container, text="Removal Delay (seconds):").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.removal_delay_var = tk.DoubleVar(value=self.config["settings"].get("removal_delay", 0.0))
        self.removal_delay_spinbox = ttk.Spinbox(settings_container, from_=0.0, to=10.0, increment=0.1, 
                                                textvariable=self.removal_delay_var, width=10)
        self.removal_delay_spinbox.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(settings_container, text="(Time to prevent accidental disk removal)").grid(row=1, column=2, sticky=tk.W, padx=5)
        
        # Desktop notifications
        ttk.Label(settings_container, text="Desktop Notifications:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.notifications_var = tk.BooleanVar(value=self.config["settings"].get("desktop_notifications", True))
        self.notifications_check = ttk.Checkbutton(settings_container, variable=self.notifications_var, 
                                                  command=self.toggle_notification_settings)
        self.notifications_check.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Notification timeout
        ttk.Label(settings_container, text="Notification Timeout (ms):").grid(row=3, column=0, sticky=tk.W, pady=5, padx=5)
        self.notification_timeout_var = tk.IntVar(value=self.config["settings"].get("notification_timeout", 8000))
        self.notification_timeout_spinbox = ttk.Spinbox(settings_container, from_=1000, to=30000, increment=1000, 
                                                       textvariable=self.notification_timeout_var, width=10)
        self.notification_timeout_spinbox.grid(row=3, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(settings_container, text="(How long notifications stay visible)").grid(row=3, column=2, sticky=tk.W, padx=5)
        
        # Auto launch manager
        ttk.Label(settings_container, text="Auto Launch Manager:").grid(row=4, column=0, sticky=tk.W, pady=5, padx=5)
        self.auto_launch_var = tk.BooleanVar(value=self.config["settings"].get("auto_launch_manager", True))
        ttk.Checkbutton(settings_container, variable=self.auto_launch_var).grid(row=4, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(settings_container, text="(Auto-open manager for new tags)").grid(row=4, column=2, sticky=tk.W, padx=5)
        
        # Save settings button
        ttk.Button(settings_container, text="Save Settings", command=self.save_settings).grid(row=5, column=1, pady=20)
        
        # Status label
        self.settings_status_var = tk.StringVar(value="Settings loaded")
        ttk.Label(settings_container, textvariable=self.settings_status_var).grid(row=6, column=0, columnspan=3, pady=5)
        
        # Set initial state for notification timeout
        self.toggle_notification_settings()
        
        settings_container.columnconfigure(1, weight=1)
        
        # Add warning label after main content
        self.create_warning_label(main_container)
    
    def toggle_notification_settings(self):
        """Enable/disable notification timeout based on notifications checkbox"""
        if self.notifications_var.get():
            self.notification_timeout_spinbox.config(state="normal")
        else:
            self.notification_timeout_spinbox.config(state="disabled")
    
    def detect_serial_ports(self):
        """Detect available serial ports"""
        import glob
        ports = []
        
        # Common Linux serial ports
        possible_ports = [
            "/dev/ttyACM*",  # Arduino Uno, Leonardo
            "/dev/ttyUSB*",  # USB serial adapters
            "/dev/ttyS*",    # Physical serial ports
            "/dev/rfidisk"   # Custom udev rule
        ]
        
        for pattern in possible_ports:
            ports.extend(glob.glob(pattern))
        
        if ports:
            port_list = "\n".join(ports)
            messagebox.showinfo("Detected Serial Ports", 
                              f"Available serial ports:\n\n{port_list}\n\nCurrent: {self.serial_port_var.get()}")
        else:
            messagebox.showwarning("No Serial Ports", "No serial ports detected. Make sure your Arduino is connected.")
    
    def save_settings(self):
        """Save configuration settings"""
        try:
            # Update config with current values
            self.config["settings"]["serial_port"] = self.serial_port_var.get().strip()
            self.config["settings"]["removal_delay"] = float(self.removal_delay_var.get())
            self.config["settings"]["desktop_notifications"] = bool(self.notifications_var.get())
            self.config["settings"]["notification_timeout"] = int(self.notification_timeout_var.get())
            self.config["settings"]["auto_launch_manager"] = bool(self.auto_launch_var.get())
            
            # Save to file
            if self.save_config():
                self.settings_status_var.set("Settings saved successfully!")
                messagebox.showinfo("Success", "Configuration saved!\n\nRestart RFIDisk for changes to take effect.")
            else:
                self.settings_status_var.set("Failed to save settings")
                
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value: {e}")
            self.settings_status_var.set("Error: Invalid values")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
            self.settings_status_var.set("Error saving settings")
    
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
    
    # Start on tags tab by default (changed from settings tab)
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
