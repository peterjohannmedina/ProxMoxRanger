# ProxMoxRanger v1.3.0 - Release Notes

## 🎉 Successfully Released and Pushed to GitHub

**Release Date**: December 28, 2025
**Repository**: https://github.com/peterjohannmedina/ProxMoxRanger
**Tag**: v1.3.0
**Commit**: 005870e

---

## 📦 What's New in v1.3.0

### Major Feature: Web Services Discovery with Persistent Full Port Scanning

ProxMoxRanger v1.3 introduces a powerful new web services discovery system that automatically scans your Proxmox infrastructure to detect and catalog all running web services across nodes, VMs, and LXC containers.

### Key Features

#### 🔍 Automatic Service Discovery
- **Port Scanning**: Detects services on 14 common web ports by default
- **Full Port Range**: Optional comprehensive scan of all 65,535 ports
- **Service Identification**: Automatically recognizes popular services:
  - Proxmox VE Web UI
  - ProxMenux Monitor
  - Portainer
  - Grafana
  - Netdata
  - Home Assistant
  - Cockpit
  - Nginx/Apache web servers
  - And more...

#### 🎯 Source Attribution
- **Proxmox API Integration**: Distinguishes between:
  - Services running directly on the node
  - Services running in virtual machines
  - Services running in LXC containers
- **Automatic IP Matching**: Maps service IPs to their host VM/LXC names

#### 📊 Live Progress Terminal
- **Real-time Updates**: Progress displayed every 500ms
- **Comprehensive Statistics**:
  - Current port being scanned
  - Ports scanned / Total ports (percentage)
  - Number of open ports found
  - Elapsed time
  - **Dynamic ETA calculation** based on scan rate
  - Current host being scanned
- **Terminal-style Display**: Green text on black background with timestamps

#### 💾 Persistent Progress
- **Survives Browser Refreshes**: Close your browser and come back anytime
- **Disk-based Storage**: Progress saved to `/tmp/proxmox-ranger-scan-progress.json`
- **Auto-Resume**: Page reload automatically resumes displaying ongoing scans
- **Background Execution**: Scans continue running on the server regardless of browser state
- **No Data Loss**: All progress, statistics, and discovered services preserved

#### ⚡ Performance
- **Quick Scan**: 10-15 seconds for common ports
- **Full Scan**: 8-12 hours per host (all 65,535 ports)
- **Resource Efficient**: Minimal CPU/memory usage
- **Non-blocking**: Runs in background thread without affecting other operations

---

## 📝 Documentation Updates

### New Documentation Files

1. **WEB_SERVICES_SETUP.md** - Comprehensive setup guide including:
   - Detailed Proxmox API token creation instructions with screenshots
   - Step-by-step configuration guide
   - Full port scan usage instructions
   - Troubleshooting section
   - Performance benchmarks

2. **CHANGELOG.md** - Complete version history and migration notes

3. **VERSION_1.3_RELEASE_NOTES.md** - This file

### Updated Documentation

- **README.md**: Added Web Services Discovery feature description
- **requirements.txt**: Updated with new dependencies (proxmoxer, requests)

---

## 🔧 Technical Details

### New Dependencies
```
proxmoxer>=2.0.0  # Proxmox API client library
requests>=2.28.0   # HTTP client for service probing
```

### New API Endpoints
- `GET /api/webservices` - Retrieve discovered services
- `POST /api/webservices/scan` - Trigger immediate scan (quick or full)
- `GET /api/webservices/progress` - Get real-time scan progress

### Configuration Variables (in pmranger.py)
```python
# Web Services Discovery
WEB_SERVICES_ENABLED = True
WEB_SERVICES_SCAN_INTERVAL = 900  # 15 minutes
WEB_PORTS = [80, 443, 8006, 8008, 8010, 8080, 8443, 3000, 5000, 5001, 9090, 8123, 3001, 19999]

# Proxmox API Configuration
PROXMOX_API_ENABLED = True
PROXMOX_HOST = 'localhost'
PROXMOX_USER = 'root@pam'
PROXMOX_TOKEN_NAME = 'ranger-scanner'
PROXMOX_TOKEN_VALUE = 'your-token-here'
```

### Progress Persistence File
- **Location**: `/tmp/proxmox-ranger-scan-progress.json`
- **Format**: JSON with scan state, progress messages, statistics
- **Auto-created**: Generated on first scan
- **Auto-loaded**: Restored on service restart

---

## 🚀 How to Get an API Token from Proxmox

### Step-by-Step Instructions

1. **Access Proxmox Web UI**
   - Navigate to `https://your-proxmox-ip:8006`
   - Log in as root

2. **Navigate to API Tokens**
   - Click **Datacenter** (top of left sidebar)
   - Click **Permissions**
   - Select **API Tokens**

3. **Create New Token**
   - Click **Add** button
   - **User**: `root@pam`
   - **Token ID**: `ranger-scanner`
   - **Privilege Separation**: **UNCHECK** (very important!)
   - Click **Add**

4. **Copy Token Value**
   - A dialog appears with your token
   - **CRITICAL**: Copy the entire UUID immediately
   - Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
   - **This is shown only once** - save it securely!

5. **Configure ProxMoxRanger**
   ```bash
   nano /opt/proxmox-ranger/bin/pmranger.py
   ```

   Update these lines (around line 70-75):
   ```python
   PROXMOX_TOKEN_NAME = 'ranger-scanner'
   PROXMOX_TOKEN_VALUE = 'paste-your-token-here'
   ```

6. **Restart Service**
   ```bash
   sudo systemctl restart proxmox-ranger
   ```

7. **Verify**
   ```bash
   tail -f /var/log/hotswap-webui.log | grep "Proxmox API"
   ```

   You should see:
   ```
   Querying Proxmox API for VMs/LXCs...
   Found X VMs/LXCs to scan
   ```

---

## 📥 Installation & Upgrade

### Fresh Installation
```bash
curl -fsSL https://raw.githubusercontent.com/peterjohannmedina/ProxMoxRanger/main/install.sh | bash
```

### Upgrade from v1.2 to v1.3
```bash
cd /opt/proxmox-ranger
git pull origin main
pip3 install -r requirements.txt
sudo systemctl restart proxmox-ranger
```

---

## 🎯 Usage Guide

### Quick Scan (Common Ports)
1. Navigate to `http://your-node-ip:8010/shares`
2. Scroll to "Web Services Discovery" card
3. Click **🔄 Refresh** button
4. Wait 10-15 seconds for results

### Full Port Scan (All 65,535 Ports)
1. Check the **"Full Port Scan (1-65535)"** checkbox
2. Click **🔄 Refresh** button
3. Live terminal appears with progress
4. **You can close your browser** - scan continues on server
5. Refresh page anytime to see current progress
6. Scan completes in 8-12 hours per host

### Viewing Progress
- Terminal shows:
  - Progress percentage
  - Ports scanned
  - Open ports found
  - Elapsed time
  - Estimated time remaining
  - Current host
- Updates every 500ms
- Auto-scrolls to latest messages

---

## 🐛 Troubleshooting

### Services Not Showing
- Check that ports are in the scan list
- Verify firewall allows connections from ProxMoxRanger host
- Enable full port scan if using non-standard ports

### VM/LXC Source Shows as "Node"
- Proxmox API not configured
- Create API token (see instructions above)
- Verify token in pmranger.py configuration
- Check logs for API errors

### Scan Stuck or Slow
- Full scans take 8-12 hours - this is normal
- Check progress in terminal for ETA
- Verify scan is actually running (check logs)

---

## 📊 Performance Benchmarks

### Quick Scan (14 Ports)
- **Duration**: 10-15 seconds
- **Ports Scanned**: 14
- **Resource Usage**: Negligible
- **Use Case**: Regular monitoring

### Full Scan (65,535 Ports)
- **Duration**: 8-12 hours per host
- **Timeout per Port**: 0.5 seconds
- **Total Time**: ~32,767 seconds + HTTP probing
- **Resource Usage**: Minimal (background thread)
- **Use Case**: Comprehensive discovery

---

## 🔐 Security Considerations

- API tokens stored in source code (only readable by root)
- IP whitelist protection applies to all API endpoints
- SSL verification disabled for self-signed certs (internal network only)
- Docker bridge IPs automatically filtered
- Only scans your own infrastructure (no external scanning)

---

## 🎁 Credits

Built with Claude Code (Anthropic)
https://claude.com/claude-code

Co-Authored-By: Claude Sonnet 4.5

---

## 📞 Support

- **GitHub Repository**: https://github.com/peterjohannmedina/ProxMoxRanger
- **Issues**: https://github.com/peterjohannmedina/ProxMoxRanger/issues
- **Documentation**: See WEB_SERVICES_SETUP.md

---

## ✅ Git Release Status

### Successfully Pushed to GitHub
- ✅ Committed to main branch
- ✅ Tagged as v1.3.0
- ✅ Pushed to remote repository
- ✅ All documentation updated
- ✅ CHANGELOG.md created

### Repository Information
- **Remote**: https://github.com/peterjohannmedina/ProxMoxRanger.git
- **Branch**: main
- **Commit Hash**: 005870e
- **Tag**: v1.3.0
- **Files Changed**: 6
- **Lines Added**: 1,856+

---

## 🎉 What's Next?

Version 1.3.0 is now live on GitHub! Users can:
1. Clone the repository to get the latest version
2. Use the one-command installation script
3. Upgrade existing installations with `git pull`
4. Browse the code and documentation at https://github.com/peterjohannmedina/ProxMoxRanger

**Thank you for using ProxMoxRanger! 🚀**
