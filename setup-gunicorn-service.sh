#!/bin/bash
# Setup script for running Gunicorn as a systemd service on EC2

set -e

echo "🚀 Setting up Gunicorn systemd service for Sonyc Backend..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$SCRIPT_DIR"
SERVICE_NAME="sonyc-backend"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  This script needs sudo privileges to install the systemd service."
    echo "Please run: sudo bash setup-gunicorn-service.sh"
    exit 1
fi

# Navigate to project directory (where the script is)
cd "$PROJECT_DIR" || { echo "❌ Directory $PROJECT_DIR not found!"; exit 1; }

# Check if app/main.py exists to verify we're in the right directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: app/main.py not found in $PROJECT_DIR"
    echo "Please run this script from the directory containing the 'app' folder"
    exit 1
fi

echo "✓ Found app directory in: $PROJECT_DIR"

echo "📦 Checking if gunicorn is installed..."

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✓ Virtual environment found"
    VENV_BIN="$PROJECT_DIR/venv/bin"
    source "$VENV_BIN/activate"
else
    echo "⚠️  No virtual environment found. Assuming gunicorn is installed globally."
    VENV_BIN="/usr/local/bin"
fi

# Check if gunicorn is installed
if ! command -v gunicorn &> /dev/null; then
    echo "❌ Gunicorn not found! Installing..."
    if [ -f "$VENV_BIN/pip" ]; then
        "$VENV_BIN/pip" install gunicorn
    else
        pip3 install gunicorn
    fi
fi

echo "✓ Gunicorn is installed"

# Copy service file to systemd directory
echo "📝 Installing systemd service file..."
cp "$SERVICE_NAME.service" /etc/systemd/system/

# Update WorkingDirectory path (replace placeholder if needed) - be exact
sed -i "s|^WorkingDirectory=/home/ubuntu/soya-project/Sonyc_Backend$|WorkingDirectory=$PROJECT_DIR|g" /etc/systemd/system/"$SERVICE_NAME.service"

# Update ExecStart with correct gunicorn path
if [ -f "$VENV_BIN/gunicorn" ]; then
    sed -i "s|ExecStart=.*gunicorn.*|ExecStart=$VENV_BIN/gunicorn app.main:app -c gunicorn_config.py|g" /etc/systemd/system/"$SERVICE_NAME.service"
elif command -v gunicorn &> /dev/null; then
    GUNICORN_PATH=$(which gunicorn)
    sed -i "s|ExecStart=.*gunicorn.*|ExecStart=$GUNICORN_PATH app.main:app -c gunicorn_config.py|g" /etc/systemd/system/"$SERVICE_NAME.service"
fi

# Update Environment PATH (include system paths too) - match the full line carefully
if [ -d "venv" ]; then
    # Match the exact pattern to avoid breaking the line
    sed -i "s|^Environment=\"PATH=/home/ubuntu/soya-project/Sonyc_Backend/venv/bin:/usr/local/bin:/usr/bin:/bin\"$|Environment=\"PATH=$VENV_BIN:/usr/local/bin:/usr/bin:/bin\"|g" /etc/systemd/system/"$SERVICE_NAME.service"
    # Also handle if it doesn't have the system paths yet
    sed -i "s|^Environment=\"PATH=/home/ubuntu/soya-project/Sonyc_Backend/venv/bin\"$|Environment=\"PATH=$VENV_BIN:/usr/local/bin:/usr/bin:/bin\"|g" /etc/systemd/system/"$SERVICE_NAME.service"
fi

# Remove EnvironmentFile line since load_dotenv() handles .env file loading
# This avoids issues if .env is a directory or doesn't exist
sed -i '/EnvironmentFile=/d' /etc/systemd/system/"$SERVICE_NAME.service"

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable service to start on boot
echo "✅ Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME.service"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 To start the service, run:"
echo "   sudo systemctl start $SERVICE_NAME"
echo ""
echo "📋 To check status:"
echo "   sudo systemctl status $SERVICE_NAME"
echo ""
echo "📋 To view logs:"
echo "   sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "📋 To stop the service:"
echo "   sudo systemctl stop $SERVICE_NAME"
echo ""
echo "📋 To restart the service:"
echo "   sudo systemctl restart $SERVICE_NAME"