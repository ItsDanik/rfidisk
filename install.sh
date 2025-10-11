#!/bin/bash

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
        arch|manjaro)
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
        arch|manjaro)
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
                arch|manjaro)
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

# Function to check Python dependencies and install if missing
check_python_deps() {
    if ! python3 -c "import serial, psutil" 2>/dev/null; then
        print_warning "Python dependencies missing, installing..."
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

# Function to get installed version from systemd service
get_installed_version() {
    local service_file="$HOME/.config/systemd/user/rfidisk.service"
    
    if [ ! -f "$service_file" ]; then
        echo ""
        return
    fi
    
    # Try to get version from the service file comments first (new method)
    local service_version
    service_version=$(grep -E '^#\s*Version\s*=' "$service_file" | sed -E 's/^#\s*Version\s*=\s*//' | head -1)
    
    if [ -n "$service_version" ]; then
        echo "$service_version"
        return
    fi
    
    # Fallback: Extract Python script path from service file and get version from script
    local python_script
    python_script=$(grep "ExecStart=" "$service_file" | cut -d'=' -f2- | awk '{print $2}')
    
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

# Function to check serial port permissions
check_serial_permissions() {
    if [ ! -w "$ARDUINO_DEVICE" ]; then
        print_warning "No write permission for $ARDUINO_DEVICE"
        echo "Adding user to dialout group..."
        sudo usermod -a -G dialout $(whoami)
        sudo usermod -a -G uucp $(whoami)
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

# Function to install systemd service
install_systemd_service() {
    local script_dir=$(pwd)
    local python_path=$(which python3)
    local current_version=$(get_current_version)
    
    print_status "Installing systemd service..."
    
    # Create user systemd directory
    mkdir -p ~/.config/systemd/user
    
    # Create service file with version comment
    cat > ~/.config/systemd/user/rfidisk.service << EOF
# RFIDisk Service
# Version=$current_version

[Unit]
Description=RFIDisk Arduino Monitor Script
After=default.target

[Service]
Type=simple
ExecStart=$python_path $script_dir/rfidisk.py
WorkingDirectory=$script_dir
Restart=on-failure
ExecStartPre=/bin/sleep 1

[Install]
WantedBy=default.target
EOF

    # Enable lingering for user services
    if ! loginctl enable-linger $(whoami); then
        print_warning "Failed to enable user lingering (may need sudo)"
    fi
    
    # Reload and enable service
    systemctl --user daemon-reload
    systemctl --user enable rfidisk.service
    systemctl --user start rfidisk.service
    
    print_success "Systemd service installed and started (Version: $current_version)"
}

# Function to uninstall RFIDisk service
uninstall_service() {
    print_status "Starting RFIDisk uninstallation..."
    
    local service_file="$HOME/.config/systemd/user/rfidisk.service"
    
    # Check if service is installed
    if [ ! -f "$service_file" ]; then
        print_warning "RFIDisk service not found. Nothing to uninstall."
        exit 0
    fi
    
    # Get installed version for confirmation
    local installed_version=$(get_installed_version)
    if [ -n "$installed_version" ]; then
        print_status "Found installed version: $installed_version"
    fi
    
    # Stop and disable service
    print_status "Stopping and disabling service..."
    if systemctl --user is-active rfidisk.service >/dev/null 2>&1; then
        systemctl --user stop rfidisk.service
    fi
    
    if systemctl --user is-enabled rfidisk.service >/dev/null 2>&1; then
        systemctl --user disable rfidisk.service
    fi
    
    # Remove service file
    print_status "Removing service file..."
    rm -f "$service_file"
    
    # Reload systemd
    systemctl --user daemon-reload
    systemctl --user reset-failed
    
    print_success "RFIDisk service uninstalled successfully"
    print_status "Configuration files have been preserved."
    echo ""
    echo "Note: Your RFID tag configurations in rfidisk_tags.json are still available."
    echo "If you reinstall later, your settings will be retained."
}

# Function to wait for Arduino to be ready
wait_for_arduino() {
    print_status "Waiting for Arduino to initialize..."
    sleep 5
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo "Install or uninstall RFIDisk service"
    echo ""
    echo "Options:"
    echo "  --uninstall    Remove RFIDisk service (preserves configuration files)"
    echo "  -h, --help     Show this help message"
    echo ""
    echo "Without options, performs normal installation/update."
}

# Main installation function
main_installation() {
    print_status "Starting RFIDisk installation..."
    
    # Check and install dependencies automatically
    check_arduino_cli
    check_python_deps
    check_and_install_tkinter
    
    # Detect hardware
    detect_arduino
    check_serial_permissions
    
    # Install Arduino firmware
    install_arduino_firmware
    wait_for_arduino
    
    # Install systemd service
    install_systemd_service
    
    print_success "RFIDisk installation completed successfully!"
    echo ""
    echo "🎉 All features are ready to use!"
    echo ""
    echo "Next steps:"
    echo "  1. Insert an RFID tag to create a new entry"
    echo "  2. The tag manager will automatically open for new tags"
    echo "  3. Check status: systemctl --user status rfidisk.service"
    echo "  4. View logs: journalctl --user-unit=rfidisk.service -f"
    echo ""
    echo "You can manually launch the tag manager anytime with:"
    echo "  python3 rfidisk-manager.py"
}

# Main script
echo "=========================================="
echo "           RFIDisk Installer"
echo "=========================================="
echo ""
echo -e "${RED}WARNING! This script has not been thouroughly tested in many setups!${NC} $1"
echo -e "${RED}Although probably the worst that could possibly happen is just installation failure!${NC} $1"
echo -e "${RED}always make sure you have backups! USE AT YOUR OWN RISK!!!\n${NC} $1"


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

# Check if already installed - get version from installed systemd service + Python script
INSTALLED_VERSION=$(get_installed_version)
if [ -n "$INSTALLED_VERSION" ]; then
    print_status "Currently installed version (from system service): $INSTALLED_VERSION"
    
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
            # Stop existing service before update
            if systemctl --user is-active rfidisk.service >/dev/null 2>&1; then
                systemctl --user stop rfidisk.service
            fi
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
    echo "  • Install Arduino libraries (Adafruit SH110X, Adafruit GFX Library, MFRC522)"
    echo "  • Upload firmware to Arduino"
    echo "  • Install systemd service for automatic startup"
    echo "  • Install Python dependencies (pyserial, psutil)"
    echo "  • Install tkinter for GUI tag manager"
    echo ""
    echo -n "Continue with installation? [Y/n]: "
    read -r response
    if [[ "$response" =~ ^[Nn]$ ]]; then
        print_status "Installation cancelled"
        exit 0
    fi
    
    main_installation
fi
