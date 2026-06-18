#!/usr/bin/env python3
"""Instagram access token exchange and refresh utility.

This script exchanges a short-lived user access token for a long-lived (60-day)
access token, validates it against the Meta Graph API, and automatically updates
the appropriate variable in the local .env file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import urllib.parse
import urllib.request
from typing import Any


def load_env_vars(env_path: str) -> dict[str, str]:
    """Parse a simple .env file into a dictionary."""
    vars_dict = {}
    if not os.path.exists(env_path):
        return vars_dict
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                # Strip quotes if present
                val = val.strip().strip("'\"")
                vars_dict[key.strip()] = val
    return vars_dict


def exchange_token(app_id: str, app_secret: str, short_lived_token: str) -> dict[str, Any]:
    """Exchange a short-lived user token for a long-lived access token."""
    url = "https://graph.facebook.com/v19.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_lived_token,
    }
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"

    print(f"Requesting token exchange from Meta Graph API...")
    try:
        req = urllib.request.Request(full_url, method="GET")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            err_json = json.loads(error_body)
            err_msg = err_json.get("error", {}).get("message", error_body)
        except Exception:
            err_msg = error_body
        raise RuntimeError(f"Meta API error: {err_msg}") from e
    except Exception as e:
        raise RuntimeError(f"Connection failed: {e}") from e


def validate_token(access_token: str, business_account_id: str | None = None) -> tuple[bool, str]:
    """Validate token viability and permissions by querying Meta API."""
    url = f"https://graph.facebook.com/v19.0/me"
    if business_account_id:
        url = f"https://graph.facebook.com/v19.0/{business_account_id}"

    params = {"access_token": access_token}
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"

    try:
        req = urllib.request.Request(full_url, method="GET")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            account_name = data.get("name", "Unknown Account")
            account_id = data.get("id", "Unknown ID")
            return True, f"Token is VALID. Connected to: {account_name} (ID: {account_id})"
    except Exception as e:
        return False, f"Token validation failed: {e}"


def update_env_file(env_path: str, key: str, value: str) -> bool:
    """Safely update a value in the .env file, making a backup first."""
    if not os.path.exists(env_path):
        print(f"Error: .env file not found at {env_path}", file=sys.stderr)
        return False

    # Create backup
    backup_path = f"{env_path}.bak"
    try:
        shutil.copy2(env_path, backup_path)
        print(f"Backup of current .env file created at: {backup_path}")
    except Exception as e:
        print(f"Warning: Failed to create .env backup: {e}", file=sys.stderr)

    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Regex pattern matching the KEY=val line (handles quotes and whitespace)
    pattern = re.compile(rf"^({key}\s*=\s*['\"]?).*?(['\"]?\s*)$", re.MULTILINE)

    if pattern.search(content):
        new_content = pattern.sub(rf"\1{value}\2", content)
        print(f"Updated existing environment variable: {key}")
    else:
        new_content = content.rstrip() + f"\n{key}={value}\n"
        print(f"Appended new environment variable: {key}")

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Exchange/refresh Instagram access token.")
    parser.add_argument(
        "--account",
        choices=["gallery", "photography"],
        help="Account to update ('gallery' for Account 1, 'photography' for Account 2)",
    )
    parser.add_argument(
        "--token",
        help="Short-lived user access token to exchange (prompts if omitted)",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to the .env file to update (default: .env)",
    )
    args = parser.parse_args()

    # Load defaults from .env
    env_vars = load_env_vars(args.env_file)

    print("=== Instagram Token Exchange Tool ===")
    
    # 1. Resolve Account Type
    account = args.account
    if not account:
        print("\nWhich account would you like to update?")
        print("1) Account 1 (Gallery)     -> INSTAGRAM__ACCESS_TOKEN")
        print("2) Account 2 (Photography) -> INSTAGRAM_ACC2__ACCESS_TOKEN (Expired in your Celery logs)")
        choice = input("Select option (1 or 2, default 2): ").strip()
        account = "gallery" if choice == "1" else "photography"

    env_var_key = "INSTAGRAM__ACCESS_TOKEN" if account == "gallery" else "INSTAGRAM_ACC2__ACCESS_TOKEN"
    bus_acct_key = "INSTAGRAM__BUSINESS_ACCOUNT_ID" if account == "gallery" else "INSTAGRAM_ACC2__BUSINESS_ACCOUNT_ID"

    # 2. Get App Credentials
    app_id = env_vars.get("INSTAGRAM__APP_ID")
    app_secret = env_vars.get("INSTAGRAM__APP_SECRET")
    business_account_id = env_vars.get(bus_acct_key)

    if not app_id or not app_secret:
        print("\nError: INSTAGRAM__APP_ID and INSTAGRAM__APP_SECRET must be configured in your .env file.", file=sys.stderr)
        sys.exit(1)

    print(f"\nConfiguration detected:")
    print(f"  App ID: {app_id}")
    print(f"  Target Key: {env_var_key}")
    print(f"  Business Account ID: {business_account_id or 'Not configured'}")

    # 3. Get Short-lived Token
    short_token = args.token
    if not short_token:
        print("\nTo generate a short-lived token:")
        print("1. Go to the Meta App Dashboard > Tools > Graph API Explorer.")
        print("2. Select your App, User Token, and ensure these permissions are granted:")
        print("   instagram_basic, instagram_content_publish, pages_read_engagement, pages_show_list")
        print("3. Copy the Access Token.")
        short_token = input("\nEnter the short-lived access token: ").strip()

    if not short_token:
        print("Error: Access token cannot be empty.", file=sys.stderr)
        sys.exit(1)

    # 4. Exchange Token
    try:
        res = exchange_token(app_id, app_secret, short_token)
        long_lived_token = res.get("access_token")
        expires_in = res.get("expires_in", 0)
        days = round(expires_in / 86400, 1) if expires_in else 60

        if not long_lived_token:
            print("Error: Exchange response did not contain an access_token.", file=sys.stderr)
            sys.exit(1)

        print(f"\nSuccessfully exchanged token! (Expires in ~{days} days)")

        # 5. Validate the New Token
        print("Validating new access token with Meta API...")
        valid, msg = validate_token(long_lived_token, business_account_id)
        if valid:
            print(f"  [SUCCESS] {msg}")
        else:
            print(f"  [WARNING] {msg}")
            confirm = input("The token failed validation. Do you still want to write it to .env? (y/n, default n): ").strip().lower()
            if confirm != "y":
                print("Aborted.")
                sys.exit(1)

        # 6. Update .env
        success = update_env_file(args.env_file, env_var_key, long_lived_token)
        if success:
            print(f"\n[SUCCESS] Updated {env_var_key} in {args.env_file} successfully!")
            print("Please restart your FastAPI and Celery processes to load the new token configuration.")
        else:
            print(f"\n[ERROR] Failed to update {args.env_file}.", file=sys.stderr)

    except Exception as e:
        print(f"\n[FAILURE] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
