# Knowledge Base: Billing Word-Limit Not Resetting After Payment

## Symptom
Account shows `"Monthly word limit exceeded: 0 words remaining"` even after successfully upgrading to Pro / Enterprise tier or after the monthly billing renewal date.

## Cause
Stripe / Apple In-App Purchase webhook delay, or Redis entitlement cache TTL lagging behind payment settlement.

## Fix
1. Log into your dashboard at `app.flowdesk.com/account/billing` and verify the invoice status is **Paid**.
2. In the desktop application, click **Settings > Account > Refresh Entitlements** to force an instant cache invalidation with the billing API.
3. If using team seats, verify the team administrator has assigned a seat license to your specific email address.

## Data Safety
Your account history, custom vocabulary, and stored shortcuts are completely secure. No account data is removed when a word limit cap is reached.

## Escalation Criteria
Escalate to Billing Ops if invoice shows paid in Stripe dashboard but backend entitlement status has not updated within 15 minutes of payment confirmation.
