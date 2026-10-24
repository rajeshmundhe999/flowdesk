# Knowledge Base: Connection Lost behind VPN, Proxy, or Firewall

## Symptom
Users encounter an instant or intermittent popup: `"Connection lost: ERR_PROXY_CONNECTION_FAILED"` or `"ERR_TUNNEL_CONNECTION_FAILED"` when connected to enterprise networks (Zscaler, Cisco AnyConnect, Palo Alto GlobalProtect, BlueCoat).

## Cause
Enterprise security software decrypts and re-encrypts SSL traffic (deep packet inspection) using a private corporate Certificate Authority (CA) or requires HTTP proxy authentication (port 8080) for outbound WebSockets. FlowDesk's networking stack does not find the custom corporate root certificate in its local trust bundle.

## Fix
1. Add an SSL bypass rule in your corporate proxy/firewall policy for destination `*.flowdesk-dictation.internal` and WebSocket port 443.
2. In FlowDesk, open **Settings > Network > Enterprise CA Certificates**, click **Import CA Bundle**, and select your company's `.pem`/`.crt` root certificate.
3. Restart FlowDesk.

## Data Safety
Your recorded voice snippets and transcripts are not lost; any failed audio buffer is retained in the local encrypted cache for 24 hours. No audio was transmitted unencrypted.

## Escalation Criteria
Escalate to Tier 3 / Network Engineering if the customer has confirmed proxy bypass is active and the diagnostic tool reports TLS handshake failure with `CERT_UNTRUSTED_ISSUER`.
