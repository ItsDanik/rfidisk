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

CONFIG_FILE = "rfidisk_config.json"

# Version number
VERSION = "0.7"

# Default configuration
default_config = {
    "settings": {
        "serial_port": "/dev/rfidisk",
        "removal_delay": 0.0,
        "desktop_notifications": True
    },
    "rfid_tags": {
        "a1b2c3d4": {
            "command": "Placeholder",
            "line1": "Example",
            "line2": "Delete this entry",
            "line3": "after you have made",
            "line4": "your own ones.",
            "terminate": "(or don't :))"
        }
    }
}

class RFIDLauncher:
    def __init__(self):
        self.config = self.load_config()
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

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    # Ensure all entries have the terminate field
                    for tag_id, tag_config in config.get("rfid_tags", {}).items():
                        if "terminate" not in tag_config:
                            tag_config["terminate"] = ""
                    return config
            except Exception as e:
                print(f"Error loading config: {e}")
        return default_config.copy()

    def save_config(self):
        """Save current config to file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"Config saved")
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def create_or_update_new_entry(self, tag_id):
        """Create or update a new entry for unknown tags"""
        new_entry_id = None
        
        # Check if there's already a "new entry"
        for existing_id, entry in self.config["rfid_tags"].items():
            if entry.get("line1") == "new entry":
                new_entry_id = existing_id
                break
        
        if new_entry_id:
            # Update existing new entry with new tag ID
            if new_entry_id != tag_id:
                self.config["rfid_tags"][tag_id] = self.config["rfid_tags"][new_entry_id]
                del self.config["rfid_tags"][new_entry_id]
                print(f"Updated new entry: {tag_id}")
        else:
            # Create new entry with terminate field
            self.config["rfid_tags"][tag_id] = {
                "command": "",
                "line1": "new entry",
                "line2": "configure me",
                "line3": "edit rfidisk_config.json",
                "line4": tag_id,
                "terminate": ""
            }
            print(f"New entry: {tag_id}")
        
        # Save the updated config
        self.save_config()
        return tag_id

    def connect_serial(self):
        """Connect to serial port with state recovery"""
        port = self.config["settings"].get("serial_port", default_config["settings"]["serial_port"])
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
                        
                        # STATE RECOVERY: Restore previous state after reconnection
                        if self.reconnecting:
                            time.sleep(0.5)
                            self.recover_after_disconnection()
                            self.reconnecting = False
                            
                        return True
            
            print("Connected (no OK message)")
            self.serial_error_count = 0
            
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
            
            # Reload config to get any changes
            self.config = self.load_config()
            
            tag_config = self.config["rfid_tags"].get(tag_id)
            if tag_config:
                # Determine icon type based on command
                icon_type = self.get_icon_type(tag_config.get("command", ""))
                # Just update the display silently - NO notifications, NO relaunch
                self.send_display_command(
                    tag_config.get("line1", "App"), 
                    tag_config.get("line2", ""),
                    tag_config.get("line3", ""),
                    tag_config.get("line4", ""),
                    icon_type  # Restore with appropriate icon
                )
                print(f"Silently restored display for {tag_id}")
            else:
                # Unknown tag - show error
                self.send_display_command(
                    "State Error",
                    "Tag config missing",
                    "Check rfidisk_config.json",
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
        
        # Truncate strings to 20 characters to save RAM
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
        # NEVER send notifications during recovery
        if self.recovery_mode or self.reconnecting:
            return False
            
        if not self.config["settings"].get("desktop_notifications", True):
            return False
            
        try:
            # Get the directory where the script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(script_dir, "floppy.png")
            
            # Check if notify-send is available
            result = subprocess.run(['which', 'notify-send'], capture_output=True)
            if result.returncode != 0:
                return False
                
            # Send the notification
            subprocess.run([
                'notify-send',
                '-i', icon_path,
                title,
                message,
                '-t', '3000'
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

    def close_current_app(self):
        """Close current app using appropriate termination method"""
        if not self.active_tag:
            return
            
        # Get the tag config to check for custom terminate command
        tag_config = self.config["rfid_tags"].get(self.active_tag, {})
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
                self.app_was_launched_by_us):
                print(f"Tag {tag_id} already active with app launched by us, ignoring")
                return
                
            # Reload config to get any changes
            self.config = self.load_config()
            
            tag_config = self.config["rfid_tags"].get(tag_id)
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
                
                # Launch app if command is specified and not already launched by us
                if (tag_config.get("command") and 
                    not self.app_was_launched_by_us):
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
                
                # Show new entry screen with icon_type=0 (no icon)
                self.send_display_command(
                    "new entry",
                    "configure me",
                    "edit rfidisk_config.json",
                    new_tag_id,
                    "0"
                )
                self.send_desktop_notification("New Tag", f"Tag {new_tag_id} added")
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

    def run(self):
        print(f"Starting RFIDisk v.{VERSION}...")
        if not self.connect_serial():
            return
        
        print("Ready")
        
        # Send initial display with icon_type=0 (no icon)
        self.send_display_command("Ready", "Insert Disk", "", f"RFIDisk v{VERSION}", "0")
        
        try:
            while self.running:
                data = self.read_serial()
                if data:
                    self.process_serial_data(data)
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.running = False

    def shutdown(self):
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except:
                pass
        print(f"RFIDisk v.{VERSION} stopped")

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
    # Print warning message first
    print_warning()
        
    launcher = RFIDLauncher()
    try:
        launcher.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        launcher.shutdown()

if __name__ == "__main__":
    main()
