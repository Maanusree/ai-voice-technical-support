# Technical Support Knowledge Base & Decision Trees

This document outlines the structured troubleshooting decision trees, FAQ datasets, and triage criteria implemented in the AI Voice Agent.

---

## 1. Summary of Support Domains

| Article ID | Category | Common Problem | Steps Count | Escalation Trigger |
|---|---|---|---|---|
| `kb_network_wifi` | Network & Connectivity | Wi-Fi connected but no internet, DNS failure | 3 | Physical fiber cut (LOS red) / 2 failed steps |
| `kb_account_password` | Account & Security | Locked account, forgotten password, 2FA missing | 3 | Lost 2FA phone / Identity verification failure |
| `kb_hardware_printer` | Hardware & Peripherals | Printer offline, stuck queue, paper jam | 3 | Mechanical grinding noise / Roller gear fault |
| `kb_os_bsod_performance` | OS & Performance | High CPU/RAM usage, BSOD crash loop | 2 | BIOS SMART hard drive failure / Unrepairable crash |
| `kb_software_install` | Software & Apps | Install error 0x80070005, Access Denied | 2 | Domain Group Policy restriction / MSI engine failure |
| `kb_critical_escalation` | Critical Escalations | Smoke, burning odor, liquid spill, supervisor | 1 | Immediate safety hazard / Direct customer demand |

---

## 2. Detailed Decision Trees

### 2.1 Wi-Fi & Internet Connectivity (`kb_network_wifi`)
```mermaid
graph TD
    Start["Caller reports Wi-Fi outage"] --> Step1["Step 1: Check router Internet/WAN lights"]
    Step1 -->|Solid Green| Step3["Step 3: Flush DNS cache ('ipconfig /flushdns')"]
    Step1 -->|Red / Blinking / Off| Step2["Step 2: 30-second router power cycle"]
    Step2 -->|Green Lights Restored| Step3
    Step2 -->|Still Red / Failed| Escalate["🚨 Tier-2 Escalation: ISP / Network Dispatch"]
    Step3 -->|Website Opens| Resolved["✅ Issue Resolved"]
    Step3 -->|Failed| Escalate
```

### 2.2 Account Lockout & Password Reset (`kb_account_password`)
```mermaid
graph TD
    Start["Caller locked out"] --> Step1["Step 1: Identify Browser vs Machine Lock Screen"]
    Step1 --> Step2["Step 2: Trigger Self-Service Reset Link to Registered Mobile"]
    Step2 -->|Consent Given| Step3["Step 3: User sets 12+ character complex password"]
    Step2 -->|No Device / Lost Phone| Escalate["🚨 Tier-2 Escalation: IAM Security Verification"]
    Step3 -->|Login Successful| Resolved["✅ Issue Resolved"]
    Step3 -->|Failed / Code Expired| Escalate
```

### 2.3 Printer & Peripheral Troubleshooting (`kb_hardware_printer`)
```mermaid
graph TD
    Start["Printer Offline / Print Stalled"] --> Step1["Step 1: Verify power & physical cable/screen status"]
    Step1 -->|Screen Ready| Step2["Step 2: Restart Windows Print Spooler service"]
    Step1 -->|Hardware Error Code / Jam| HardwareCheck["Clear paper path & inspect rollers"]
    Step2 --> Step3["Step 3: Print Windows Test Page"]
    Step3 -->|Test Page Printed| Resolved["✅ Issue Resolved"]
    Step3 -->|Nothing Prints / Error| Escalate["🚨 Tier-2 Escalation: On-Site Hardware Tech"]
```

### 2.4 OS Performance & BSOD Recovery (`kb_os_bsod_performance`)
```mermaid
graph TD
    Start["Computer Freeze / Blue Screen"] --> Step1["Step 1: Inspect Task Manager CPU/Memory usage"]
    Step1 -->|High App Usage| KillTask["End Task for rogue background process"]
    Step1 -->|System Binary Fault / BSOD| Step2["Step 2: Run 'sfc /scannow' System File Checker"]
    Step2 -->|Integrity Repaired| Resolved["✅ Issue Resolved"]
    Step2 -->|Corrupt / BSOD Loop| Escalate["🚨 Tier-2 Escalation: Desktop Engineering"]
```

### 2.5 Software Installation & Error 0x80070005 (`kb_software_install`)
```mermaid
graph TD
    Start["Installer Error 0x80070005 / Crash"] --> Step1["Step 1: Execute installer with 'Run as administrator'"]
    Step1 -->|Setup Proceeds| Resolved["✅ Issue Resolved"]
    Step1 -->|Access Denied Persists| Step2["Step 2: Purge '%temp%' installer cache directory"]
    Step2 -->|Install Completes| Resolved
    Step2 -->|Still Failed| Escalate["🚨 Tier-2 Escalation: System Administrator"]
```

### 2.6 Critical Hardware Hazards & Supervisor Demands (`kb_critical_escalation`)
```mermaid
graph TD
    Hazard["Smoke / Burning / Liquid / Supervisor Demand"] --> SafetyWarning["⚠️ Safety Warning: Unplug Power Immediately"]
    SafetyWarning --> InstantTicket["Generate CRITICAL Tier-2 Ticket"]
    InstantTicket --> LiveTransfer["Direct Transfer to Emergency Response Lead"]
```

---

## 3. General FAQ Dataset

- **Q: What are your technical support hours?**  
  **A:** Our automated AI technical support voice system is available 24 hours a day, 7 days a week. Live human engineering specialists are available 24/7 for critical incidents and 8 AM to 8 PM EST for standard tickets.
- **Q: Can I request a human support specialist at any time?**  
  **A:** Yes, you can request a human specialist at any point during this call by saying "speak with a representative" or clicking the Escalate button on your screen.
- **Q: Where can I track my support ticket status?**  
  **A:** You can view all your active tickets and call history directly in the Support Dashboard tab on this portal.
