# Knowledge Base: Microphone and Bluetooth Device Switching

## Symptom
Audio input switches unexpectedly between USB microphones and Bluetooth headsets mid-dictation, or audio quality degrades drastically into mono "Hands-Free AG Audio" mode.

## Cause
Windows Audio Service (WASAPI) or macOS CoreAudio switches the default communication device when a headset connects or reconnects. Dual-channel Bluetooth headsets switch from stereo A2DP to low-bitrate bidirectional HFP profile when the microphone is engaged.

## Fix
1. In FlowDesk **Settings > Audio > Input Device**, change from **System Default** to your specific dedicated microphone (e.g. "USB Blue Yeti Microphone").
2. On Windows: Open **Settings > Sound > More sound settings**, locate the Bluetooth headset Hands-Free device under Recording, right-click and choose **Disable** if you only want to use an external desk mic.
3. Restart FlowDesk.

## Data Safety
Any audio snippet degraded by device switching is safely discarded if quality falls below transcription confidence threshold; no partial recordings are exposed.

## Escalation Criteria
Escalate to Audio team if WASAPI throws `AUDCLNT_E_UNSUPPORTED_FORMAT` when connecting to standard 48kHz audio interfaces.
