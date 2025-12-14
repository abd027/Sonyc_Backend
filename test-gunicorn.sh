#!/bin/bash
# Quick test script to verify gunicorn can start manually

echo "Testing Gunicorn startup..."

cd "$(dirname "$0")" || exit 1

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Activated virtual environment"
fi

# Check if gunicorn is available
if ! command -v gunicorn &> /dev/null; then
    echo "❌ Gunicorn not found in PATH"
    exit 1
fi

echo "✓ Gunicorn found: $(which gunicorn)"

# Check if app/main.py exists
if [ ! -f "app/main.py" ]; then
    echo "❌ app/main.py not found"
    exit 1
fi

echo "✓ Found app/main.py"

# Check if config exists
if [ ! -f "gunicorn_config.py" ]; then
    echo "⚠️  gunicorn_config.py not found, will use defaults"
    CONFIG_ARG=""
else
    echo "✓ Found gunicorn_config.py"
    CONFIG_ARG="-c gunicorn_config.py"
fi

echo ""
echo "Attempting to start Gunicorn (press Ctrl+C to stop)..."
echo ""

# Try to start gunicorn (will run in foreground for testing)
gunicorn app.main:app $CONFIG_ARG --bind 0.0.0.0:8000 --timeout 120
