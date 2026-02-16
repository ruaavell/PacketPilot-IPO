# Security Policy

## Core Security Principles

Internet Performance Optimizer (IPO) is designed with security as a first-class concern. This document outlines our security model, policies, and guidelines.

### 1. Principle of Least Privilege

**Goal**: IPO requests the minimum permissions necessary for each operation.

**Implementation**:
- Benchmarking (read-only): No admin privileges required
- Router config generation: No admin privileges (generates files only)
- NIC tuning (Windows): Requires admin, with explicit user consent

**User Experience**:
```
$ ipo bench --target 1.1.1.1
✓ Running (no admin required)

$ ipo tuner apply nic-rss-enable
⚠️  This operation requires administrator privileges
    Command: Enable-NetAdapterRss -Name '*'
    Do you want to proceed? [y/N]
```

### 2. No Direct Execution

**Policy**: IPO NEVER executes system-modifying commands directly.

**Rationale**:
- Prevent privilege escalation attacks
- Allow user verification of all changes
- Enable security auditing
- Maintain transparency

**Implementation**:
All tuners follow the **Generate → Review → Apply** pattern:

1. **Generate**: Create PowerShell, shell script, or config file
2. **Review**: User manually reviews the generated script
3. **Apply**: User manually executes the script (not IPO)

**Example**:
```bash
# IPO generates this script
$ ipo router openwrt --download 100 --upload 20 --output sqm.sh

# User reviews sqm.sh
$ cat sqm.sh
# #!/bin/sh
# # OpenWRT SQM Configuration
# uci set sqm.@queue[-1].download='95000'
# ...

# User manually applies (not IPO)
$ scp sqm.sh root@router:/tmp/
$ ssh root@router 'sh /tmp/sqm.sh'
```

### 3. Reversibility

**Requirement**: Every change MUST be reversible.

**Implementation**:

#### Automatic Backups
Before any change:
```python
def apply_change(command: str) -> ApplyResult:
    # 1. Backup current state
    backup_path = create_backup(get_current_state())
    
    # 2. Generate rollback script
    rollback_script = generate_rollback(backup_path)
    
    # 3. Apply change (with verification)
    result = execute_with_verification(command)
    
    # 4. Return result with rollback info
    return ApplyResult(
        success=result.success,
        backup_path=backup_path,
        rollback_script=rollback_script
    )
```

#### Rollback Commands
Every recommendation includes rollback commands:
```python
Recommendation(
    id="nic_rss_enable",
    commands=[
        "Enable-NetAdapterRss -Name '*'"
    ],
    rollback_commands=[
        "Disable-NetAdapterRss -Name '*'"
    ],
    reversible=True
)
```

### 4. Explicit Consent

**Policy**: NO silent changes. Users must explicitly approve every system modification.

**Implementation**:

#### CLI Consent Flow
```bash
$ ipo tuner apply nic-rss-enable

⚠️  WARNING: System Modification
────────────────────────────────────────
Operation:     Enable Receive Side Scaling (RSS)
Category:      Network Adapter (NIC)
Risk Level:    Low
Reversible:    Yes
Admin Required: Yes

Commands to be executed:
  1. Get-NetAdapterRss  # Backup current state
  2. Enable-NetAdapterRss -Name '*'

Rollback available: Yes
Backup location: %APPDATA%\IPO\backups\20240216_143000\

Do you want to proceed? [y/N]: _
```

#### GUI Consent Flow
```
┌─────────────────────────────────────────┐
│ ⚠️  Administrator Privileges Required    │
├─────────────────────────────────────────┤
│ This operation will modify your network │
│ adapter settings.                        │
│                                          │
│ • Backup will be created automatically  │
│ • You can rollback with one click       │
│ • All commands are logged               │
│                                          │
│ [Cancel]              [Show Details] [✓ Apply] │
└─────────────────────────────────────────┘
```

### 5. No Permanent Security Disabling

**Policy**: NEVER permanently disable Windows Update, Defender, or other security features.

**Allowed**:
- Temporary pause with strong warnings
- Scheduling alternatives
- Documentation of risks

**Forbidden**:
- Permanent registry changes to disable updates
- Disabling antivirus permanently
- Modifying security policies without clear user understanding

**Example** (what we DON'T do):
```powershell
# ❌ FORBIDDEN - Never included in IPO
Stop-Service wuauserv
Set-Service wuauserv -StartupType Disabled
```

**Alternative** (if user explicitly requests update management):
```
⚠️  IPO does not support disabling Windows Update.
    
    Why? Because:
    • It's a security risk
    • Updates often include network stack improvements
    • Temporary pausing is usually sufficient
    
    If you need to control updates:
    1. Use Windows built-in "Pause Updates" feature
    2. Configure Active Hours in Windows Settings
    3. Use Group Policy (Pro/Enterprise) for scheduling
```

### 6. No Kernel Drivers

**Policy**: IPO does NOT ship, install, or recommend unsigned kernel drivers.

**Rationale**:
- Kernel drivers have unlimited system access
- Unsigned drivers require disabling Driver Signature Enforcement (huge security risk)
- Most optimizations don't need kernel-level access

**Alternative Approaches**:
- User-space network tools (ping, iperf3)
- PowerShell cmdlets for NIC configuration
- Router-level optimizations (no Windows kernel involvement)

**Future Consideration**:
If kernel-level features are proposed:
1. Open RFC issue for community discussion
2. Require Microsoft signing
3. Implement behind "Advanced/Developer" flag with strong warnings
4. Document all security implications

### 7. Input Validation

**Policy**: All user inputs are validated and sanitized.

**Implementation**:

#### Command Injection Prevention
```python
# ❌ DANGEROUS
def ping(target: str) -> None:
    os.system(f"ping {target}")  # Allows: target="1.1.1.1; rm -rf /"

# ✅ SAFE
def ping(target: str) -> None:
    # Validate target
    if not is_valid_ip_or_hostname(target):
        raise ValueError("Invalid target")
    
    # Use subprocess with list (not shell=True)
    subprocess.run(["ping", "-n", "100", target], shell=False)
```

#### Path Traversal Prevention
```python
# ❌ DANGEROUS
def load_benchmark(filename: str) -> BenchmarkResult:
    with open(filename, 'r') as f:  # Allows: filename="../../etc/passwd"
        return json.load(f)

# ✅ SAFE
def load_benchmark(filename: str) -> BenchmarkResult:
    # Resolve to absolute path
    path = Path(filename).resolve()
    
    # Ensure it's within allowed directory
    allowed_dir = get_benchmark_dir().resolve()
    if not path.is_relative_to(allowed_dir):
        raise ValueError("Invalid benchmark file path")
    
    with open(path, 'r') as f:
        return BenchmarkResult(**json.load(f))
```

#### DNS Resolver Validation
```python
def validate_dns_resolver(ip: str) -> bool:
    """Validate DNS resolver IP address."""
    try:
        import ipaddress
        addr = ipaddress.ip_address(ip)
        
        # Reject invalid ranges
        if addr.is_loopback or addr.is_link_local or addr.is_multicast:
            return False
        
        return True
    except ValueError:
        return False
```

### 8. Dependency Security

**Policy**: Minimize dependencies and keep them updated.

**Current Dependencies**:
- `click`: CLI framework (widely used, well-maintained)
- `psutil`: System info (cross-platform, security-conscious)
- `pydantic`: Data validation (type-safe, prevents injection)
- `PyQt6`: GUI framework (optional, for GUI only)
- `requests`: HTTP client (for future features)

**Security Practices**:
- Pin major versions in `setup.py`
- Dependabot alerts enabled
- Regular security audits
- No dependencies with known CVEs

**Forbidden Dependencies**:
- Any package that requires elevated privileges to install
- Packages with poor maintenance history
- Packages with known security issues

### 9. Data Privacy

**Policy**: Zero data collection by default.

**Implementation**:

#### No Telemetry
```python
# IPO does NOT include any of these
import analytics  # ❌
import sentry_sdk  # ❌
import google_analytics  # ❌
```

#### Opt-in Only (if ever added)
```python
# If telemetry is added in the future, it must be:
if config.get("telemetry_enabled", False):  # Default: False
    # And must clearly disclose:
    print("""
    Telemetry Collection (Opt-in)
    ────────────────────────────
    Data collected:
      • Benchmark results (anonymized)
      • Operating system version
      • IPO version
    
    Data NOT collected:
      • IP addresses
      • Hostnames
      • Network adapter MACs
      • Personal information
    
    Data storage: Your own GitHub Gist (you control it)
    """)
```

#### PII Scrubbing
If benchmarks are shared:
```python
def anonymize_benchmark(benchmark: BenchmarkResult) -> BenchmarkResult:
    """Remove PII from benchmark results."""
    benchmark.system_info.pop("hostname", None)
    benchmark.system_info.pop("username", None)
    
    # Anonymize network interfaces
    for iface in benchmark.system_info.get("network_interfaces", []):
        iface["name"] = f"Interface {hash(iface['name']) % 10}"
        # Keep address prefix only
        iface["address"] = ".".join(iface["address"].split(".")[:2]) + ".x.x"
    
    return benchmark
```

### 10. Logging Security

**Policy**: Logs must not contain sensitive information.

**Implementation**:

#### Safe Logging
```python
# ❌ DANGEROUS
logger.debug(f"Connecting to {username}:{password}@{host}")

# ✅ SAFE
logger.debug(f"Connecting to {host} (credentials redacted)")
```

#### Log Access Control
```python
# Logs stored in user-specific directory (not world-readable)
if platform.system() == "Windows":
    log_dir = Path.home() / "AppData" / "Roaming" / "IPO" / "logs"
else:
    log_dir = Path.home() / ".ipo" / "logs"
    log_dir.chmod(0o700)  # Owner-only access
```

## Vulnerability Disclosure

### Reporting Security Issues

**DO NOT** open public GitHub issues for security vulnerabilities.

**Instead**:
1. Email: security@example.com (replace with actual contact)
2. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Fix Development**: Depends on severity
  - Critical: 7-14 days
  - High: 14-30 days
  - Medium/Low: Next release cycle

### Disclosure Policy

- **Private Fix**: Develop and test patch privately
- **Coordinated Disclosure**: Publish fix and advisory simultaneously
- **Credit**: Reporter credited in release notes (unless anonymous request)

## Security Checklist for Contributors

Before submitting a PR, verify:

- [ ] No `shell=True` in subprocess calls with user input
- [ ] All file paths validated (no path traversal)
- [ ] User input sanitized and validated
- [ ] No secrets or credentials in code
- [ ] No telemetry without opt-in
- [ ] Admin operations require explicit consent
- [ ] Changes are reversible (backup + rollback)
- [ ] Security-sensitive operations logged
- [ ] Tests cover security-critical code paths

## Known Limitations

1. **iperf3 Dependency**: Relies on external iperf3 binary
   - Mitigation: Validate checksum if auto-downloading (future)
   
2. **PowerShell Execution**: Generated scripts executed by user
   - Mitigation: Clear warnings, script review encouraged
   
3. **Ping Requires Privileges**: Some systems require root for raw sockets
   - Mitigation: Fallback to system ping command

## Security Updates

This document is versioned with the project. Check for updates:

```bash
git log -p docs/security.md
```

Last updated: 2024-02-16
Version: 0.1.0
