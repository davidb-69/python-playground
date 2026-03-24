import json
import os
from datetime import date

import streamlit as st

DATA_FILE = "applications.json"
STATUSES = ["Applied", "Phone Screen", "Interview", "Offer", "Rejected", "Withdrawn"]

STATUS_COLORS = {
    "Applied": "#4A90D9",
    "Phone Screen": "#9B59B6",
    "Interview": "#F39C12",
    "Offer": "#27AE60",
    "Rejected": "#E74C3C",
    "Withdrawn": "#95A5A6",
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE) as f:
        return json.load(f)


def save_data(apps):
    with open(DATA_FILE, "w") as f:
        json.dump(apps, f, indent=2)


def next_id(apps):
    return max((a["id"] for a in apps), default=0) + 1


def status_badge(status):
    color = STATUS_COLORS.get(status, "#888")
    return f'<span style="background:{color};color:white;padding:2px 10px;border-radius:12px;font-size:0.8em;font-weight:600">{status}</span>'


# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Job Tracker", page_icon="💼", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    h1 { font-size: 2rem; }
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ── State ─────────────────────────────────────────────────────────────────────

if "editing_id" not in st.session_state:
    st.session_state.editing_id = None

apps = load_data()

# ── Header ────────────────────────────────────────────────────────────────────

st.title("💼 Job Application Tracker")

total = len(apps)
counts = {s: sum(1 for a in apps if a["status"] == s) for s in STATUSES}

cols = st.columns(6)
for col, status in zip(cols, STATUSES):
    col.metric(status, counts[status])

st.divider()

# ── Add form ──────────────────────────────────────────────────────────────────

with st.expander("➕ Add New Application", expanded=not apps):
    with st.form("add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        company = c1.text_input("Company *")
        role = c2.text_input("Role *")

        c3, c4, c5 = st.columns(3)
        applied = c3.date_input("Date Applied", value=date.today())
        status = c4.selectbox("Status", STATUSES)
        recruiter = c5.text_input("Recruiter Name")

        notes = st.text_area("Notes", height=80)

        submitted = st.form_submit_button("Add Application", type="primary")
        if submitted:
            if not company or not role:
                st.error("Company and Role are required.")
            else:
                apps.append({
                    "id": next_id(apps),
                    "company": company,
                    "role": role,
                    "date_applied": str(applied),
                    "status": status,
                    "recruiter": recruiter,
                    "notes": notes,
                })
                save_data(apps)
                st.success(f"Added: {company} — {role}")
                st.rerun()

# ── Edit modal ────────────────────────────────────────────────────────────────

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
            recruiter = c5.text_input("Recruiter Name", value=app.get("recruiter", ""))

            notes = st.text_area("Notes", value=app.get("notes", ""), height=80)

            sc1, sc2 = st.columns([1, 5])
            save = sc1.form_submit_button("Save", type="primary")
            cancel = sc2.form_submit_button("Cancel")

            if save:
                app.update({
                    "company": company,
                    "role": role,
                    "date_applied": str(applied),
                    "status": status,
                    "recruiter": recruiter,
                    "notes": notes,
                })
                save_data(apps)
                st.session_state.editing_id = None
                st.rerun()
            if cancel:
                st.session_state.editing_id = None
                st.rerun()

        st.divider()

# ── Applications table ────────────────────────────────────────────────────────

st.subheader(f"Applications ({total})")

if not apps:
    st.info("No applications yet. Add one above to get started.")
else:
    # Sort controls
    sort_col, filter_col = st.columns([1, 2])
    sort_by = sort_col.selectbox("Sort by", ["Date (newest)", "Date (oldest)", "Company", "Status"], label_visibility="collapsed")
    filter_status = filter_col.multiselect("Filter by status", STATUSES, placeholder="Filter by status...", label_visibility="collapsed")

    filtered = [a for a in apps if not filter_status or a["status"] in filter_status]

    if sort_by == "Date (newest)":
        filtered.sort(key=lambda a: a["date_applied"], reverse=True)
    elif sort_by == "Date (oldest)":
        filtered.sort(key=lambda a: a["date_applied"])
    elif sort_by == "Company":
        filtered.sort(key=lambda a: a["company"].lower())
    elif sort_by == "Status":
        filtered.sort(key=lambda a: STATUSES.index(a["status"]))

    # Header row
    h = st.columns([2.5, 2.5, 1.5, 1.8, 1.8, 2, 0.7, 0.7])
    for col, label in zip(h, ["Company", "Role", "Date Applied", "Status", "Recruiter", "Notes", "", ""]):
        col.markdown(f"**{label}**")
    st.markdown('<hr style="margin:4px 0 8px">', unsafe_allow_html=True)

    for app in filtered:
        row = st.columns([2.5, 2.5, 1.5, 1.8, 1.8, 2, 0.7, 0.7])
        row[0].write(app["company"])
        row[1].write(app["role"])
        row[2].write(app["date_applied"])
        row[3].markdown(status_badge(app["status"]), unsafe_allow_html=True)
        row[4].write(app.get("recruiter", ""))
        row[5].write(app.get("notes", ""))
        if row[6].button("✏️", key=f"edit_{app['id']}", help="Edit"):
            st.session_state.editing_id = app["id"]
            st.rerun()
        if row[7].button("🗑️", key=f"del_{app['id']}", help="Delete"):
            apps.remove(app)
            save_data(apps)
            st.rerun()
