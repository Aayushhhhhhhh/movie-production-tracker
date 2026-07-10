"""
Movie Production Tracker Dashboard
Single-user Streamlit app implementing the PRD:
Act -> Scene, pipeline status tracking, client/internal revision counters,
project/act completion rollups, local JSON persistence.
"""

import streamlit as st
import json
import os
import uuid
from datetime import datetime

# ---------------------------------------------------------------------------
# Config / persistence
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Movie Production Tracker", page_icon="🎬", layout="wide")

DATA_FILE = os.path.join(os.path.dirname(__file__), "tracker_data.json")

STAGES = [
    "Not Started",
    "In Progress",
    "Video Generated",
    "Sent to Post-Production",
    "Post-Production Complete",
    "Client Finalized",
]

# Auto-derived completion % per stage (manually overridable per scene)
STAGE_COMPLETION = {
    "Not Started": 0,
    "In Progress": 20,
    "Video Generated": 40,
    "Sent to Post-Production": 60,
    "Post-Production Complete": 80,
    "Client Finalized": 100,
}

STAGE_COLORS = {
    "Not Started": "#9e9e9e",
    "In Progress": "#2196f3",
    "Video Generated": "#9c27b0",
    "Sent to Post-Production": "#ff9800",
    "Post-Production Complete": "#3f51b5",
    "Client Finalized": "#4caf50",
}


def default_data():
    return {
        "acts": [
            {"id": str(uuid.uuid4()), "number": i, "name": f"Act {i}", "scenes": []}
            for i in range(1, 5)
        ]
    }


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return default_data()
    return default_data()


def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(st.session_state.data, f, indent=2)


if "data" not in st.session_state:
    st.session_state.data = load_data()


def new_scene(name):
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "status": "Not Started",
        "client_changes_pre": 0,
        "client_changes_post": 0,
        "completion_override": None,  # None means auto-derived
        "notes": "",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def scene_completion(scene):
    if scene.get("completion_override") is not None:
        return scene["completion_override"]
    return STAGE_COMPLETION.get(scene["status"], 0)


def act_completion(act):
    if not act["scenes"]:
        return 0
    return round(sum(scene_completion(s) for s in act["scenes"]) / len(act["scenes"]))


def project_completion(data):
    all_scenes = [s for a in data["acts"] for s in a["scenes"]]
    if not all_scenes:
        return 0
    return round(sum(scene_completion(s) for s in all_scenes) / len(all_scenes))


def touch(scene):
    scene["updated_at"] = datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Sidebar: navigation + quick add
# ---------------------------------------------------------------------------

data = st.session_state.data

st.sidebar.title("🎬 Production Tracker")
page = st.sidebar.radio("View", ["Project Overview", "Act View", "Change Requests"])

st.sidebar.divider()
st.sidebar.caption(f"Data file: `{os.path.basename(DATA_FILE)}` (auto-saved)")
if st.sidebar.button("💾 Force save now"):
    save_data()
    st.sidebar.success("Saved.")

# ---------------------------------------------------------------------------
# Page: Project Overview
# ---------------------------------------------------------------------------

if page == "Project Overview":
    st.title("Project Overview")

    all_scenes = [s for a in data["acts"] for s in a["scenes"]]
    total_scenes = len(all_scenes)
    proj_pct = project_completion(data)

    c1, c2, c3 = st.columns(3)
    c1.metric("Overall Completion", f"{proj_pct}%")
    c2.metric("Total Scenes", total_scenes)
    c3.metric("Total Acts", len(data["acts"]))

    st.progress(proj_pct / 100)

    st.subheader("Per-Act Completion")
    for act in sorted(data["acts"], key=lambda a: a["number"]):
        pct = act_completion(act)
        st.write(f"**Act {act['number']} — {act['name']}** ({len(act['scenes'])} scenes)")
        st.progress(pct / 100, text=f"{pct}%")

    st.subheader("Pipeline Stage Counts")
    stage_counts = {stg: 0 for stg in STAGES}
    for s in all_scenes:
        stage_counts[s["status"]] += 1

    cols = st.columns(len(STAGES))
    for col, stg in zip(cols, STAGES):
        with col:
            st.markdown(
                f"<div style='background-color:{STAGE_COLORS[stg]}22;"
                f"border-left:4px solid {STAGE_COLORS[stg]};padding:8px;border-radius:4px'>"
                f"<b>{stage_counts[stg]}</b><br><span style='font-size:0.8em'>{stg}</span></div>",
                unsafe_allow_html=True,
            )

    if total_scenes == 0:
        st.info("No scenes yet. Go to **Act View** to add scenes to an act.")

# ---------------------------------------------------------------------------
# Page: Act View
# ---------------------------------------------------------------------------

elif page == "Act View":
    st.title("Act View")

    act_labels = [f"Act {a['number']} — {a['name']}" for a in sorted(data["acts"], key=lambda a: a["number"])]
    sorted_acts = sorted(data["acts"], key=lambda a: a["number"])
    idx = st.selectbox("Select Act", range(len(sorted_acts)), format_func=lambda i: act_labels[i])
    act = sorted_acts[idx]

    with st.expander("✏️ Rename this act"):
        new_name = st.text_input("Act name", value=act["name"], key=f"rename_{act['id']}")
        if st.button("Save name", key=f"savename_{act['id']}"):
            act["name"] = new_name
            save_data()
            st.rerun()

    pct = act_completion(act)
    st.metric(f"Act {act['number']} Completion", f"{pct}%")
    st.progress(pct / 100)

    st.subheader("Add Scene")
    with st.form(key=f"add_scene_{act['id']}", clear_on_submit=True):
        scene_name = st.text_input("Scene name/number (e.g. '1.3 — Rooftop chase')")
        submitted = st.form_submit_button("Add Scene")
        if submitted and scene_name.strip():
            act["scenes"].append(new_scene(scene_name.strip()))
            save_data()
            st.rerun()

    st.subheader(f"Scenes ({len(act['scenes'])})")

    if not act["scenes"]:
        st.info("No scenes in this act yet.")

    for scene in act["scenes"]:
        pct_s = scene_completion(scene)
        badge_color = STAGE_COLORS[scene["status"]]
        header = f"{scene['name']}  ·  {scene['status']}  ·  {pct_s}%"
        with st.expander(header):
            st.markdown(
                f"<span style='background:{badge_color};color:white;padding:2px 8px;"
                f"border-radius:10px;font-size:0.8em'>{scene['status']}</span>",
                unsafe_allow_html=True,
            )
            st.write("")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Pipeline Status**")
                new_status = st.selectbox(
                    "Status stage", STAGES, index=STAGES.index(scene["status"]),
                    key=f"status_{scene['id']}"
                )
                if new_status != scene["status"]:
                    scene["status"] = new_status
                    touch(scene)
                    save_data()
                    st.rerun()

            with col2:
                st.markdown("**Client Change Counters**")

                def counter_row(field, label):
                    c_a, c_b, c_c = st.columns([2, 1, 1])
                    c_a.write(f"{label}: **{scene[field]}**")
                    if c_b.button("➖", key=f"dec_{field}_{scene['id']}"):
                        scene[field] = max(0, scene[field] - 1)
                        touch(scene)
                        save_data()
                        st.rerun()
                    if c_c.button("➕", key=f"inc_{field}_{scene['id']}"):
                        scene[field] += 1
                        touch(scene)
                        save_data()
                        st.rerun()

                counter_row("client_changes_pre", "Client changes (pre-post)")
                counter_row("client_changes_post", "Client changes (post-post)")

                st.markdown("**Completion % override**")
                override_on = st.checkbox(
                    "Manually override completion %",
                    value=scene["completion_override"] is not None,
                    key=f"ov_toggle_{scene['id']}",
                )
                if override_on:
                    ov_val = st.slider(
                        "Completion %",
                        0, 100,
                        value=scene["completion_override"] if scene["completion_override"] is not None else STAGE_COMPLETION[scene["status"]],
                        key=f"ov_slider_{scene['id']}",
                    )
                    if scene["completion_override"] != ov_val:
                        scene["completion_override"] = ov_val
                        touch(scene)
                        save_data()
                        st.rerun()
                else:
                    if scene["completion_override"] is not None:
                        scene["completion_override"] = None
                        touch(scene)
                        save_data()
                        st.rerun()

            st.markdown("**Notes**")
            notes_val = st.text_area("Notes", value=scene["notes"], key=f"notes_{scene['id']}", label_visibility="collapsed")
            if notes_val != scene["notes"]:
                scene["notes"] = notes_val
                touch(scene)
                save_data()

            st.caption(f"Last updated: {scene['updated_at']}")

            if st.button("🗑️ Remove scene", key=f"del_{scene['id']}"):
                act["scenes"] = [s for s in act["scenes"] if s["id"] != scene["id"]]
                save_data()
                st.rerun()

# ---------------------------------------------------------------------------
# Page: Change Requests
# ---------------------------------------------------------------------------

elif page == "Change Requests":
    st.title("Change-Request Tracking")

    all_scenes = []
    for act in data["acts"]:
        for s in act["scenes"]:
            all_scenes.append((act, s))

    if not all_scenes:
        st.info("No scenes yet.")
    else:
        total_pre = sum(s["client_changes_pre"] for _, s in all_scenes)
        total_post_client = sum(s["client_changes_post"] for _, s in all_scenes)
        c1, c2 = st.columns(2)
        c1.metric("Total client changes (pre-post)", total_pre)
        c2.metric("Total client changes (post-post)", total_post_client)

        st.subheader("Per-Act Rollup")
        act_rows = []
        for act in sorted(data["acts"], key=lambda a: a["number"]):
            act_rows.append({
                "Act": f"{act['number']} — {act['name']}",
                "Scenes": len(act["scenes"]),
                "Client changes (pre-post)": sum(s["client_changes_pre"] for s in act["scenes"]),
                "Client changes (post-post)": sum(s["client_changes_post"] for s in act["scenes"]),
            })
        st.dataframe(act_rows, use_container_width=True, hide_index=True)

        st.subheader("Scene-level detail")
        threshold = st.slider("Highlight scenes with total change rounds ≥", 0, 10, 3)

        rows = []
        for act, s in all_scenes:
            total_changes = s["client_changes_pre"] + s["client_changes_post"]
            rows.append({
                "Act": act["number"],
                "Scene": s["name"],
                "Status": s["status"],
                "Client changes (pre-post)": s["client_changes_pre"],
                "Client changes (post-post)": s["client_changes_post"],
                "Total": total_changes,
            })
        rows.sort(key=lambda r: r["Total"], reverse=True)

        flagged = [r for r in rows if r["Total"] >= threshold]
        if flagged:
            st.warning(f"⚠️ {len(flagged)} scene(s) at or above threshold ({threshold} total change rounds):")
            st.dataframe(flagged, use_container_width=True, hide_index=True)

        st.subheader("All scenes")
        st.dataframe(rows, use_container_width=True, hide_index=True)
