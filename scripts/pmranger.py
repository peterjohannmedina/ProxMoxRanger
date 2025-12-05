#!/usr/bin/env python3

import subprocess
import json
import logging
from flask import Flask, render_template_string, request, redirect, url_for, abort, send_file, session, flash, jsonify
from functools import wraps
import ipaddress
import os
from datetime import timedelta
import socket
import threading
import time
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(filename='/var/log/hotswap-webui.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Flask session configuration
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

# ============================================================================
# MULTI-NODE SUPPORT - Node Registry and Management
# ============================================================================

# Node registry - stores discovered/registered nodes
NODES = []
NODES_LOCK = threading.Lock()

# Configuration
NODE_DISCOVERY_ENABLED = True
NODE_DISCOVERY_INTERVAL = 60  # 1 minute
LOCAL_NODE_INFO = {
    'hostname': None,
    'ip': None,
    'port': 8010,
    'version': '1.2.0'
}

def get_local_node_info():
    """Get information about the local node"""
    if LOCAL_NODE_INFO['hostname'] is None:
        success, hostname = run_cmd_simple("hostname")
        LOCAL_NODE_INFO['hostname'] = hostname if success else "unknown"

    if LOCAL_NODE_INFO['ip'] is None:
        try:
            # Get IP by connecting to external host
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            LOCAL_NODE_INFO['ip'] = s.getsockname()[0]
            s.close()
        except:
            LOCAL_NODE_INFO['ip'] = '127.0.0.1'

    return LOCAL_NODE_INFO

def run_cmd_simple(cmd):
    """Simple command execution without full error handling"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return result.returncode == 0, result.stdout.strip()
    except:
        return False, ""

def register_node(hostname: str, ip: str, port: int = 8010, auto_discovered: bool = False):
    """Register a node in the registry"""
    with NODES_LOCK:
        # Check if node already exists
        for node in NODES:
            if node['ip'] == ip and node['port'] == port:
                # Update existing node
                node['last_seen'] = time.time()
                node['status'] = 'online'
                return node

        # Add new node
        node = {
            'hostname': hostname,
            'ip': ip,
            'port': port,
            'auto_discovered': auto_discovered,
            'registered_at': time.time(),
            'last_seen': time.time(),
            'status': 'online'
        }
        NODES.append(node)
        logging.info(f"Registered node: {hostname} ({ip}:{port})")
        return node

def unregister_node(ip: str, port: int = 8010):
    """Remove a node from the registry"""
    with NODES_LOCK:
        NODES[:] = [n for n in NODES if not (n['ip'] == ip and n['port'] == port)]
        logging.info(f"Unregistered node: {ip}:{port}")

def get_nodes():
    """Get list of all registered nodes"""
    with NODES_LOCK:
        return list(NODES)

def check_node_status(ip: str, port: int = 8010, timeout: int = 2) -> bool:
    """Check if a node is online by trying to connect"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def discover_nodes_on_network(network_range: str = None):
    """Discover ProxMox Ranger nodes on the local network"""
    if not NODE_DISCOVERY_ENABLED:
        return

    logging.info("Starting node discovery scan...")

    # If no network range specified, use local network
    if network_range is None:
        local_ip = get_local_node_info()['ip']
        # Convert to /24 network
        ip_parts = local_ip.split('.')
        network_range = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"

    try:
        network = ipaddress.ip_network(network_range, strict=False)
        discovered_count = 0

        for ip in network.hosts():
            ip_str = str(ip)

            # Skip local IP
            if ip_str == get_local_node_info()['ip']:
                continue

            # Quick port check
            if check_node_status(ip_str, 8010, timeout=0.5):
                try:
                    # Try to get node info via API
                    import urllib.request
                    url = f"http://{ip_str}:8010/api/info"
                    req = urllib.request.Request(url, headers={'User-Agent': 'ProxMoxRanger/1.2'})
                    with urllib.request.urlopen(req, timeout=2) as response:
                        if response.status == 200:
                            data = json.loads(response.read().decode())
                            if data.get('app') == 'ProxMoxRanger':
                                register_node(
                                    hostname=data.get('hostname', ip_str),
                                    ip=ip_str,
                                    port=8010,
                                    auto_discovered=True
                                )
                                discovered_count += 1
                                logging.info(f"Discovered node: {data.get('hostname')} at {ip_str}")
                except:
                    pass

        logging.info(f"Node discovery complete. Found {discovered_count} nodes.")
    except Exception as e:
        logging.error(f"Node discovery error: {e}")

def node_discovery_worker():
    """Background worker for periodic node discovery"""
    while NODE_DISCOVERY_ENABLED:
        try:
            discover_nodes_on_network()
        except Exception as e:
            logging.error(f"Discovery worker error: {e}")

        # Wait for next scan
        time.sleep(NODE_DISCOVERY_INTERVAL)

# Start discovery worker thread
if NODE_DISCOVERY_ENABLED:
    discovery_thread = threading.Thread(target=node_discovery_worker, daemon=True)
    discovery_thread.start()
    logging.info("Node discovery worker started")



# IP Whitelist Configuration
# Add allowed IP addresses or CIDR ranges here
# Default: Allow local network (192.168.0.0/16) and localhost
ALLOWED_IPS = [
    '127.0.0.1',          # Localhost
    '::1',                # IPv6 localhost
    '192.168.0.0/16',     # Common private network range
    '10.0.0.0/8',         # Another common private range
    '172.16.0.0/12',      # Third common private range
]

def is_ip_allowed(ip):
    """Check if an IP address is in the whitelist"""
    try:
        client_ip = ipaddress.ip_address(ip)
        for allowed in ALLOWED_IPS:
            try:
                # Check if it's a network range (CIDR notation)
                if '/' in allowed:
                    if client_ip in ipaddress.ip_network(allowed, strict=False):
                        return True
                # Check if it's a specific IP
                elif client_ip == ipaddress.ip_address(allowed):
                    return True
            except ValueError:
                continue
        return False
    except ValueError:
        # Invalid IP format
        logging.warning(f"Invalid IP address format: {ip}")
        return False

def ip_whitelist_required(f):
    """Decorator to enforce IP whitelist on routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get client IP (handle X-Forwarded-For for proxies)
        if request.headers.get('X-Forwarded-For'):
            client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        else:
            client_ip = request.remote_addr

        if not is_ip_allowed(client_ip):
            logging.warning(f"Access denied for IP: {client_ip}")
            abort(403)  # Forbidden

        return f(*args, **kwargs)
    return decorated_function


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ProxMox Ranger - {{ hostname }}</title>
    <style>
        /* ===== MODERN DARK THEME DESIGN ===== */
        /* Inspired by ProxMenux Monitor & Modern Dashboard Principles */

        :root[data-theme="dark"] {
            /* Background Colors */
            --bg-primary: #0f1419;
            --bg-secondary: #1a1f2e;
            --bg-tertiary: #252d3d;
            --bg-hover: #2d3548;

            /* Text Colors */
            --text-primary: #e4e7eb;
            --text-secondary: #9ca3af;
            --text-tertiary: #6b7280;

            /* Accent Colors */
            --accent-primary: #3b82f6;
            --accent-primary-hover: #2563eb;
            --accent-success: #10b981;
            --accent-warning: #f59e0b;
            --accent-danger: #ef4444;
            --accent-info: #06b6d4;

            /* Border & Divider */
            --border-color: #2d3548;
            --divider-color: #374151;

            /* Shadows */
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
            --shadow-glow: 0 0 20px rgba(59, 130, 246, 0.15);

            /* Status Colors */
            --status-online: #10b981;
            --status-offline: #6b7280;
            --status-warning: #f59e0b;
            --status-error: #ef4444;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }

        /* ===== LAYOUT ===== */
        .app-container {
            display: flex;
            min-height: 100vh;
        }

        .sidebar {
            width: 260px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            position: fixed;
            height: 100vh;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }

        .sidebar-brand {
            padding: 24px;
            border-bottom: 1px solid var(--border-color);
        }

        .brand-logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-logo img {
            height: 56px;
            width: auto;
        }

        .brand-text h1 {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 2px;
        }

        .brand-text .subtitle {
            font-size: 12px;
            color: var(--text-secondary);
        }

        /* Node Selector */
        .node-selector-container {
            padding: 16px 20px;
            border-top: 1px solid var(--border-color);
            border-bottom: 1px solid var(--border-color);
            background: var(--bg-tertiary);
        }

        .node-selector-label {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .node-icon {
            font-size: 14px;
        }

        .node-selector {
            width: 100%;
            padding: 10px 12px;
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-primary);
            font-size: 14px;
            font-family: inherit;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-bottom: 8px;
        }

        .node-selector:hover {
            border-color: var(--primary-color);
            background: var(--bg-hover);
        }

        .node-selector:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }

        .node-selector option {
            background: var(--bg-primary);
            color: var(--text-primary);
            padding: 8px;
        }

        .btn-discover-nodes {
            width: 100%;
            padding: 8px 12px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-secondary);
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }

        .btn-discover-nodes:hover {
            background: var(--primary-color);
            color: white;
            border-color: var(--primary-color);
        }

        .discover-icon {
            font-size: 14px;
        }

        .nav-menu {
            flex: 1;
            padding: 16px 0;
            overflow-y: auto;
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 24px;
            border-radius: 0;
            margin: 0;
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.15s ease;
        }

        .nav-item:hover {
            background: var(--bg-hover);
            color: var(--text-primary);
        }

        .nav-item.active {
            background: var(--bg-tertiary);
            color: var(--accent-primary);
            border-left: 3px solid var(--accent-primary);
            padding-left: 21px;
        }

        .nav-icon {
            width: 20px;
            height: 20px;
            display: inline-block;
        }

        /* ===== USER MENU ===== */
        .user-menu {
            padding: 16px 20px;
            border-top: 1px solid var(--border-color);
            position: absolute;
            bottom: 0;
            width: 260px;
            background: var(--bg-secondary);
        }

        .user-info {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }

        .user-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: var(--accent-primary);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 14px;
        }

        .user-details {
            flex: 1;
        }

        .user-name {
            font-size: 14px;
            font-weight: 500;
            color: var(--text-primary);
        }

        .user-role {
            font-size: 12px;
            color: var(--text-secondary);
        }

        .btn-logout {
            width: 100%;
            padding: 8px 12px;
            background: var(--bg-hover);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            text-decoration: none;
            display: block;
            text-align: center;
            transition: all 0.2s;
        }

        .btn-logout:hover {
            background: var(--bg-tertiary);
        }

        /* ===== MAIN CONTENT ===== */
        .main-content {
            margin-left: 260px;
            flex: 1;
            padding: 24px;
            width: calc(100% - 260px);
        }

        /* ===== HEADER ===== */
        .page-header {
            margin-bottom: 32px;
        }

        .page-title-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .page-title {
            font-size: 24px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .server-info {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: var(--text-secondary);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--status-online);
            box-shadow: 0 0 8px var(--status-online);
        }

        /* ===== CARDS ===== */
        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: var(--shadow-sm);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--divider-color);
        }

        .card-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .card-actions {
            display: flex;
            gap: 8px;
        }

        /* ===== TABLES ===== */
        .table-container {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }

        thead {
            border-bottom: 1px solid var(--divider-color);
        }

        th {
            text-align: left;
            padding: 12px 16px;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
        }

        td {
            padding: 14px 16px;
            color: var(--text-primary);
            border-bottom: 1px solid var(--border-color);
        }

        tbody tr {
            transition: background 0.15s ease;
        }

        tbody tr:hover {
            background: var(--bg-hover);
        }

        tbody tr:last-child td {
            border-bottom: none;
        }

        /* ===== BUTTONS ===== */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            border: none;
            cursor: pointer;
            transition: all 0.15s ease;
            text-decoration: none;
            white-space: nowrap;
        }

        .btn-sm {
            padding: 5px 10px;
            font-size: 12px;
        }

        .btn-primary {
            background: var(--accent-primary);
            color: white;
        }

        .btn-primary:hover {
            background: var(--accent-primary-hover);
            box-shadow: 0 0 12px rgba(59, 130, 246, 0.3);
        }

        .btn-success {
            background: var(--accent-success);
            color: white;
        }

        .btn-success:hover {
            background: #059669;
        }

        .btn-danger {
            background: var(--accent-danger);
            color: white;
        }

        .btn-danger:hover {
            background: #dc2626;
        }

        .btn-secondary {
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }

        .btn-secondary:hover {
            background: var(--bg-hover);
        }

        .btn-ghost {
            background: transparent;
            color: var(--text-secondary);
        }

        .btn-ghost:hover {
            background: var(--bg-hover);
            color: var(--text-primary);
        }

        /* ===== BADGES ===== */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }

        .badge-success {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-success);
        }

        .badge-warning {
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-warning);
        }

        .badge-danger {
            background: rgba(239, 68, 68, 0.15);
            color: var(--accent-danger);
        }

        .badge-info {
            background: rgba(6, 182, 212, 0.15);
            color: var(--accent-info);
        }

        .badge-neutral {
            background: rgba(107, 114, 128, 0.15);
            color: var(--text-secondary);
        }

        .badge-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: currentColor;
        }

        /* ===== ALERTS ===== */
        .alert {
            padding: 14px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 13px;
            line-height: 1.5;
            border-left: 3px solid;
        }

        .alert-success {
            background: rgba(16, 185, 129, 0.1);
            border-color: var(--accent-success);
            color: var(--text-primary);
        }

        .alert-error {
            background: rgba(239, 68, 68, 0.1);
            border-color: var(--accent-danger);
            color: var(--text-primary);
        }

        .alert-info {
            background: rgba(6, 182, 212, 0.1);
            border-color: var(--accent-info);
            color: var(--text-primary);
        }

        .alert strong {
            font-weight: 600;
            color: var(--text-primary);
        }

        /* ===== FORMS ===== */
        .form-group {
            margin-bottom: 16px;
        }

        .form-label {
            display: block;
            margin-bottom: 6px;
            font-size: 13px;
            font-weight: 500;
            color: var(--text-secondary);
        }

        input[type="text"],
        input[type="password"],
        select {
            width: 100%;
            padding: 9px 12px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-primary);
            font-size: 13px;
            transition: all 0.15s ease;
        }

        input:focus,
        select:focus {
            outline: none;
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        /* ===== GRID LAYOUTS ===== */
        .grid {
            display: grid;
            gap: 16px;
        }

        .grid-cols-4 {
            grid-template-columns: repeat(4, 1fr);
        }

        .grid-cols-3 {
            grid-template-columns: repeat(3, 1fr);
        }

        .grid-cols-2 {
            grid-template-columns: repeat(2, 1fr);
        }

        /* ===== STATS CARDS ===== */
        .stat-card {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 16px;
        }

        .stat-label {
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .stat-value {
            font-size: 24px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .stat-change {
            font-size: 12px;
            margin-top: 4px;
        }

        /* ===== RESPONSIVE ===== */
        @media (max-width: 1024px) {
            .sidebar {
                transform: translateX(-100%);
                transition: transform 0.3s ease;
            }

            .main-content {
                margin-left: 0;
                width: 100%;
            }

            .grid-cols-4,
            .grid-cols-3 {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 640px) {
            .grid-cols-4,
            .grid-cols-3,
            .grid-cols-2 {
                grid-template-columns: 1fr;
            }

            .main-content {
                padding: 16px;
            }

            .page-title {
                font-size: 20px;
            }
        }

        /* ===== MOBILE PORTRAIT MODE ENHANCEMENTS ===== */
        @media (max-width: 480px) and (orientation: portrait) {
            body {
                font-size: 14px;
            }

            .main-content {
                padding: 12px;
            }

            .page-title {
                font-size: 18px;
            }

            .page-title-row {
                flex-direction: column;
                align-items: flex-start;
                gap: 8px;
            }

            .server-info {
                font-size: 12px;
            }

            .card {
                padding: 16px;
                margin-bottom: 16px;
            }

            .card-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 12px;
                margin-bottom: 16px;
            }

            .card-title {
                font-size: 15px;
            }

            .card-actions {
                width: 100%;
                flex-wrap: wrap;
            }

            .card-actions .btn {
                flex: 1;
                min-width: 120px;
            }

            /* Table responsiveness */
            .table-container {
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
            }

            table {
                font-size: 12px;
                min-width: 600px;
            }

            th, td {
                padding: 10px 12px;
            }

            th {
                font-size: 11px;
            }

            /* Button adjustments */
            .btn {
                padding: 10px 14px;
                font-size: 13px;
            }

            .btn-sm {
                padding: 8px 12px;
                font-size: 12px;
            }

            /* Form inputs */
            input[type="text"],
            input[type="password"],
            select {
                font-size: 16px; /* Prevents iOS zoom */
                padding: 12px;
            }

            /* Stat cards */
            .stat-value {
                font-size: 22px;
            }

            .stat-label {
                font-size: 11px;
            }

            /* Modal adjustments */
            .modal-content {
                width: 95%;
                padding: 20px;
                max-height: 90vh;
                overflow-y: auto;
            }

            .modal-title {
                font-size: 16px;
            }

            .modal-footer {
                flex-direction: column;
                gap: 8px;
            }

            .modal-footer .btn {
                width: 100%;
            }

            /* Badge adjustments */
            .badge {
                font-size: 10px;
                padding: 3px 8px;
            }

            /* Code block scrolling */
            .code-block {
                font-size: 11px;
                padding: 10px;
                overflow-x: auto;
                white-space: nowrap;
            }
        }

        /* ===== SMALL MOBILE DEVICES ===== */
        @media (max-width: 375px) {
            .main-content {
                padding: 8px;
            }

            .page-title {
                font-size: 16px;
            }

            .card {
                padding: 12px;
            }

            table {
                font-size: 11px;
                min-width: 550px;
            }

            th, td {
                padding: 8px 10px;
            }
        }

        /* ===== UTILITIES ===== */
        .text-sm { font-size: 13px; }
        .text-xs { font-size: 12px; }
        .font-mono { font-family: 'SF Mono', 'Monaco', 'Cascadia Code', 'Courier New', monospace; }
        .flex { display: flex; }
        .items-center { align-items: center; }
        .justify-between { justify-content: space-between; }
        .gap-2 { gap: 8px; }
        .gap-3 { gap: 12px; }
        .mb-4 { margin-bottom: 16px; }
        .mt-4 { margin-top: 16px; }

        /* ===== LOADING INDICATORS ===== */
        /* Loading spinner */
        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: #3b82f6;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Button loading state */
        .btn-loading {
            position: relative;
            color: transparent !important;
            pointer-events: none;
            opacity: 0.7;
        }

        .btn-loading::after {
            content: "";
            position: absolute;
            width: 16px;
            height: 16px;
            top: 50%;
            left: 50%;
            margin-left: -8px;
            margin-top: -8px;
            border: 2px solid #ffffff;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 0.8s linear infinite;
        }

        /* Disable form during submission */
        .form-submitting {
            opacity: 0.6;
            pointer-events: none;
        }

        /* Status overlay for devices table */
        .device-row-loading {
            background-color: rgba(59, 130, 246, 0.1);
            position: relative;
        }

        .device-row-loading::before {
            content: attr(data-status);
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(59, 130, 246, 0.9);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            z-index: 10;
        }

        /* Toast notification */
        .toast-notification {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px 20px;
            box-shadow: var(--shadow-lg);
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 300px;
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        .toast-content {
            display: flex;
            align-items: center;
            gap: 12px;
            color: var(--text-primary);
            font-size: 14px;
        }

        .toast-info {
            border-left: 4px solid var(--accent-primary);
        }

        .toast-success {
            border-left: 4px solid var(--accent-success);
        }

        .toast-error {
            border-left: 4px solid var(--accent-danger);
        }

        /* ===== MODAL ===== */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(4px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }

        .modal-content {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 24px;
            max-width: 500px;
            width: 90%;
            box-shadow: var(--shadow-lg);
        }

        .modal-header {
            margin-bottom: 20px;
        }

        .modal-title {
            font-size: 18px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .modal-body {
            margin-bottom: 20px;
        }

        .modal-footer {
            display: flex;
            justify-content: flex-end;
            gap: 12px;
        }

        .code-block {
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 12px;
            font-family: 'SF Mono', monospace;
            font-size: 13px;
            word-break: break-all;
            color: var(--accent-info);
            margin: 12px 0;
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Sidebar Navigation -->
        <aside class="sidebar">
            <div class="sidebar-brand">
                <div class="brand-logo">
                    <img src="/static/logo" alt="Ranger">
                    <div class="brand-text">
                        <h1>ProxMox Ranger</h1>
                        <div class="subtitle">Hot-Swap Manager v1.2</div>
                    </div>
                </div>
            </div>

            <!-- Node Selector -->
            <div class="node-selector-container">
                <label for="nodeSelector" class="node-selector-label">
                    <span class="node-icon">🖥️</span>
                    Select Node
                </label>
                <select id="nodeSelector" class="node-selector" onchange="switchNode()">
                    <option value="local" selected>{{ hostname }} (Local)</option>
                </select>
                <button class="btn-discover-nodes" onclick="discoverNodes()" title="Discover nodes on network">
                    <span class="discover-icon">🔍</span> Scan
                </button>
            </div>

            <nav class="nav-menu">
                <a href="/shares" class="nav-item active">
                    <span class="nav-icon">◆</span>
                    Devices & Shares
                </a>
                <a href="#users" class="nav-item">
                    <span class="nav-icon">●</span>
                    User Management
                </a>
                <a href="/logs" class="nav-item">
                    <span class="nav-icon">▪</span>
                    System Logs
                </a>
            </nav>

            <div class="user-menu">
                <div class="user-info">
                    <div class="user-avatar">{{ username[0].upper() if username else 'U' }}</div>
                    <div class="user-details">
                        <div class="user-name">{{ username or 'User' }}</div>
                        <div class="user-role">Administrator</div>
                    </div>
                </div>
                <a href="/logout" class="btn-logout">Sign Out</a>
            </div>
        </aside>

        <!-- Main Content -->
        <main class="main-content">
            <div class="page-header">
                <div class="page-title-row">
                    <h1 class="page-title">Storage Management</h1>
                    <div class="server-info">
                        <span class="status-dot"></span>
                        <span>{{ hostname }}</span>
                    </div>
                </div>
            </div>

            {% if message %}
                <div class="alert {{ 'alert-success' if success else 'alert-error' }}">
                    <strong>{{ 'Success' if success else 'Error' }}:</strong> {{ message }}
                </div>
            {% endif %}

            <!-- Block Devices Card -->
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">Block Devices</h2>
                    <div class="card-actions">
                        <button class="btn btn-ghost btn-sm">Refresh</button>
                    </div>
                </div>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Device</th>
                                <th>Size</th>
                                <th>Type</th>
                                <th>Label</th>
                                <th>Mountpoint</th>
                                <th>Usage</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for dev in devices %}
                            <tr>
                                <td><span class="font-mono">{{ dev.name }}</span></td>
                                <td>{{ dev.size }}</td>
                                <td>
                                    {% if dev.fstype %}
                                        <span class="badge badge-neutral">{{ dev.fstype }}</span>
                                    {% else %}
                                        <span class="text-tertiary">-</span>
                                    {% endif %}
                                </td>
                                <td>{{ dev.label or '-' }}</td>
                                <td>
                                    {% if dev.mountpoint %}
                                        <span class="font-mono text-sm">{{ dev.mountpoint }}</span>
                                    {% else %}
                                        <span class="text-tertiary">Not mounted</span>
                                    {% endif %}
                                </td>
                                <td>
                                    {% if dev.used != '-' %}
                                        <div class="flex items-center gap-2">
                                            <span class="text-sm">{{ dev.used }} / {{ dev.available }}</span>
                                            <span class="badge badge-{{ 'warning' if dev.usage_percent.rstrip('%')|int > 80 else 'success' }}">
                                                <span class="badge-dot"></span>
                                                {{ dev.usage_percent }}
                                            </span>
                                        </div>
                                    {% else %}
                                        <span class="text-tertiary">-</span>
                                    {% endif %}
                                </td>
                                <td>
                                    <div class="flex gap-2">
                                        {% if not dev.mountpoint %}
                                            <form method="post" class="mount-form" data-device="{{ dev.name }}" style="display:inline;">
                                                <input type="hidden" name="action" value="mount">
                                                <input type="hidden" name="device" value="{{ dev.name }}">
                                                <button type="submit" class="btn btn-success btn-sm mount-btn">Mount</button>
                                            </form>
                                            <form method="post" style="display:inline;">
                                                <input type="hidden" name="action" value="format">
                                                <input type="hidden" name="device" value="{{ dev.name }}">
                                                <select name="fstype" class="btn-sm" style="width: auto;">
                                                    <option value="ext4">ext4</option>
                                                    <option value="ntfs">NTFS</option>
                                                    <option value="exfat">exFAT</option>
                                                    <option value="fat32">FAT32</option>
                                                </select>
                                                <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('WARNING: This will destroy all data on {{ dev.name }}. Continue?')">Format</button>
                                            </form>
                                        {% else %}
                                            <form method="post" class="unmount-form" data-device="{{ dev.name }}" style="display:inline;">
                                                <input type="hidden" name="action" value="unmount">
                                                <input type="hidden" name="device" value="{{ dev.name }}">
                                                <button type="submit" class="btn btn-danger btn-sm unmount-btn">Unmount</button>
                                            </form>
                                        {% endif %}
                                    </div>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- SMB Shares Card -->
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">SMB Network Shares</h2>
                </div>

                <div class="alert alert-info mb-4">
                    <strong>Authentication Required</strong><br>
                    Use your system credentials to access shares. Username: root or your system username.
                </div>

                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Share Name</th>
                                <th>Path</th>
                                <th>Comment</th>
                                <th>Access</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for share in shares %}
                            <tr>
                                <td><strong>{{ share.name }}</strong></td>
                                <td><span class="font-mono text-sm">{{ share.path }}</span></td>
                                <td>{{ share.comment }}</td>
                                <td>
                                    <button onclick="openShare('{{ share.name }}', '{{ hostname }}')" class="btn btn-primary btn-sm">
                                        Access Share
                                    </button>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- User Management Card -->
            <div class="card" id="users">
                <div class="card-header">
                    <h2 class="card-title">User & Permissions</h2>
                </div>

                <!-- Add User Form -->
                <div style="background: var(--bg-tertiary); padding: 20px; border-radius: 6px; margin-bottom: 24px;">
                    <h3 style="font-size: 14px; font-weight: 600; margin-bottom: 16px; color: var(--text-primary);">Create New User</h3>
                    <form method="post" action="/users/add" class="grid grid-cols-4 gap-3">
                        <div class="form-group" style="margin: 0;">
                            <label class="form-label">Username</label>
                            <input type="text" name="username" placeholder="username" required pattern="[a-z][a-z0-9_-]{2,31}">
                        </div>
                        <div class="form-group" style="margin: 0;">
                            <label class="form-label">Password</label>
                            <input type="password" name="password" placeholder="Min 8 characters" required minlength="8">
                        </div>
                        <div class="form-group" style="margin: 0;">
                            <label class="form-label">Confirm Password</label>
                            <input type="password" name="password_confirm" placeholder="Confirm" required minlength="8">
                        </div>
                        <div style="display: flex; align-items: flex-end;">
                            <button type="submit" class="btn btn-success" style="width: 100%;">Create User</button>
                        </div>
                    </form>
                    <p class="text-xs" style="margin-top: 12px; color: var(--text-secondary);">
                        Creates both system and SMB user with access to all shares
                    </p>
                </div>

                <!-- System Users -->
                <h3 class="text-sm" style="margin-bottom: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px;">System Users (smbusers group)</h3>
                {% if system_users %}
                <div class="table-container mb-4">
                    <table>
                        <thead>
                            <tr>
                                <th>Username</th>
                                <th>UID</th>
                                <th>Groups</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for user in system_users %}
                            <tr>
                                <td><strong>{{ user.username }}</strong></td>
                                <td>{{ user.uid }}</td>
                                <td><span class="badge badge-success">{{ user.groups }}</span></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <div class="alert alert-info mb-4">No users in smbusers group</div>
                {% endif %}

                <!-- SMB Users -->
                <h3 class="text-sm" style="margin-bottom: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px;">SMB Authenticated Users</h3>
                {% if smb_users %}
                <div class="table-container mb-4">
                    <table>
                        <thead>
                            <tr>
                                <th>Username</th>
                                <th>Password Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for user in smb_users %}
                            <tr>
                                <td><strong>{{ user.username }}</strong></td>
                                <td>
                                    <span class="badge badge-{{ 'success' if user.has_password == 'Yes' else 'warning' }}">
                                        <span class="badge-dot"></span>
                                        {{ user.has_password }}
                                    </span>
                                </td>
                                <td>
                                    <form method="post" action="/users/remove" style="display: inline;">
                                        <input type="hidden" name="username" value="{{ user.username }}">
                                        <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('Remove SMB access for {{ user.username }}? System account will be preserved.')">
                                            Remove Access
                                        </button>
                                    </form>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <div class="alert alert-info mb-4">No SMB users configured</div>
                {% endif %}

                <!-- Share ACLs -->
                <h3 class="text-sm" style="margin-bottom: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px;">Share Access Control</h3>
                {% if share_acls %}
                    {% for share in share_acls %}
                    <div style="margin-bottom: 20px; padding: 16px; background: var(--bg-tertiary); border-radius: 6px;">
                        <h4 style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: var(--text-primary);">{{ share.name }}</h4>
                        <table>
                            <thead>
                                <tr>
                                    <th>Principal</th>
                                    <th>Permission</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for acl in share.acls %}
                                <tr>
                                    <td><strong>{{ acl.principal }}</strong></td>
                                    <td>
                                        <span class="badge badge-{{ 'success' if acl.permission == 'Full Control' else 'warning' if acl.permission == 'Read Only' else 'danger' }}">
                                            {{ acl.permission }}
                                        </span>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                    {% endfor %}
                {% else %}
                <div class="alert alert-info">No shares configured</div>
                {% endif %}
            </div>

            <!-- Mounted Filesystems -->
            <div class="grid grid-cols-2">
                <div class="card">
                    <div class="card-header">
                        <h2 class="card-title">Mounted Devices</h2>
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Device</th>
                                    <th>Mountpoint</th>
                                    <th>Type</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for fs in mounts %}
                                <tr>
                                    <td><span class="font-mono">{{ fs.device }}</span></td>
                                    <td><span class="font-mono text-sm">{{ fs.mountpoint }}</span></td>
                                    <td><span class="badge badge-success">{{ fs.fstype }}</span></td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h2 class="card-title">System Filesystems</h2>
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Device</th>
                                    <th>Mountpoint</th>
                                    <th>Type</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for fs in all_mounts %}
                                <tr>
                                    <td><span class="font-mono text-sm">{{ fs.device }}</span></td>
                                    <td><span class="font-mono text-xs">{{ fs.mountpoint }}</span></td>
                                    <td><span class="badge badge-neutral">{{ fs.fstype }}</span></td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <!-- Share Access Modal -->
    <div id="shareModal" class="modal-overlay" style="display: none;">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">Access SMB Share</h3>
            </div>
            <div class="modal-body">
                <p id="modalMessage" style="margin-bottom: 16px; color: var(--text-secondary); line-height: 1.5;"></p>
                <div class="code-block" id="sharePath"></div>
            </div>
            <div class="modal-footer">
                <button onclick="copyPath()" class="btn btn-success">Copy Path</button>
                <button onclick="closeModal()" class="btn btn-secondary">Close</button>
            </div>
        </div>
    </div>

    <script>
        let currentSharePath = '';

        function openShare(shareName, serverHost) {
            const userAgent = navigator.userAgent.toLowerCase();
            const isWindows = userAgent.indexOf('windows') !== -1;
            const isMac = userAgent.indexOf('mac') !== -1;
            const isLinux = userAgent.indexOf('linux') !== -1 && userAgent.indexOf('android') === -1;

            if (isWindows) {
                currentSharePath = '\\\\\\\\' + serverHost + '\\\\' + shareName;
                document.getElementById('modalMessage').innerHTML =
                    '<strong>Windows Instructions:</strong><br>' +
                    '1. Copy the path below<br>' +
                    '2. Press Win+E to open File Explorer<br>' +
                    '3. Paste (Ctrl+V) in the address bar<br>' +
                    '4. Press Enter and login';
                document.getElementById('sharePath').textContent = currentSharePath;
                document.getElementById('shareModal').style.display = 'flex';
                navigator.clipboard.writeText(currentSharePath).catch(() => {});
            } else if (isMac || isLinux) {
                const shareUrl = 'smb://' + serverHost + '/' + shareName;
                window.location.href = shareUrl;
            } else {
                currentSharePath = 'smb://' + serverHost + '/' + shareName;
                document.getElementById('modalMessage').textContent =
                    'Copy the SMB path and paste it into your file manager:';
                document.getElementById('sharePath').textContent = currentSharePath;
                document.getElementById('shareModal').style.display = 'flex';
            }
        }

        function copyPath() {
            navigator.clipboard.writeText(currentSharePath).then(() => {
                alert('Path copied to clipboard!');
            }).catch(() => {
                const temp = document.createElement('textarea');
                temp.value = currentSharePath;
                document.body.appendChild(temp);
                temp.select();
                document.execCommand('copy');
                document.body.removeChild(temp);
                alert('Path copied!');
            });
        }

        function closeModal() {
            document.getElementById('shareModal').style.display = 'none';
        }

        document.getElementById('shareModal').addEventListener('click', (e) => {
            if (e.target === document.getElementById('shareModal')) closeModal();
        });

        // ===== MULTI-NODE SUPPORT FUNCTIONS =====

        let currentSelectedNode = 'local';
        let nodesCache = [];

        // Load nodes on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadNodes();
        });

        function loadNodes() {
            fetch('/api/nodes')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        nodesCache = data.nodes;
                        updateNodeSelector();
                    }
                })
                .catch(error => console.error('Error loading nodes:', error));
        }

        function updateNodeSelector() {
            const selector = document.getElementById('nodeSelector');
            if (!selector) return;

            // Clear existing options
            selector.innerHTML = '';

            // Add nodes to dropdown
            nodesCache.forEach(node => {
                const option = document.createElement('option');
                option.value = node.is_local ? 'local' : node.ip;
                option.textContent = node.is_local
                    ? `${node.hostname} (Local)`
                    : `${node.hostname} (${node.ip})${node.auto_discovered ? ' 🔍' : ''}`;

                if (node.status !== 'online') {
                    option.textContent += ' [OFFLINE]';
                    option.disabled = true;
                }

                if (node.is_local || option.value === currentSelectedNode) {
                    option.selected = true;
                    currentSelectedNode = option.value;
                }

                selector.appendChild(option);
            });
        }

        function switchNode() {
            const selector = document.getElementById('nodeSelector');
            const selectedValue = selector.value;

            currentSelectedNode = selectedValue;

            if (selectedValue === 'local') {
                // Reload current page to show local node
                window.location.reload();
            } else {
                // Navigate to remote node
                const selectedNode = nodesCache.find(n => n.ip === selectedValue);
                if (selectedNode) {
                    const remoteUrl = `http://${selectedNode.ip}:${selectedNode.port}/shares`;
                    window.location.href = remoteUrl;
                }
            }
        }

        function discoverNodes() {
            const btn = event.target.closest('.btn-discover-nodes');
            const originalText = btn.innerHTML;

            // Show loading state
            btn.disabled = true;
            btn.innerHTML = '<span class="discover-icon">⏳</span> Scanning...';

            fetch('/api/nodes/discover', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Wait a bit for discovery to find nodes, then reload
                    setTimeout(() => {
                        loadNodes();
                        btn.disabled = false;
                        btn.innerHTML = '<span class="discover-icon">✓</span> Complete!';
                        setTimeout(() => {
                            btn.innerHTML = originalText;
                        }, 2000);
                    }, 3000);
                } else {
                    btn.disabled = false;
                    btn.innerHTML = '<span class="discover-icon">✗</span> ' + (data.error || 'Failed');
                    setTimeout(() => {
                        btn.innerHTML = originalText;
                    }, 3000);
                }
            })
            .catch(error => {
                console.error('Discovery error:', error);
                btn.disabled = false;
                btn.innerHTML = originalText;
            });
        }
    </script>
</body>
</html>
"""

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)

def ensure_samba_config():
    """Ensure Samba is configured to show username field in authentication dialogs"""
    try:
        smb_conf = '/etc/samba/smb.conf'

        # Read current config
        with open(smb_conf, 'r') as f:
            config = f.read()

        modified = False

        # Ensure map to guest is set to Never (requires username)
        if 'map to guest' not in config.lower():
            logging.info("Adding 'map to guest = Never' to Samba config")
            # Add to global section
            config = config.replace('[global]', '[global]\n   map to guest = Never\n   security = user')
            modified = True
        elif 'map to guest = bad user' in config.lower():
            logging.info("Changing 'map to guest' from 'Bad User' to 'Never'")
            config = config.replace('map to guest = Bad User', 'map to guest = Never')
            config = config.replace('map to guest = bad user', 'map to guest = Never')
            modified = True

        # Ensure security mode is set to user
        if 'security = user' not in config.lower():
            logging.info("Adding 'security = user' to Samba config")
            config = config.replace('[global]', '[global]\n   security = user')
            modified = True

        if modified:
            # Backup original config
            import shutil
            from datetime import datetime
            backup_path = f"{smb_conf}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy(smb_conf, backup_path)
            logging.info(f"Backed up Samba config to {backup_path}")

            # Write updated config
            with open(smb_conf, 'w') as f:
                f.write(config)
            logging.info("Updated Samba configuration")

            # Restart Samba
            run_cmd("systemctl restart smbd 2>/dev/null || systemctl restart samba 2>/dev/null")
            logging.info("Restarted Samba service")
            return True
        else:
            logging.info("Samba configuration already correct")
            return False

    except PermissionError:
        logging.warning("Unable to modify Samba config - insufficient permissions. Run as root for full functionality.")
        return False
    except Exception as e:
        logging.error(f"Error configuring Samba: {e}")
        return False

def get_system_users():
    """Get all users in the smbusers group"""
    try:
        success, output = run_cmd("getent group smbusers")
        if success and output:
            # Format: smbusers:x:1001:user1,user2,user3
            parts = output.strip().split(':')
            if len(parts) >= 4 and parts[3]:
                usernames = parts[3].split(',')
                users = []
                for username in usernames:
                    username = username.strip()
                    if username:
                        # Get user details
                        success_id, id_output = run_cmd(f"id {username}")
                        uid = '-'
                        groups = []
                        if success_id:
                            # Parse: uid=1000(username) gid=1000(group) groups=1000(group),1001(smbusers)
                            for part in id_output.split():
                                if part.startswith('uid='):
                                    uid = part.split('(')[0].replace('uid=', '')
                                elif part.startswith('groups='):
                                    groups_str = part.replace('groups=', '')
                                    groups = [g.split('(')[1].rstrip(')') for g in groups_str.split(',') if '(' in g]

                        users.append({
                            'username': username,
                            'uid': uid,
                            'groups': ', '.join(groups) if groups else 'smbusers'
                        })
                return users
        return []
    except Exception as e:
        logging.error(f"Error getting system users: {e}")
        return []

def get_smb_users():
    """Get all SMB authenticated users"""
    try:
        success, output = run_cmd("pdbedit -L -w 2>/dev/null")
        if success and output:
            users = []
            for line in output.strip().split('\n'):
                if line and ':' in line:
                    # Format: username:uid:XXXXXXXX:YYYYYYYY:[U          ]:LCT-...
                    parts = line.split(':')
                    if len(parts) >= 2:
                        username = parts[0]
                        # Check if user has password set (not disabled)
                        has_password = len(parts) >= 4 and parts[3] and parts[3] != 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
                        users.append({
                            'username': username,
                            'has_password': 'Yes' if has_password else 'No'
                        })
            return users
        return []
    except Exception as e:
        logging.error(f"Error getting SMB users: {e}")
        return []

def get_share_acls():
    """Get ACLs for all shares"""
    try:
        shares_with_acls = []
        success, share_list = run_cmd("net usershare list")
        if success and share_list:
            for share_name in share_list.strip().split('\n'):
                if share_name:
                    share_name = share_name.strip()
                    success_info, info_output = run_cmd(f"net usershare info {share_name}")
                    if success_info:
                        acls = []
                        for line in info_output.split('\n'):
                            if line.startswith('usershare_acl='):
                                # Format: usershare_acl=Everyone:F,user1:R
                                acl_str = line.replace('usershare_acl=', '').strip().rstrip(',')
                                for acl_entry in acl_str.split(','):
                                    if ':' in acl_entry:
                                        principal, perm = acl_entry.split(':', 1)
                                        perm_name = {'F': 'Full Control', 'R': 'Read Only', 'D': 'Deny'}.get(perm, perm)
                                        acls.append({
                                            'principal': principal,
                                            'permission': perm_name
                                        })
                        shares_with_acls.append({
                            'name': share_name,
                            'acls': acls
                        })
        return shares_with_acls
    except Exception as e:
        logging.error(f"Error getting share ACLs: {e}")
        return []

def create_user(username, password):
    """
    Create both system and SMB user in one integrated operation

    Security features:
    - Username validation (alphanumeric, lowercase, 3-32 chars)
    - Password minimum length check
    - No password logging
    - Automatic addition to smbusers group
    """
    import re

    # Validate username format
    if not re.match(r'^[a-z][a-z0-9_-]{2,31}$', username):
        return False, "Username must start with lowercase letter, contain only lowercase letters, numbers, hyphens, or underscores, and be 3-32 characters long"

    # Check password strength
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    # Check if user already exists
    success, _ = run_cmd(f"id {username} 2>/dev/null")
    if success:
        return False, f"User '{username}' already exists"

    try:
        # Step 1: Create system user with home directory and add to smbusers group
        success, output = run_cmd(f"useradd -m -G smbusers -s /bin/bash {username}")
        if not success:
            logging.error(f"Failed to create system user: {output}")
            return False, f"Failed to create system user: {output}"

        logging.info(f"Created system user: {username}")

        # Step 2: Set system password using chpasswd (secure, no password in process list)
        import subprocess
        try:
            proc = subprocess.Popen(['chpasswd'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(input=f"{username}:{password}\n".encode())
            if proc.returncode != 0:
                logging.error(f"Failed to set system password: {stderr.decode()}")
                # Rollback: delete user
                run_cmd(f"userdel -r {username}")
                return False, f"Failed to set system password: {stderr.decode()}"
        except Exception as e:
            logging.error(f"Error setting system password: {e}")
            run_cmd(f"userdel -r {username}")
            return False, f"Error setting system password: {str(e)}"

        logging.info(f"Set system password for: {username}")

        # Step 3: Create SMB password using smbpasswd
        try:
            proc = subprocess.Popen(['smbpasswd', '-a', '-s', username],
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(input=f"{password}\n{password}\n".encode())
            if proc.returncode != 0:
                logging.error(f"Failed to set SMB password: {stderr.decode()}")
                # Rollback: delete user
                run_cmd(f"smbpasswd -x {username} 2>/dev/null")
                run_cmd(f"userdel -r {username}")
                return False, f"Failed to set SMB password: {stderr.decode()}"
        except Exception as e:
            logging.error(f"Error setting SMB password: {e}")
            run_cmd(f"userdel -r {username}")
            return False, f"Error setting SMB password: {str(e)}"

        logging.info(f"Set SMB password for: {username}")

        # Step 4: Enable SMB user
        success, output = run_cmd(f"smbpasswd -e {username}")
        if not success:
            logging.warning(f"Failed to enable SMB user (may already be enabled): {output}")

        logging.info(f"Successfully created integrated user: {username}")
        return True, f"Successfully created user '{username}' with system and SMB access"

    except Exception as e:
        logging.error(f"Error creating user: {e}")
        # Attempt cleanup
        run_cmd(f"smbpasswd -x {username} 2>/dev/null")
        run_cmd(f"userdel -r {username} 2>/dev/null")
        return False, f"Error creating user: {str(e)}"

def remove_smb_user(username):
    """
    Remove only SMB access for a user (keeps system account)

    This is safer than full user deletion as it preserves:
    - User's home directory and files
    - System account and UID
    - Only removes SMB authentication
    """
    try:
        # Check if user exists
        success, _ = run_cmd(f"id {username} 2>/dev/null")
        if not success:
            return False, f"User '{username}' does not exist"

        # Remove SMB password
        success, output = run_cmd(f"smbpasswd -x {username} 2>&1")
        if not success and "not found" not in output.lower():
            logging.error(f"Failed to remove SMB user: {output}")
            return False, f"Failed to remove SMB access: {output}"

        # Remove from smbusers group
        success, output = run_cmd(f"gpasswd -d {username} smbusers 2>&1")
        if not success and "not a member" not in output.lower():
            logging.warning(f"Failed to remove from smbusers group: {output}")

        logging.info(f"Removed SMB access for user: {username}")
        return True, f"Successfully removed SMB access for '{username}' (system account preserved)"

    except Exception as e:
        logging.error(f"Error removing SMB user: {e}")
        return False, f"Error removing SMB access: {str(e)}"

def get_devices():
    """
    Get list of mountable block devices and their partitions.
    Shows partitions that have filesystems, and parent disks only if they have no partitions.
    """
    success, output = run_cmd("lsblk -J -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT,TYPE")
    if success:
        data = json.loads(output)
        devices = []

        def process_device(dev, parent_path=''):
            """Recursively process device and its children (partitions)"""
            # Build device path
            if parent_path:
                device_name = f"{parent_path}{dev['name']}"
            else:
                device_name = f"/dev/{dev['name']}"

            # Get device properties
            mountpoint = dev.get('mountpoint')
            fstype = dev.get('fstype')
            dev_type = dev.get('type', 'disk')
            has_children = 'children' in dev and len(dev['children']) > 0

            # Get storage usage for mounted devices
            used = '-'
            available = '-'
            usage_percent = '-'

            if mountpoint:
                # Use df to get storage info
                success_df, df_output = run_cmd(f"df -h {mountpoint} | tail -1")
                if success_df:
                    parts = df_output.split()
                    if len(parts) >= 5:
                        # Format: Filesystem Size Used Avail Use% Mounted
                        used = parts[2]
                        available = parts[3]
                        usage_percent = parts[4]

            # Decide if this device should be shown:
            # 1. If it's a partition with a filesystem, always show it
            # 2. If it's a partition that's mounted (even without fstype, e.g. LVM), show it
            # 3. If it's a disk with no partitions and has a filesystem, show it
            # 4. Skip disks that have partitions (can't mount them directly)
            # 5. Skip swap, lvm volumes, and other system types unless mounted

            should_show = False

            if dev_type == 'part':
                # Show partitions if they have a filesystem OR are mounted
                if fstype and fstype not in ('LVM2_member', 'zfs_member'):
                    should_show = True
                elif mountpoint:
                    should_show = True
            elif dev_type == 'disk':
                # Show disks only if they have NO partitions AND have a filesystem
                if not has_children and fstype:
                    should_show = True

            if should_show:
                devices.append({
                    'name': device_name,
                    'size': dev.get('size', '-'),
                    'fstype': fstype,
                    'label': dev.get('label'),
                    'mountpoint': mountpoint,
                    'used': used,
                    'available': available,
                    'usage_percent': usage_percent,
                    'type': dev_type
                })

            # Recursively process children (partitions)
            if has_children:
                for child in dev['children']:
                    process_device(child, parent_path)

        # Process all block devices
        for dev in data.get('blockdevices', []):
            # Only process hotswap-type devices
            if dev['name'].startswith(('sd', 'nvme', 'vd')):
                process_device(dev)

        return devices
    return []

def get_mounts():
    success, output = run_cmd("mount | grep -E '/dev/sd|/dev/nvme|/dev/vd'")
    mounts = []
    if success:
        for line in output.split('\n'):
            if line:
                parts = line.split()
                if len(parts) >= 3:
                    mounts.append({
                        'device': parts[0],
                        'mountpoint': parts[2],
                        'fstype': parts[4] if len(parts) > 4 else '-'
                    })
    return mounts

def get_all_mounts():
    success, output = run_cmd("mount | grep -v -E '/dev/sd|/dev/nvme|/dev/vd'")
    all_mounts = []
    if success:
        for line in output.split('\n'):
            if line:
                parts = line.split()
                if len(parts) >= 3:
                    all_mounts.append({
                        'device': parts[0],
                        'mountpoint': parts[2],
                        'fstype': parts[4] if len(parts) > 4 else '-'
                    })
    return all_mounts

def get_shares():
    """Get list of SMB usershares, skipping any corrupted entries"""
    success, output = run_cmd("net usershare list")
    shares = []
    corrupted_shares = []

    if success and output:
        share_names = output.strip().split('\n')
        for share_name in share_names:
            share_name = share_name.strip()
            if not share_name:
                continue

            # Get detailed info for each share
            success_info, info_output = run_cmd(f"net usershare info {share_name} 2>&1")

            if success_info and info_output:
                path = ""
                comment = ""
                for line in info_output.split('\n'):
                    if line.startswith('path='):
                        path = line.split('=', 1)[1]
                    elif line.startswith('comment='):
                        comment = line.split('=', 1)[1]

                # Only add if we got valid path
                if path:
                    shares.append({
                        'name': share_name,
                        'path': path,
                        'comment': comment
                    })
                else:
                    logging.warning(f"Share {share_name} has no path, skipping")
                    corrupted_shares.append(share_name)
            else:
                # Share info failed - likely corrupted
                logging.error(f"Failed to get info for share '{share_name}': {info_output}")
                corrupted_shares.append(share_name)

    # Log summary
    if corrupted_shares:
        logging.warning(f"Skipped {len(corrupted_shares)} corrupted share(s): {', '.join(corrupted_shares)}")
        logging.info(f"To clean up corrupted shares, run: net usershare delete <sharename>")

    return shares

def mount_device(device):
    logging.info(f"Mounting device: {device}")
    # Get filesystem type
    success, fstype = run_cmd(f"blkid -s TYPE -o value {device}")
    fstype = fstype if success else "unknown"
    
    # Get label
    success, label = run_cmd(f"blkid -s LABEL -o value {device}")
    if not success or not label:
        success, uuid = run_cmd(f"blkid -s UUID -o value {device}")
        if success and uuid:
            label = f"usb_{uuid[:8]}"
        else:
            label = f"usb_{device.split('/')[-1]}"
    
    mountpoint = f"/media/{label}"
    run_cmd(f"mkdir -p {mountpoint}")
    
    success, _ = run_cmd(f"mount {device} {mountpoint}")
    if success:
        # Set proper permissions for multi-user write access
        # Using 2775: rwxrwsr-x
        # - 2xxx = setgid bit (new files inherit group)
        # - x7xx = owner (root) has rwx
        # - x7x = group (smbusers) has rwx
        # - xx5 = others have rx
        run_cmd(f"chgrp -R smbusers {mountpoint}")
        run_cmd(f"chmod 2775 {mountpoint}")

        # Set permissions on existing files/dirs if any
        run_cmd(f"find {mountpoint} -type d -exec chmod 2775 {{}} \\; 2>/dev/null")
        run_cmd(f"find {mountpoint} -type f -exec chmod 664 {{}} \\; 2>/dev/null")
        run_cmd(f"find {mountpoint} -exec chgrp smbusers {{}} \\; 2>/dev/null")

        success_hn, hn = run_cmd("hostname")
        hn = hn if success_hn else "server"

        # Create share with guest_ok=no to require authentication
        # This ensures the username field appears in auth dialogs
        run_cmd(f"net usershare add {label} {mountpoint} 'Shared {label}' '' 'guest_ok=no'")

        # Set full access ACL for authenticated users
        run_cmd(f"net usershare setacl {label} Everyone:F")

        logging.info(f"Mounted {device} ({fstype}) to {mountpoint} and shared as {label} (auth required, write enabled)")
        return True, f"Mounted {device} ({fstype}) to {mountpoint} and shared as \\\\{hn}\\{label} (requires authentication, write enabled)"
    else:
        run_cmd(f"rmdir {mountpoint}")
        logging.error(f"Failed to mount {device}")
        return False, f"Failed to mount {device}"

def unmount_device(device):
    success, mountpoint = run_cmd(f"mount | grep '^{device}' | awk '{{print $3}}'")
    if success and mountpoint:
        label = mountpoint.split('/')[-1]
        run_cmd(f"net usershare delete {label}")
        run_cmd(f"umount {mountpoint}")
        run_cmd(f"rmdir {mountpoint}")
        return True, f"Unmounted and removed share for {device}"
    return False, f"Device {device} is not mounted"

def format_device(device, fstype):
    logging.info(f"Formatting device: {device} as {fstype}")
    # Install tools if needed
    if fstype == "ext4":
        run_cmd("apt-get install -y e2fsprogs")
        cmd = f"mkfs.ext4 -F {device}"
    elif fstype == "ntfs":
        run_cmd("apt-get install -y ntfs-3g")
        cmd = f"mkfs.ntfs -f {device}"
    elif fstype == "exfat":
        run_cmd("apt-get install -y exfatprogs")
        cmd = f"mkfs.exfat {device}"
    elif fstype == "fat32":
        run_cmd("apt-get install -y dosfstools")
        cmd = f"mkfs.vfat -F 32 {device}"
    else:
        logging.error(f"Unsupported filesystem: {fstype}")
        return False, f"Unsupported filesystem: {fstype}"
    
    success, output = run_cmd(cmd)
    if success:
        logging.info(f"Successfully formatted {device} as {fstype}")
        return True, f"Successfully formatted {device} as {fstype}"
    else:
        logging.error(f"Failed to format {device}: {output}")
        return False, f"Failed to format {device}: {output}"


# ============================================================================
# REST API ENDPOINTS - Multi-Node Communication
# ============================================================================

@app.route('/api/info', methods=['GET'])
def api_info():
    """Public endpoint - Returns basic node information"""
    node_info = get_local_node_info()
    return jsonify({
        'app': 'ProxMoxRanger',
        'version': node_info['version'],
        'hostname': node_info['hostname'],
        'ip': node_info['ip'],
        'port': node_info['port']
    })

@app.route('/api/devices', methods=['GET'])
@ip_whitelist_required
def api_get_devices():
    """API endpoint - Get all block devices"""
    try:
        devices = get_devices()
        return jsonify({'success': True, 'devices': devices})
    except Exception as e:
        logging.error(f"API error getting devices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/mounts', methods=['GET'])
@ip_whitelist_required
def api_get_mounts():
    """API endpoint - Get all mounted devices"""
    try:
        mounts = get_mounts()
        return jsonify({'success': True, 'mounts': mounts})
    except Exception as e:
        logging.error(f"API error getting mounts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/shares', methods=['GET'])
@ip_whitelist_required
def api_get_shares():
    """API endpoint - Get all SMB shares"""
    try:
        shares = get_shares()
        return jsonify({'success': True, 'shares': shares})
    except Exception as e:
        logging.error(f"API error getting shares: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/mount', methods=['POST'])
@ip_whitelist_required
def api_mount_device():
    """API endpoint - Mount a device"""
    try:
        data = request.get_json()
        device = data.get('device')
        if not device:
            return jsonify({'success': False, 'error': 'Device parameter required'}), 400

        success, message = mount_device(device)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        logging.error(f"API error mounting device: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/unmount', methods=['POST'])
@ip_whitelist_required
def api_unmount_device():
    """API endpoint - Unmount a device"""
    try:
        data = request.get_json()
        device = data.get('device')
        if not device:
            return jsonify({'success': False, 'error': 'Device parameter required'}), 400

        success, message = unmount_device(device)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        logging.error(f"API error unmounting device: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/nodes', methods=['GET'])
@ip_whitelist_required
def api_get_nodes():
    """API endpoint - Get all registered nodes"""
    try:
        nodes = get_nodes()
        local_info = get_local_node_info()

        # Add local node to the list
        all_nodes = [{
            'hostname': local_info['hostname'],
            'ip': local_info['ip'],
            'port': local_info['port'],
            'status': 'online',
            'is_local': True
        }]

        # Add registered nodes
        for node in nodes:
            all_nodes.append({
                'hostname': node['hostname'],
                'ip': node['ip'],
                'port': node['port'],
                'status': node['status'],
                'is_local': False,
                'auto_discovered': node.get('auto_discovered', False)
            })

        return jsonify({'success': True, 'nodes': all_nodes})
    except Exception as e:
        logging.error(f"API error getting nodes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/nodes/register', methods=['POST'])
@ip_whitelist_required
def api_register_node():
    """API endpoint - Manually register a node"""
    try:
        data = request.get_json()
        hostname = data.get('hostname')
        ip = data.get('ip')
        port = data.get('port', 8010)

        if not hostname or not ip:
            return jsonify({'success': False, 'error': 'Hostname and IP required'}), 400

        node = register_node(hostname, ip, port, auto_discovered=False)
        return jsonify({'success': True, 'node': node})
    except Exception as e:
        logging.error(f"API error registering node: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/nodes/unregister', methods=['POST'])
@ip_whitelist_required
def api_unregister_node():
    """API endpoint - Unregister a node"""
    try:
        data = request.get_json()
        ip = data.get('ip')
        port = data.get('port', 8010)

        if not ip:
            return jsonify({'success': False, 'error': 'IP required'}), 400

        unregister_node(ip, port)
        return jsonify({'success': True, 'message': f'Node {ip}:{port} unregistered'})
    except Exception as e:
        logging.error(f"API error unregistering node: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/nodes/discover', methods=['POST'])
@login_required
@ip_whitelist_required
def api_discover_nodes():
    """API endpoint - Trigger node discovery scan"""
    try:
        data = request.get_json() or {}
        network_range = data.get('network_range')

        # Run discovery in background thread
        thread = threading.Thread(target=discover_nodes_on_network, args=(network_range,))
        thread.start()

        return jsonify({'success': True, 'message': 'Node discovery started'})
    except Exception as e:
        logging.error(f"API error starting discovery: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/login', methods=['GET', 'POST'])
@ip_whitelist_required
def login():
    """Login page and authentication handler"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Verify credentials against Proxmox host using PAM
        if verify_pam_credentials(username, password):
            session['logged_in'] = True
            session['username'] = username
            session.permanent = True
            logging.info(f"User {username} logged in successfully")

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            logging.warning(f"Failed login attempt for user {username}")
            flash('Invalid credentials', 'error')

    login_template = """
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - ProxMox Ranger</title>
    <style>
        :root[data-theme="dark"] {
            --bg-primary: #0f1419;
            --bg-secondary: #1a1f2e;
            --bg-tertiary: #252d3d;
            --text-primary: #e4e7eb;
            --text-secondary: #9ca3af;
            --accent-primary: #3b82f6;
            --accent-primary-hover: #2563eb;
            --accent-danger: #ef4444;
            --border-color: #2d3548;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .login-container {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 48px;
            width: 100%;
            max-width: 420px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }

        .login-header {
            text-align: center;
            margin-bottom: 32px;
        }

        .login-header h1 {
            font-size: 24px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 8px;
        }

        .login-header p {
            font-size: 14px;
            color: var(--text-secondary);
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            font-size: 14px;
            font-weight: 500;
            color: var(--text-primary);
            margin-bottom: 8px;
        }

        .form-group input {
            width: 100%;
            padding: 12px 16px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 14px;
            transition: all 0.2s;
        }

        .form-group input:focus {
            outline: none;
            border-color: var(--accent-primary);
        }

        .btn-login {
            width: 100%;
            padding: 12px 16px;
            background: var(--accent-primary);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-login:hover {
            background: var(--accent-primary-hover);
        }

        .alert {
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }

        .alert-error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid var(--accent-danger);
            color: var(--accent-danger);
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1>ProxMox Ranger</h1>
            <p>Sign in with your Proxmox credentials</p>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST" action="{{ url_for('login') }}">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required autofocus>
            </div>

            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>

            <button type="submit" class="btn-login">Sign In</button>
        </form>
    </div>
</body>
</html>
"""

    return render_template_string(login_template)

@app.route('/logout')
def logout():
    """Logout handler"""
    username = session.get('username', 'unknown')
    session.clear()
    logging.info(f"User {username} logged out")
    return redirect(url_for('login'))

def verify_pam_credentials(username, password):
    """Verify credentials against system PAM (Proxmox host authentication)"""
    try:
        # Use 'su' to verify credentials via PAM
        # This is more secure than reading /etc/shadow and works with any auth backend
        process = subprocess.Popen(
            ['su', username, '-c', 'true'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=password + '\n', timeout=5)

        # If 'su' succeeded, credentials are valid
        if process.returncode == 0:
            return True
        return False
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout verifying credentials for user {username}")
        return False
    except Exception as e:
        logging.error(f"Failed to verify credentials: {e}")
        return False

@app.route('/')
@ip_whitelist_required
@login_required
def index():
    """Redirect root to /shares"""
    return redirect(url_for('shares'))

@login_required
@app.route('/shares', methods=['GET', 'POST'])
@ip_whitelist_required
def shares():
    logging.info("Web UI accessed")
    message = None
    success = False

    # Check for query parameters (from redirects)
    if request.args.get('message'):
        message = request.args.get('message')
        success = request.args.get('success', 'false') == 'true'

    if request.method == 'POST':
        action = request.form.get('action')
        device = request.form.get('device')
        logging.info(f"POST request: action={action}, device={device}")

        if action == 'mount':
            success, message = mount_device(device)
        elif action == 'unmount':
            success, message = unmount_device(device)
        elif action == 'format':
            fstype = request.form.get('fstype')
            success, message = format_device(device, fstype)
    
    devices = get_devices()
    mounts = get_mounts()
    shares = get_shares()
    all_mounts = get_all_mounts()

    # Get user and permissions data
    system_users = get_system_users()
    smb_users = get_smb_users()
    share_acls = get_share_acls()

    success, hostname = run_cmd("hostname")
    hostname = hostname if success else "Unknown"

    # Get the actual IP address for SMB/SFTP links
    # This ensures links work even if hostname doesn't resolve on client
    import socket
    try:
        # Get IP of the interface that would route to 8.8.8.8
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        server_ip = s.getsockname()[0]
        s.close()
    except:
        # Fallback to hostname if we can't get IP
        server_ip = hostname

    return render_template_string(HTML_TEMPLATE,
                                devices=devices,
                                mounts=mounts,
                                all_mounts=all_mounts,
                                shares=shares,
                                system_users=system_users,
                                smb_users=smb_users,
                                share_acls=share_acls,
                                hostname=server_ip,  # Use IP instead of hostname
                                message=message,
                                success=success)

@login_required
@app.route('/users/add', methods=['POST'])
@ip_whitelist_required
def add_user():
    """Handle user creation POST request"""
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '')
    password_confirm = request.form.get('password_confirm', '')

    # Validate passwords match
    if password != password_confirm:
        return redirect(url_for('shares') + '?message=Passwords do not match&success=false')

    # Create integrated user (system + SMB)
    success, message = create_user(username, password)

    # Redirect back to main page with message
    success_param = 'true' if success else 'false'
    return redirect(url_for('shares') + f'?message={message}&success={success_param}')

@login_required
@app.route('/users/remove', methods=['POST'])
@ip_whitelist_required
def remove_user():
    """Handle SMB user removal POST request"""
    username = request.form.get('username', '').strip()

    if not username:
        return redirect(url_for('shares') + '?message=Username required&success=false')

    # Remove SMB access only (preserve system account)
    success, message = remove_smb_user(username)

    # Redirect back to main page with message
    success_param = 'true' if success else 'false'
    return redirect(url_for('shares') + f'?message={message}&success={success_param}')


@login_required
@app.route('/static/logo')
def serve_logo():
    """Serve the RangerMark logo"""
    # Try multiple potential logo locations
    logo_paths = [
        '/opt/proxmox-ranger/lib/assets/RangerMark.png',
        '/opt/proxmox-ranger/assets/RangerMark.png',
        '/usr/local/bin/pmranger/assets/RangerMark.png',
        '/opt/proxmox-ranger/RangerMark.png'
    ]

    for logo_path in logo_paths:
        if os.path.exists(logo_path):
            return send_file(logo_path, mimetype='image/png')

    # Fallback: return 404
    logging.warning("RangerMark logo not found in any expected location")
    abort(404)

@login_required
@app.route('/logs')
@ip_whitelist_required
def logs():
    logging.info("Logs page accessed")
    try:
        with open('/var/log/hotswap-manager.log', 'r') as f:
            manager_logs = f.read()
    except FileNotFoundError:
        manager_logs = "Log file not found"
    
    try:
        with open('/var/log/hotswap-webui.log', 'r') as f:
            webui_logs = f.read()
    except FileNotFoundError:
        webui_logs = "Log file not found"
    
    logs_template = '''
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Logs - {{ hostname }}</title>
    <style>
        /* ===== MODERN DARK THEME DESIGN ===== */
        :root[data-theme="dark"] {
            --bg-primary: #0f1419;
            --bg-secondary: #1a1f2e;
            --bg-tertiary: #252d3d;
            --bg-hover: #2d3548;
            --text-primary: #e4e7eb;
            --text-secondary: #9ca3af;
            --text-tertiary: #6b7280;
            --accent-primary: #3b82f6;
            --accent-primary-hover: #2563eb;
            --accent-success: #10b981;
            --border-color: #2d3548;
            --shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }

        .app-container {
            display: flex;
            min-height: 100vh;
        }

        /* Sidebar */
        .sidebar {
            width: 260px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            position: fixed;
            height: 100vh;
            overflow-y: auto;
        }

        .sidebar-brand {
            padding: 24px 20px;
            border-bottom: 1px solid var(--border-color);
        }

        .brand-logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-logo img {
            height: 56px;
            width: auto;
        }

        .brand-text h1 {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 2px;
        }

        .subtitle {
            font-size: 12px;
            color: var(--text-secondary);
        }

        .nav-menu {
            padding: 16px 0;
        }

        .nav-item {
            display: flex;
            align-items: center;
            padding: 12px 20px;
            color: var(--text-secondary);
            text-decoration: none;
            transition: all 0.2s;
            font-size: 14px;
            gap: 12px;
        }

        .nav-item:hover, .nav-item.active {
            background: var(--bg-hover);
            color: var(--text-primary);
        }

        .nav-item.active {
            border-left: 3px solid var(--accent-primary);
        }

        /* Main Content */
        .main-content {
            flex: 1;
            margin-left: 260px;
            padding: 32px;
        }

        .page-header {
            margin-bottom: 32px;
        }

        .page-header h1 {
            font-size: 28px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 8px;
        }

        .page-header p {
            font-size: 14px;
            color: var(--text-secondary);
        }

        /* Cards */
        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: var(--shadow);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-color);
        }

        .card-header h2 {
            font-size: 18px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .log-container {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            max-height: 500px;
            overflow-y: auto;
        }

        .log-container pre {
            color: var(--text-primary);
            font-family: 'Courier New', 'Consolas', monospace;
            font-size: 13px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            border: none;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-primary {
            background: var(--accent-primary);
            color: white;
        }

        .btn-primary:hover {
            background: var(--accent-primary-hover);
        }

        /* User menu */
        .user-menu {
            padding: 16px 20px;
            border-top: 1px solid var(--border-color);
            position: absolute;
            bottom: 0;
            width: 260px;
            background: var(--bg-secondary);
        }

        .user-info {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
        }

        .user-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: var(--accent-primary);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 14px;
        }

        .user-details {
            flex: 1;
        }

        .user-name {
            font-size: 14px;
            font-weight: 500;
            color: var(--text-primary);
        }

        .user-role {
            font-size: 12px;
            color: var(--text-secondary);
        }

        .btn-logout {
            width: 100%;
            padding: 8px 12px;
            background: var(--bg-hover);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-logout:hover {
            background: var(--bg-tertiary);
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Sidebar Navigation -->
        <aside class="sidebar">
            <div class="sidebar-brand">
                <div class="brand-logo">
                    <img src="/static/logo" alt="Ranger">
                    <div class="brand-text">
                        <h1>ProxMox Ranger</h1>
                        <div class="subtitle">Hot-Swap Manager</div>
                    </div>
                </div>
            </div>

            <nav class="nav-menu">
                <a href="/shares" class="nav-item">
                    <span>▪</span> Shares
                </a>
                <a href="/logs" class="nav-item active">
                    <span>▪</span> System Logs
                </a>
            </nav>

            <div class="user-menu">
                <div class="user-info">
                    <div class="user-avatar">{{ username[0].upper() if username else 'U' }}</div>
                    <div class="user-details">
                        <div class="user-name">{{ username or 'User' }}</div>
                        <div class="user-role">Administrator</div>
                    </div>
                </div>
                <a href="/logout" class="btn-logout">Sign Out</a>
            </div>
        </aside>

        <!-- Main Content -->
        <main class="main-content">
            <div class="page-header">
                <h1>System Logs</h1>
                <p>View application and manager logs - {{ hostname }}</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <h2>Manager Script Logs</h2>
                </div>
                <div class="log-container">
                    <pre>{{ manager_logs }}</pre>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <h2>Web UI Logs</h2>
                </div>
                <div class="log-container">
                    <pre>{{ webui_logs }}</pre>
                </div>
            </div>
        </main>
    </div>

    <script>
    // Mount/Unmount operation feedback
    document.addEventListener('DOMContentLoaded', function() {
        // Handle all mount forms
        const mountForms = document.querySelectorAll('.mount-form, .unmount-form');

        mountForms.forEach(form => {
            form.addEventListener('submit', function(e) {
                const button = this.querySelector('button');
                const deviceName = this.dataset.device;
                const isMounting = this.classList.contains('mount-form');

                // Add loading class to button
                button.classList.add('btn-loading');
                button.disabled = true;

                // Find the device row and highlight it
                const rows = document.querySelectorAll('tbody tr');
                rows.forEach(row => {
                    const deviceCell = row.querySelector('td:first-child span');
                    if (deviceCell && deviceCell.textContent.trim() === deviceName) {
                        row.classList.add('device-row-loading');
                        if (isMounting) {
                            row.setAttribute('data-status', 'Mounting device...');
                        } else {
                            row.setAttribute('data-status', 'Unmounting device...');
                        }
                    }
                });

                // Disable all other mount buttons to prevent concurrent operations
                document.querySelectorAll('.mount-btn, .unmount-btn').forEach(btn => {
                    if (btn !== button) {
                        btn.disabled = true;
                        btn.style.opacity = '0.5';
                    }
                });

                // Show a toast notification
                showToast(isMounting ? 'Mounting device...' : 'Unmounting device...', 'info');
            });
        });

        // Toast notification system
        function showToast(message, type = 'info') {
            // Remove existing toast
            const existing = document.querySelector('.toast-notification');
            if (existing) existing.remove();

            const toast = document.createElement('div');
            toast.className = `toast-notification toast-${type}`;
            toast.innerHTML = `
                <div class="toast-content">
                    ${type === 'info' ? '<span class="spinner"></span>' : ''}
                    <span>${message}</span>
                </div>
            `;

            document.body.appendChild(toast);

            // Auto-remove after operation completes (page will reload)
            setTimeout(() => toast.remove(), 30000);
        }
    });
    </script>
</body>
</html>
'''
    
    success, hostname = run_cmd("hostname")
    hostname = hostname if success else "Unknown"
    
    return render_template_string(logs_template, 
                                manager_logs=manager_logs,
                                webui_logs=webui_logs,
                                hostname=hostname,
                                username=session.get('username', 'User'))

if __name__ == '__main__':
    # Ensure Samba is configured properly for username authentication
    logging.info("Starting Hot-Swap Web UI")
    ensure_samba_config()
    logging.info("Starting Flask application on port 8010")
    app.run(host='0.0.0.0', port=8010, debug=False)
