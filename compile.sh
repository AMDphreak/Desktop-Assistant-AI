#!/bin/bash

# Function to check if Python is installed
check_python() {
    if command -v python3 &>/dev/null; then
        echo "Python is already installed."
        return 0
    else
        echo "Python is not installed."
        return 1
    fi
}

# Function to install Python on Linux
install_python_linux() {
    echo "Installing the latest version of Python on Linux..."
    sudo apt update && sudo apt install -y python3 python3-pip
    if [ $? -eq 0 ]; then
        echo "Python installation complete on Linux."
    else
        echo "Python installation failed. Please check the logs."
        exit 1
    fi
}

# Function to install Python on macOS
install_python_mac() {
    echo "Installing the latest version of Python on macOS..."
    if ! command -v brew &>/dev/null; then
        echo "Homebrew not found. Installing Homebrew first..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        export PATH="/usr/local/bin:$PATH"
    fi
    brew install python
    if [ $? -eq 0 ]; then
        echo "Python installation complete on macOS."
    else
        echo "Python installation failed. Please check the logs."
        exit 1
    fi
}

# Function to compile Python files
compile_python_files() {
    echo "Compiling all Python files in the current directory..."
    python3 -m compileall ./src > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "Compilation successful."
    else
        echo "Compilation failed. Please check for errors."
        exit 1
    fi
}

# Function to create the run.sh script
create_run_script() {
    echo "Creating 'run.sh' script..."
    cat << EOF > "run.sh"
#!/bin/bash

# Check if Python is installed
if ! command -v python3 &>/dev/null; then
    echo "Python is not installed. Please run './compile.sh' first to set up Python and compile the scripts."
    exit 1
fi

# Check if the compiled file exists
if [ ! -f "./__pycache__/main.cpython-*.pyc" ]; then
    echo "Compiled file not found. Please run './compile.sh' first."
    exit 1
fi

# Run the compiled Python file
python3 ./__pycache__/main.cpython-*.pyc
if [ $? -ne 0 ]; then
    echo "Failed to execute the Python script. Please check for errors in your code."
    exit 1
fi

EOF

    chmod +x run.sh
    echo "'run.sh' has been created successfully."
}

# Detect operating system and proceed
if ! check_python; then
    case "$(uname -s)" in
        Linux*) install_python_linux ;;
        Darwin*) install_python_mac ;;
        *)
            echo "Unsupported operating system. Please install Python manually."
            exit 1
            ;;
    esac
fi

compile_python_files
create_run_script
