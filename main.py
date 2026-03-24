import base64
import csv
import io
import os
from datetime import date

from dotenv import load_dotenv
from supabase import create_client, Client
import streamlit as st

load_dotenv()

def get_secret(key: str) -> str:
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.environ[key]

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
APP_PASSWORD = get_secret("APP_PASSWORD")

STATUSES = ["Applied", "Initial Screening", "Interview", "Offer", "Rejected", "Withdrawn"]

STATUS_COLORS = {
    "Applied": "#4A90D9",
    "Initial Screening": "#9B59B6",
    "Interview": "#F39C12",
    "Offer": "#27AE60",
    "Rejected": "#E74C3C",
    "Withdrawn": "#95A5A6",
}

# Staleness only applies when status hasn't progressed beyond Applied
STALE_STATUSES = {"Applied"}


# ── Supabase client ────────────────────────────────────────────────────────────

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ── Data helpers ───────────────────────────────────────────────────────────────

def load_data():
    sb = get_supabase()
    result = sb.table("applications").select("*").order("created_at").execute()
    return result.data


def add_application(record: dict):
    sb = get_supabase()
    sb.table("applications").insert(record).execute()


def update_application(app_id: str, updates: dict):
    sb = get_supabase()
    sb.table("applications").update(updates).eq("id", app_id).execute()


def delete_application(app_id: str):
    sb = get_supabase()
    sb.table("applications").delete().eq("id", app_id).execute()


def days_since(date_str):
    try:
        return (date.today() - date.fromisoformat(date_str)).days
    except (ValueError, TypeError):
        return None


# ── UI helpers ─────────────────────────────────────────────────────────────────

def status_badge(status):
    color = STATUS_COLORS.get(status, "#888")
    return (
        f'<span style="background:{color};color:white;padding:2px 10px;'
        f'border-radius:12px;font-size:0.8em;font-weight:600">{status}</span>'
    )


def staleness_style(app):
    """Return a left-border CSS style based on recency, only for stale statuses."""
    if app["status"] not in STALE_STATUSES:
        return ""
    days = days_since(app["date_applied"])
    if days is None:
        return ""
    if days <= 7:
        color = "#27AE60"   # green
    elif days <= 14:
        color = "#F39C12"   # amber
    else:
        color = "#E74C3C"   # red
    return f"border-left: 4px solid {color}; padding-left: 6px;"


# ── Export helpers ─────────────────────────────────────────────────────────────

def build_csv(apps) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Company", "Role", "Date Applied", "Interview Date", "Days", "Status", "Recruiter", "Notes"])
    for app in apps:
        days = days_since(app["date_applied"])
        writer.writerow([
            app["company"],
            app["role"],
            app["date_applied"],
            app.get("interview_date") or "",
            str(days) if days is not None else "",
            app["status"],
            app.get("recruiter") or "",
            app.get("notes") or "",
        ])
    return buf.getvalue().encode()


def build_print_html(apps) -> str:
    rows_html = ""
    for app in apps:
        days = days_since(app["date_applied"])
        color = STATUS_COLORS.get(app["status"], "#888")
        notes_escaped = (app.get("notes") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rows_html += (
            f"<tr>"
            f"<td>{app['company']}</td>"
            f"<td>{app['role']}</td>"
            f"<td>{app['date_applied']}</td>"
            f"<td>{app.get('interview_date') or '—'}</td>"
            f"<td style='text-align:center'>{str(days) if days is not None else '—'}</td>"
            f"<td><span class='badge' style='background:{color}'>{app['status']}</span></td>"
            f"<td>{app.get('recruiter') or ''}</td>"
            f"<td class='notes'>{notes_escaped}</td>"
            f"</tr>\n"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Job Applications Export</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            font-size: 12px; color: #111; padding: 24px; background: #fff; }}
    h1 {{ font-size: 1.4rem; font-weight: 700; margin-bottom: 4px; }}
    .meta {{ color: #666; font-size: 0.82rem; margin-bottom: 20px; }}
    table {{ border-collapse: collapse; width: 100%; table-layout: auto; }}
    thead th {{ background: #f4f4f4; padding: 7px 10px; text-align: left;
                font-size: 10px; font-weight: 700; text-transform: uppercase;
                letter-spacing: 0.06em; border-bottom: 2px solid #ccc; white-space: nowrap; }}
    tbody td {{ padding: 7px 10px; border-bottom: 1px solid #e8e8e8; vertical-align: top; }}
    tbody tr:nth-child(even) {{ background: #fafafa; }}
    .badge {{ display: inline-block; color: #fff; padding: 2px 8px;
              border-radius: 10px; font-size: 10px; font-weight: 600; white-space: nowrap; }}
    .notes {{ max-width: 180px; font-size: 11px; color: #444; word-break: break-word; }}
    .print-btn {{ display: inline-block; margin-bottom: 18px; padding: 8px 20px;
                  background: #4A90D9; color: #fff; border: none; border-radius: 6px;
                  font-size: 0.9rem; cursor: pointer; font-family: inherit; }}
    .print-btn:hover {{ background: #3a7bc8; }}
    @media print {{
      .print-btn {{ display: none; }}
      body {{ padding: 0; }}
      tbody tr:nth-child(even) {{ background: none; }}
      thead th {{ background: #eee; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
      .badge {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    }}
  </style>
</head>
<body>
  <button class="print-btn no-print" onclick="window.print()">🖨 Print</button>
  <h1>💼 Job Applications</h1>
  <p class="meta">Exported {date.today().strftime("%-d %B %Y")} &nbsp;·&nbsp; {len(apps)} application{"s" if len(apps) != 1 else ""}</p>
  <table>
    <thead>
      <tr>
        <th>Company</th>
        <th>Role</th>
        <th>Date Applied</th>
        <th>Interview Date</th>
        <th>Days</th>
        <th>Status</th>
        <th>Recruiter</th>
        <th>Notes</th>
      </tr>
    </thead>
    <tbody>
{rows_html}    </tbody>
  </table>
</body>
</html>"""


# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Job Tracker", page_icon="💼", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    h1 { font-size: 2rem; }
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ── Auth ───────────────────────────────────────────────────────────────────────

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("""
    <style>
        section[data-testid="stMain"] > div { display: flex; justify-content: center; }
        div[data-testid="stVerticalBlockBorderWrapper"] { max-width: 380px; width: 100%; }
        .login-title { text-align: center; font-size: 1.6rem; font-weight: 700;
                       margin-bottom: 0.25rem; color: #e0e0e0; }
        .login-sub { text-align: center; color: #888; font-size: 0.9rem; margin-bottom: 1.5rem; }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="login-title">💼 Job Tracker</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Enter your password to continue</div>', unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password", label_visibility="collapsed",
                            placeholder="Password")
        if st.button("Sign in", type="primary", use_container_width=True):
            if pwd == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    st.stop()

# ── State ──────────────────────────────────────────────────────────────────────

if "editing_id" not in st.session_state:
    st.session_state.editing_id = None

apps = load_data()

# ── Header ─────────────────────────────────────────────────────────────────────

st.title("💼 Job Application Tracker")

total = len(apps)
counts = {s: sum(1 for a in apps if a["status"] == s) for s in STATUSES}

cols = st.columns(6)
for col, status in zip(cols, STATUSES):
    col.metric(status, counts[status])

st.divider()

# ── Add form ───────────────────────────────────────────────────────────────────

with st.expander("➕ Add New Application", expanded=not apps):
    with st.form("add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        company = c1.text_input("Company *")
        role = c2.text_input("Role *")

        c3, c4, c5 = st.columns(3)
        applied = c3.date_input("Date Applied", value=date.today())
        status = c4.selectbox("Status", STATUSES)
        recruiter = c5.text_input("Recruiter Name")

        c6, c7 = st.columns(2)
        interview_date = c6.date_input("Interview Date (optional)", value=None)
        notes = c7.text_area("Notes", height=80)

        submitted = st.form_submit_button("Add Application", type="primary")
        if submitted:
            if not company or not role:
                st.error("Company and Role are required.")
            else:
                add_application({
                    "company": company,
                    "role": role,
                    "date_applied": str(applied),
                    "interview_date": str(interview_date) if interview_date else None,
                    "status": status,
                    "recruiter": recruiter,
                    "notes": notes,
                })
                st.success(f"Added: {company} — {role}")
                st.rerun()

# ── Edit form ──────────────────────────────────────────────────────────────────

if st.session_state.editing_id is not None:
    app = next((a for a in apps if a["id"] == st.session_state.editing_id), None)
    if app:
        st.subheader(f"Edit — {app['company']} / {app['role']}")
        with st.form("edit_form"):
            c1, c2 = st.columns(2)
            company = c1.text_input("Company *", value=app["company"])
            role = c2.text_input("Role *", value=app["role"])

            c3, c4, c5 = st.columns(3)
            applied = c3.date_input("Date Applied", value=date.fromisoformat(app["date_applied"]))
            status = c4.selectbox("Status", STATUSES, index=STATUSES.index(app["status"]))
            recruiter = c5.text_input("Recruiter Name", value=app.get("recruiter") or "")

            c6, c7 = st.columns(2)
            existing_interview = app.get("interview_date") or ""
            interview_date = c6.date_input(
                "Interview Date (optional)",
                value=date.fromisoformat(existing_interview) if existing_interview else None,
            )
            notes = c7.text_area("Notes", value=app.get("notes") or "", height=80)

            sc1, sc2 = st.columns([1, 5])
            save = sc1.form_submit_button("Save", type="primary")
            cancel = sc2.form_submit_button("Cancel")

            if save:
                update_application(app["id"], {
                    "company": company,
                    "role": role,
                    "date_applied": str(applied),
                    "interview_date": str(interview_date) if interview_date else None,
                    "status": status,
                    "recruiter": recruiter,
                    "notes": notes,
                })
                st.session_state.editing_id = None
                st.rerun()
            if cancel:
                st.session_state.editing_id = None
                st.rerun()

        st.divider()

# ── Applications table ─────────────────────────────────────────────────────────

st.subheader(f"Applications ({total})")

if not apps:
    st.info("No applications yet. Add one above to get started.")
else:
    sort_col, filter_col = st.columns([1, 2])
    sort_by = sort_col.selectbox(
        "Sort by",
        ["Date (newest)", "Date (oldest)", "Company", "Status", "Days since applied"],
        label_visibility="collapsed",
    )
    filter_status = filter_col.multiselect(
        "Filter by status", STATUSES, placeholder="Filter by status...", label_visibility="collapsed"
    )

    filtered = [a for a in apps if not filter_status or a["status"] in filter_status]

    if sort_by == "Date (newest)":
        filtered.sort(key=lambda a: a["date_applied"], reverse=True)
    elif sort_by == "Date (oldest)":
        filtered.sort(key=lambda a: a["date_applied"])
    elif sort_by == "Company":
        filtered.sort(key=lambda a: a["company"].lower())
    elif sort_by == "Status":
        filtered.sort(key=lambda a: STATUSES.index(a["status"]))
    elif sort_by == "Days since applied":
        filtered.sort(key=lambda a: days_since(a["date_applied"]) or 0, reverse=True)

    # Column layout: company, role, date applied, interview date, days, status, recruiter, actions
    COLS = [2, 2, 1.3, 1.3, 0.9, 1.6, 1.6, 0.6, 0.6]
    HEADERS = ["Company", "Role", "Applied", "Interview", "Days", "Status", "Recruiter", "", ""]

    h = st.columns(COLS)
    for col, label in zip(h, HEADERS):
        col.markdown(f"**{label}**")
    st.markdown('<hr style="margin:4px 0 8px">', unsafe_allow_html=True)

    for app in filtered:
        row = st.columns(COLS)
        style = staleness_style(app)
        days = days_since(app["date_applied"])

        row[0].markdown(f'<div style="{style}">{app["company"]}</div>', unsafe_allow_html=True)
        row[1].write(app["role"])
        row[2].write(app["date_applied"])
        row[3].write(app.get("interview_date") or "—")
        row[4].write(str(days) if days is not None else "—")
        row[5].markdown(status_badge(app["status"]), unsafe_allow_html=True)
        row[6].write(app.get("recruiter") or "")

        if row[7].button("✏️", key=f"edit_{app['id']}", help="Edit"):
            st.session_state.editing_id = app["id"]
            st.rerun()
        if row[8].button("🗑️", key=f"del_{app['id']}", help="Delete"):
            delete_application(app["id"])
            st.rerun()

        # Expandable notes
        if app.get("notes"):
            with st.expander(f"Notes — {app['company']}", expanded=False):
                st.write(app["notes"])

# ── Export ─────────────────────────────────────────────────────────────────────

st.divider()
st.subheader("Export")

exp1, exp2 = st.columns(2)

with exp1:
    csv_bytes = build_csv(apps)
    st.download_button(
        label="⬇️ Export to CSV",
        data=csv_bytes,
        file_name=f"job_applications_{date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

with exp2:
    html_content = build_print_html(apps)
    b64 = base64.b64encode(html_content.encode()).decode()
    st.markdown(
        f'<a href="data:text/html;base64,{b64}" target="_blank" '
        f'style="display:block;text-align:center;padding:0.45rem 1rem;'
        f'background:#4A90D9;color:white;border-radius:6px;text-decoration:none;'
        f'font-size:0.9rem;font-weight:500;width:100%;">🖨️ Print-Friendly View</a>',
        unsafe_allow_html=True,
    )
