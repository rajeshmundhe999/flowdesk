# Knowledge Base: Non-QWERTY Layout (AZERTY, QWERTZ, Dvorak) Text Insertion

## Symptom
When dictating on non-QWERTY keyboard layouts (French AZERTY, German QWERTZ, Dvorak), inserted characters are swapped (e.g. `A` becomes `Q`, `Z` becomes `W`) or punctuation marks are garbled.

## Cause
The keystroke simulation driver generates scan codes or virtual key codes mapped to the standard US-QWERTY hardware matrix rather than passing unicode character events via `KEYEVENTF_UNICODE`.

## Fix
1. In FlowDesk **Settings > Insertion Mode**, change from **Direct Keystroke Simulation** to **Unicode Clipboard Injection**.
2. Or use the shortcut **Ctrl+Shift+V** (or **Cmd+Shift+V**) to paste the unformatted unicode text directly from clipboard history.
3. Verify that your operating system language bar matches your physical keyboard.

## Data Safety
Your dictated text is transcribed accurately in memory and preserved in FlowDesk history; the corruption only occurs during physical keycode translation into the foreground window.

## Escalation Criteria
Escalate to Client Platform team if Unicode Clipboard Injection mode still produces garbled text in non-English layouts.
