"""InsightMetric — Hacker News engagement."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from lib import api, theme

api.page("Hacker News")
api.sidebar_status()

st.title("Hacker News Trending")
st.caption("Front-page stories ranked by engagement, and the themes spanning several of them.")

config = api.load(api.settings)
if config is None:
    st.stop()

day = st.sidebar.selectbox("Day", config["available_dates"], index=0,
                           format_func=lambda d: pd.to_datetime(d).strftime("%a %d %b %Y"))
data = api.load(api.hacker_news, date=day)
if data is None:
    st.stop()

stories = pd.DataFrame(data["stories"])
if stories.empty:
    st.info("No Hacker News data for this day.")
    st.stop()

m1, m2, m3 = st.columns(3)
m1.metric("Stories", len(stories))
m2.metric("Total points", int(stories["points"].sum()))
m3.metric("Total comments", int(stories["comments"].sum()))

st.subheader("Points against comments")
fig = px.scatter(stories, x="points", y="comments", size="points_per_hour",
                 hover_name="title", size_max=28)
fig.update_traces(marker_color=theme.ACCENT, marker_line_width=0)
top = max(stories["points"].max(), stories["comments"].max())
fig.add_shape(type="line", x0=0, y0=0, x1=top, y1=top,
              line=dict(color=theme.UNKNOWN, dash="dot"))
fig.update_layout(height=440, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig, width="stretch")
st.caption("Marker size is points per hour. Stories above the dotted line are being argued about; "
           "below it, quietly upvoted.")

if data["themes"]:
    st.subheader("Themes across stories")
    themes = pd.DataFrame(data["themes"])
    fig = px.bar(themes.sort_values("points"), x="points", y="keyword", orientation="h",
                 hover_data=["stories", "comments", "top_story"])
    fig.update_traces(marker_color=theme.ACCENT)
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), yaxis_title=None)
    st.plotly_chart(fig, width="stretch")
    st.caption("Only keywords appearing in two or more stories — one story's own words are not a theme.")
else:
    st.caption("No keyword spanned two or more front-page stories on this day.")

st.subheader("Stories")
st.dataframe(
    stories[["title", "points", "comments", "points_per_hour", "engagement", "discussion_url"]],
    hide_index=True, width="stretch",
    column_config={"discussion_url": st.column_config.LinkColumn("discussion", display_text="open")},
)
