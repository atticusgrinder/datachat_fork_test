# Screenshots

Place page screenshots here. The main repo `README.md` references them by filename, so once you drop a PNG in this folder it'll render automatically.

## Capture conventions

- **Format:** PNG, browser zoom at 100%.
- **Theme:** dark (`midnight-ocean` is the default new-user theme — it's the most photogenic).
- **Window size:** 1440×900 viewport is a good baseline; 1920×1080 also works.
- **Trim chrome:** crop to the app surface (no browser address bar / OS chrome).
- **Realistic data:** use the auto-attached "Demo: RetailFlow" warehouse so charts have shape — empty states are honest but boring.
- **Naming:** kebab-case, one file per page. See the list below.

## Pages

Capture these routes from the running app and save under the listed filename:

| Route                | Filename                | Notes                                                                  |
|----------------------|-------------------------|------------------------------------------------------------------------|
| `/chat`              | `chat.png`              | Hero shot — show a real conversation with an inline chart rendered.    |
| `/chat`              | `chat-empty.png`        | (Optional) new-conversation state with the input prompt.               |
| `/dashboard`         | `dashboard.png`         | Warehouse + uploads overview.                                          |
| `/reports`           | `reports.png`           | Reports list with at least 2 reports visible.                          |
| `/reports/:id`       | `report-detail.png`     | Report with multiple visualizations + the schedule panel.              |
| `/context`           | `context.png`           | Context file editor with a few entries (user-authored + dbt-synced).   |
| `/settings`          | `settings.png`          | Scroll to make Teammates section visible.                              |
| `/usage`             | `usage.png`             | Usage banner + history table.                                          |
| `/admin`             | `admin.png`             | (Admin users only.)                                                    |
| `/pricing`           | `pricing.png`           | Self-hosters with no Stripe will see the upgrade buttons disabled.     |
| `/changelog`         | `changelog.png`         | Latest entries.                                                        |
| `/sign-in`           | `sign-in.png`           | Clerk-provided form.                                                   |
| `/sign-up`           | `sign-up.png`           | Clerk-provided form.                                                   |

## Updating the README

The main `README.md` has a **Screenshots** section that uses the filenames above. If you add or rename one, update the references there too.
