import csv
import os
import smtplib
import sys
from datetime import date, datetime, timedelta
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path
from zoneinfo import ZoneInfo

from agencies import AGENCIES

SEND_FROM          = "luke.harold89@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
LOG_FILE           = Path(__file__).parent / "sent_log.csv"
LOG_FIELDS         = ["period", "agency", "to", "subject", "sent_at", "message_id"]


def previous_month(today):
    last_day  = today.replace(day=1) - timedelta(days=1)
    first_day = last_day.replace(day=1)
    return first_day, last_day


# AP-style month abbreviations, e.g. "Oct. 1-31"
AP_MONTHS = ["Jan.", "Feb.", "March", "April", "May", "June",
             "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]


def build_request(agency, first_day, last_day):
    dates   = f"{AP_MONTHS[first_day.month - 1]} {first_day.day}-{last_day.day}"
    subject = f"Public Records Act Request: {agency['key']} Tort Claims, {dates}, {first_day.year}"

    body = f"""Hi,

Pursuant to the California Public Records Act, I am requesting copies of all tort claims filed against {agency['agency']} during the period of {dates}, in which the claimant alleges personal injury, wrongful death, excessive force, false arrest or imprisonment, civil rights violations, or other tortious conduct by {agency['key']} personnel.

I am requesting the actual claim forms themselves, not a log or summary of claims. Please also include any attachments referenced in or submitted with each claim form, including any documents incorporated by reference under fields describing the nature of the incident or damages.

Thank you for your assistance.

Luke Harold
"""
    return subject, body


def load_log():
    if not LOG_FILE.exists():
        return []
    with LOG_FILE.open(newline="") as f:
        return list(csv.DictReader(f))


def append_log(row):
    new = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(row)


def send_email(to, subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"]    = subject
    msg["From"]       = SEND_FROM
    msg["To"]         = to
    msg["Date"]       = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="gmail.com")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SEND_FROM, GMAIL_APP_PASSWORD)
        server.sendmail(SEND_FROM, [to], msg.as_string())
    return msg["Message-ID"]


def check_login():
    if not GMAIL_APP_PASSWORD:
        sys.exit("Login check failed: GMAIL_APP_PASSWORD is empty")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SEND_FROM, GMAIL_APP_PASSWORD)
    except smtplib.SMTPAuthenticationError as e:
        sys.exit(f"Login check failed: Gmail rejected the app password - {e}")
    print(f"Login check passed: Gmail accepted the app password for {SEND_FROM}. Nothing was sent.")


def main():
    if "--check-login" in sys.argv:
        check_login()
        return

    dry_run = "--dry-run" in sys.argv

    today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    if "--date" in sys.argv:
        today = date.fromisoformat(sys.argv[sys.argv.index("--date") + 1])

    first_day, last_day = previous_month(today)
    period = first_day.strftime("%Y-%m")
    already_sent = {(r["period"], r["agency"]) for r in load_log()}

    if not dry_run:
        placeholders = [a["key"] for a in AGENCIES if "REPLACE_ME" in a["to"]]
        if placeholders:
            sys.exit(f"Refusing to send: fill in the 'to' address in agencies.py for {', '.join(placeholders)}")
        if not GMAIL_APP_PASSWORD:
            sys.exit("Refusing to send: GMAIL_APP_PASSWORD is empty")

    failures = 0
    for agency in AGENCIES:
        if (period, agency["key"]) in already_sent:
            print(f"{agency['key']}: request for {period} already sent, skipping")
            continue

        subject, body = build_request(agency, first_day, last_day)

        if dry_run:
            print(f"--- DRY RUN: {agency['key']} -> {agency['to']}")
            print(f"Subject: {subject}\n\n{body}")
            continue

        try:
            message_id = send_email(agency["to"], subject, body)
        except Exception as e:
            failures += 1
            print(f"{agency['key']}: FAILED to send - {e}")
            continue

        append_log({
            "period":     period,
            "agency":     agency["key"],
            "to":         agency["to"],
            "subject":    subject,
            "sent_at":    datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(timespec="seconds"),
            "message_id": message_id,
        })
        print(f"{agency['key']}: sent to {agency['to']} - {subject}")

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
