#!/usr/bin/env python3
import serial
import time
import subprocess
import sys
import json
import os
import platform
import psutil
import signal
import argparse

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Use absolute paths for config files
CONFIG_FILE = os.path.join(SCRIPT_DIR, "rfidisk_config.json")
TAGS_FILE = os.path.join(SCRIPT_DIR, "rfidisk_tags.json")
SHARED_FILE = "/dev/shm/rfidisk"
LOAD_FILE = "/dev/shm/rfidisk-load"

# Version number
VERSION = "0.95"

# Default configuration
default_config = {
    "settings": {
        "serial_port": "/dev/ACM0",
        "removal_delay": 0.0,
        "desktop_notifications": True,
        "notification_timeout": 8000,
        "auto_launch_manager": True,
        "disable_autolaunch": False
    }
}

# Default tags with example entry
default_tags = {
    "example": {
        "command": "",
        "line1": "Example Tag",
        "line2": "Configure me",
        "line3": "Edit rfidisk_tags.json",
        "line4": "example",
        "terminate": ""
    }
}

def load_config():
    """Load configuration from separate files"""
    config = default_config.copy()
    tags = default_tags.copy()
    
    # Load settings
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                user_config = json.load(f)
                # Merge settings while preserving structure
                if "settings" in user_config:
                    config["settings"].update(user_config["settings"])
        except Exception as e:
            print(f"Error loading config: {e}")
    else:
        # Create default config file
        save_config(config)
        print(f"Created default config file: {CONFIG_FILE}")
    
    # Load tags
    if os.path.exists(TAGS_FILE):
        try:
            with open(TAGS_FILE, 'r') as f:
                tags = json.load(f)
                # Ensure all entries have the terminate field
                for tag_id, tag_config in tags.items():
                    if "terminate" not in tag_config:
                        tag_config["terminate"] = ""
        except Exception as e:
            print(f"Error loading tags: {e}")
    else:
        # Create default tags file with example entry
        save_tags(tags)
        print(f"Created default tags file: {TAGS_FILE}")
    
    return config, tags

def save_config(config):
    """Save configuration to config file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def save_tags(tags):
    """Save tags to tags file"""
    try:
        with open(TAGS_FILE, 'w') as f:
            json.dump(tags, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving tags: {e}")
        return False

class RFIDLauncher:
    def __init__(self):
        self.config, self.tags = load_config()
        self.serial_conn = None
        self.active_tag = None
        self.active_process = None
        self.process_tree_pids = []
        self.running = True
        self.last_unknown_tag = None
        self.serial_error_count = 0
        self.max_serial_errors = 5
        self.reconnecting = False
        self.last_display_state = ("Ready", "Insert Disk", "", f"RFIDisk v{VERSION}")
        
        # State tracking in RAM only
        self.app_was_launched_by_us = False
        self.recovery_mode = False  # Prevent notifications during recovery
        self.pending_load_command = None  # Track command waiting for load

    def create_shared_files(self):
        """Create the shared RAM files upon initialization"""
        try:
            # Write initial ready state to shared file
            content = f"Ready|Insert Disk||RFIDisk v{VERSION}"
            with open(SHARED_FILE, 'w') as f:
                f.write(content)
            print(f"Created shared display file: {SHARED_FILE}")
            
            # Create empty load command file
            with open(LOAD_FILE, 'w') as f:
                f.write("")
            print(f"Created shared load file: {LOAD_FILE}")
            
            return True
        except Exception as e:
            print(f"Error creating shared files: {e}")
            return False

    def update_shared_file(self, line1, line2, line3="", line4=""):
        """Update the shared display file with current display info"""
        try:
            # Format: line1|line2|line3|line4
            content = f"{line1}|{line2}|{line3}|{line4}"
            with open(SHARED_FILE, 'w') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error updating shared file: {e}")
            return False

    def write_load_command(self, command):
        """Write the launch command to the load file"""
        try:
            with open(LOAD_FILE, 'w') as f:
                f.write(command)
            self.pending_load_command = command
            print(f"Written load command: {command}")
            return True
        except Exception as e:
            print(f"Error writing load command: {e}")
            return False

    def clear_load_command(self):
        """Clear the load command file"""
        try:
            with open(LOAD_FILE, 'w') as f:
                f.write("")
            self.pending_load_command = None
            return True
        except Exception as e:
            print(f"Error clearing load command: {e}")
            return False

    def check_load_command(self):
        """Check if there's a pending load command to execute"""
        try:
            if os.path.exists(LOAD_FILE):
                with open(LOAD_FILE, 'r') as f:
                    lines = f.read().strip().split('\n')
                
                if len(lines) >= 2 and lines[1] == "TRIGGER":
                    command = lines[0].strip()
                    print(f"Load trigger detected for command: {command}")
                    # Clear the trigger but keep the command
                    with open(LOAD_FILE, 'w') as f:
                        f.write(command)
                    return command
            return None
        except Exception as e:
            print(f"Error checking load command: {e}")
            return None

    def delete_shared_files(self):
        """Delete the shared RAM files on exit"""
        try:
            if os.path.exists(SHARED_FILE):
                os.remove(SHARED_FILE)
                print(f"Deleted shared display file: {SHARED_FILE}")
            if os.path.exists(LOAD_FILE):
                os.remove(LOAD_FILE)
                print(f"Deleted shared load file: {LOAD_FILE}")
            return True
        except Exception as e:
            print(f"Error deleting shared files: {e}")
            return False

    def launch_tag_manager(self, tag_id):
        """Launch the tag manager GUI for configuring a new tag"""
        if not self.config["settings"].get("auto_launch_manager", True):
            return False
            
        manager_script = os.path.join(SCRIPT_DIR, "rfidisk-manager.py")
        if os.path.exists(manager_script):
            try:
                subprocess.Popen([sys.executable, manager_script, "--edit", tag_id])
                print(f"Launched tag manager for tag: {tag_id}")
                return True
            except Exception as e:
                print(f"Failed to launch tag manager: {e}")
        else:
            print(f"Tag manager not found at: {manager_script}")
        return False

    def create_or_update_new_entry(self, tag_id):
        """Create or update a new entry for unknown tags"""
        new_entry_id = None
        
        # Check if there's already a "new entry"
        for existing_id, entry in self.tags.items():
            if entry.get("line1") == "new entry":
                new_entry_id = existing_id
                break
        
        if new_entry_id:
            # Update existing new entry with new tag ID
            if new_entry_id != tag_id:
                self.tags[tag_id] = self.tags[new_entry_id]
                del self.tags[new_entry_id]
                print(f"Updated new entry: {tag_id}")
        else:
            # Create new entry with terminate field
            self.tags[tag_id] = {
                "command": "",
                "line1": "new entry",
                "line2": "configure me",
                "line3": "edit rfidisk_tags.json",
                "line4": tag_id,
                "terminate": ""
            }
            print(f"New entry: {tag_id}")
        
        # Save the updated tags
        self.save_tags()
        return tag_id

    def connect_serial(self):
        """Connect to serial port with state recovery"""
        port = self.config["settings"].get("serial_port", "/dev/rfidisk")
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
            
            print(f"Connecting to {port}...")
            self.serial_conn = serial.Serial(port, 9600, timeout=0.1)
            time.sleep(2.5)
            
            # Clear any boot messages
            if self.serial_conn.in_waiting > 0:
                self.serial_conn.read(self.serial_conn.in_waiting)
            
            # Wait for Arduino ready
            start_time = time.time()
            while time.time() - start_time < 3:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if "OK" in line:
                        print("Arduino ready!")
                        self.serial_error_count = 0
                        
                        # Create shared files when Arduino is ready
                        self.create_shared_files()
                        
                        # STATE RECOVERY: Restore previous state after reconnection
                        if self.reconnecting:
                            time.sleep(0.5)
                            self.recover_after_disconnection()
                            self.reconnecting = False
                            
                        return True
            
            print("Connected (no OK message)")
            self.serial_error_count = 0
            
            # Create shared files even without OK message
            self.create_shared_files()
            
            # STATE RECOVERY: Still restore state even without OK message
            if self.reconnecting:
                time.sleep(0.5)
                self.recover_after_disconnection()
                self.reconnecting = False
                
            return True
            
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.serial_conn = None
            return False

    def recover_after_disconnection(self):
        """Recover state after serial disconnection - SILENT RECOVERY"""
        print("Silent recovery after disconnection...")
        
        # Enable recovery mode to suppress notifications
        self.recovery_mode = True
        
        # Check if we had an active tag and we launched the app
        if self.active_tag and self.app_was_launched_by_us:
            tag_id = self.active_tag
            print(f"Recovering active tag: {tag_id} (app was launched by us)")
            
            # Reload config and tags to get any changes
            self.config, self.tags = load_config()
            
            tag_config = self.tags.get(tag_id)
            if tag_config:
                # Determine icon type based on command
                icon_type = self.get_icon_type(tag_config.get("command", ""))
                # Update the display silently, no notifications, no relaunch
                self.send_display_command(
                    tag_config.get("line1", "App"), 
                    tag_config.get("line2", ""),
                    tag_config.get("line3", ""),
                    tag_config.get("line4", ""),
                    icon_type  
                )
                print(f"Silently restored display for {tag_id}")
            else:
                # Unknown tag - show error
                self.send_display_command(
                    "State Error",
                    "Tag config missing",
                    "Check rfidisk_tags.json",
                    tag_id,
                    "0"
                )
        else:
            # No active tag or app wasn't launched by us, restore ready state
            self.active_tag = None
            self.app_was_launched_by_us = False
            self.send_display_command("Ready", "Insert Disk", "", f"RFIDisk v{VERSION}", "0")
            print("Restored ready state")
        
        # Disable recovery mode after recovery is complete
        self.recovery_mode = False

    def get_icon_type(self, command):
        """Determine icon type based on command"""
        if command.lower().startswith("steam"):
            return "2"  # Steam icon
        elif command.strip():  # Any other command
            return "1"  # Floppy icon
        else:  # No command or empty
            return "0"  # No icon

    def reconnect_serial(self):
        """Attempt to reconnect to serial port"""
        print("Attempting to reconnect...")
        self.serial_error_count += 1
        self.reconnecting = True
        
        if self.serial_error_count > self.max_serial_errors:
            print("Too many serial errors, giving up...")
            return False
            
        # Close existing connection
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except:
                pass
            self.serial_conn = None
        
        # Wait before reconnecting
        time.sleep(2)
        return self.connect_serial()

    def send_display_command(self, line1, line2, line3="", line4="", icon_type="0"):
        """Send display command with error handling and state tracking"""
        # Store the current display state
        self.last_display_state = (line1, line2, line3, line4)
        
        # Update the shared RAM file with the current display info
        self.update_shared_file(line1, line2, line3, line4)
        
        # Truncate strings
        line1_trunc = line1[:20]
        line2_trunc = line2[:20]
        line3_trunc = line3[:14]
        line4_trunc = line4[:14]
        
        if not self.serial_conn or not self.serial_conn.is_open:
            if not self.reconnect_serial():
                return False
            
        try:
            # Escape any pipes in the strings
            line1_esc = line1_trunc.replace('|', '_')
            line2_esc = line2_trunc.replace('|', '_')
            line3_esc = line3_trunc.replace('|', '_')
            line4_esc = line4_trunc.replace('|', '_')
            
            # Updated command: D|line1|line2|line3|line4|iconType
            command = f"D|{line1_esc}|{line2_esc}|{line3_esc}|{line4_esc}|{icon_type}\n"
            self.serial_conn.write(command.encode())
            self.serial_conn.flush()
            return True
            
        except (serial.SerialException, OSError) as e:
            print(f"Serial write error: {e}")
            if not self.reconnect_serial():
                return False
            return False
        except Exception as e:
            print(f"Display error: {e}")
            return False

    def send_desktop_notification(self, title, message):
        """Send desktop notification on Linux systems - SUPPRESSED DURING RECOVERY"""
        # Never send notifications during recovery
        if self.recovery_mode or self.reconnecting:
            return False
            
        if not self.config["settings"].get("desktop_notifications", True):
            return False
            
        try:
            # Use the script directory to find the icon
            icon_path = os.path.join(SCRIPT_DIR, "floppy.png")
            
            # Check if notify-send is available
            result = subprocess.run(['which', 'notify-send'], capture_output=True)
            if result.returncode != 0:
                return False
            
            # Get notification timeout from config, default to 8000ms
            notification_timeout = str(self.config["settings"].get("notification_timeout", 8000))
                
            # Send the notification
            subprocess.run([
                'notify-send',
                '-i', icon_path,
                title,
                message,
                '-t', notification_timeout
            ])
            return True
            
        except Exception as e:
            return False

    def get_full_process_tree(self, root_pid):
        try:
            process_tree = []
            root_process = psutil.Process(root_pid)
            process_tree.append(root_pid)
            for child in root_process.children(recursive=True):
                process_tree.append(child.pid)
            return process_tree
        except psutil.NoSuchProcess:
            return []

    def is_process_running(self):
        """Check if the active process is still running"""
        if not self.active_process:
            return False
        return self.active_process.poll() is None

    def launch_application(self, app_command, tag_line1, tag_line2):
        # Don't launch if we already launched this app
        if self.app_was_launched_by_us and self.active_tag:
            print(f"App already launched by us for tag: {self.active_tag}")
            return self.active_process
            
        try:
            # Send desktop notification (only on first launch)
            self.send_desktop_notification("RFIDisk Inserted", f"{tag_line1}\n{tag_line2}")
            
            process = subprocess.Popen(
                app_command, 
                shell=True,
                preexec_fn=os.setsid
            )
            
            self.active_process = process
            self.app_was_launched_by_us = True  # Mark that we launched this app
            time.sleep(1.0)
            
            self.process_tree_pids = self.get_full_process_tree(process.pid)
            print(f"Launched: {process.pid}")
            
            return process
        except Exception as e:
            print(f"Launch error: {e}")
            self.send_desktop_notification("Error", f"Failed: {tag_line1}")
            return None

    def terminate_application(self, tag_config):
        """Terminate application using custom command or fallback method"""
        terminate_command = tag_config.get("terminate", "").strip()
        
        if terminate_command:
            # Use custom terminate command
            print(f"Using custom terminate command: {terminate_command}")
            try:
                process = subprocess.Popen(
                    terminate_command, 
                    shell=True,
                    preexec_fn=os.setsid
                )
                # Wait a bit for the terminate command to take effect
                time.sleep(2)
                print("Custom terminate command executed")
            except Exception as e:
                print(f"Custom terminate command failed: {e}")
                # Fall back to standard method if custom command fails
                self.terminate_standard()
        else:
            # Use standard termination method
            self.terminate_standard()

    def terminate_standard(self):
        """Standard process termination method"""
        if not self.active_process:
            return
            
        print(f"Standard termination: {self.active_process.pid}")
        
        try:
            try:
                os.killpg(os.getpgid(self.active_process.pid), signal.SIGTERM)
                time.sleep(2)
                if self.active_process.poll() is None:
                    os.killpg(os.getpgid(self.active_process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
                    
        except Exception as e:
            print(f"Standard termination error: {e}")
        finally:
            self.active_process = None
            self.process_tree_pids = []
            # NEW: Reset launch tracking when process is terminated
            self.app_was_launched_by_us = False

    def close_current_app(self):
        """Close current app using appropriate termination method"""
        if not self.active_tag:
            return
            
        # Get the tag config to check for custom terminate command
        tag_config = self.tags.get(self.active_tag, {})
        self.terminate_application(tag_config)
        
        # Reset launch tracking
        self.app_was_launched_by_us = False

    def process_serial_data(self, data):
        # Ignore RFID events during reconnection to prevent double-launching
        if self.reconnecting:
            print(f"Ignoring RFID during reconnect: {data}")
            return
            
        print(f"RFID: {data}")
        
        if data.startswith("ON:"):
            tag_id = data[3:].strip().lower()
            print(f"Tag: {tag_id}")
            
            # Don't process the same tag if app is already running and was launched by us
            if (self.active_tag == tag_id and 
                self.app_was_launched_by_us and
                self.is_process_running()):  # NEW: Also check if process is actually running
                print(f"Tag {tag_id} already active with app launched by us, ignoring")
                return
                
            # Reload config and tags to get any changes
            self.config, self.tags = load_config()
            
            tag_config = self.tags.get(tag_id)
            if tag_config:
                # Only close current app if it's a different tag
                if self.active_process and self.active_tag != tag_id:
                    print("Closing previous app...")
                    self.close_current_app()
                    time.sleep(0.5)
                
                self.active_tag = tag_id
                
                # Determine icon type based on command
                icon_type = self.get_icon_type(tag_config.get("command", ""))
                
                # Update display with appropriate icon
                self.send_display_command(
                    tag_config.get("line1", "App"), 
                    tag_config.get("line2", ""),
                    tag_config.get("line3", ""),
                    tag_config.get("line4", ""),
                    icon_type
                )
                
                # Check if command is empty and launch manager if needed
                command = tag_config.get("command", "").strip()
                if not command:
                    # Empty command detected - launch manager for configuration
                    print(f"Empty command detected for tag {tag_id}, launching manager")
                    self.send_display_command(
                        "Please configure",
                        "Tag (executable",
                        "not found)",
                        tag_id,
                        "0"
                    )
                    
                    if self.launch_tag_manager(tag_id):
                        self.send_desktop_notification(
                            "Configuration Required", 
                            f"Please configure tag {tag_id}\n(executable not found)"
                        )
                        print(f"Launched tag manager for unconfigured tag: {tag_id}")
                    else:
                        self.send_display_command(
                            "Config Error",
                            "Manager not found",
                            "Edit manually:",
                            tag_id,
                            "0"
                        )
                
                # Handle autolaunch logic with load command file
                elif command and not self.app_was_launched_by_us:
                    if self.config["settings"].get("disable_autolaunch", False):
                        # Autolaunch disabled - write command to load file
                        print(f"Autolaunch disabled - writing command to load file")
                        self.write_load_command(command)
                        self.send_desktop_notification(
                            "RFIDisk Ready", 
                            f"{tag_config.get('line1', 'App')} ready\nUse 'rfidisk.py --load' to launch"
                        )
                    else:
                        # Autolaunch enabled - launch directly
                        print(f"Launch: {tag_config['command']}")
                        self.launch_application(
                            tag_config['command'], 
                            tag_config.get("line1", "App"),
                            tag_config.get("line2", "")
                        )
                elif self.app_was_launched_by_us:
                    print("App already launched by us, not relaunching")
                    
            else:
                # Unknown tag - create/update new entry
                self.active_tag = tag_id
                self.last_unknown_tag = tag_id
                new_tag_id = self.create_or_update_new_entry(tag_id)
                
                # Show new entry screen
                self.send_display_command(
                    "new tag detected",
                    "launching config",
                    "please wait...",
                    new_tag_id,
                    "0"
                )
                
                # Auto-launch tag manager for configuration
                if self.launch_tag_manager(new_tag_id):
                    self.send_desktop_notification("New Tag", f"Configuring tag {new_tag_id}")
                    print(f"Auto-launched tag manager for new tag: {new_tag_id}")
                else:
                    # Fallback if manager can't be launched
                    self.send_display_command(
                        "new entry",
                        "configure me",
                        "edit rfidisk_tags.json",
                        new_tag_id,
                        "0"
                    )
                    self.send_desktop_notification("New Tag", f"Tag {new_tag_id} added - configure manually")
                
                print(f"New tag: {tag_id}")
                
        elif data.startswith("OF:"):
            tag_id = data[3:].strip().lower()
            print(f"Remove: {tag_id}")
            
            if tag_id == self.active_tag:
                removal_delay = self.config["settings"].get("removal_delay", 2.0)
                print(f"Wait {removal_delay}s...")
                time.sleep(removal_delay)
                if self.active_tag == tag_id:
                    self.close_current_app()
                    self.active_tag = None
                    self.clear_load_command()  # Clear load command on disk removal
                    self.send_display_command("Ready", "Insert Disk", "", f"RFIDisk v{VERSION}", "0")
                    print("App closed")

    def read_serial(self):
        """Read from serial with robust error handling"""
        if not self.serial_conn or not self.serial_conn.is_open:
            if not self.reconnect_serial():
                return None
        
        try:
            if self.serial_conn.in_waiting > 0:
                data = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                if data:
                    self.serial_error_count = 0  # Reset counter on successful read
                    return data
        except (serial.SerialException, OSError) as e:
            print(f"Serial read error: {e}")
            if not self.reconnect_serial():
                return None
        except Exception as e:
            print(f"Unexpected serial error: {e}")
            
        return None

    def save_tags(self):
        """Save tags to file"""
        return save_tags(self.tags)

    def run(self):
        print(f"Starting RFIDisk v.{VERSION}...")
        
        # Check if autolaunch is disabled
        if self.config["settings"].get("disable_autolaunch", False):
            print("AUTOLAUNCH DISABLED - Inserting disks will not auto-launch apps")
            print("Use 'python3 rfidisk.py --load' to launch the current app")
        
        if not self.connect_serial():
            return
        
        print("Ready")
        
        # Send initial display with icon_type=0 (no icon)
        self.send_display_command("Ready", "Insert Disk", "", f"RFIDisk v{VERSION}", "0")
        
        try:
            load_check_counter = 0
            process_check_counter = 0
            while self.running:
                # Check for serial data
                data = self.read_serial()
                if data:
                    self.process_serial_data(data)
                
                # NEW: Check if process is still running (every 2 seconds)
                process_check_counter += 1
                if process_check_counter >= 20:  # 20 * 0.1s = 2 seconds
                    process_check_counter = 0
                    if (self.app_was_launched_by_us and 
                        self.active_process and 
                        not self.is_process_running()):
                        print("Process is no longer running - resetting launch tracking")
                        self.app_was_launched_by_us = False
                        self.active_process = None
                        self.process_tree_pids = []
                
                # Check for load commands every 1 second (instead of every loop)
                load_check_counter += 1
                if load_check_counter >= 10:  # 10 * 0.1s = 1 second
                    load_check_counter = 0
                    load_command = self.check_load_command()
                    if load_command and self.active_tag and not self.app_was_launched_by_us:
                        print(f"Executing load command: {load_command}")
                        tag_config = self.tags.get(self.active_tag, {})
                        success = self.launch_application(
                            load_command,
                            tag_config.get("line1", "App"),
                            tag_config.get("line2", "")
                        )
                        if success:
                            print("App launched successfully via load command")
                        else:
                            print("Failed to launch app via load command")
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.running = False
        finally:
            # Ensure shutdown is always called
            self.shutdown()

    def shutdown(self):
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except:
                pass
        # Delete the shared RAM files on shutdown
        self.delete_shared_files()
        print(f"RFIDisk v.{VERSION} stopped")

def handle_load_command():
    """Handle the --load command by writing the trigger"""
    try:
        if not os.path.exists(LOAD_FILE):
            print("No app ready to load - insert a disk first")
            return False
        
        with open(LOAD_FILE, 'r') as f:
            current_content = f.read().strip()
        
        if current_content:
            # Add trigger to existing command
            with open(LOAD_FILE, 'w') as f:
                f.write(f"{current_content}\nTRIGGER")
            print("Load trigger activated - daemon should launch the app")
            return True
        else:
            print("No app ready to load - insert a disk first")
            return False
            
    except Exception as e:
        print(f"Error handling load command: {e}")
        return False

def handle_list_command():
    """Handle the --list command by displaying formatted info"""
    try:
        if not os.path.exists(SHARED_FILE):
            print("RFIDisk daemon not running or no disk inserted")
            return False
        
        # Read display info
        with open(SHARED_FILE, 'r') as f:
            display_content = f.read().strip()

        # Parse display lines
        parts = display_content.split('|')
        line1 = parts[0] if len(parts) > 0 else ""
        line2 = parts[1] if len(parts) > 1 else ""
        line3 = parts[2] if len(parts) > 2 else ""
        line4 = parts[3] if len(parts) > 3 else ""

        # Check if no disk is inserted (ready state)
        if line1 == "Ready" and line2 == "Insert Disk":
            print(f"RFIDisk v{VERSION}\n")
            print("No disk")
            return True
        
        # Get launch command
        launch_command = ""
        if os.path.exists(LOAD_FILE):
            with open(LOAD_FILE, 'r') as f:
                launch_content = f.read().strip()
                # Remove TRIGGER line if present
                if '\n' in launch_content:
                    launch_command = launch_content.split('\n')[0]
                else:
                    launch_command = launch_content
        
        # Get terminate command and tag ID (if we can find the active tag)
        terminate_command = ""
        tag_id = ""
        try:
            # Try to find the active tag by matching line1 with tag configurations
            config, tags = load_config()
            for current_tag_id, tag_config in tags.items():
                if (tag_config.get('line1', '') == line1 and 
                    tag_config.get('line2', '') == line2):
                    terminate_command = tag_config.get('terminate', '')
                    tag_id = current_tag_id
                    break
        except:
            pass  # If we can't load tags, just leave terminate_command empty
        
        # Output formatted information
        print(f"RFIDisk v{VERSION}\n")
        print(f"Tag ID:       {tag_id}")
        print(f"Launch:       {launch_command}")
        print(f"Terminate:    {terminate_command}")
        print("")
        print(line1)
        print(line2)
        print(line3)
        print(line4)
        return True
        
    except Exception as e:
        print(f"Error handling list command: {e}")
        return False

def handle_list_title_command():
    """Handle the --list-title command by displaying only line1 and line2"""
    try:
        if not os.path.exists(SHARED_FILE):
            return False
        
        # Read display info
        with open(SHARED_FILE, 'r') as f:
            display_content = f.read().strip()
        
        # Parse display lines
        parts = display_content.split('|')
        line1 = parts[0] if len(parts) > 0 else ""
        line2 = parts[1] if len(parts) > 1 else ""
        
        # Format as "line1 line2" (replace first pipe with space, remove everything after second pipe)
        formatted_title = f"{line1} {line2}".strip()
        print(formatted_title)
        
        return True
        
    except Exception as e:
        return False

def print_warning():
    """Print warning message in red text"""
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    warning_message = [
        "",
        "This software can automatically launch applications.",
        "Make sure your configuration only contains",
        "trusted commands to avoid potential security risks.            ",
        ""
    ]
    
    print(f"")
    print(f"{RED}{BOLD}WARNING! USE AT YOUR OWN RISK!!!{RESET}")

    for line in warning_message:
        print(f"{BOLD}{line}{RESET}")

def main():
    # Parse command line arguments including --load, --list, and --list-title
    parser = argparse.ArgumentParser(
        description='💾 RFIDisk - Physical App Launcher\n\n'
                   'Reads RFID tags through a hardware rfidisk USB device\n'
                   'and launches/terminates games, apps, or scripts.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''

Read https://github.com/ItsDanik/rfidisk/blob/main/README.md for more info.

        '''
    )
    
    # Add arguments
    parser.add_argument('--load', action='store_true',
                       help='Launch the app for the currently inserted disk')
    parser.add_argument('--list', action='store_true',
                       help='Display current disk info, launch command, and terminate command')
    parser.add_argument('--list-title', action='store_true',
                       help='Display only the title of current disk (line1 & line2 of entry)')
    
    args = parser.parse_args()
    
    # Handle mutually exclusive arguments
    arg_count = sum([args.load, args.list, args.list_title])
    if arg_count > 1:
        print("Error: --load, --list, and --list-title are mutually exclusive")
        sys.exit(1)
    
    # Print warning message only for daemon mode
    if not any([args.load, args.list, args.list_title]):
        print_warning()
    
    # Handle --load mode
    if args.load:
        print("Load mode: Triggering app launch via daemon...")
        if handle_load_command():
            print("Load command sent successfully")
        else:
            print("Failed to trigger load command")
            sys.exit(1)
    
    # Handle --list mode
    elif args.list:
        if not handle_list_command():
            print("No disk information available")
            sys.exit(1)
    
    # Handle --list-title mode
    elif args.list_title:
        if not handle_list_title_command():
            sys.exit(1)
    
    else:
        # Normal daemon mode
        launcher = RFIDLauncher()
        try:
            launcher.run()
        except Exception as e:
            print(f"Fatal error: {e}")
            launcher.shutdown()

if __name__ == "__main__":
    main()
