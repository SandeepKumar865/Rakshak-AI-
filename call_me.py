"""
Rakshak AI — Outbound Call Trigger
Initiates an automated voice call from your Twilio number to your target mobile.
Uses environment credentials from .env and config.py.

Usage:
    python call_me.py
    python call_me.py --to +919876543210
"""

import sys
import argparse
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_PHONE_NUMBER,
    DEMO_TO_NUMBER,
    BASE_URL,
    mask_phone,
)


def make_outbound_call(to_number: str = None, from_number: str = None, base_url: str = None):
    to_phone = to_number or DEMO_TO_NUMBER
    from_phone = from_number or TWILIO_PHONE_NUMBER
    url_base = (base_url or BASE_URL).rstrip("/")

    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print("[ERROR] Twilio credentials missing! Please configure TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env")
        sys.exit(1)

    if not to_phone or not from_phone:
        print("[ERROR] Phone numbers missing! Please configure TWILIO_PHONE_NUMBER and DEMO_TO_NUMBER in .env")
        sys.exit(1)

    print("=" * 60)
    print("  Rakshak AI — Initiating Outbound Demo Call")
    print("=" * 60)
    print(f"  Destination (Caller) : {mask_phone(to_phone)}")
    print(f"  Caller ID (Twilio)   : {mask_phone(from_phone)}")
    print(f"  Webhook URL          : {url_base}/incoming-call")
    print("=" * 60)

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        call = client.calls.create(
            to=to_phone,
            from_=from_phone,
            url=f"{url_base}/incoming-call",
            method="POST",
        )
        print("  [SUCCESS] Call dispatched successfully!")
        print(f"  Call SID  : {call.sid}")
        print(f"  Status    : {call.status}")
        print("=" * 60)
        print("  Your phone should ring in a few moments.")
        print("  Pick up and follow the voice instructions!")
        print("=" * 60)
        return call.sid

    except TwilioRestException as e:
        print(f"  [TWILIO API ERROR] Code {e.code}: {e.msg}")
        if e.code in (21216, 21608):
            print("\n  [TRIAL ACCOUNT NOTICE]")
            print(f"  The destination number {mask_phone(to_phone)} is unverified on your Twilio Trial account.")
            print("  To verify it, visit Twilio Console:")
            print("  https://console.twilio.com/us1/develop/phone-numbers/manage/verified")
            print("  Once verified, re-run this script.")
        elif e.code == 20003:
            print("\n  [AUTH ERROR] Authentication failed. Please verify TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.")
        sys.exit(1)

    except Exception as e:
        print(f"  [UNEXPECTED ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger an outbound Rakshak AI demo call.")
    parser.add_argument("--to", help="Destination phone number (E.164 format, e.g. +919876543210)")
    parser.add_argument("--from-num", help="Twilio phone number (E.164 format, e.g. +1234567890)")
    parser.add_argument("--base-url", help="Public webhook base URL (e.g. https://xxx.trycloudflare.com)")
    args = parser.parse_args()

    make_outbound_call(to_number=args.to, from_number=args.from_num, base_url=args.base_url)
