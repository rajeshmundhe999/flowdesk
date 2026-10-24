# Knowledge Base: Android Work Profile and MDM Sandbox Isolation

## Symptom
On Android devices managed by enterprise MDM (Samsung Knox, Microsoft Intune, Google Workspace), dictation fails with `"AudioRecord permission denied"` or transcribed text cannot be pasted into managed corporate applications (Outlook, Teams, Slack).

## Cause
Mobile Device Management (MDM) security policies isolate hardware sensors (Microphone) and prevent cross-profile clipboard sharing between personal and work containers to protect confidential corporate data.

## Fix
1. Install FlowDesk directly inside the **Work Profile** (via the managed Google Play store) rather than the Personal space.
2. Ask your corporate IT administrator to whitelist FlowDesk in Microsoft Intune or Knox policy under **Permitted Audio Input Applications**.
3. In Intune app protection policy, enable **Allow paste between managed and personal apps** if personal dictation is required.

## Data Safety
Corporate data is protected in compliance with enterprise MDM sandboxing rules. No enterprise documents or clipboard contents are leaked across container boundaries.

## Escalation Criteria
Escalate to Mobile Enterprise Support if FlowDesk is installed inside the managed work profile container with microphone permission explicitly granted by MDM, but Android still returns `SecurityException`.
