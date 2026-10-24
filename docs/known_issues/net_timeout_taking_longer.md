# Knowledge Base: "Taking Longer Than Usual" Dictation Timeouts

## Symptom
Floating recording pill spins for 10-15 seconds displaying `"Taking longer than usual..."` before either erroring out with `"Request Aborted"` or eventually pasting text after substantial delay.

## Cause
Elevated network latency (>800ms round-trip), packet loss exceeding 5%, or temporary transcription worker queue saturation on the inference cluster.

## Fix
1. Test your network latency to the cloud endpoint using the local diagnostic utility (`python diagnose.py`).
2. Switch network from Wi-Fi to a wired Ethernet or alternate Wi-Fi hotspot if latency exceeds 300ms.
3. In **Settings > Advanced > Network**, toggle **Enable Low-Latency Streaming Chunking**.
4. Restart the desktop app.

## Data Safety
Your dictated text is preserved in local history even if the real-time cloud return timed out. You can access recent drafts in **Menu > Dictation History**.

## Escalation Criteria
Escalate to Infrastructure / SRE on-call if 5+ independent users report the issue across distinct ISPs within a 30-minute window (indicates regional worker backlog).
