"""InsightMetric — Open-source releases."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from lib import api, theme

api.page("Releases")
api.sidebar_status()

st.title("Open-Source Releases")
st.caption("Recent releases across the projects InsightMetric watches.")

c1, c2 = st.columns([1, 2])
days = c1.number_input("Days", min_value=7, max_value=365, value=30, step=7)
show_pre = c2.toggle("Include pre-releases and nightly builds", value=False)

data = api.load(api.releases, days=int(days), include_prereleases=show_pre)
if data is None:
    st.stop()

if data["count"] == 0:
    st.info("No releases in this window. The release log fills up as collection runs.")
    st.stop()

m1, m2, m3 = st.columns(3)
m1.metric("Releases", data["count"])
m2.metric("Projects", len(data["by_project"]))
m3.metric("Stable minor or major", data["by_kind"].get("minor", 0) + data["by_kind"].get("major", 0))

left, right = st.columns([2, 1])
with left:
    st.subheader("Releases by project")
    by_project = pd.DataFrame({"project": list(data["by_project"]),
                               "releases": list(data["by_project"].values())})
    fig = px.bar(by_project.sort_values("releases"), x="releases", y="project", orientation="h")
    fig.update_traces(marker_color=theme.ACCENT)
    fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0), yaxis_title=None)
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("By kind")
    by_kind = pd.DataFrame({"kind": list(data["by_kind"]), "count": list(data["by_kind"].values())})
    fig = px.pie(by_kind, names="kind", values="count", hole=0.55)
    fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")

st.subheader("Release log")
frame = pd.DataFrame(data["releases"])
st.dataframe(
    frame, hide_index=True, width="stretch",
    column_config={"url": st.column_config.LinkColumn("link", display_text="open"),
                   "published": st.column_config.DateColumn("published")},
)
st.sidebar.divider()
st.sidebar.download_button("Download releases (CSV)", frame.to_csv(index=False).encode(),
                           file_name="insightmetric_releases.csv", mime="text/csv")
