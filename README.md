# QuotaCloud — Multi-User Cloud Storage Quota and Resource Management SaaS

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Framework: Flask](https://img.shields.io/badge/Framework-Flask_2.3+-teal.svg)](https://flask.palletsprojects.com/)
[![Storage: Hadoop HDFS & Local](https://img.shields.io/badge/Storage-HDFS%20%26%20Local-yellowgreen.svg)](https://hadoop.apache.org/)
[![Database: SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey.svg)](https://sqlite.org/)

**QuotaCloud** is an enterprise-grade, multi-user cloud storage management platform built with a Software-as-a-Service (SaaS) architecture. It enables users to securely upload, download, explore, and delete files within server-enforced storage quotas, while granting administrators complete control over user account provisioning, storage limit allocation, real-time resource utilization tracking, and system-wide activity audits.

Designed specifically for **College Cloud Computing Mini-Projects & Academic Demonstrations**, QuotaCloud incorporates a modular **Storage Abstraction Layer** capable of switching seamlessly between **Local Development Storage** and a real **Apache Hadoop Distributed File System (HDFS)** cluster without altering application business logic.

---

## Table of Contents
1. [Key Features](#1-key-features)
2. [SaaS & Cloud Computing Architecture](#2-saas--cloud-computing-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Database Design (ER Diagram)](#4-database-design-er-diagram)
5. [Storage Quota System Mechanics](#5-storage-quota-system-mechanics)
6. [Hadoop HDFS vs Local Development Mode](#6-hadoop-hdfs-vs-local-development-mode)
7. [Installation & Quick Start Guide](#7-installation--quick-start-guide)
8. [Ubuntu / Linux Hadoop HDFS Deployment Guide](#8-ubuntu--linux-hadoop-hdfs-deployment-guide)
9. [Automated Testing Suite](#9-automated-testing-suite)
10. [Default Demo Credentials](#10-default-demo-credentials)
11. [College Viva & Cloud Computing Interview Questions](#11-college-viva--cloud-computing-interview-questions)

---

## 1. Key Features

### For Regular Users:
- **Personalized Cloud Dashboard**: Visual progress bars, total assigned storage, real-time used bytes, remaining quota, and file count.
- **Strict Quota Enforcement**: Real-time server-side validation rejecting any upload exceeding remaining storage.
- **Proactive Storage Warning (80% Threshold)**: Dynamic warning banners alerting users when their consumption reaches or exceeds 80% capacity.
- **Cloud File Explorer**: Search by filename, sort by upload date, file size, or filename.
- **Drag-and-Drop Uploader**: Real-time AJAX upload progress bar showing byte transfer speeds.
- **Secure File Downloads**: Authenticated streaming preventing unauthorized URL tampering.
- **Safe File Deletion**: Instant quota recalculation and refund upon file removal.
- **Account Security**: Secure password updates with PBKDF2:SHA-256 hashing.

### For Administrators:
- **Central Control Center**: Real-time aggregated statistics across all tenants (Total Users, Files Stored, Total Allocated Quotas, Cluster Used vs Free Capacity).
- **Interactive Chart.js Visualizations**: System-wide storage capacity gauges and per-user quota distribution bar charts.
- **User Provisioning & Quota Allocation**: Create accounts, dynamically scale quota limits (e.g. from 20 MB to 200 MB), toggle active/deactivated statuses, and purge user accounts with all associated cloud files.
- **HDFS Infrastructure Diagnostics**: Real-time health check verifying NameNode and DataNode connectivity, response times, and failure diagnostics. Never falsely reports HDFS as connected when offline.
- **Security & Audit Logs**: Immutable audit trail tracking user logins, file operations, quota modifications, and unauthorized access attempts with client IP addresses.

---

## 2. SaaS & Cloud Computing Architecture

```
                       +-----------------------------------+
                       |    Client Browser (Bootstrap 5)   |
                       | HTML5 / CSS3 / JavaScript / Chart |
                       +-----------------+-----------------+
                                         |
                                (HTTPS / REST API)
                                         |
                                         v
    +------------------------------------+------------------------------------+
    |                        Flask SaaS Application Server                    |
    |                                                                         |
    |  [Authentication & RBAC]   [Audit Service]   [Storage Alert Service]    |
    |                                                                         |
    |                    [Quota Service & Concurrency Lock]                   |
    |                    - Enforces: Quota - Used = Remaining                 |
    |                    - Rejects uploads if Size > Remaining                |
    +-----------------+-----------------------------------+-------------------+
                      |                                   |
                      v                                   v
          +-----------+-----------+           +-----------+-----------+
          |     SQLite Database   |           |   Storage Abstraction |
          |   (Users, Files,      |           |          Layer        |
          |    Logs, Alerts,      |           +-----+-----------+-----+
          |    System Settings)   |                 |           |
          +-----------------------+                 v           v
                                           +--------+--+     +--+--------+
                                           | Local Mode|     | HDFS Mode |
                                           | storage/  |     | WebHDFS   |
                                           | data/     |     | Port 9870 |
                                           +-----------+     +-----------+
```

---

## 3. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | HTML5, CSS3, JavaScript (ES6) | Responsive, mobile-friendly interface |
| **UI Framework** | Bootstrap 5.3 + Bootstrap Icons | Modern SaaS Navy Blue & Teal aesthetic |
| **Data Visualization** | Chart.js 4.4 | Real-time doughnut and bar charts |
| **Backend** | Python 3.8+ with Flask | Modular Blueprint architecture & REST endpoints |
| **Database** | SQLite + Flask-SQLAlchemy | ACID-compliant relational metadata store |
| **Security** | Werkzeug Hashing, CSRF Tokens | Safe sessions, path traversal prevention |
| **Storage Engine** | Hadoop HDFS & Local File Abstraction | Modular storage decoupling |

---

## 4. Database Design (ER Diagram)

```
 +------------------------+             +------------------------+
 |         Users          |             |         Files          |
 +------------------------+             +------------------------+
 | id (PK)                |<---1:N----->| id (PK)                |
 | username (VARCHAR)     |             | user_id (FK)           |
 | email (VARCHAR)        |             | original_filename      |
 | password_hash (VARCHAR)|             | stored_filename        |
 | role (admin/user)      |             | storage_path           |
 | quota_bytes (BIGINT)   |             | size_bytes (BIGINT)    |
 | used_bytes (BIGINT)    |             | mime_type (VARCHAR)    |
 | is_active (BOOLEAN)    |             | created_at (DATETIME)  |
 | created_at (DATETIME)  |             +------------------------+
 +-----------+------------+
             |
             +---1:N---> +------------------------+
             |           |      ActivityLogs      |
             |           +------------------------+
             |           | id (PK)                |
             |           | user_id (FK)           |
             |           | action (VARCHAR)       |
             |           | details (TEXT)         |
             |           | ip_address (VARCHAR)   |
             |           | timestamp (DATETIME)   |
             |           +------------------------+
             |
             +---1:N---> +------------------------+
                         |     StorageAlerts      |
                         +------------------------+
                         | id (PK)                |
                         | user_id (FK)           |
                         | alert_type (VARCHAR)   |
                         | message (TEXT)         |
                         | is_resolved (BOOLEAN)  |
                         | created_at (DATETIME)  |
                         +------------------------+
```

---

## 5. Storage Quota System Mechanics

### A. Quota Formulas
$$\text{Remaining Storage} = \text{Allocated Quota} - \text{Used Storage}$$
$$\text{Storage Usage Percentage} = \left(\frac{\text{Used Storage}}{\text{Allocated Quota}}\right) \times 100$$

### B. Safe Upload Sequence (Atomic Transaction)
1. User submits file via web interface or API.
2. Server validates user session and account active status.
3. Server calculates exact file size in bytes from the stream buffer.
4. Server acquires an exclusive thread lock (`_user_locks[user_id]`) to prevent race conditions during concurrent uploads.
5. Server queries the user's fresh database record:
   - If $\text{File Size} > \text{Remaining Storage}$, the upload is immediately rejected with HTTP 400 (`QuotaExceededError`). A `QUOTA_EXCEEDED` alert and `UPLOAD_BLOCKED` audit log are created.
   - If sufficient quota exists, the file is streamed to the active storage engine (Local or HDFS).
6. Upon successful storage write:
   - Database record created in `files` table.
   - User's `used_bytes` incremented atomically (`used_bytes += file_size`).
   - If usage $\ge 80\%$, a `WARNING_80_PERCENT` alert is triggered.
   - Database transaction committed.
7. If an unexpected storage failure occurs (e.g., HDFS offline, disk write failure), the file is cleaned up, database changes are rolled back, and the user's quota is preserved.

### C. File Deletion and Refund Sequence
1. User clicks Delete on a file.
2. System checks authorization: only the file owner or an administrator can delete a file.
3. File is removed from storage backend.
4. File record deleted from SQLite.
5. User's `used_bytes` is decreased:
   $$\text{used\_bytes} = \max(0, \text{used\_bytes} - \text{file\_size})$$
6. If usage drops below 80%, previously active 80% warning alerts are marked as resolved.

---

## 6. Hadoop HDFS vs Local Development Mode

QuotaCloud provides a unified interface (`BaseStorageService`):

| Characteristic | Local Development Mode (`local`) | Hadoop HDFS Mode (`hdfs`) |
|---|---|---|
| **Target Audience** | Development on Windows/macOS/Linux without Hadoop | College cluster or Linux Hadoop demo |
| **Requirements** | Zero external dependencies (built into Python) | Running Hadoop 2.x or 3.x cluster |
| **Path Scheme** | `storage/data/users/<user_id>/files/<uuid>_<name>` | `/quotacloud/users/<user_id>/files/<uuid>_<name>` |
| **Protocol** | Native POSIX File System | WebHDFS REST API (Port 9870 or 50070) |
| **Connection Check** | Verifies directory write access & disk usage | HTTP ping to NameNode `GETHOMEDIRECTORY` |
| **Offline Behavior** | Always connected | Accurately reports `Disconnected` with debug info |

---

## 7. Installation & Quick Start Guide

### Step 1: Open Terminal in Project Directory
```powershell
cd C:\Users\BAPPA\.gemini\antigravity\scratch\quotacloud
```

### Step 2: Create and Activate Virtual Environment (Recommended)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(On Linux/macOS: `source venv/bin/activate`)*

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Initialize Database with Demo Accounts
```powershell
python init_db.py
```

### Step 5: Start QuotaCloud Application
```powershell
python run.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000/`**

---

## 8. Ubuntu / Linux Hadoop HDFS Deployment Guide

To connect QuotaCloud to a live Apache Hadoop cluster:

### Step 1: Ensure WebHDFS is Enabled on Hadoop
In your Hadoop `hdfs-site.xml` (located in `$HADOOP_HOME/etc/hadoop/hdfs-site.xml`):
```xml
<configuration>
    <property>
        <name>dfs.webhdfs.enabled</name>
        <value>true</value>
    </property>
</configuration>
```

### Step 2: Start Hadoop Daemons
```bash
start-dfs.sh
```
Verify that NameNode and DataNode are running:
```bash
jps
```
*(Expected output includes `NameNode`, `DataNode`, and `SecondaryNameNode`)*.

### Step 3: Configure QuotaCloud for HDFS
Edit `.env` in the `quotacloud` directory:
```env
# Switch storage backend to hdfs
STORAGE_BACKEND=hdfs

# Hadoop NameNode URL (Default port is 9870 for Hadoop 3.x, 50070 for Hadoop 2.x)
HDFS_NAMENODE_URL=http://localhost:9870
HDFS_USER=hadoop
HDFS_ROOT_DIR=/quotacloud/users
```

### Step 4: Restart QuotaCloud
```bash
python run.py
```
Navigate to **Admin -> Resource Monitoring**. You will see:
- Engine: **HDFS**
- Status: **Connected**
- Root Directory: **/quotacloud/users**

---

## 9. Automated Testing Suite

QuotaCloud includes a full unit and integration test suite covering:
- User registration, login, and bad password handling
- Uploads within storage quota
- Upload rejections when quota is exceeded
- Proactive 80% quota warning triggers
- File deletion and quota refund verification
- Access control (preventing cross-tenant downloads)
- Storage path traversal prevention
- HDFS connection offline resilience

To execute all tests:
```powershell
python tests/run_tests.py
```
Or with pytest:
```powershell
pytest -v
```

---

## 10. Default Demo Credentials

| Role | Username | Password | Default Quota | Description |
|---|---|---|---|---|
| **Administrator** | `admin` | `Admin@123` | 100 MB | Full admin control, quota allocator, monitoring |
| **Regular User 1** | `user1` | `User@123` | 50 MB | Pre-loaded with welcome file |
| **Regular User 2** | `user2` | `User@123` | 10 MB | Suitable for testing 80% quota warning & overflow |

---

## 11. College Viva & Cloud Computing Interview Questions

**Q1: What cloud deployment and service model does QuotaCloud follow?**  
*Answer:* QuotaCloud is built on the **Software-as-a-Service (SaaS)** delivery model. End-users access cloud storage via standard web browsers without managing servers, operating systems, or cluster hardware. Storage multi-tenancy is enforced through logical isolation and database-backed quotas.

**Q2: Why use HDFS for cloud storage instead of traditional relational databases?**  
*Answer:* Relational databases (like SQLite or PostgreSQL) are optimized for transactional metadata, not large binary objects (BLOBs). HDFS is designed for high-throughput, distributed, fault-tolerant storage across commodity hardware, offering automatic replication and horizontal scalability.

**Q3: How does QuotaCloud prevent race conditions during concurrent file uploads?**  
*Answer:* QuotaCloud implements a per-user concurrency lock (`threading.Lock` per user_id) combined with database row checks. When multiple uploads arrive concurrently, quota checks and storage reservations are synchronized, preventing users from exceeding their allocated byte limits.

**Q4: How does WebHDFS work without native Hadoop binaries on Windows?**  
*Answer:* WebHDFS is an HTTP REST protocol exposed by Hadoop. File creation is a two-step process:
1. Client sends HTTP PUT to NameNode with `op=CREATE`.
2. NameNode responds with HTTP 307 Redirect specifying the target DataNode URL.
3. Client streams file bytes directly to the DataNode. This eliminates the need for native C++ binaries (`winutils.exe`) on Windows.

**Q5: How does QuotaCloud protect against insecure direct object references (IDOR)?**  
*Answer:* In `/files/<file_id>/download`, the application checks:
`if file.user_id != session['user_id'] and not user.is_admin: abort(403)`.
Even if a malicious user alters the file ID in the URL, they are blocked with HTTP 403 Forbidden.
