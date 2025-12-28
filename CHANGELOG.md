# Changelog

All notable changes to ProxMoxRanger will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2025-12-28

### Added - Web Services Discovery Feature

#### Core Functionality
- **Automatic Web Services Discovery**: Port scanning to detect running web services on nodes, VMs, and LXC containers
- **Full Port Range Scanning**: Optional scan of all 65,535 ports for comprehensive service discovery
- **Proxmox API Integration**: Distinguishes between services running on nodes vs. VMs vs. LXC containers
- **Service Identification**: Automatically identifies common services (Proxmox Web UI, Portainer, Grafana, Netdata, Home Assistant, Cockpit, etc.)
- **Clickable Service Links**: One-click access to discovered services in new browser tabs

#### Progress Tracking & Persistence (Major Feature)
- **Live Terminal Display**: Real-time progress updates during port scanning
- **Persistent Progress**: Scans continue in background and survive browser refreshes
- **Progress Saved to Disk**: All scan progress stored in `/tmp/proxmox-ranger-scan-progress.json`
- **Auto-Resume on Page Load**: Automatically detects and resumes displaying ongoing scans
- **ETA Calculation**: Dynamic estimation of time remaining based on current scan rate
- **Detailed Statistics**:
  - Ports scanned / Total ports (percentage)
  - Number of open ports found
  - Elapsed time
  - Estimated time remaining
  - Current host being scanned

#### User Interface Enhancements
- **Web Services Discovery Card**: New dashboard card displaying all discovered services
- **Live Progress Terminal**: Terminal-style display with auto-scrolling and green text on black background
- **Full Port Scan Checkbox**: Toggle between quick scan (14 ports) and full scan (65,535 ports)
- **Rearranged Controls**: Refresh button and Full Port Scan checkbox positioned on left side
- **Progress Persistence**: Terminal state survives page refreshes and browser restarts
- **Auto-Poll Updates**: Progress updates every 500ms during active scans
- **Hide/Show Terminal**: Manual toggle button to collapse/expand progress display

#### API Endpoints
- `GET /api/webservices` - Retrieve discovered web services
- `POST /api/webservices/scan` - Trigger immediate scan (quick or full)
- `GET /api/webservices/progress` - Get real-time scan progress with statistics

#### Configuration & Integration
- **Common Web Ports**: Default scanning of ports 80, 443, 8006, 8008, 8010, 8080, 8443, 3000, 5000, 5001, 9090, 8123, 3001, 19999
- **Proxmox API Token Support**: Secure API token authentication for VM/LXC detection
- **Background Scanning**: Automatic scans every 15 minutes
- **Docker IP Filtering**: Automatically skips Docker bridge IPs (172.17.x, 172.18.x, 172.19.x)
- **Local Node Only**: Scans only VMs/LXCs on the local node to avoid network timeouts

### Changed
- **Web Services Scanning**: Progress reporting every 100 ports for full scans (vs. every port for quick scans)
- **Terminal Message Limit**: Increased from 50 to 100 messages for better full-scan visibility
- **Scan Completion Behavior**: Terminal stays visible for full scans, auto-hides after 10s for quick scans

### Documentation
- **WEB_SERVICES_SETUP.md**: Comprehensive setup guide with:
  - Step-by-step Proxmox API token creation instructions
  - Detailed configuration examples
  - Full port scan usage guide
  - Troubleshooting section
  - Performance estimates
- **README.md**: Updated with Web Services Discovery feature description
- **CHANGELOG.md**: Created to track all version changes

### Performance Notes
- **Quick Scan**: 10-15 seconds for 14 common ports
- **Full Scan**: 8-12 hours per host for all 65,535 ports
- **Resource Usage**: Minimal CPU during scans, ~100KB memory for progress cache
- **Network Impact**: ~1KB per port probe, ~5KB per HTTP service identification

### Technical Details
- Added `proxmoxer>=2.0.0` dependency for Proxmox API integration
- Added `requests>=2.28.0` dependency for HTTP service probing
- Implemented thread-safe progress caching with file persistence
- Added JSON-based progress storage for cross-restart persistence
- Implemented dynamic ETA calculation based on scan rate

---

## [1.2.0] - Previous Release

### Features
- Hot-swap storage management
- SMB/CIFS network share creation
- User & permissions management
- Real-time device monitoring
- Secure login with PAM authentication
- IP whitelist protection
- Modern dark-themed UI
- Mobile-responsive design
- ZFS storage support
- System log viewer

---

## Migration Notes

### Upgrading from v1.2 to v1.3

1. **Update Dependencies:**
   ```bash
   cd /opt/proxmox-ranger
   pip3 install -r requirements.txt
   ```

2. **Configure Proxmox API (Optional but Recommended):**
   - Create an API token in Proxmox Web UI
   - Update `PROXMOX_TOKEN_NAME` and `PROXMOX_TOKEN_VALUE` in `pmranger.py`
   - See WEB_SERVICES_SETUP.md for detailed instructions

3. **Restart Service:**
   ```bash
   sudo systemctl restart proxmox-ranger
   ```

4. **Verify Installation:**
   - Navigate to `http://your-node-ip:8010/shares`
   - Scroll to "Web Services Discovery" card
   - Click Refresh to test scanning

### Breaking Changes
- None. All existing functionality remains unchanged.

### New Files
- `/tmp/proxmox-ranger-scan-progress.json` - Progress persistence file (auto-created)

---

## Support

For issues, feature requests, or questions:
- GitHub Issues: https://github.com/peterjohannmedina/ProxMoxRanger/issues
- Documentation: See WEB_SERVICES_SETUP.md for detailed setup instructions
