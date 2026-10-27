# Police Records Request Bot

Emails a California Public Records Act request to LAPD and LASD on the 1st of every month, asking for all tort claims filed during the previous calendar month.

- Sends from `luke.harold89@gmail.com` via Gmail SMTP (App Password)
- Runs on GitHub Actions: `0 16 1 * *` (9am PDT / 8am PST on the 1st)
- Every sent request is logged in `sent_log.csv` and committed, so a month is never sent twice

## Setup

1. Add the `GMAIL_APP_PASSWORD` repo secret
2. Run the workflow manually with "dry run" checked to preview

## Local preview

```bash
python3 request.py --dry-run
python3 request.py --dry-run --date 2026-12-01
```
