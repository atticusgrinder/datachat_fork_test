---
title: Demo CSV on signup, three-tier pricing, self-host vs cloud UI split
date: 2026-05-09
version: '0.14.0'
tags: [feature, improvement]
---
New users now land in chat with both the Demo: RetailFlow warehouse AND a Demo: Marketing Spend CSV pre-loaded into their local DuckDB — two different shapes of demo data side-by-side. Both demos are dismissable from Settings; once dismissed, they don't reappear on next login. Pricing rolled up into three tiers (Self-host / Cloud $299 / Enterprise) with the Self-host option pointing at the open-source GitHub repo. Plan/upgrade UI in Settings is now hidden when billing isn't configured (driven by Stripe key presence, with a `BILLING_ENABLED` env override). The standalone onboarding flow is gone; sign-up routes directly to chat. Default theme is Midnight Ocean.
