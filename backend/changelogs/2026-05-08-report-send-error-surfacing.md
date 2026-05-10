---
title: Surface real error when a report email fails to send
date: 2026-05-08
version: '0.11.1'
tags: [fix]
---
When the email provider rejects a report send (e.g. an unverified sender domain), the Reports page now shows the actual error message instead of a generic "Cannot connect to backend" toast.
