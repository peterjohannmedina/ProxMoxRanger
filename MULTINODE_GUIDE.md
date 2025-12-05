# ProxMox Ranger v1.2 - Multi-Node Guide

**Version:** 1.2.0
**Release Date:** December 2025
**Multi-Node Support:** ✅ Enabled

---

## 🎯 What's New in v1.2

ProxMox Ranger v1.2 introduces **multi-node support** allowing you to manage hot-swap storage across multiple Proxmox nodes from a single unified interface.

### Key Features

1. **Node Selector Dropdown** - Switch between nodes directly from the sidebar
2. **Auto-Discovery** - Automatically scan your network for other ProxMox Ranger instances
3. **REST API** - All operations exposed via HTTP API for inter-node communication
4. **Unified Interface** - Manage all nodes without switching between multiple URLs
5. **No SSH Required** - Simple HTTP-based communication (no key management!)

---

## 🏗️ Architecture Overview

### How It Works

```
┌─────────────────────────────────────────────────────┐
│  ProxMox Ranger Node 1 (192.168.1.233:8010)        │
│  ├─ Web UI with Node Selector                      │
│  ├─ REST API Endpoints                             │
│  ├─ Auto-Discovery Worker (scans network)          │
│  └─ Local Device Management                        │
└─────────────────────────────────────────────────────┘
                    ↕ HTTP API
┌─────────────────────────────────────────────────────┐
│  ProxMox Ranger Node 2 (192.168.1.234:8010)        │
│  ├─ Web UI with Node Selector                      │
│  ├─ REST API Endpoints                             │
│  ├─ Auto-Discovery Worker                          │
│  └─ Local Device Management                        │
└─────────────────────────────────────────────────────┘
                    ↕ HTTP API
┌─────────────────────────────────────────────────────┐
│  ProxMox Ranger Node 3 (192.168.1.235:8010)        │
│  ├─ Web UI with Node Selector                      │
│  ├─ REST API Endpoints                             │
│  ├─ Auto-Discovery Worker                          │
│  └─ Local Device Management                        │
└─────────────────────────────────────────────────────┘
```

**Important:** Each node must have ProxMox Ranger installed because mount operations require local execution. You cannot remotely mount `/dev/sdb` from another machine!

---

## 📦 Installation

### Installation is Identical on All Nodes

```bash
# On Node 1
curl -sSL https://raw.githubusercontent.com/peterjohannmedina/ProxMoxRanger/main/install.sh | bash

# On Node 2
curl -sSL https://raw.githubusercontent.com/peterjohannmedina/ProxMoxRanger/main/install.sh | bash

# On Node 3
curl -sSL https://raw.githubusercontent.com/peterjohannmedina/ProxMoxRanger/main/install.sh | bash
```

**That's it!** No master/agent distinction. Each node is equal.

### What Gets Installed

On each node:
- **Binary:** `/opt/proxmox-ranger/bin/pmranger` (renamed from webui)
- **Service:** `proxmox-ranger.service` (systemd)
- **Port:** 8010 (configurable)
- **Logs:** `/var/log/hotswap-webui.log`
- **Assets:** `/opt/proxmox-ranger/assets/`

---

## 🔍 Auto-Discovery

### How Auto-Discovery Works

1. **Background Scanner:** Each node runs a discovery worker every 5 minutes
2. **Network Scan:** Scans local /24 network for open port 8010
3. **API Check:** Calls `/api/info` to verify it's ProxMox Ranger
4. **Auto-Register:** Adds discovered nodes to the dropdown

### Configuration

Edit `pmranger.py` to customize:

```python
# Node discovery settings
NODE_DISCOVERY_ENABLED = True
NODE_DISCOVERY_INTERVAL = 300  # 5 minutes (in seconds)
```

### Manual Discovery

Click the **🔍 Scan** button in the sidebar to trigger immediate discovery.

---

## 🎛️ Using the Node Selector

### Location

The node selector is located in the sidebar, directly under the ProxMox Ranger branding:

```
┌─────────────────────┐
│  🤠 ProxMox Ranger  │
│  Hot-Swap Manager   │
│  v1.2               │
├─────────────────────┤
│  🖥️ Select Node    │
│  [Dropdown ▼]       │
│  [🔍 Scan]          │
├─────────────────────┤
│  ◆ Devices & Shares │
│  ● User Management  │
│  ▪ System Logs      │
└─────────────────────┘
```

### Dropdown Options

- **Local Node:** `pver430 (Local)` - The current node
- **Auto-Discovered:** `pver431 (192.168.1.234) 🔍` - Found via scan
- **Offline Nodes:** `pver432 (192.168.1.235) [OFFLINE]` - Grayed out

### Switching Nodes

1. Select a node from the dropdown
2. Page automatically redirects to that node's UI
3. All operations now affect the selected node

**Example:**
- Select "pver431" → Redirects to `http://192.168.1.234:8010/shares`
- You're now managing Node 2's storage
- Node selector on Node 2 will show Node 2 as "Local"

---

## 📡 REST API Reference

### Public Endpoints (No Auth)

#### GET `/api/info`
Returns basic node information for discovery.

```bash
curl http://192.168.1.233:8010/api/info
```

Response:
```json
{
  "app": "ProxMoxRanger",
  "version": "1.2.0",
  "hostname": "pver430",
  "ip": "192.168.1.233",
  "port": 8010
}
```

### Protected Endpoints (IP Whitelist)

#### GET `/api/devices`
Get all block devices on the node.

```bash
curl http://192.168.1.233:8010/api/devices
```

Response:
```json
{
  "success": true,
  "devices": [
    {
      "name": "/dev/sda2",
      "size": "1G",
      "fstype": "VFAT",
      "label": "",
      "mountpoint": null
    }
  ]
}
```

#### GET `/api/mounts`
Get all mounted devices.

#### GET `/api/shares`
Get all SMB shares.

#### POST `/api/mount`
Mount a device.

```bash
curl -X POST http://192.168.1.233:8010/api/mount \
  -H "Content-Type: application/json" \
  -d '{"device": "/dev/sdb1"}'
```

Response:
```json
{
  "success": true,
  "message": "Device mounted successfully"
}
```

#### POST `/api/unmount`
Unmount a device.

#### GET `/api/nodes`
Get all registered nodes.

```bash
curl http://192.168.1.233:8010/api/nodes
```

Response:
```json
{
  "success": true,
  "nodes": [
    {
      "hostname": "pver430",
      "ip": "192.168.1.233",
      "port": 8010,
      "status": "online",
      "is_local": true
    },
    {
      "hostname": "pver431",
      "ip": "192.168.1.234",
      "port": 8010,
      "status": "online",
      "is_local": false,
      "auto_discovered": true
    }
  ]
}
```

#### POST `/api/nodes/register`
Manually register a node.

```bash
curl -X POST http://192.168.1.233:8010/api/nodes/register \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "pver432",
    "ip": "192.168.1.235",
    "port": 8010
  }'
```

#### POST `/api/nodes/unregister`
Remove a node from the registry.

#### POST `/api/nodes/discover`
Trigger immediate network scan.

```bash
curl -X POST http://192.168.1.233:8010/api/nodes/discover \
  -H "Content-Type: application/json"
```

---

## 🔒 Security

### IP Whitelisting

By default, API endpoints are restricted to:
- `127.0.0.1` - Localhost
- `192.168.0.0/16` - Private network
- `10.0.0.0/8` - Private network
- `172.16.0.0/12` - Private network

### Modify Whitelist

Edit `pmranger.py`:

```python
ALLOWED_IPS = [
    '127.0.0.1',
    '::1',
    '192.168.0.0/16',
    '10.0.0.0/8',
    '172.16.0.0/12',
]
```

### No Authentication on API?

The `/api/info` endpoint is public for discovery. All other endpoints require:
1. IP whitelisting (enforced)
2. Same authentication as Web UI (session-based)

---

## 🐛 Troubleshooting

### Node Not Appearing in Dropdown

**Check 1:** Is the node online?
```bash
curl http://192.168.1.234:8010/api/info
```

**Check 2:** Is port 8010 open?
```bash
ss -tlnp | grep :8010
```

**Check 3:** Is discovery running?
```bash
tail -f /var/log/hotswap-webui.log | grep discovery
```

**Check 4:** Manually trigger discovery
- Click **🔍 Scan** button
- Or via API: `curl -X POST http://localhost:8010/api/nodes/discover`

### Node Shows as OFFLINE

The node was discovered but is no longer reachable.

**Solution:**
1. Check if node is actually offline
2. Check network connectivity
3. Restart proxmox-ranger service:
   ```bash
   systemctl restart proxmox-ranger
   ```

### Discovery Not Finding Nodes

**Check 1:** Are nodes on same /24 network?
- Discovery scans `192.168.1.0/24` by default
- All nodes must be in same subnet

**Check 2:** Is discovery enabled?
```python
NODE_DISCOVERY_ENABLED = True  # In pmranger.py
```

**Check 3:** Firewall blocking port 8010?
```bash
# Allow port 8010
iptables -A INPUT -p tcp --dport 8010 -j ACCEPT
```

### "Cannot switch to node" Error

The selected node might be offline or inaccessible.

**Solution:**
1. Verify node is online
2. Check network connectivity
3. Manually browse to node: `http://NODE_IP:8010/shares`

---

## 🆚 Version Comparison

| Feature | v1.0 | v1.2 |
|---------|------|------|
| Single-node management | ✅ | ✅ |
| Node selector dropdown | ❌ | ✅ |
| Auto-discovery | ❌ | ✅ |
| REST API | ❌ | ✅ |
| Multi-node switching | ❌ | ✅ |
| SSH required | N/A | ❌ |
| Installation per node | ✅ | ✅ |
| Version display | ❌ | ✅ (v1.2) |

---

## 🔧 Configuration Options

### Disable Auto-Discovery

If you don't want automatic network scanning:

```python
# In pmranger.py
NODE_DISCOVERY_ENABLED = False
```

### Change Discovery Interval

```python
# Scan every 10 minutes instead of 5
NODE_DISCOVERY_INTERVAL = 600  # seconds
```

### Change Default Port

```python
# At the end of pmranger.py
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8010, debug=False)
    #                             ^^^^ Change this
```

Then restart the service:
```bash
systemctl restart proxmox-ranger
```

---

## 📚 Additional Resources

- **GitHub Repository:** https://github.com/peterjohannmedina/ProxMoxRanger
- **Installation Guide:** [INSTALL.md](INSTALL.md)
- **Troubleshooting:** [diagnostics/README.md](diagnostics/README.md)
- **Tools:** [tools/README.md](tools/README.md)

---

## 🚀 Quick Start Example

### Scenario: 3 Proxmox Nodes

You have 3 Proxmox nodes and want to manage them all from one interface.

**Step 1:** Install on all nodes
```bash
# Run on each node
curl -sSL https://raw.githubusercontent.com/peterjohannmedina/ProxMoxRanger/main/install.sh | bash
```

**Step 2:** Access any node's UI
```
http://192.168.1.233:8010/shares
```

**Step 3:** Click **🔍 Scan** to discover other nodes
- Wait 3-5 seconds for scan to complete
- Node dropdown will populate with discovered nodes

**Step 4:** Switch between nodes
- Select "pver431" from dropdown
- UI reloads showing Node 2's storage
- Mount/unmount operations now affect Node 2

**That's it!** No additional configuration needed.

---

## 💡 Pro Tips

1. **Bookmark Each Node** - While you can switch via dropdown, bookmarking each node's direct URL is faster
2. **Use Scan Sparingly** - Auto-discovery runs every 5 minutes; manual scans are usually unnecessary
3. **Check Logs** - Discovery events are logged: `tail -f /var/log/hotswap-webui.log`
4. **API for Automation** - Use the REST API for scripting and automation tasks
5. **Consistent Naming** - Give your nodes clear hostnames so they're easy to identify in the dropdown

---

## 🎉 Summary

ProxMox Ranger v1.2 makes multi-node storage management simple:

✅ **Same installation on every node**
✅ **No SSH key management**
✅ **Automatic node discovery**
✅ **REST API for everything**
✅ **Switch nodes with one click**

Enjoy managing your Proxmox cluster's storage!

---

**Questions or Issues?**
Open an issue on GitHub: https://github.com/peterjohannmedina/ProxMoxRanger/issues
