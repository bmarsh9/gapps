#!/bin/bash
# =============================================================================
# Masri Digital Compliance Platform - Cloudways First-Time Setup
# =============================================================================
# Run this ONCE after cloning the repo on your Cloudways server.
# It installs Python dependencies, sets up the virtualenv, configures
# Supervisor, and initializes the database.
#
# Usage:
#   ssh your-cloudways-server
#   cd /home/master/applications/<your-app>/public_html
#   git clone <your-repo-url> .
#   bash cloudways_setup.sh
#
# After this, every future deploy is automatic via:
#   bash deploy.sh        (manual)
#   git pull               (then deploy.sh runs via post-merge hook)
# =============================================================================

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SUPERVISOR_CONF="/etc/supervisor/conf.d/masri-compliance.conf"

echo "============================================="
echo " Masri Digital Compliance - Cloudways Setup"
echo "============================================="

# --- Step 1: System dependencies ---
echo "[1/7] Checking system dependencies..."
if ! command -v $PYTHON_BIN &>/dev/null; then
    echo "[ERROR] $PYTHON_BIN not found. Install Python 3.9+ first:"
    echo "  sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv"
    exit 1
fi

# Install system packages needed for PyMySQL and cryptography
if command -v apt-get &>/dev/null; then
    echo "  Installing system packages..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3-venv python3-dev libffi-dev build-essential supervisor 2>/dev/null || true
fi

# --- Step 2: Python virtual environment ---
echo "[2/7] Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    $PYTHON_BIN -m venv "$VENV_DIR"
    echo "  Created virtualenv at $VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip install --upgrade pip setuptools wheel -q

# --- Step 3: Install dependencies ---
echo "[3/7] Installing Python dependencies..."
pip install -r "$APP_DIR/requirements.txt" -q

# --- Step 4: Create .env if it doesn't exist ---
echo "[4/7] Checking environment configuration..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "  Created .env from .env.example"
    echo "  [ACTION REQUIRED] Edit .env with your Cloudways database credentials:"
    echo "    nano $APP_DIR/.env"
    echo ""
    echo "  Your Cloudways MariaDB credentials are in:"
    echo "    Cloudways Dashboard > Application > Database"
    echo ""
else
    echo "  .env already exists"
fi

# --- Step 5: Create required directories ---
echo "[5/7] Creating required directories..."
mkdir -p "$APP_DIR/app/files/evidence"
mkdir -p "$APP_DIR/app/files/reports"

# --- Step 6: Supervisor config ---
echo "[6/7] Setting up Supervisor..."
PORT=${PORT:-5000}
GUNICORN_WORKERS=${GUNICORN_WORKERS:-2}
GUNICORN_THREADS=${GUNICORN_THREADS:-4}
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-120}

sudo tee "$SUPERVISOR_CONF" > /dev/null <<SUPERVISOR
[program:masri-compliance]
command=$VENV_DIR/bin/gunicorn --bind 0.0.0.0:$PORT flask_app:app --workers=$GUNICORN_WORKERS --threads=$GUNICORN_THREADS --timeout=$GUNICORN_TIMEOUT --access-logfile - --error-logfile -
directory=$APP_DIR
user=master
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/supervisor/masri-compliance-err.log
stdout_logfile=/var/log/supervisor/masri-compliance-out.log
stdout_logfile_maxbytes=10MB
stderr_logfile_maxbytes=10MB
environment=FLASK_CONFIG="default",PATH="$VENV_DIR/bin:%(ENV_PATH)s"
SUPERVISOR

echo "  Supervisor config written to $SUPERVISOR_CONF"
sudo supervisorctl reread 2>/dev/null || true
sudo supervisorctl update 2>/dev/null || true

# --- Step 7: Git hook for auto-deploy ---
echo "[7/7] Setting up Git auto-deploy hook..."
GIT_HOOKS_DIR="$APP_DIR/.git/hooks"
if [ -d "$GIT_HOOKS_DIR" ]; then
    cat > "$GIT_HOOKS_DIR/post-merge" <<'HOOK'
#!/bin/bash
# Auto-deploy after git pull
echo "[deploy] Git pull detected, running deploy..."
bash "$(git rev-parse --show-toplevel)/deploy.sh"
HOOK
    chmod +x "$GIT_HOOKS_DIR/post-merge"
    echo "  Installed post-merge hook (auto-deploys on git pull)"
fi

echo ""
echo "============================================="
echo " Setup complete!"
echo "============================================="
echo ""
echo " Next steps:"
echo "  1. Edit your .env file with Cloudways DB credentials:"
echo "       nano $APP_DIR/.env"
echo ""
echo "  2. Initialize the database:"
echo "       source $VENV_DIR/bin/activate"
echo "       python3 tools/check_db_connection.py"
echo "       python3 manage.py init_db"
echo ""
echo "  3. Start the application:"
echo "       sudo supervisorctl start masri-compliance"
echo ""
echo "  4. Configure Cloudways Nginx to proxy to port $PORT"
echo "       (Application Settings > Varnish & Nginx > Nginx Config)"
echo ""
echo " Future deployments:"
echo "   git pull origin main   (auto-deploys via hook)"
echo "   bash deploy.sh         (manual deploy)"
echo ""
