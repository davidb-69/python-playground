"""
One-time migration: import applications.json into Supabase.
Run once: python migrate.py
"""
import json
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

with open("applications.json") as f:
    apps = json.load(f)

records = []
for app in apps:
    records.append({
        "company": app["company"],
        "role": app["role"],
        "date_applied": app["date_applied"],
        "interview_date": app["interview_date"] if app.get("interview_date") else None,
        "status": app["status"],
        "recruiter": app.get("recruiter") or None,
        "notes": app.get("notes") or None,
    })

if records:
    result = sb.table("applications").insert(records).execute()
    print(f"Migrated {len(result.data)} applications.")
else:
    print("No applications found in applications.json.")
