# Knowledge Base: Login and Captcha Verification Loops

## Symptom
User completes Google SSO or email authentication with Cloudflare Turnstile captcha checkmark, but browser redirects back to the login page or reports `"state_mismatch"` error.

## Cause
Browser third-party cookie blocking, aggressive ad-blocking extensions (uBlock Origin, Privacy Badger), or browser clocks out of sync by more than 60 seconds with NTP servers.

## Fix
1. Ensure your computer's system date, time, and timezone are synchronized via automatic internet time.
2. Disable ad-blocking extensions on `app.flowdesk.com` or open login in an Incognito / Private window without extensions.
3. In Chrome/Brave/Edge, allow third-party cookies for the authentication domain.
4. If logging into desktop app, copy the manual authorization code token from the browser page and paste it into FlowDesk.

## Data Safety
Your account credentials and SSO tokens remain protected via PKCE OAuth 2.0 flow. No unauthorized access occurs during redirection loops.

## Escalation Criteria
Escalate to Identity & Auth team if `state_mismatch` persists across multiple clean browser profiles (suggests OAuth redis session cluster desynchronization).
