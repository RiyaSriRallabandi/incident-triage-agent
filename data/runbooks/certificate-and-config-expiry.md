# Certificate or credential expiry

## Symptoms

A sudden, total failure that starts at a round wall-clock time with no deploy and
no traffic change. Errors mention an expired certificate, an invalid or expired
token, a signature failure, or an authentication rejection. Often affects every
request on a path at once, and may hit several services that share the same
certificate or credential.

## Likely causes

- A TLS certificate reached its expiry date and was not renewed or not reloaded
  after renewal.
- A signing key, API token, or service-account credential expired or was rotated
  without updating all consumers.
- A trust bundle or intermediate certificate changed.
- A time-skewed host rejecting otherwise-valid certificates.

## How to confirm

- Check the expiry date of the certificate or credential in use and compare it to
  the incident start time; an exact match is conclusive.
- Verify whether a renewal happened but the process did not reload it.
- Confirm host clocks are correct.

## Mitigation

Install and reload the renewed certificate or credential. If renewal is not ready,
issue a short-lived one. Afterwards, monitor expiry dates with alerting well
ahead of the deadline, automate renewal and reload, and stagger expiry across
services.

## References

- Google SRE Book, "Practical Alerting" and "Being On-Call": https://sre.google/books/
