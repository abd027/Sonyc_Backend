# Gunicorn Daemon Setup Guide

This guide explains how to run your FastAPI backend as a daemon using Gunicorn on your EC2 server.

## Quick Start (Recommended: systemd)

### Step 1: Install Gunicorn

On your EC2 server, navigate to your project directory and install gunicorn:

```bash
cd ~/soya-project/Sonyc_Backend
source venv/bin/activate  # If using virtual environment
pip install gunicorn
```

Or if you've updated requirements.txt:
```bash
pip install -r requirements.txt
```

### Step 2: Run Setup Script (Easiest)

```bash
cd ~/soya-project/Sonyc_Backend
sudo bash setup-gunicorn-service.sh
```

Then start the service:
```bash
sudo systemctl start sonyc-backend
sudo systemctl status sonyc-backend
```

### Step 3: Manual Setup (Alternative)

If you prefer to set it up manually:

1. **Copy the service file:**
```bash
sudo cp sonyc-backend.service /etc/systemd/system/
```

2. **Edit the service file to match your paths:**
```bash
sudo nano /etc/systemd/system/sonyc-backend.service
```

Update these paths if different:
- `WorkingDirectory`: Should point to your project directory (where `app` folder is located)
- `ExecStart`: Path to gunicorn executable
- `EnvironmentFile`: Path to your `.env` file

3. **Reload systemd and enable the service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable sonyc-backend
sudo systemctl start sonyc-backend
```

## Service Management Commands

### Start the service
```bash
sudo systemctl start sonyc-backend
```

### Stop the service
```bash
sudo systemctl stop sonyc-backend
```

### Restart the service
```bash
sudo systemctl restart sonyc-backend
```

### Check status
```bash
sudo systemctl status sonyc-backend
```

### View logs (real-time)
```bash
sudo journalctl -u sonyc-backend -f
```

### View recent logs
```bash
sudo journalctl -u sonyc-backend -n 100
```

### Reload service (after code changes)
```bash
sudo systemctl reload sonyc-backend
```

## Alternative: Using nohup (Quick but not recommended for production)

If you want a quick solution without systemd:

```bash
cd ~/soya-project/Sonyc_Backend
source venv/bin/activate  # If using virtual environment
nohup gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 > gunicorn.log 2>&1 &
```

To stop it:
```bash
# Find the process
ps aux | grep gunicorn
# Kill it
kill <PID>
```

## Configuration

### Gunicorn Config (`gunicorn_config.py`)

The configuration file includes:
- Worker processes: Automatically calculated based on CPU cores
- Timeout: 120 seconds
- Logging: To stdout/stderr (captured by systemd)
- Worker class: UvicornWorker (for ASGI support)

You can modify `gunicorn_config.py` to adjust:
- Number of workers
- Timeout values
- Logging levels
- Other Gunicorn settings

### Adjusting Worker Count

Edit `gunicorn_config.py`:

```python
# For CPU-bound applications, use: CPU cores + 1
workers = multiprocessing.cpu_count() + 1

# For I/O-bound applications (like FastAPI), use: (2 * CPU cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1
```

### Environment Variables

Make sure your `.env` file in the backend directory contains all required variables:
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `GOOGLE_API_KEY`
- `CORS_ORIGINS`
- etc.

The systemd service will automatically load these from the `.env` file.

## Troubleshooting

### Service won't start

1. Check the status:
```bash
sudo systemctl status sonyc-backend
```

2. Check logs:
```bash
sudo journalctl -u sonyc-backend -n 50
```

3. Verify paths in the service file:
```bash
sudo cat /etc/systemd/system/sonyc-backend.service
```

4. Test gunicorn manually:
```bash
cd ~/soya-project/Sonyc_Backend
source venv/bin/activate
gunicorn app.main:app -c gunicorn_config.py
```

### Port already in use

If port 8000 is already in use:

1. Find what's using it:
```bash
sudo lsof -i :8000
```

2. Kill the process or change the port in `gunicorn_config.py`

### Permission issues

Make sure the service file has correct ownership:
```bash
sudo chown root:root /etc/systemd/system/sonyc-backend.service
sudo chmod 644 /etc/systemd/system/sonyc-backend.service
```

## Benefits of systemd over nohup

1. ✅ Automatic restart on failure
2. ✅ Starts on boot
3. ✅ Better logging integration
4. ✅ Process management (start/stop/restart/reload)
5. ✅ Resource limits and security settings
6. ✅ Dependency management (waits for network/database)

## Monitoring

### Check if service is running
```bash
sudo systemctl is-active sonyc-backend
```

### Check if service is enabled (auto-start on boot)
```bash
sudo systemctl is-enabled sonyc-backend
```

### Monitor resource usage
```bash
sudo systemctl status sonyc-backend
# Look for the "Memory" and "CPU" lines
```

## Updating the Application

After deploying new code:

1. **Option 1: Restart (downtime ~5-10 seconds)**
```bash
sudo systemctl restart sonyc-backend
```

2. **Option 2: Reload (zero downtime)**
```bash
sudo systemctl reload sonyc-backend
```

Reload is better for production as it gracefully restarts workers one by one.