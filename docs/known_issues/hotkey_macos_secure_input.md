# Knowledge Base: Hotkey Conflicts and macOS Secure Keyboard Entry

## Symptom
Global dictation hotkey (e.g., `Option+Space`) stops responding when Terminal, iTerm2, 1Password, Bitwarden, or a macOS password dialogue is focused.

## Cause
macOS security feature `Secure Keyboard Entry` (`EnableSecureEventInput`) intentionally disables global `CGEventTap` hotkey listeners while sensitive input is active to prevent malware from logging keystrokes.

## Fix
1. In Terminal or iTerm2, click the application menu in the top menu bar (e.g., **Terminal** or **iTerm2**) and uncheck **Secure Keyboard Entry**.
2. If inside a password manager or login prompt, complete the authentication or click away from the password input field.
3. In FlowDesk, open **Settings > Shortcuts** and assign an alternate secondary trigger (e.g., Double-tap Left Control).

## Data Safety
This is an OS-enforced security isolation boundary. None of your keystrokes or audio buffers are captured while Secure Input is active.

## Escalation Criteria
Escalate to Client Platform team if Secure Keyboard Entry remains locked globally even after closing all terminal and password manager applications (indicates orphaned `loginwindow` lock).
