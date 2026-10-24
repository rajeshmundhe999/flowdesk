# Knowledge Base: Text Not Pasting After Dictation

## Symptom
Dictation completes successfully and transcript text appears in the FlowDesk floating preview pill, but no text is pasted into the active application (Slack, Notion, Word, browser).

## Cause
On macOS, operating system Accessibility permission has become stale or desynchronized after an OS update. On Windows, target window runs as Administrator (UAC boundary) while FlowDesk is running as standard user.

## Fix
**macOS**:
1. Open **System Settings > Privacy & Security > Accessibility**.
2. Toggle FlowDesk **OFF**, then click the minus (`-`) button to remove it.
3. Re-launch FlowDesk and click **Grant Accessibility Permission** when prompted.

**Windows**:
1. If pasting into an elevated command prompt or Admin app, right-click FlowDesk and select **Run as Administrator**.
2. Or use **Settings > Insertion > Fallback to Clipboard (Ctrl+V)**.

## Data Safety
Your transcription was successfully generated and saved in FlowDesk local history. You can open **FlowDesk History** to manually copy any generated snippet.

## Escalation Criteria
Escalate if Accessibility permissions are confirmed valid via `tccutil` and synthetic keystroke injection still fails across all applications.
