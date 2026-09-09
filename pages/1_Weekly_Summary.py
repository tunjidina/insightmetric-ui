"""InsightMetric — Weekly Summary. Presentation only; all figures come from the API."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from wordcloud import WordCloud

from lib import api, theme

api.page("Weekly Summary")
api.sidebar_status()

st.title("Weekly Trend Summary")
st.caption("A week rolled up: what persisted, what faded, and how the mix shifted.")

config = api.load(api.settings)
if config is None:
    st.stop()

week = st.sidebar.selectbox("Week", config["available_weeks"], index=0)
data = api.load(api.weekly, week=week)
if data is None:
    st.stop()

start, end = pd.to_datetime(data["start"]), pd.to_datetime(data["end"])
st.subheader(f"{week} · {start:%d %b} – {end:%d %b %Y}")
if not data["complete"]:
    st.info("This week is still in progress. Week-on-week comparisons are hidden until it completes — "
            "comparing a partial week with a full one is not a comparison.")

m = data["metrics"]
c1, c2, c3 = st.columns(3)
c1.metric("Trend-days", m["trends"])
c2.metric("Avg sentiment", f"{m['avg_sentiment']:+.2f}")
c3.metric("Avg coverage", f"{m['avg_coverage']:.1f}")

# --- persistence --------------------------------------------------------------
st.subheader("Persistence leaders")
topics = pd.DataFrame(data["topics"])
if topics.empty:
    st.caption("No topics recorded this week.")
else:
    fig = px.bar(topics.head(12).sort_values("days_present"),
                 x="days_present", y="topic", orientation="h", color="category",
                 labels={"days_present": "days in the top ten", "topic": ""})
    fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0), legend_title=None)
    st.plotly_chart(fig, width="stretch")
    st.caption("Topics that held a place across several days are the ones with substance behind them.")

# --- category mix -------------------------------------------------------------
left, right = st.columns(2)
with left:
    st.subheader("Category mix")
    mix = pd.DataFrame({"category": list(data["category_mix"]), "trend_days": list(data["category_mix"].values())})
    previous = data.get("previous_category_mix")
    if previous and data["complete"]:
        mix["previous"] = mix["category"].map(previous).fillna(0).astype(int)
        mix["change"] = mix["trend_days"] - mix["previous"]
        st.dataframe(mix.sort_values("trend_days", ascending=False), hide_index=True, width="stretch")
    else:
        fig = px.pie(mix, names="category", values="trend_days", hole=0.55)
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Sentiment by day")
    daily = pd.DataFrame(data["daily"])
    if not daily.empty:
        fig = px.line(daily, x="date", y="avg_sentiment", markers=True)
        fig.update_traces(line_color=theme.ACCENT)
        fig.add_hline(y=0, line_dash="dot", line_color=theme.UNKNOWN)
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0),
                          yaxis_title="avg sentiment", xaxis_title=None, yaxis_range=[-1, 1])
        st.plotly_chart(fig, width="stretch")

# --- keywords -----------------------------------------------------------------
st.subheader("Keywords this week")
weights = {k["keyword"]: k["weight"] for k in data["keywords"]}
if weights:
    cloud = WordCloud(width=1200, height=380, background_color=None, mode="RGBA",
                      colormap="Blues", prefer_horizontal=0.9).generate_from_frequencies(weights)
    st.image(cloud.to_image(), width="stretch")

# --- table + download ---------------------------------------------------------
with st.expander("All topics this week"):
    st.dataframe(topics, hide_index=True, width="stretch")

st.sidebar.divider()
if not topics.empty:
    st.sidebar.download_button("Download this week (CSV)", topics.to_csv(index=False).encode(),
                               file_name=f"insightmetric_{week}.csv", mime="text/csv")
