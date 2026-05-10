# Security policy

## Reporting a vulnerability

If you find a security issue in Datachat, please **do not** open a public GitHub issue.

Instead, report it privately by opening a [GitHub Security Advisory](https://github.com/gazerlabs/datachat/security/advisories/new) on this repository. We aim to acknowledge reports within 3 business days and to provide a fix or mitigation timeline within 14 days.

We're a small team — please be patient and don't share PoCs publicly until we've had a chance to ship a fix.

## Scope

The OSS code in this repository is in scope. Issues affecting the hosted service at https://datachat.gazerlabs.com that are not present in the public code (e.g. infrastructure misconfigurations specific to Gazer Labs's deployment) should also be reported through the same channel.

## Out of scope

- Issues in third-party services (Anthropic, Clerk, Stripe, Resend, MotherDuck, etc.). Report those to the upstream vendor.
- Denial of service through resource exhaustion of unconfigured rate limits.
- Vulnerabilities that require a malicious admin to be already authenticated as admin on the same instance.

## Hosted service

For privacy and security details about Gazer Labs's hosted version of Datachat, see the [Security & Privacy page](https://datachat.gazerlabs.com/security).
