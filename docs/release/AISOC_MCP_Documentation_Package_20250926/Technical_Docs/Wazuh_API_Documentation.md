# Wazuh API REST v4.12.0 - Dokumentasi Lengkap 📡

## Daftar Isi
- [Pengenalan](#pengenalan)
- [Authentication](#authentication)
- [Struktur Response](#struktur-response)
- [Error Handling](#error-handling)
- [Endpoints Utama](#endpoints-utama)
- [API Info](#api-info)
- [Active Response](#active-response)
- [Agents Management](#agents-management)
- [Cluster Management](#cluster-management)
- [Decoders](#decoders)
- [Events](#events)
- [Experimental](#experimental)
- [Groups](#groups)
- [Lists (CDB)](#lists-cdb)
- [Logtest](#logtest)
- [Manager](#manager)
- [MITRE](#mitre)
- [Overview](#overview)
- [Rootcheck](#rootcheck)
- [Rules](#rules)
- [SCA](#sca)
- [Security](#security)
- [Syscheck](#syscheck)
- [Syscollector](#syscollector)
- [Tasks](#tasks)
- [Examples & Best Practices](#examples--best-practices)

---

## Pengenalan

Wazuh API REST adalah API open-source yang memungkinkan interaksi dengan Wazuh manager dari web browser, command line tools seperti cURL atau script/program yang dapat melakukan web requests. 

### Key Features:
- 🔐 **JWT Authentication** - Secure token-based authentication
- 📊 **Complete Management** - Manage agents, rules, decoders, dan configurations
- 🚀 **RESTful Design** - Standard HTTP methods (GET, POST, PUT, DELETE)
- 📈 **Real-time Monitoring** - Access to logs, stats, dan system information
- 🔧 **Configuration Management** - Update configurations via API

### Base URL
```
https://<HOST_IP>:55000
```

### Supported Formats
- **Request**: JSON, XML (untuk beberapa endpoints)
- **Response**: JSON (default), Plain text (dengan parameter `raw=true`)

---

## Authentication

### Overview
Semua endpoint Wazuh API memerlukan authentication menggunakan JWT (JSON Web Token). Token memiliki durasi default 900 detik (15 menit).

### Basic Authentication
Gunakan username dan password untuk mendapatkan JWT token:

```bash
curl -u <USER>:<PASSWORD> -k -X POST "https://<HOST_IP>:55000/security/user/authenticate"
```

**Response:**
```json
{
    "data": {
        "token": "<YOUR_JWT_TOKEN>"
    },
    "error": 0
}
```

### Menggunakan JWT Token
Gunakan token untuk semua API calls:

```bash
curl -k -X <METHOD> "https://<HOST_IP>:55000/<ENDPOINT>" \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>"
```

### Mengatur Durasi Token
```bash
curl -k -X PUT "https://<HOST_IP>:55000/security/config" \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -d '{"auth_token_exp_timeout": <NEW_EXPIRE_TIME_IN_SECONDS>}'
```

### Authentication Schemes

| Scheme | Type | Description |
|--------|------|-------------|
| `basicAuth` | HTTP Basic | Username/Password untuk login |
| `jwt` | HTTP Bearer | JWT token untuk API access |

---

## Struktur Response

### Standard Response Format
```json
{
    "data": {
        "affected_items": [...],
        "total_affected_items": 0,
        "total_failed_items": 0,
        "failed_items": []
    },
    "message": "Success message",
    "error": 0
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `data` | object | Main response data |
| `affected_items` | array | Successfully processed items |
| `total_affected_items` | integer | Count of successful items |
| `failed_items` | array | Items that failed processing |
| `total_failed_items` | integer | Count of failed items |
| `message` | string | Human readable message |
| `error` | integer | Error code (0 = success) |

---

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| **200** | OK - Request successful |
| **400** | Bad Request - Invalid request format |
| **401** | Unauthorized - Authentication required |
| **403** | Forbidden - Permission denied |
| **404** | Not Found - Resource doesn't exist |
| **405** | Method Not Allowed - Invalid HTTP method |
| **406** | Not Acceptable - Invalid content-type |
| **413** | Payload Too Large - Request body too big |
| **415** | Unsupported Media Type |
| **429** | Too Many Requests - Rate limit exceeded |

### Error Response Example
```json
{
    "title": "Unauthorized",
    "detail": "The server could not verify that you are authorized to access the URL requested",
    "status": 401,
    "type": "about:blank"
}
```

---

## Endpoints Utama

## API Info

### Get API Information
Mendapatkan informasi dasar tentang API.

**Endpoint:** `GET /`

**Parameters:**
- `pretty` (boolean): Format response dalam human-readable

**Example:**
```bash
curl -k -X GET "https://localhost:55000/" \
  -H "Authorization: Bearer <TOKEN>"
```

**Response:**
```json
{
    "title": "Wazuh API",
    "api_version": "v4.12.0",
    "revision": "beta1",
    "license_name": "GPL 2.0",
    "license_url": "https://github.com/wazuh/wazuh/blob/v4.12.0/LICENSE",
    "hostname": "wazuh",
    "timestamp": "2024-01-01T08:08:11Z"
}
```

---

## Active Response

Active Response memungkinkan eksekusi commands pada agents secara remote.

### Run Command
Menjalankan command pada agents.

**Endpoint:** `PUT /active-response`

**Parameters:**
- `agents_list` (array): List of agent IDs
- `pretty` (boolean): Format output
- `wait_for_complete` (boolean): Disable timeout

**Request Body:**
```json
{
    "command": "restart-wazuh",
    "arguments": ["-r"],
    "alert": {
        "data": {}
    }
}
```

**Example:**
```bash
curl -k -X PUT "https://localhost:55000/active-response" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "restart-wazuh",
    "arguments": ["-r"]
  }'
```

---

## Agents Management

Manajemen comprehensive untuk Wazuh agents.

### List All Agents
Mendapatkan informasi semua agents.

**Endpoint:** `GET /agents`

**Parameters:**
- `agents_list` (array): Specific agent IDs
- `offset` (int): Pagination offset
- `limit` (int): Max items (1-100000, default: 500)
- `select` (array): Fields to return
- `sort` (string): Sort field (+/- for asc/desc)
- `search` (string): Search string
- `status` (array): Filter by status (active, pending, never_connected, disconnected)
- `os.platform` (string): Filter by OS platform
- `os.version` (string): Filter by OS version
- `version` (string): Filter by agent version
- `group` (string): Filter by group
- `node_name` (string): Filter by node name
- `name` (string): Filter by name
- `ip` (string): Filter by IP
- `registerIP` (string): Filter by registration IP

**Example:**
```bash
curl -k -X GET "https://localhost:55000/agents?limit=10&sort=+name" \
  -H "Authorization: Bearer <TOKEN>"
```

### Add New Agent
Menambahkan agent baru ke sistem.

**Endpoint:** `POST /agents`

**Request Body:**
```json
{
    "name": "NewAgent",
    "ip": "192.168.1.100"
}
```

**Example:**
```bash
curl -k -X POST "https://localhost:55000/agents" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "NewAgent", "ip": "192.168.1.100"}'
```

### Delete Agents
Menghapus agents dari sistem.

**Endpoint:** `DELETE /agents`

**Parameters:**
- `agents_list` (array): Agent IDs to delete
- `older_than` (string): Delete agents older than specified time
- `status` (array): Delete by status

### Get Agent Key
Mendapatkan key untuk agent tertentu.

**Endpoint:** `GET /agents/{agent_id}/key`

**Example:**
```bash
curl -k -X GET "https://localhost:55000/agents/001/key" \
  -H "Authorization: Bearer <TOKEN>"
```

### Restart Agent
Me-restart agent tertentu.

**Endpoint:** `PUT /agents/{agent_id}/restart`

**Example:**
```bash
curl -k -X PUT "https://localhost:55000/agents/001/restart" \
  -H "Authorization: Bearer <TOKEN>"
```

### Upgrade Agents
Upgrade agents ke versi terbaru.

**Endpoint:** `PUT /agents/upgrade`

**Parameters:**
- `agents_list` (array): Required. Agent IDs to upgrade
- `wpk_repo` (string): WPK repository URL
- `upgrade_version` (string): Target Wazuh version
- `use_http` (boolean): Use HTTP instead of HTTPS
- `force` (boolean): Force upgrade
- `package_type` (string): rpm/deb package type

**Example:**
```bash
curl -k -X PUT "https://localhost:55000/agents/upgrade?agents_list=001,002" \
  -H "Authorization: Bearer <TOKEN>"
```

### Get Agent Configuration
Mendapatkan konfigurasi aktif dari agent.

**Endpoint:** `GET /agents/{agent_id}/config/{component}/{configuration}`

### Get Agent Stats
Mendapatkan statistik daemon dari agent.

**Endpoint:** `GET /agents/{agent_id}/daemons/stats`

---

## Cluster Management

Manajemen Wazuh cluster dan nodes.

### Get Cluster Status
Mendapatkan status cluster.

**Endpoint:** `GET /cluster/status`

**Example:**
```bash
curl -k -X GET "https://localhost:55000/cluster/status" \
  -H "Authorization: Bearer <TOKEN>"
```

**Response:**
```json
{
    "data": {
        "enabled": "yes",
        "running": "yes"
    },
    "error": 0
}
```

### Get Cluster Nodes
Mendapatkan informasi semua nodes dalam cluster.

**Endpoint:** `GET /cluster/nodes`

### Update Node Configuration
Update konfigurasi untuk node tertentu.

**Endpoint:** `PUT /cluster/{node_id}/configuration`

---

## Decoders

Manajemen decoders untuk log parsing.

### List Decoders
Mendapatkan semua decoders.

**Endpoint:** `GET /decoders`

**Parameters:**
- `decoder_names` (array): Filter by decoder names
- `filename` (array): Filter by filename
- `relative_dirname` (string): Filter by directory
- `status` (string): enabled/disabled/all

### Get Decoder Files
Mendapatkan informasi file decoders.

**Endpoint:** `GET /decoders/files`

### Get Parent Decoders
Mendapatkan parent decoders.

**Endpoint:** `GET /decoders/parents`

---

## Events

Endpoint untuk ingestion events ke analysisd.

### Ingest Events
Mengirim security events ke analysisd.

**Endpoint:** `POST /events`

**Limits:**
- Max 30 requests per minute
- Max 100 events per request

**Request Body:**
```json
{
    "events": [
        "Event value 1",
        "{\"someKey\": \"Event value 2\"}"
    ]
}
```

**Example:**
```bash
curl -k -X POST "https://localhost:55000/events" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
        "Jan 1 12:00:00 server sshd: Failed password for root from 192.168.1.1"
    ]
  }'
```

---

## Experimental

⚠️ **Not ready for production endpoints. Use with caution.**

### Clear Rootcheck Database
Membersihkan database rootcheck.

**Endpoint:** `DELETE /experimental/rootcheck`

### Clear Syscheck Database
Membersihkan database FIM.

**Endpoint:** `DELETE /experimental/syscheck`

### Get System Information
Various endpoints untuk mendapatkan system information:

- `GET /experimental/syscollector/hardware` - Hardware info
- `GET /experimental/syscollector/netaddr` - Network addresses
- `GET /experimental/syscollector/netiface` - Network interfaces
- `GET /experimental/syscollector/netproto` - Network protocols
- `GET /experimental/syscollector/os` - Operating system info
- `GET /experimental/syscollector/packages` - Installed packages
- `GET /experimental/syscollector/ports` - Open ports
- `GET /experimental/syscollector/processes` - Running processes
- `GET /experimental/syscollector/hotfixes` - System hotfixes

---

## Groups

Manajemen agent groups dan centralized configurations.

### List Groups
Mendapatkan informasi semua groups.

**Endpoint:** `GET /groups`

**Example:**
```bash
curl -k -X GET "https://localhost:55000/groups" \
  -H "Authorization: Bearer <TOKEN>"
```

### Create Group
Membuat group baru.

**Endpoint:** `POST /groups`

**Request Body:**
```json
{
    "group_id": "web-servers"
}
```

### Get Agents in Group
Mendapatkan agents dalam group tertentu.

**Endpoint:** `GET /groups/{group_id}/agents`

### Get Group Configuration
Mendapatkan konfigurasi group.

**Endpoint:** `GET /groups/{group_id}/configuration`

### Update Group Configuration
Update konfigurasi group dengan file XML.

**Endpoint:** `PUT /groups/{group_id}/configuration`

**Content-Type:** `application/xml`

### Get Group Files
Mendapatkan files dalam group.

**Endpoint:** `GET /groups/{group_id}/files`

### Delete Groups
Menghapus groups.

**Endpoint:** `DELETE /groups`

---

## Lists (CDB)

Manajemen CDB lists untuk lookup tables.

### Get CDB Lists
Mendapatkan informasi semua CDB lists.

**Endpoint:** `GET /lists`

### Get CDB List Files
Mendapatkan path semua CDB list files.

**Endpoint:** `GET /lists/files`

### Update CDB List File
Update atau upload CDB list file.

**Endpoint:** `PUT /lists/files/{filename}`

**Content-Type:** `application/octet-stream`

### Delete CDB List File
Menghapus CDB list file.

**Endpoint:** `DELETE /lists/files/{filename}`

---

## Logtest

Tool untuk testing dan verification rules dan decoders.

### Run Logtest
Menjalankan logtest tool.

**Endpoint:** `PUT /logtest`

**Request Body:**
```json
{
    "token": "session_token",
    "log_format": "syslog",
    "location": "/var/log/messages",
    "event": "Jan 1 12:00:00 server sshd: Failed password"
}
```

**Log Formats:**
- syslog
- json
- snort-full
- squid
- eventlog
- eventchannel
- audit
- mysql_log
- postgresql_log
- nmapg
- iis
- command
- full_command
- djb-multilog
- multi-line

**Example:**
```bash
curl -k -X PUT "https://localhost:55000/logtest" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "log_format": "syslog",
    "location": "/var/log/auth.log",
    "event": "Jan 1 12:00:00 server sshd: Failed password for root from 192.168.1.1"
  }'
```

### End Logtest Session
Mengakhiri session logtest.

**Endpoint:** `DELETE /logtest/sessions/{token}`

---

## Manager

Wazuh manager management dan monitoring.

### Get Manager Status
Mendapatkan status semua Wazuh daemons.

**Endpoint:** `GET /manager/status`

**Example:**
```bash
curl -k -X GET "https://localhost:55000/manager/status" \
  -H "Authorization: Bearer <TOKEN>"
```

### Get Manager Information
Mendapatkan informasi dasar manager.

**Endpoint:** `GET /manager/info`

### Get Manager Configuration
Mendapatkan konfigurasi Wazuh.

**Endpoint:** `GET /manager/configuration`

**Parameters:**
- `section` (string): Specific configuration section
- `field` (string): Specific field in section
- `raw` (boolean): Return in plain text format

**Available Sections:**
- active-response
- agentless
- alerts
- auth
- client
- cluster
- command
- database_output
- email_alerts
- global
- integration
- labels
- localfile
- logging
- remote
- reports
- rootcheck
- ruleset
- sca
- socket
- syscheck
- syslog_output
- vulnerability-detection
- indexer
- aws-s3
- azure-logs
- cis-cat
- docker-listener
- open-scap
- osquery
- syscollector

**Example:**
```bash
curl -k -X GET "https://localhost:55000/manager/configuration?section=global" \
  -H "Authorization: Bearer <TOKEN>"
```

### Update Manager Configuration
Update konfigurasi Wazuh dengan file ossec.conf.

**Endpoint:** `PUT /manager/configuration`

**Content-Type:** `application/octet-stream`

### Get Daemon Statistics
Mendapatkan statistik daemon.

**Endpoint:** `GET /manager/daemons/stats`

**Parameters:**
- `daemons_list` (array): wazuh-analysisd, wazuh-remoted, wazuh-db

### Get Manager Stats
Mendapatkan statistik manager.

**Endpoint:** `GET /manager/stats`
- `GET /manager/stats/hourly` - Hourly stats
- `GET /manager/stats/weekly` - Weekly stats

### Get Manager Logs
Mendapatkan log entries.

**Endpoint:** `GET /manager/logs`

**Parameters:**
- `offset` (int): Pagination
- `limit` (int): Max 500 lines
- `sort` (string): Sort field
- `search` (string): Search string
- `tag` (string): Component filter
- `level` (string): Log level (critical, debug, debug2, error, info, warning)

### Get Logs Summary
Mendapatkan summary dari logs.

**Endpoint:** `GET /manager/logs/summary`

### Get API Configuration
Mendapatkan konfigurasi API lokal.

**Endpoint:** `GET /manager/api/config`

### Restart Manager
Me-restart Wazuh manager.

**Endpoint:** `PUT /manager/restart`

### Validate Configuration
Memeriksa validitas konfigurasi Wazuh.

**Endpoint:** `GET /manager/configuration/validation`

### Check Available Updates
Memeriksa update yang tersedia.

**Endpoint:** `GET /manager/version/check`

**Parameters:**
- `force_query` (boolean): Force query to CTI service

---

## MITRE

Informasi technique dari MITRE database.

### Get MITRE Metadata
**Endpoint:** `GET /mitre/metadata`

### Get MITRE Groups
**Endpoint:** `GET /mitre/groups`

### Get MITRE References
**Endpoint:** `GET /mitre/references`

### Get MITRE Software
**Endpoint:** `GET /mitre/software`

### Get MITRE Techniques
**Endpoint:** `GET /mitre/techniques`

---

## Overview

Overview comprehensive dari Wazuh system.

### Get Agents Overview
Mendapatkan overview lengkap agents.

**Endpoint:** `GET /overview/agents`

**Response:**
```json
{
    "data": {
        "nodes": [...],
        "groups": [...],
        "agent_os": [...],
        "agent_status": {...},
        "agent_version": [...],
        "last_registered_agent": [...]
    },
    "error": 0
}
```

---

## Rootcheck

Policy monitoring dan rootkit detection.

### Run Rootcheck Scan
Menjalankan rootcheck scan.

**Endpoint:** `PUT /rootcheck`

**Parameters:**
- `agents_list` (array): Agent IDs

### Get Rootcheck Results
Mendapatkan hasil rootcheck.

**Endpoint:** `GET /rootcheck/{agent_id}`

### Clear Rootcheck Results
Membersihkan hasil rootcheck.

**Endpoint:** `DELETE /rootcheck`

### Get Last Scan Time
Mendapatkan waktu scan terakhir.

**Endpoint:** `GET /rootcheck/{agent_id}/last_scan`

---

## Rules

Manajemen detection rules.

### List Rules
Mendapatkan semua rules.

**Endpoint:** `GET /rules`

**Parameters:**
- `rule_ids` (array): Specific rule IDs
- `filename` (array): Filter by filename
- `relative_dirname` (string): Filter by directory
- `status` (string): enabled/disabled/all
- `group` (array): Filter by rule groups
- `level` (string): Filter by rule level
- `pci_dss` (array): Filter by PCI DSS requirements
- `gdpr` (array): Filter by GDPR articles
- `hipaa` (array): Filter by HIPAA sections
- `nist_800_53` (array): Filter by NIST requirements

### Get Rule Groups
Mendapatkan groups rules.

**Endpoint:** `GET /rules/groups`

### Get Rule Requirements
Mendapatkan compliance requirements.

**Endpoint:** `GET /rules/requirement/{requirement}`

### Get Rules Files
Mendapatkan informasi file rules.

**Endpoint:** `GET /rules/files`

### Update Rules File
Update file rules.

**Endpoint:** `PUT /rules/files/{filename}`

### Delete Rules File
Menghapus file rules.

**Endpoint:** `DELETE /rules/files/{filename}`

---

## SCA

Security Configuration Assessment.

### Get SCA Results
Mendapatkan hasil SCA assessment.

**Endpoint:** `GET /sca/{agent_id}`

### Get SCA Policy Checks
Mendapatkan checks untuk policy tertentu.

**Endpoint:** `GET /sca/{agent_id}/checks/{policy_id}`

---

## Security

RBAC administration dan user authentication management.

### Authentication Endpoints

#### Login
Mendapatkan JWT token.

**Endpoint:** `POST /security/user/authenticate`

**Authorization:** Basic Auth (username:password)

#### Logout
Invalidate semua tokens user.

**Endpoint:** `DELETE /security/user/authenticate`

#### Get Current User Info
Mendapatkan informasi user saat ini.

**Endpoint:** `GET /security/users/me`

### User Management

#### List Users
**Endpoint:** `GET /security/users`

#### Create User
**Endpoint:** `POST /security/users`

**Request Body:**
```json
{
    "username": "newuser",
    "password": "SecurePassword123"
}
```

#### Update User
**Endpoint:** `PUT /security/users/{user_id}`

#### Delete Users
**Endpoint:** `DELETE /security/users`

#### Enable/Disable Run As
**Endpoint:** `PUT /security/users/{user_id}/run_as`

### Role Management

#### List Roles
**Endpoint:** `GET /security/roles`

#### Create Role
**Endpoint:** `POST /security/roles`

**Request Body:**
```json
{
    "name": "read-only"
}
```

#### Update Role
**Endpoint:** `PUT /security/roles/{role_id}`

#### Delete Roles
**Endpoint:** `DELETE /security/roles`

### Policy Management

#### List Policies
**Endpoint:** `GET /security/policies`

#### Create Policy
**Endpoint:** `POST /security/policies`

**Request Body:**
```json
{
    "name": "agents_read",
    "policy": {
        "actions": ["agent:read"],
        "resources": ["agent:id:*"],
        "effect": "allow"
    }
}
```

#### Update Policy
**Endpoint:** `PUT /security/policies/{policy_id}`

### Security Rules

#### List Security Rules
**Endpoint:** `GET /security/rules`

#### Create Security Rule
**Endpoint:** `POST /security/rules`

### Role-User-Policy Relationships

#### Add Roles to User
**Endpoint:** `POST /security/users/{user_id}/roles`

#### Remove Roles from User
**Endpoint:** `DELETE /security/users/{user_id}/roles`

#### Add Policies to Role
**Endpoint:** `POST /security/roles/{role_id}/policies`

#### Remove Policies from Role
**Endpoint:** `DELETE /security/roles/{role_id}/policies`

### RBAC Information

#### List RBAC Actions
**Endpoint:** `GET /security/actions`

#### List RBAC Resources
**Endpoint:** `GET /security/resources`

### Security Configuration

#### Get Security Config
**Endpoint:** `GET /security/config`

#### Update Security Config
**Endpoint:** `PUT /security/config`

**Request Body:**
```json
{
    "auth_token_exp_timeout": 900,
    "rbac_mode": "white"
}
```

#### Restore Default Security Config
**Endpoint:** `DELETE /security/config`

---

## Syscheck

File Integrity Monitoring (FIM).

### Run FIM Scan
Menjalankan FIM scan.

**Endpoint:** `PUT /syscheck`

**Parameters:**
- `agents_list` (array): Agent IDs

### Get FIM Results
Mendapatkan hasil FIM.

**Endpoint:** `GET /syscheck/{agent_id}`

### Clear FIM Results
Membersihkan hasil FIM.

**Endpoint:** `DELETE /syscheck/{agent_id}`

### Get Last FIM Scan
Mendapatkan waktu scan FIM terakhir.

**Endpoint:** `GET /syscheck/{agent_id}/last_scan`

---

## Syscollector

System inventory dan monitoring.

### Get Hardware Info
**Endpoint:** `GET /syscollector/{agent_id}/hardware`

### Get Network Address Info
**Endpoint:** `GET /syscollector/{agent_id}/netaddr`

### Get Network Interface Info
**Endpoint:** `GET /syscollector/{agent_id}/netiface`

### Get Network Protocol Info
**Endpoint:** `GET /syscollector/{agent_id}/netproto`

### Get Operating System Info
**Endpoint:** `GET /syscollector/{agent_id}/os`

### Get Packages Info
**Endpoint:** `GET /syscollector/{agent_id}/packages`

### Get Ports Info
**Endpoint:** `GET /syscollector/{agent_id}/ports`

### Get Processes Info
**Endpoint:** `GET /syscollector/{agent_id}/processes`

### Get Hotfixes Info (Windows)
**Endpoint:** `GET /syscollector/{agent_id}/hotfixes`

---

## Tasks

Task management dan monitoring.

### List Tasks
Mendapatkan informasi semua tasks.

**Endpoint:** `GET /tasks/status`

**Parameters:**
- `agents_list` (array): Filter by agents
- `command` (string): Filter by command
- `node` (array): Filter by nodes
- `module` (array): Filter by modules
- `status` (array): Filter by status

---

## Examples & Best Practices

### 1. Complete Agent Management Workflow

```bash
#!/bin/bash

# Set variables
API_URL="https://localhost:55000"
USERNAME="wazuh"
PASSWORD="wazuh"
AGENT_NAME="web-server-01"
AGENT_IP="192.168.1.100"

# 1. Login and get token
TOKEN=$(curl -s -u $USERNAME:$PASSWORD -k -X POST "$API_URL/security/user/authenticate" | jq -r '.data.token')

# 2. Add new agent
AGENT_RESPONSE=$(curl -s -k -X POST "$API_URL/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$AGENT_NAME\", \"ip\": \"$AGENT_IP\"}")

# 3. Get agent ID from response
AGENT_ID=$(echo $AGENT_RESPONSE | jq -r '.data.id')
echo "Created agent with ID: $AGENT_ID"

# 4. Get agent key
AGENT_KEY=$(curl -s -k -X GET "$API_URL/agents/$AGENT_ID/key" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.data.affected_items[0].key')

echo "Agent Key: $AGENT_KEY"

# 5. Assign to group
curl -s -k -X PUT "$API_URL/agents/$AGENT_ID/group/web-servers" \
  -H "Authorization: Bearer $TOKEN"

# 6. Check agent status
curl -s -k -X GET "$API_URL/agents/$AGENT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.affected_items[0].status'
```

### 2. Bulk Operations

```python
import requests
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class WazuhAPI:
    def __init__(self, url, username, password):
        self.url = url
        self.token = self._get_token(username, password)
    
    def _get_token(self, username, password):
        login_url = f"{self.url}/security/user/authenticate"
        response = requests.post(login_url, auth=(username, password), verify=False)
        return response.json()['data']['token']
    
    def _make_request(self, method, endpoint, data=None):
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        url = f"{self.url}{endpoint}"
        response = requests.request(method, url, headers=headers, json=data, verify=False)
        return response.json()
    
    def get_agents(self, **params):
        return self._make_request('GET', '/agents', params)
    
    def restart_agents(self, agent_ids):
        return self._make_request('PUT', f'/agents/restart?agents_list={",".join(agent_ids)}')
    
    def upgrade_agents(self, agent_ids, version=None):
        endpoint = f'/agents/upgrade?agents_list={",".join(agent_ids)}'
        if version:
            endpoint += f'&upgrade_version={version}'
        return self._make_request('PUT', endpoint)

# Usage
api = WazuhAPI('https://localhost:55000', 'wazuh', 'wazuh')

# Get all active agents
active_agents = api.get_agents(status='active')

# Restart multiple agents
agent_ids = ['001', '002', '003']
result = api.restart_agents(agent_ids)
print(f"Restart result: {result}")
```

### 3. Monitoring Dashboard Data

```javascript
class WazuhMonitoring {
    constructor(apiUrl, token) {
        this.apiUrl = apiUrl;
        this.token = token;
    }

    async makeRequest(endpoint) {
        const response = await fetch(`${this.apiUrl}${endpoint}`, {
            headers: {
                'Authorization': `Bearer ${this.token}`
            }
        });
        return response.json();
    }

    async getDashboardData() {
        const [
            agentsOverview,
            managerStatus,
            recentAlerts,
            systemStats
        ] = await Promise.all([
            this.makeRequest('/overview/agents'),
            this.makeRequest('/manager/status'),
            this.makeRequest('/manager/logs?limit=100'),
            this.makeRequest('/manager/stats')
        ]);

        return {
            agentsOverview: agentsOverview.data,
            managerStatus: managerStatus.data,
            recentAlerts: recentAlerts.data,
            systemStats: systemStats.data
        };
    }

    async getAgentDetails(agentId) {
        const [
            agentInfo,
            agentOs,
            agentPackages,
            agentPorts
        ] = await Promise.all([
            this.makeRequest(`/agents/${agentId}`),
            this.makeRequest(`/syscollector/${agentId}/os`),
            this.makeRequest(`/syscollector/${agentId}/packages?limit=20`),
            this.makeRequest(`/syscollector/${agentId}/ports?limit=20`)
        ]);

        return {
            info: agentInfo.data.affected_items[0],
            os: agentOs.data.affected_items[0],
            packages: agentPackages.data.affected_items,
            ports: agentPorts.data.affected_items
        };
    }
}
```

### 4. Configuration Management

```bash
#!/bin/bash

# Configuration backup and restore script

API_URL="https://localhost:55000"
TOKEN="your_jwt_token"

# Backup current configuration
backup_config() {
    echo "Backing up current configuration..."
    
    # Manager configuration
    curl -s -k -X GET "$API_URL/manager/configuration?raw=true" \
      -H "Authorization: Bearer $TOKEN" > backup/ossec.conf
    
    # Rules files
    curl -s -k -X GET "$API_URL/rules/files" \
      -H "Authorization: Bearer $TOKEN" | jq -r '.data.affected_items[].filename' | \
    while read filename; do
        curl -s -k -X GET "$API_URL/rules/files/$filename?raw=true" \
          -H "Authorization: Bearer $TOKEN" > "backup/rules/$filename"
    done
    
    # Decoder files
    curl -s -k -X GET "$API_URL/decoders/files" \
      -H "Authorization: Bearer $TOKEN" | jq -r '.data.affected_items[].filename' | \
    while read filename; do
        curl -s -k -X GET "$API_URL/decoders/files/$filename?raw=true" \
          -H "Authorization: Bearer $TOKEN" > "backup/decoders/$filename"
    done
    
    echo "Backup completed!"
}

# Validate configuration
validate_config() {
    echo "Validating configuration..."
    VALIDATION=$(curl -s -k -X GET "$API_URL/manager/configuration/validation" \
      -H "Authorization: Bearer $TOKEN")
    
    if [ $(echo $VALIDATION | jq '.error') -eq 0 ]; then
        echo "Configuration is valid!"
        return 0
    else
        echo "Configuration validation failed!"
        echo $VALIDATION | jq '.message'
        return 1
    fi
}

# Update configuration
update_config() {
    local config_file=$1
    
    if validate_config; then
        echo "Updating configuration from $config_file"
        curl -s -k -X PUT "$API_URL/manager/configuration" \
          -H "Authorization: Bearer $TOKEN" \
          -H "Content-Type: application/octet-stream" \
          --data-binary "@$config_file"
        
        # Restart manager to apply changes
        curl -s -k -X PUT "$API_URL/manager/restart" \
          -H "Authorization: Bearer $TOKEN"
    fi
}

# Usage
case "$1" in
    backup)
        backup_config
        ;;
    validate)
        validate_config
        ;;
    update)
        update_config $2
        ;;
    *)
        echo "Usage: $0 {backup|validate|update <config_file>}"
        ;;
esac
```

### 5. Best Practices

#### Security
- Selalu gunakan HTTPS dalam production
- Rotate JWT tokens secara regular
- Gunakan RBAC untuk membatasi access
- Monitor API access logs
- Implementasikan rate limiting

#### Performance
- Gunakan pagination untuk large datasets (`limit`, `offset`)
- Filter results dengan parameter yang sesuai
- Cache responses yang jarang berubah
- Gunakan `select` parameter untuk hanya mengambil field yang diperlukan

#### Error Handling
```python
def safe_api_call(func, *args, **kwargs):
    try:
        response = func(*args, **kwargs)
        if response.get('error', 0) != 0:
            raise Exception(f"API Error: {response.get('message', 'Unknown error')}")
        return response
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network Error: {str(e)}")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON response")
```

#### Logging
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_api_call(endpoint, method, response_code, execution_time):
    logger.info(f"API Call: {method} {endpoint} - {response_code} ({execution_time}ms)")
```

---

## Rate Limiting

Wazuh API memiliki rate limiting untuk mencegah abuse:

- **Default**: Max 30 requests per minute untuk endpoints tertentu
- **Events endpoint**: Max 30 requests per minute, max 100 events per request
- **Response**: HTTP 429 ketika limit exceeded

---

## Changelog & Version Notes

### v4.12.0 Features
- Enhanced RBAC capabilities
- Improved cluster management
- New MITRE ATT&CK integration
- Enhanced security configuration options
- Better error handling and responses
- Performance improvements

---

## Useful Resources

- **Official Documentation**: https://documentation.wazuh.com/current/user-manual/api/
- **OpenAPI Specification**: https://raw.githubusercontent.com/wazuh/wazuh/v4.12.0/api/api/spec/spec.yaml
- **GitHub Repository**: https://github.com/wazuh/wazuh
- **Community Forum**: https://wazuh.com/community/
- **License**: GPL 2.0

---

## Support & Troubleshooting

### Common Issues

1. **Authentication Errors (401)**
   - Verify username/password
   - Check token expiration
   - Ensure proper Authorization header format

2. **Permission Denied (403)**
   - Verify RBAC policies
   - Check user roles and permissions
   - Ensure resource access is allowed

3. **Rate Limiting (429)**
   - Implement request throttling
   - Add delays between requests
   - Consider batch operations

4. **Large Response Timeouts**
   - Use pagination (`limit`, `offset`)
   - Apply filters to reduce dataset
   - Consider `wait_for_complete=false`

### Debugging Tips

- Enable verbose logging with `pretty=true`
- Use curl with `-v` flag for detailed request/response info  
- Monitor Wazuh manager logs for API-related messages
- Validate JSON payloads before sending

---

**Documentation created on August 26, 2025 based on Wazuh API REST v4.12.0**
