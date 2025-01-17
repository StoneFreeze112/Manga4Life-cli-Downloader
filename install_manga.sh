#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Check if the script is run with root privileges
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or using sudo."
  exit 1
fi

# Detect package manager
if command -v apt-get &> /dev/null; then
    PACKAGE_MANAGER="apt-get"
elif command -v dnf &> /dev/null; then
    PACKAGE_MANAGER="dnf"
elif command -v pacman &> /dev/null; then
    PACKAGE_MANAGER="pacman"
else
    echo "No supported package manager found. Please install Python 3 and pip manually."
    exit 1
fi

# Define script and executable names
SCRIPT_NAME="D4C.py"
EXECUTABLE_NAME="D4C"
README_FILE="README_D4C.txt"

# Install required dependencies
echo "Installing dependencies..."

# Install Python 3 if not installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found, installing..."
    if [ "$PACKAGE_MANAGER" == "apt-get" ]; then
        apt-get update && apt-get install -y python3
    elif [ "$PACKAGE_MANAGER" == "dnf" ]; then
        dnf install -y python3
    elif [ "$PACKAGE_MANAGER" == "pacman" ]; then
        pacman -S python
    fi
fi

# Install pip if not installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 not found, installing..."
    if [ "$PACKAGE_MANAGER" == "apt-get" ]; then
        apt-get install -y python3-pip
    elif [ "$PACKAGE_MANAGER" == "dnf" ]; then
        dnf install -y python3-pip
    elif [ "$PACKAGE_MANAGER" == "pacman" ]; then
        pacman -S python-pip
    fi
fi

# Install required Python packages
echo "Installing Python packages..."
pip3 install aiohttp aiofiles reportlab colorama

# Ensure the script file exists in the current directory
if [ ! -f "$SCRIPT_NAME" ]; then
  echo "Error: $SCRIPT_NAME not found in the current directory."
  exit 1
fi

# Copy the script to /usr/local/bin and make it executable
echo "Installing $EXECUTABLE_NAME..."
cp "$SCRIPT_NAME" /usr/local/bin/$EXECUTABLE_NAME
chmod +x /usr/local/bin/$EXECUTABLE_NAME

# Create a README file with usage instructions
echo "Creating README file..."
cat << EOF > "$README_FILE"
# D4C Manga Downloader

## Description
D4C is a command-line tool for downloading manga chapters as PDFs. It supports features such as:
- Specifying chapter ranges (e.g., 1-5).
- Download history.
- Customizable manga name formatting.
- A colorful progress bar for download progress.

## Dependencies
The following dependencies are automatically installed:
- \`aiohttp\`
- \`aiofiles\`
- \`reportlab\`
- \`colorama\`

## Usage
Run the following command to use D4C after installation:
\`\`\`
D4C
\`\`\`

You will be prompted to:
1. Enter the manga name.
2. Specify chapters to download (e.g., 1-5).
3. Choose whether to make the manga name uppercase.
4. Decide if you want to edit the manga name.

### Examples
1. Download chapters 1 to 5 of "One Piece":
   \`\`\`
   D4C
   # Enter "One Piece"
   # Enter "1-5"
   \`\`\`

2. Download specific chapters (e.g., 1, 3, and 5):
   \`\`\`
   D4C
   # Enter "Naruto"
   # Enter "1,3,5"
   \`\`\`

3. View download history:
   Modify the code to call the \`load_history\` method if needed.

## Features
- Automatically determines the number of pages in a chapter.
- Saves each chapter as a high-quality PDF in the \`Mangas/<Manga Name>\` directory.
- Ensures each chapter is uniquely formatted (e.g., leading zeros for chapter numbers).
- Color-coded progress bar.

## Troubleshooting
If you encounter issues:
1. Ensure Python 3 is installed: \`python3 --version\`.
2. Check if all dependencies are installed: \`aiohttp\`, \`aiofiles\`, \`reportlab\`, \`colorama\`.

## Reinstallation
To reinstall or update, rerun this installation script:
\`\`\`
sudo ./install.sh
\`\`\`

## Note
Run the script with sufficient privileges if required.
EOF

# Notify the user of successful installation and usage
echo "$EXECUTABLE_NAME has been installed successfully."
echo "Usage:"
echo "  Run \`D4C\` and follow the prompts to download manga."
echo "Refer to the README file ($README_FILE) for more information."

echo "Installation completed!"

