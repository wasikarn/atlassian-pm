#!/usr/bin/env python3
"""Link all Sprint 32 issues to release 1.32.0 (version ID: 10268).

Usage:
    python3 scripts/link-sprint32-to-release.py [--dry-run]
"""

import json
import sys
import os

# Add lib path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '.claude', 'skills', 'atlassian-scripts'))

from lib.auth import create_ssl_context, load_credentials, get_auth_header
from lib.jira_api import JiraAPI, derive_jira_url

DRY_RUN = "--dry-run" in sys.argv
VERSION_ID = "10268"
EXCLUDE = {"BEP-2998"}

ISSUES = [
    "BEP-3340", "BEP-3339", "BEP-3337", "BEP-3334", "BEP-3331",
    "BEP-3319", "BEP-3318", "BEP-3313", "BEP-3312", "BEP-3311",
    "BEP-3309", "BEP-3308", "BEP-3307", "BEP-3304", "BEP-3303",
    "BEP-3301", "BEP-3300", "BEP-3299", "BEP-3298", "BEP-3297",
    "BEP-3295", "BEP-3294", "BEP-3293", "BEP-3291", "BEP-3290",
    "BEP-3289", "BEP-3288", "BEP-3287", "BEP-3286", "BEP-3280",
    "BEP-3276", "BEP-3275", "BEP-3274", "BEP-3270", "BEP-3235",
    "BEP-3230", "BEP-3219", "BEP-3218", "BEP-3211", "BEP-3198",
    "BEP-3167", "BEP-3166", "BEP-3165", "BEP-3164", "BEP-3162",
    "BEP-3161", "BEP-3157", "BEP-3156", "BEP-3124", "BEP-3089",
]

to_update = [k for k in ISSUES if k not in EXCLUDE]

print(f"{'[DRY RUN] ' if DRY_RUN else ''}Linking {len(to_update)} issues → release 1.32.0 (v{VERSION_ID})")
print(f"Skipped: {EXCLUDE & set(ISSUES) or 'none (BEP-2998 not in Sprint 32)'}\n")

if DRY_RUN:
    for key in to_update:
        print(f"  Would update: {key}")
    sys.exit(0)

creds = load_credentials()
api = JiraAPI(
    base_url=derive_jira_url(creds["CONFLUENCE_URL"]),
    auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
    ssl_context=create_ssl_context(),
)

ok, fail = [], []
for key in to_update:
    try:
        api._request("PUT", f"/rest/api/3/issue/{key}", {
            "fields": {
                "fixVersions": [{"id": VERSION_ID}]
            }
        })
        print(f"  ✓ {key}")
        ok.append(key)
    except Exception as e:
        print(f"  ✗ {key}: {e}")
        fail.append(key)

print(f"\nDone: {len(ok)} ok, {len(fail)} failed")
if fail:
    print(f"Failed: {fail}")
