#!/bin/bash

# Installer Version = "0.95"

# RFIDisk Installation Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to detect user's shell and get config file
detect_shell_and_config() {
    local shell_name=$(basename "$SHELL")
    local config_file=""
    
    case "$shell_name" in
        bash)
            if [ -f "$HOME/.bashrc" ]; then
                config_file="$HOME/.bashrc"
            elif [ -f "$HOME/.bash_profile" ]; then
                config_file="$HOME/.bash_profile"
            fi
            ;;
        zsh)
            if [ -f "$HOME/.zshrc" ]; then
                config_file="$HOME/.zshrc"
            fi
            ;;
        fish)
            if [ -f "$HOME/.config/fish/config.fish" ]; then
                config_file="$HOME/.config/fish/config.fish"
            fi
            ;;
        *)
            config_file=""
            ;;
    esac
    
    echo "$shell_name:$config_file"
}

# Function to check if alias already exists
alias_exists() {
    local config_file="$1"
    local alias_pattern="$2"
    
    if [ -z "$config_file" ] || [ ! -f "$config_file" ]; then
        return 1
    fi
    
    # Check for exact alias match
    if grep -q "alias rfidisk=" "$config_file" 2>/dev/null; then
        return 0
    fi
    
    # For fish shell, check for different syntax
    if [[ "$config_file" == *"fish/config.fish" ]] && grep -q "alias rfidisk" "$config_file" 2>/dev/null; then
        return 0
    fi
    
    return 1
}

# Function to add alias to shell config
add_shell_alias() {
    local shell_name="$1"
    local config_file="$2"
    local script_dir="$3"
    
    if [ -z "$config_file" ]; then
        print_warning "No shell configuration file found for $shell_name"
        return 1
    fi
    
    # Create config file if it doesn't exist
    if [ ! -f "$config_file" ]; then
        mkdir -p "$(dirname "$config_file")"
        touch "$config_file"
    fi
    
    local alias_line=""
    case "$shell_name" in
        bash|zsh)
            alias_line="alias rfidisk=\"python3 '$script_dir/rfidisk.py'\""
            ;;
        fish)
            alias_line="alias rfidisk=\"python3 '$script_dir/rfidisk.py'\""
            ;;
        *)
            print_warning "Unsupported shell: $shell_name"
            return 1
            ;;
    esac
    
    # Add alias to config file
    echo "" >> "$config_file"
    echo "# RFIDisk alias - added by installer" >> "$config_file"
    echo "$alias_line" >> "$config_file"
    
    print_success "Added rfidisk alias to $config_file"
    print_status "You can now use 'rfidisk' command to start RFIDisk Manager"
    return 0
}

# Function to offer alias installation
offer_alias_installation() {
    local script_dir=$(pwd)
    
    echo ""
    print_status "Would you like to add a 'rfidisk' alias to your shell configuration?"
    print_status "This will allow you to start RFIDisk Manager by simply typing 'rfidisk'"
    echo ""
    
    # Detect shell and config
    local shell_info=$(detect_shell_and_config)
    local shell_name=$(echo "$shell_info" | cut -d: -f1)
    local config_file=$(echo "$shell_info" | cut -d: -f2)
    
    if [ -n "$config_file" ]; then
        print_status "Detected shell: $shell_name"
        print_status "Config file: $config_file"
        
        # Check if alias already exists
        if alias_exists "$config_file" "rfidisk"; then
            print_success "rfidisk alias already exists in $config_file"
            return 0
        fi
        
        echo -n "Add 'rfidisk' alias to $config_file? [Y/n]: "
        read -r response
        if [[ "$response" =~ ^[Nn]$ ]]; then
            print_status "Alias not added. You can manually add it later."
        else
            if add_shell_alias "$shell_name" "$config_file" "$script_dir"; then
                print_status "Please restart your shell or run: source $config_file"
            else
                print_warning "Failed to add alias automatically"
                print_status "You can manually add this line to your shell config:"
                case "$shell_name" in
                    bash|zsh)
                        echo "  alias rfidisk=\"python3 '$script_dir/rfidisk.py'\""
                        ;;
                    fish)
                        echo "  alias rfidisk=\"python3 '$script_dir/rfidisk.py'\""
                        ;;
                    *)
                        echo "  alias rfidisk=\"python3 '$script_dir/rfidisk.py'\""
                        ;;
                esac
            fi
        fi
    else
        print_warning "Could not detect shell configuration file"
        print_status "You can manually add this alias to your shell config:"
        echo "  alias rfidisk=\"python3 '$script_dir/rfidisk.py'\""
    fi
}

# Function to detect Hyprland and configure window rule
configure_hyprland_window_rule() {
    # Check if Hyprland is running
    if [ -n "$HYPRLAND_INSTANCE_SIGNATURE" ] || pgrep -x "hyprland" > /dev/null || [ -n "$XDG_CURRENT_DESKTOP" ] && [[ "$XDG_CURRENT_DESKTOP" == *"Hyprland"* ]]; then
        print_status "Hyprland detected - checking for window rule configuration..."
        
        local hyprland_conf="$HOME/.config/hypr/hyprland.conf"
        local window_rule='windowrule = float, class:^(Tk)$'
        
        # Check if hyprland config exists
        if [ -f "$hyprland_conf" ]; then
            # Check if the rule already exists (exact match)
            if grep -qFx "$window_rule" "$hyprland_conf"; then
                print_success "Window rule for Tk windows already exists in hyprland.conf"
                return 0
            else
                # Also check for similar rules that might accomplish the same thing
                if grep -q "windowrule.*float.*class.*Tk" "$hyprland_conf"; then
                    print_success "Similar window rule for Tk windows already exists in hyprland.conf"
                    return 0
                fi
                
                echo ""
                print_warning "For optimal RFIDisk Manager experience on Hyprland,"
                print_warning "it's recommended to add a window rule to make Tk windows float."
                echo ""
                echo -n "Add window rule to ~/.config/hypr/hyprland.conf? [y/N]: "
                read -r response
                if [[ "$response" =~ ^[Yy]$ ]]; then
                    # Backup the config file
                    cp "$hyprland_conf" "${hyprland_conf}.backup.$(date +%Y%m%d_%H%M%S)"
                    
                    # Add the window rule
                    echo "" >> "$hyprland_conf"
                    echo "# RFIDisk Manager - float Tk windows" >> "$hyprland_conf"
                    echo "$window_rule" >> "$hyprland_conf"
                    
                    print_success "Window rule added to hyprland.conf"
                    print_warning "You may need to reload Hyprland for changes to take effect"
                    echo "You can reload Hyprland with: hyprctl reload"
                    return 0
                else
                    print_status "Window rule not added. You can manually add it later to:"
                    echo "  ~/.config/hypr/hyprland.conf"
                    echo "Add this line:"
                    echo "  $window_rule"
                    return 0
                fi
            fi
        else
            print_warning "Hyprland config not found at: $hyprland_conf"
            print_status "If you're using Hyprland, you may want to add this window rule manually:"
            echo "  $window_rule"
            return 0
        fi
    else
        print_status "Hyprland not detected - skipping window rule configuration"
        return 0
    fi
}

# Function to detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    else
        DISTRO="unknown"
    fi
    echo "$DISTRO"
}

# Function to install arduino-cli based on distro
install_arduino_cli() {
    local distro=$1
    print_status "Installing arduino-cli for $distro..."
    
    case $distro in
        ubuntu|debian)
            if command -v apt &> /dev/null; then
                sudo apt update
                sudo apt install -y arduino-cli
            else
                install_arduino_cli_manual
            fi
            ;;
        fedora|rhel|centos)
            if command -v dnf &> /dev/null; then
                sudo dnf install -y arduino-cli
            elif command -v yum &> /dev/null; then
                sudo yum install -y arduino-cli
            else
                install_arduino_cli_manual
            fi
            ;;
        arch|manjaro|cachyos)  # Added cachyos
            if command -v pacman &> /dev/null; then
                sudo pacman -Sy --noconfirm arduino-cli
            else
                install_arduino_cli_manual
            fi
            ;;
        *)
            install_arduino_cli_manual
            ;;
    esac
}

# Function to install arduino-cli manually
install_arduino_cli_manual() {
    print_status "Installing arduino-cli manually..."
    curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
        echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
        export PATH="$HOME/bin:$PATH"
    fi
}

# Function to install system dependencies based on distro
install_system_dependencies() {
    local distro=$1
    print_status "Installing system dependencies for $distro..."
    
    case $distro in
        ubuntu|debian)
            sudo apt update
            sudo apt install -y python3-pip python3-serial python3-psutil python3-tk
            ;;
        fedora|rhel|centos)
            if command -v dnf &> /dev/null; then
                sudo dnf install -y python3-pip python3-pyserial python3-psutil python3-tkinter
            elif command -v yum &> /dev/null; then
                sudo yum install -y python3-pip python3-pyserial python3-psutil tkinter
            else
                print_error "Cannot install dependencies - no package manager found"
                return 1
            fi
            ;;
        arch|manjaro|cachyos)  # Added cachyos
            sudo pacman -Sy --noconfirm arduino-cli python-pyserial python-psutil tk
            ;;
        *)
            print_warning "Cannot automatically install dependencies for $distro"
            print_status "Please install manually: python3, pip, pyserial, psutil, tkinter"
            return 1
            ;;
    esac
    
    print_success "System dependencies installed successfully"
    return 0
}

# Function to install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."
    if command -v pip3 &> /dev/null; then
        pip3 install pyserial psutil
    elif command -v pip &> /dev/null; then
        pip install pyserial psutil
    else
        print_error "Neither pip nor pip3 found. Please install pip first."
        exit 1
    fi
}

# Function to install tkinter based on distro
install_tkinter() {
    local distro=$1
    print_status "Installing tkinter for $distro..."
    
    case $distro in
        ubuntu|debian)
            sudo apt update
            sudo apt install -y python3-tk
            ;;
        fedora|rhel|centos)
            if command -v dnf &> /dev/null; then
                sudo dnf install -y python3-tkinter
            elif command -v yum &> /dev/null; then
                sudo yum install -y tkinter
            else
                print_error "Cannot install tkinter - no package manager found"
                return 1
            fi
            ;;
        arch|manjaro|cachyos)  # Added cachyos
            sudo pacman -Sy --noconfirm tk
            ;;
        *)
            print_error "Cannot automatically install tkinter for $distro"
            echo "Please install tkinter manually for your distribution"
            return 1
            ;;
    esac
    
    # Verify installation
    if python3 -c "import tkinter" 2>/dev/null; then
        print_success "tkinter installed successfully"
        return 0
    else
        print_error "tkinter installation failed"
        return 1
    fi
}

# Function to check for tkinter and install if missing
check_and_install_tkinter() {
    print_status "Checking for tkinter (GUI manager dependency)..."
    if python3 -c "import tkinter" 2>/dev/null; then
        print_success "tkinter found - GUI manager will be available"
        return 0
    else
        print_warning "tkinter not found - installing automatically..."
        local distro=$(detect_distro)
        if install_tkinter "$distro"; then
            print_success "tkinter installed successfully - GUI manager will be available"
            return 0
        else
            print_warning "tkinter installation failed - GUI manager will not work"
            echo "You can manually install tkinter later:"
            case $distro in
                ubuntu|debian)
                    echo "  sudo apt install python3-tk"
                    ;;
                fedora|rhel|centos)
                    echo "  sudo dnf install python3-tkinter"
                    ;;
                arch|manjaro|cachyos)
                    echo "  sudo pacman -S tk"
                    ;;
                *)
                    echo "  Install tkinter for your distribution"
                    ;;
            esac
            return 1
        fi
    fi
}

# Function to check if arduino-cli is available and install if not
check_arduino_cli() {
    if ! command -v arduino-cli &> /dev/null; then
        print_warning "arduino-cli not found in PATH, attempting to install..."
        local distro=$(detect_distro)
        install_arduino_cli "$distro"
        
        # Verify installation
        if ! command -v arduino-cli &> /dev/null; then
            print_error "Failed to install arduino-cli automatically"
            echo "Please install arduino-cli manually from: https://arduino.github.io/arduino-cli/latest/installation/"
            exit 1
        fi
    fi
    print_success "arduino-cli found"
}

# Function to install Arduino AVR core
install_arduino_core() {
    print_status "Installing Arduino AVR core..."
    if ! arduino-cli core install arduino:avr; then
        print_error "Failed to install Arduino AVR core"
        exit 1
    fi
    print_success "Arduino AVR core installed successfully"
}

# Function to check Python dependencies and install if missing
check_python_deps() {
    print_status "Checking Python dependencies..."
    
    # Check if we can import the required modules
    if ! python3 -c "import serial, psutil" 2>/dev/null; then
        print_warning "Python dependencies missing, attempting to install via system package manager..."
        local distro=$(detect_distro)
        
        if install_system_dependencies "$distro"; then
            # Verify installation
            if python3 -c "import serial, psutil" 2>/dev/null; then
                print_success "Python dependencies installed successfully via system package manager"
                return 0
            fi
        fi
        
        # Fallback to pip installation
        print_warning "Falling back to pip installation..."
        install_python_deps
        
        # Verify installation
        if ! python3 -c "import serial, psutil" 2>/dev/null; then
            print_error "Failed to install Python dependencies"
            exit 1
        fi
    fi
    print_success "Python dependencies found"
}

# Function to extract version from Python script
get_python_version() {
    local python_file="$1"
    if [ -f "$python_file" ]; then
        grep -E '^VERSION\s*=\s*"' "$python_file" | sed -E 's/^VERSION\s*=\s*"([^"]+)"/\1/' | head -1
    else
        echo ""
    fi
}

# Function to get installed version from desktop entry
get_installed_version() {
    local desktop_file="$HOME/.config/autostart/rfidisk.desktop"
    
    if [ ! -f "$desktop_file" ]; then
        echo ""
        return
    fi
    
    # Try to get version from the desktop file comments
    local desktop_version
    desktop_version=$(grep -E '^#\s*Version\s*=' "$desktop_file" | sed -E 's/^#\s*Version\s*=\s*//' | head -1)
    
    if [ -n "$desktop_version" ]; then
        echo "$desktop_version"
        return
    fi
    
    # Fallback: Extract Python script path from desktop file and get version from script
    local python_script
    python_script=$(grep "Exec=" "$desktop_file" | cut -d'=' -f2- | awk '{print $2}')
    
    if [ -z "$python_script" ] || [ ! -f "$python_script" ]; then
        echo ""
        return
    fi
    
    # Get version from the installed Python script
    get_python_version "$python_script"
}

# Function to get the version we're going to install (from current directory)
get_current_version() {
    get_python_version "rfidisk.py"
}

# Function to detect Arduino device
detect_arduino() {
    local devices=()
    
    # Check common Arduino device paths
    for device in /dev/ttyACM* /dev/ttyUSB*; do
        if [ -e "$device" ]; then
            devices+=("$device")
        fi
    done
    
    if [ ${#devices[@]} -eq 0 ]; then
        print_error "No Arduino device found"
        echo "Please connect your Arduino and try again"
        exit 1
    elif [ ${#devices[@]} -eq 1 ]; then
        ARDUINO_DEVICE="${devices[0]}"
        print_success "Found Arduino at: $ARDUINO_DEVICE"
    else
        print_status "Multiple serial devices found:"
        for i in "${!devices[@]}"; do
            echo "  $((i+1))) ${devices[$i]}"
        done
        echo -n "Select device (1-${#devices[@]}): "
        read -r choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le ${#devices[@]} ]; then
            ARDUINO_DEVICE="${devices[$((choice-1))]}"
            print_success "Selected: $ARDUINO_DEVICE"
        else
            print_error "Invalid selection"
            exit 1
        fi
    fi
}

# Function to ensure required groups exist and add user
setup_serial_groups() {
    print_status "Setting up serial port permissions..."
    
    # Check and create dialout group if needed
    if ! getent group dialout > /dev/null; then
        print_warning "dialout group not found, creating it..."
        sudo groupadd dialout
    fi
    
    # Check and create uucp group if needed
    if ! getent group uucp > /dev/null; then
        print_warning "uucp group not found, creating it..."
        sudo groupadd uucp
    fi
    
    # Add user to groups
    local current_user=$(whoami)
    sudo usermod -a -G dialout "$current_user"
    sudo usermod -a -G uucp "$current_user"
    
    print_success "User $current_user added to dialout and uucp groups"
}

# Function to check serial port permissions
check_serial_permissions() {
    if [ ! -w "$ARDUINO_DEVICE" ]; then
        print_warning "No write permission for $ARDUINO_DEVICE"
        setup_serial_groups
        print_warning "You need to logout and login again for group changes to take effect."
        echo "After logging back in, run this installer again."
        exit 1
    fi
    print_success "Serial port permissions OK"
}

# Function to install Arduino libraries and upload firmware
install_arduino_firmware() {
    print_status "Installing Arduino libraries..."
    
    # Install libraries with correct names
    arduino-cli lib install "Adafruit SH110X"
    arduino-cli lib install "Adafruit GFX Library"
    arduino-cli lib install "MFRC522"
    
    print_status "Compiling firmware..."
    if ! arduino-cli compile rfidisk.ino -p "$ARDUINO_DEVICE" -b arduino:avr:uno; then
        print_error "Failed to compile Arduino sketch"
        exit 1
    fi
    
    print_status "Uploading firmware..."
    if ! arduino-cli upload rfidisk.ino -p "$ARDUINO_DEVICE" -b arduino:avr:uno; then
        print_error "Failed to upload to Arduino"
        exit 1
    fi
    
    print_success "Arduino firmware installed successfully"
}

# Function to install desktop autostart entry
install_desktop_autostart() {
    local script_dir=$(pwd)
    local python_path=$(which python3)
    local current_version=$(get_current_version)
    
    print_status "Installing desktop autostart entry..."
    mkdir -p ~/.config/autostart
    
    cat > ~/.config/autostart/rfidisk.desktop << EOF
# Version=$current_version
[Desktop Entry]
Type=Application
Name=RFIDisk
Comment=Physical App Launcher - Version $current_version
Exec=sh -c "sleep 10 && cd '$script_dir' && $python_path rfidisk.py"
Path=$script_dir
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

    print_success "Desktop autostart entry installed (Version: $current_version)"
}

# Function to install RFIDisk Manager application entry
install_manager_application() {
    local script_dir=$(pwd)
    local python_path=$(which python3)
    
    print_status "Installing RFIDisk Manager application entry..."
    mkdir -p ~/.local/share/applications
    
    cat > ~/.local/share/applications/rfidisk-manager.desktop << EOF
[Desktop Entry]
Type=Application
Name=RFIDisk Manager
Comment=Manage RFIDisk tags and settings
Exec=sh -c "cd '$script_dir' && $python_path rfidisk-manager.py"
Path=$script_dir
Terminal=false
Icon=$script_dir/floppy.png
Categories=Utility;
EOF

    print_success "RFIDisk Manager application entry installed"
}

# Function to uninstall RFIDisk
uninstall_service() {
    print_status "Starting RFIDisk uninstallation..."
    
    local desktop_file="$HOME/.config/autostart/rfidisk.desktop"
    local manager_file="$HOME/.local/share/applications/rfidisk-manager.desktop"
    
    # Check if anything is installed
    if [ ! -f "$desktop_file" ] && [ ! -f "$manager_file" ]; then
        print_warning "RFIDisk not found. Nothing to uninstall."
        exit 0
    fi
    
    # Get installed version for confirmation
    local installed_version=$(get_installed_version)
    if [ -n "$installed_version" ]; then
        print_status "Found installed version: $installed_version"
    fi
    
    # Remove autostart file
    if [ -f "$desktop_file" ]; then
        print_status "Removing desktop autostart entry..."
        rm -f "$desktop_file"
        print_success "Desktop autostart entry removed"
    fi
    
    # Remove manager application file
    if [ -f "$manager_file" ]; then
        print_status "Removing RFIDisk Manager application entry..."
        rm -f "$manager_file"
        print_success "RFIDisk Manager application entry removed"
    fi
    
    # Kill any running RFIDisk processes
    print_status "Stopping any running RFIDisk processes..."
    pkill -f "rfidisk.py" || true
    
    print_success "RFIDisk uninstalled successfully"
    print_status "Configuration files have been preserved."
    echo ""
    echo "Note: Your RFID tag configurations in rfidisk_tags.json are still available."
    echo "If you reinstall later, your settings will be preserved."
}

# Function to wait for Arduino to be ready
wait_for_arduino() {
    print_status "Waiting for Arduino to initialize..."
    sleep 5
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo "Install or uninstall RFIDisk"
    echo ""
    echo "Options:"
    echo "  --uninstall    Remove RFIDisk (preserves configuration files)"
    echo "  -h, --help     Show this help message"
    echo ""
    echo "Without options, performs normal installation/update."
}

# Main installation function
main_installation() {
    print_status "Starting RFIDisk installation..."
    
    # Check and install dependencies automatically
    check_arduino_cli
    install_arduino_core  # Install AVR core
    check_python_deps
    check_and_install_tkinter
    
    # Detect hardware
    detect_arduino
    check_serial_permissions
    
    # Install Arduino firmware
    install_arduino_firmware
    wait_for_arduino
    
    # Install desktop entries
    install_desktop_autostart
    install_manager_application
    
    # Configure Hyprland window rule if detected
    configure_hyprland_window_rule
    
    # Offer to add shell alias
    offer_alias_installation
    
    print_success "RFIDisk installation completed successfully!"
    echo ""
    echo "🎉 All features are ready to use!"
    echo ""
    echo "Desktop entries installed:"
    echo "  • Autostart entry: ~/.config/autostart/rfidisk.desktop (starts on login with 10s delay)"
    echo "  • Application entry: ~/.local/share/applications/rfidisk-manager.desktop"
    echo ""
    echo "Next steps:"
    echo "  1. Logout and login again to start RFIDisk automatically"
    echo "  2. Insert an RFID tag to create a new entry"
    echo "  3. The tag manager will automatically open for new tags"
    echo "  4. You can manually launch the tag manager from your application menu"
    echo ""
    echo "The RFIDisk Manager can also be launched manually with:"
    echo "  python3 rfidisk-manager.py"
}

# Main script
echo "=========================================="
echo "           RFIDisk Installer"
echo "=========================================="
echo ""
echo -e "${RED}WARNING! This script has not been thouroughly tested in many setups!${NC}"
echo -e "${RED}Although probably the worst that could possibly happen is just installation failure!${NC}"
echo -e "${RED}always make sure you have backups! USE AT YOUR OWN RISK!!!\n${NC}"

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_usage
        exit 0
        ;;
    --uninstall)
        uninstall_service
        exit 0
        ;;
    "")
        # No arguments, continue with normal installation
        ;;
    *)
        print_error "Unknown option: $1"
        show_usage
        exit 1
        ;;
esac

# Get current Python script version (to be installed) - from local rfidisk.py
CURRENT_VERSION=$(get_current_version)
if [ -z "$CURRENT_VERSION" ]; then
    print_error "Could not find rfidisk.py in current directory"
    echo "Please run this script from the RFIDisk project directory"
    exit 1
fi

print_status "Version to install (from local rfidisk.py): $CURRENT_VERSION"

# Check if already installed - get version from desktop entry
INSTALLED_VERSION=$(get_installed_version)
if [ -n "$INSTALLED_VERSION" ]; then
    print_status "Currently installed version (from desktop entry): $INSTALLED_VERSION"
    
    if [ "$INSTALLED_VERSION" == "$CURRENT_VERSION" ]; then
        print_success "Latest version ($CURRENT_VERSION) already installed"
        echo "Nothing to do."
        exit 0
    else
        print_warning "Different version installed"
        echo -n "Do you want to update from $INSTALLED_VERSION to $CURRENT_VERSION? [y/N]: "
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            print_status "Proceeding with update..."
            # Stop existing processes before update
            pkill -f "rfidisk.py" || true
            # For update, we reinstall everything including Arduino firmware
            main_installation
        else
            print_status "Update cancelled"
            exit 0
        fi
    fi
else
    # Fresh installation
    print_status "No existing installation found"
    echo ""
    echo "This will:"
    echo "  • Install Arduino CLI and AVR core"
    echo "  • Install Arduino libraries (Adafruit SH110X, Adafruit GFX Library, MFRC522)"
    echo "  • Upload firmware to Arduino"
    echo "  • Install desktop autostart entry (starts automatically on login)"
    echo "  • Install RFIDisk Manager application entry (accessible from app menu)"
    echo "  • Install Python dependencies (pyserial, psutil)"
    echo "  • Install tkinter for GUI tag manager"
    echo "  • Set up serial port permissions"
    echo ""
    echo -n "Continue with installation? [Y/n]: "
    read -r response
    if [[ "$response" =~ ^[Nn]$ ]]; then
        print_status "Installation cancelled"
        exit 0
    fi
    
    main_installation
fi
