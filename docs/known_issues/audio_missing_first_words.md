# Knowledge Base: Missing First Words in Transcripts

## Symptom
When dictating using wireless Bluetooth earbuds or headsets (Apple AirPods, Sony WH-1000XM, Bose QC45), the initial 1-3 words of speech are completely omitted from the final transcript.

## Cause
Bluetooth Low Energy / Hands-Free Profile (HFP) hardware power-saving puts the microphone into standby. When the hotkey is triggered, the OS takes 300-500ms to wake up the SCO audio channel, during which early audio frames are dropped.

## Fix
1. In **Settings > Audio > Bluetooth Options**, enable **Pre-roll Audio Keepalive** (keeps the Bluetooth mic channel warm).
2. As an immediate operational workaround, pause for half a second after pressing the hotkey before speaking your first word.
3. Test using your computer's built-in microphone in **Settings > Audio Input** to confirm the transcription engine itself captures full speech.

## Data Safety
Your speech data is only captured while the hotkey is engaged and is securely transmitted over TLS. No audio is recorded during idle periods.

## Escalation Criteria
Escalate to Audio Engineering if the issue reproduces on wired USB microphones or built-in hardware mics.
