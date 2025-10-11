#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import os
import subprocess
import sys

TAGS_FILE = "rfidisk_tags.json"

class TagManager:
    def __init__(self, root):
        self.root = root
        self.root.title("RFIDisk Tag Manager")
        self.root.geometry("800x600")
        
        self.tags = self.load_tags()
        self.current_tag = None
        self.display_mode = "tag_id"  # or "line1"
        
        self.create_widgets()
        self.refresh_tag_list()
    
    def load_tags(self):
        if os.path.exists(TAGS_FILE):
            with open(TAGS_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def save_tags(self):
        with open(TAGS_FILE, 'w') as f:
            json.dump(self.tags, f, indent=2)
    
    def create_widgets(self):
        # Left panel - tag list
        left_frame = ttk.Frame(self.root)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Display mode toggle
        display_frame = ttk.Frame(left_frame)
        display_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(display_frame, text="Display:").pack(side=tk.LEFT)
        self.display_btn = ttk.Button(display_frame, text="Show Names", command=self.toggle_display_mode)
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
        
        # Right panel - tag editor
        right_frame = ttk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tag ID
        ttk.Label(right_frame, text="Tag ID:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.tag_id_var = tk.StringVar()
        self.tag_id_entry = ttk.Entry(right_frame, textvariable=self.tag_id_var, width=30)
        self.tag_id_entry.grid(row=0, column=1, sticky=tk.W+tk.E, pady=2)
        
        # Command
        ttk.Label(right_frame, text="Launch Command:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.command_var = tk.StringVar()
        self.command_entry = ttk.Entry(right_frame, textvariable=self.command_var, width=30)
        self.command_entry.grid(row=1, column=1, sticky=tk.W+tk.E, pady=2)
        ttk.Button(right_frame, text="Browse", command=self.browse_command).grid(row=1, column=2, padx=5)
        
        # Display lines
        ttk.Label(right_frame, text="Display Line 1:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.line1_var = tk.StringVar()
        self.line1_entry = ttk.Entry(right_frame, textvariable=self.line1_var, width=30)
        self.line1_entry.grid(row=2, column=1, sticky=tk.W+tk.E, pady=2)
        
        ttk.Label(right_frame, text="Display Line 2:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.line2_var = tk.StringVar()
        ttk.Entry(right_frame, textvariable=self.line2_var, width=30).grid(row=3, column=1, sticky=tk.W+tk.E, pady=2)
        
        ttk.Label(right_frame, text="Display Line 3:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.line3_var = tk.StringVar()
        ttk.Entry(right_frame, textvariable=self.line3_var, width=30).grid(row=4, column=1, sticky=tk.W+tk.E, pady=2)
        
        ttk.Label(right_frame, text="Display Line 4:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.line4_var = tk.StringVar()
        ttk.Entry(right_frame, textvariable=self.line4_var, width=30).grid(row=5, column=1, sticky=tk.W+tk.E, pady=2)
        
        # Terminate command
        ttk.Label(right_frame, text="Terminate Command:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.terminate_var = tk.StringVar()
        ttk.Entry(right_frame, textvariable=self.terminate_var, width=30).grid(row=6, column=1, sticky=tk.W+tk.E, pady=2)
        
        # Save button
        ttk.Button(right_frame, text="Save Changes", command=self.save_current_tag).grid(row=7, column=1, pady=10)
        
        # Test buttons
        test_frame = ttk.Frame(right_frame)
        test_frame.grid(row=8, column=0, columnspan=3, pady=10)
        ttk.Button(test_frame, text="Test Launch", command=self.test_launch).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_frame, text="Test Terminate", command=self.test_terminate).pack(side=tk.LEFT, padx=5)
        
        right_frame.columnconfigure(1, weight=1)
    
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
            # Store the actual tag_id as hidden data (we'll use the index to map back)
        
        # Update the status label to show what we're displaying
        status_text = f"Showing: {self.display_mode.upper()}"
        if hasattr(self, 'status_label'):
            self.status_label.config(text=status_text)
    
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
        self.root.quit()

def main():
    # Check if we're being called to edit a specific tag
    edit_tag_id = None
    if len(sys.argv) > 2 and sys.argv[1] == "--edit":
        edit_tag_id = sys.argv[2]
    
    root = tk.Tk()
    app = TagManager(root)
    
    # If we were asked to edit a specific tag, select it
    if edit_tag_id and edit_tag_id in app.tags:
        display_items = app.get_display_items()
        for i, (tag_id, _) in enumerate(display_items):
            if tag_id == edit_tag_id:
                app.tag_listbox.selection_set(i)
                app.load_tag_data(edit_tag_id)
                break
    elif edit_tag_id and edit_tag_id not in app.tags:
        # New tag - create it and select it
        app.tags[edit_tag_id] = {
            'command': '',
            'line1': 'New Tag',
            'line2': 'Configure me',
            'line3': '',
            'line4': edit_tag_id,
            'terminate': ''
        }
        app.save_tags()
        app.refresh_tag_list()
        
        # Select the new tag
        display_items = app.get_display_items()
        for i, (tag_id, _) in enumerate(display_items):
            if tag_id == edit_tag_id:
                app.tag_listbox.selection_set(i)
                app.load_tag_data(edit_tag_id)
                break
    
    root.mainloop()

if __name__ == "__main__":
    main()
