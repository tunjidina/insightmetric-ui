"""InsightMetric — Settings. Preferences live in the browser session, not on a server."""
from __future__ import annotations

import streamlit as st

from lib import api

api.page("Settings")
api.sidebar_status()

st.title("Settings")
st.caption("Choose what appears on the other pages. Changes apply straight away.")

config = api.load(api.settings)
if config is None:
    st.stop()

# --- categories ---------------------------------------------------------------
st.subheader("Categories")
st.session_state.setdefault("categories", config["categories"])
chosen = st.multiselect("Show these categories", config["categories"],
                        default=st.session_state["categories"])
st.session_state["categories"] = chosen or config["categories"]
if not chosen:
    st.caption("Nothing selected, so every category is shown.")

# The category list comes from the API, so a new category added upstream appears here
# without a change to this page.
st.caption(f"{len(config['categories'])} categories are currently defined.")

# --- appearance ---------------------------------------------------------------
st.subheader("Appearance")
st.write(
    "Use the theme switch in Streamlit's own menu — the ☰ button in the top right, "
    "then **Settings → Theme**. It offers Light, Dark and System, remembers your choice, "
    "and applies to every chart on every page."
)
st.caption("Streamlit's built-in switch replaced the custom toggle: fewer moving parts, and it "
           "follows your operating system automatically.")

# --- data freshness -----------------------------------------------------------
st.subheader("Data")
health = api.load(api.health)
if health:
    c1, c2, c3 = st.columns(3)
    c1.metric("Days collected", health.get("days", "—"))
    c2.metric("Rows", health.get("rows", "—"))
    c3.metric("Latest day", str(health.get("latest_date", "—")))
    if health.get("problems"):
        for problem in health["problems"]:
            st.warning(problem)
    else:
        st.success("Everything looks healthy.")

with st.expander("Connection"):
    st.write(f"API: `{api.base_url()}`")
    st.caption("Set with `API_URL` in Streamlit secrets or as an environment variable.")
    if st.button("Clear cached responses"):
        api.get.clear()
        st.rerun()
