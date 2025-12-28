# Web Services Discovery - Setup Guide

## Overview

The Web Services Discovery feature automatically scans your Proxmox nodes to detect running web services and displays them on the ProxMoxRanger dashboard with clickable links. It can distinguish between services running on the node itself versus those running in VMs or LXC containers.

## Features

### Core Scanning
- **Automatic Port Scanning**: Scans common web ports (80, 443, 8006, 8008, 8010, 8080, 8443, 3000, 5000, 5001, 9090, 8123, 3001, 19999)
- **Full Port Range Scanning**: Optional scan of all 65,535 ports with persistent progress tracking
- **Service Identification**: Automatically identifies common services (Proxmox Web UI, Portainer, Grafana, Netdata, etc.)
- **VM/LXC Detection**: Shows whether services are running on the node, in a VM, or in an LXC container

### Progress Tracking *(New in v1.3)*
- **Live Terminal Display**: Real-time progress updates during scanning
- **Persistent Progress**: Scans continue in background and survive browser refreshes
- **ETA Calculation**: Shows estimated time remaining for full port scans
- **Detailed Statistics**: Ports scanned, open ports found, elapsed time, percentage complete

### User Interface
- **Automatic Scanning**: Runs every 15 minutes in the background
- **Manual Refresh**: Click the Refresh button to trigger an immediate scan
- **Full Port Scan Checkbox**: Enable to scan all 65,535 ports (takes 8-12 hours per host)
- **Clickable Links**: Open any discovered service in a new browser tab
- **Auto-Resume**: On page reload, automatically resumes displaying ongoing scan progress

## Installation Steps

### 1. Install Dependencies

```bash
cd /opt/proxmox-ranger
pip3 install -r requirements.txt
```

This will install:
- `proxmoxer>=2.0.0` - Proxmox API client library
- `requests>=2.28.0` - HTTP client library

### 2. Configure Proxmox API Access

To enable VM/LXC detection, you need to configure Proxmox API credentials.

#### Option A: API Token (Recommended - More Secure)

##### Step 1: Create an API Token in Proxmox Web UI

1. **Log into your Proxmox Web Interface**
   - Open your browser and navigate to `https://your-proxmox-ip:8006`
   - Log in with your root credentials

2. **Navigate to API Tokens**
   - In the left sidebar, click on **Datacenter** (at the very top of the tree)
   - Click on **Permissions** in the Datacenter menu
   - Select **API Tokens** from the submenu

3. **Create a New Token**
   - Click the **Add** button at the top of the API Tokens panel
   - A dialog will appear with the following fields:

   **Configuration:**
   - **User**: Select `root@pam` from the dropdown
   - **Token ID**: Enter `ranger-scanner` (or choose your own name)
   - **Privilege Separation**: **UNCHECK this box**
     - ⚠️ **Important**: Unchecking this allows the token to inherit all permissions from root@pam
     - If checked, you'll need to manually assign permissions (not recommended for this use case)
   - **Expire**: Leave as "No" for tokens that don't expire, or set a date if you want them to expire
   - **Comment**: (Optional) Add "ProxMoxRanger Web Services Scanner" for documentation

4. **Save the Token**
   - Click **Add** to create the token
   - A confirmation dialog will appear showing your token value
   - **CRITICAL**: Copy the entire token value immediately
     - Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (UUID format)
     - This token will **NEVER be shown again** after you close this dialog
     - Store it in a secure location (password manager recommended)

5. **Verify Token Creation**
   - After closing the dialog, you should see your new token listed:
     - User: `root@pam`
     - Token ID: `ranger-scanner`
     - Privilege Separation: `No`
     - Status: `Enabled`

##### Step 2: Configure ProxMoxRanger

1. **Edit the configuration file:**

   ```bash
   nano /opt/proxmox-ranger/bin/pmranger.py
   ```

2. **Locate the Proxmox API Configuration section** (around lines 70-75):

   ```python
   # Proxmox API Configuration
   PROXMOX_API_ENABLED = True
   PROXMOX_HOST = 'localhost'
   PROXMOX_USER = 'root@pam'
   PROXMOX_TOKEN_NAME = 'ranger-scanner'  # Must match your Token ID
   PROXMOX_TOKEN_VALUE = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'  # Paste your token here
   ```

3. **Update the values:**
   - `PROXMOX_API_ENABLED`: Set to `True`
   - `PROXMOX_HOST`: Usually `'localhost'` (or your Proxmox IP if running remotely)
   - `PROXMOX_USER`: Keep as `'root@pam'`
   - `PROXMOX_TOKEN_NAME`: Match the Token ID you created (e.g., `'ranger-scanner'`)
   - `PROXMOX_TOKEN_VALUE`: Paste the full token value you copied (between the quotes)

4. **Save and exit:**
   - Press `Ctrl+X`, then `Y`, then `Enter` to save in nano

##### Step 3: Restart ProxMoxRanger Service

```bash
sudo systemctl restart proxmox-ranger
```

##### Step 4: Verify Configuration

Check the logs to ensure the API connection is working:

```bash
sudo tail -f /var/log/hotswap-webui.log | grep -i "proxmox api"
```

You should see messages like:
```
Querying Proxmox API for VMs/LXCs...
Found 6 VMs/LXCs to scan
```

If you see errors like "Proxmox API enabled but credentials not configured", double-check:
- Token name matches exactly (case-sensitive)
- Token value is complete and correct
- No extra spaces or quotes in the configuration

#### Option B: Username/Password (Less Secure)

If you prefer not to use API tokens, you can modify the `get_proxmox_vms_and_lxcs()` function in `pmranger.py`:

```python
# Replace the ProxmoxAPI initialization (around line 273) with:
proxmox = ProxmoxAPI(
    PROXMOX_HOST,
    user=PROXMOX_USER,
    password='your-root-password-here',
    verify_ssl=False
)
```

**Security Note**: Storing passwords in code is not recommended. Use API tokens instead.

### 3. Restart ProxMoxRanger Service

```bash
sudo systemctl restart proxmox-ranger
```

### 4. Verify Service is Running

```bash
sudo systemctl status proxmox-ranger
```

Check the logs:

```bash
sudo tail -f /var/log/hotswap-webui.log
```

You should see:
```
Web services discovery worker started
Starting web services discovery scan...
Web services discovery complete. Found X services.
```

## Using the Feature

### Accessing the Dashboard

1. Open your browser and navigate to: `http://YOUR-NODE-IP:8010/shares`
2. Scroll down to the **"Web Services Discovery"** card
3. The card will automatically load discovered services within 30 seconds (initial scan delay)

### Table Columns

- **Service Name**: Identified service (e.g., "Proxmox VE Web UI", "Portainer", "Nginx Web Server")
- **Host**: Hostname and IP address of the service
- **Port**: TCP port number the service is running on
- **Protocol**: HTTP or HTTPS
- **Source**: Where the service is running:
  - `Node` - Running directly on the Proxmox host
  - `VM (vm-name)` - Running inside a virtual machine
  - `LXC (container-name)` - Running inside an LXC container
- **Actions**: "Open ↗" button to launch the service in a new browser tab

### Scanning Options

#### Quick Scan (Common Ports)

1. Click the **🔄 Refresh** button to trigger an immediate scan
2. Scans 14 common web ports (80, 443, 8006, 8008, 8010, 8080, 8443, 3000, 5000, 5001, 9090, 8123, 3001, 19999)
3. Completes in **10-15 seconds**
4. Progress terminal shows real-time scanning status
5. Results automatically populate the table when complete

The button will show:
- ⏳ - Scanning in progress
- ✓ - Scan completed successfully
- 🔄 - Ready for next scan

#### Full Port Scan (1-65535) *(New in v1.3)*

**Important**: Full port scans take **8-12 hours per host**. Use this feature when you need comprehensive discovery of all services.

1. **Enable Full Scan:**
   - Check the **"Full Port Scan (1-65535)"** checkbox
   - Click the **🔄 Refresh** button

2. **Monitor Progress:**
   - A live terminal window appears showing:
     - **Progress**: Current port / Total ports (percentage)
     - **Found**: Number of open ports discovered
     - **Elapsed**: Time since scan started
     - **ETA**: Estimated time remaining (calculated dynamically)
     - **Current**: Host being scanned
   - Terminal updates every 500ms with latest scan status
   - Example progress display:
     ```
     Progress: 5,234 / 65,535 ports (7.99%)
     Found: 12 open ports
     Elapsed: 18m 45s
     ETA: 3h 15m remaining
     Current: 192.168.1.233
     ```

3. **Persistent Scanning:**
   - ✅ **You can close your browser** - the scan continues running on the server
   - ✅ **You can refresh the page** - progress automatically resumes displaying
   - ✅ **Survives network interruptions** - progress is saved to disk every update
   - ✅ **Runs in background** - doesn't block other ProxMoxRanger operations
   - Progress is stored in `/tmp/proxmox-ranger-scan-progress.json`

4. **Resuming Scans:**
   - Simply reload the page at any time
   - If a scan is running, the terminal automatically appears
   - All progress, statistics, and ETA are restored
   - No manual action needed

5. **Scan Completion:**
   - Services table automatically refreshes with all discovered services
   - Terminal remains visible for full scans (hidden after 10s for quick scans)
   - Click the "Hide" button in the terminal to manually collapse it

## Configuration Options

Edit `pmranger.py` to customize the feature:

### Enable/Disable Feature

```python
WEB_SERVICES_ENABLED = True  # Set to False to disable
```

### Change Scan Interval

```python
WEB_SERVICES_SCAN_INTERVAL = 900  # Seconds (900 = 15 minutes)
```

### Customize Scanned Ports

```python
WEB_PORTS = [80, 443, 8006, 8080, 8443, 3000, 5000, 5001, 9090, 8123, 3001, 19999]
# Add or remove ports as needed
```

### Disable Proxmox API Integration

If you only want network scanning without VM/LXC detection:

```python
PROXMOX_API_ENABLED = False
```

All services will show as `Source: Node` in this mode.

## Troubleshooting

### No Services Discovered

1. **Check if the feature is enabled:**
   ```bash
   grep "WEB_SERVICES_ENABLED" /opt/proxmox-ranger/bin/pmranger.py
   ```

2. **Verify background worker is running:**
   ```bash
   sudo tail -f /var/log/hotswap-webui.log | grep "web services"
   ```

3. **Manually trigger a scan** by clicking the Refresh button in the UI

4. **Check firewall rules** - ensure ports are accessible from the ProxMoxRanger host

### VM/LXC Source Shows as "Node"

This means Proxmox API integration is not working. Check:

1. **API credentials are configured** in `pmranger.py`

2. **API token has correct permissions:**
   - Navigate to: **Datacenter → Permissions → API Tokens**
   - Verify the token exists and "Privilege Separation" is unchecked

3. **Check logs for API errors:**
   ```bash
   sudo tail -f /var/log/hotswap-webui.log | grep "Proxmox API"
   ```

4. **Test Proxmox API manually:**
   ```bash
   python3 << EOF
   from proxmoxer import ProxmoxAPI
   proxmox = ProxmoxAPI(
       'localhost',
       user='root@pam',
       token_name='ranger-scanner',
       token_value='YOUR-TOKEN-HERE',
       verify_ssl=False
   )
   nodes = proxmox.nodes.get()
   print(f"Found {len(nodes)} nodes")
   EOF
   ```

### Service Names Show as "Unknown Web Service"

This happens when:
- The service doesn't respond to HTTP/HTTPS requests
- The service returns a non-standard response
- The HTTP connection times out

The service is still accessible via the "Open ↗" button - it just couldn't be identified automatically.

### HTTPS Certificate Errors

The scanner automatically accepts self-signed certificates. If you see SSL errors in logs, this is normal for internal services and won't prevent discovery.

## Security Considerations

- **IP Whitelist**: The web services API endpoints respect the existing IP whitelist configuration
- **No External Scanning**: Only scans registered Proxmox nodes (your own infrastructure)
- **Credentials**: API tokens are stored in the pmranger.py file, which should be readable only by root
- **Self-Signed Certs**: SSL verification is disabled for internal services (acceptable in private networks)

## Supported Services

The scanner automatically recognizes these services:

- **Proxmox VE Web UI** (port 8006)
- **Portainer** (Docker management)
- **Grafana** (monitoring dashboards)
- **Netdata** (port 19999, real-time monitoring)
- **Home Assistant** (port 8123)
- **Cockpit** (port 9090, system management)
- **Nginx/Apache** web servers
- Generic web services (displays HTML title)

## Performance Impact

- **CPU**: Minimal (only during 15-minute scan intervals)
- **Memory**: <10MB for cache (100 services)
- **Network**: ~5-10KB per scanned host
- **Scan Duration**: 3-8 seconds per node with 1-3 services

## Future Enhancements

Planned features for future versions:
- Service health monitoring with uptime tracking
- Custom port profiles per node
- Service groups and categories
- Alert system for service downtime
- Real-time WebSocket updates

## Support

For issues or questions:
- Check the main README.md
- Review logs: `/var/log/hotswap-webui.log`
- Check ProxMoxRanger documentation: `/opt/proxmox-ranger/README.md`
