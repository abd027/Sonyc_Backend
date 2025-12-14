"""Gunicorn configuration file for production deployment"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1  # Formula: (2 * CPU cores) + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "sonyc_backend"

# Server mechanics
daemon = False  # Let systemd handle daemonization
pidfile = None  # Let systemd handle PID file
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed in future)
# keyfile = None
# certfile = None

def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting SONYC Backend server...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading workers...")

def worker_int(worker):
    """Called when a worker receives the INT or QUIT signal."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forking new master process...")

def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("Shutting down: Master")

def worker_abort(worker):
    """Called when a worker times out."""
    worker.log.info("Worker timed out")