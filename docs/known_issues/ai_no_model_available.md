# Knowledge Base: "No Model Available" Error

## Symptom
Pressing the dictation hotkey displays a modal alert: `"No Model Available for current language/tier"`. Dictation cannot begin.

## Cause
The client requested an inference model endpoint that is either de-provisioned, undergoing rolling restart, or the user's language selection has not been assigned a warm worker in that cloud region.

## Fix
1. Verify the selected language in **Settings > General > Dictation Language** is set to a supported language (e.g. English US/UK).
2. Click **Settings > Account > Refresh Entitlements** to force-sync account tier and model permissions.
3. Completely quit FlowDesk from the system tray/menu bar and relaunch.

## Data Safety
No audio recording was created, and no user data or draft text was affected.

## Escalation Criteria
**P0 Incident**: If 3 or more users report this error across different accounts, trigger immediate P0 escalation to Machine Learning Platform on-call.
