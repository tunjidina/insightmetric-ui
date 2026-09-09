"""
InsightMetric — Daily Trends.

Presentation only. Every number comes from the API; this file decides how to draw it.

Run:  streamlit run Daily_Trends.py
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from wordcloud import WordCloud

from lib import api, theme

api.page()
api.sidebar_status()

st.title("Daily Trends")
st.caption("**Tech Trends, Minus the Noise.**")
st.caption("Topics moving across technology today, with an estimate of which ones return tomorrow.")

# --- controls -----------------------------------------------------------------
config = api.load(api.settings)
if config is None:
    st.stop()

dates = config["available_dates"]
day = st.sidebar.selectbox(
    "Day", dates, index=0,
    format_func=lambda d: pd.to_datetime(d).strftime("%a %d %b %Y"),
)
chosen = st.sidebar.multiselect("Categories", config["categories"], default=config["categories"])

data = api.load(api.daily, date=day, categories=chosen if len(chosen) < len(config["categories"]) else None)
if data is None:
    st.stop()

trends = data["trends"]
metrics = data["metrics"]

# --- headline figures ---------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Trends today", metrics["trends"])
c2.metric("Avg sentiment", f"{metrics['avg_sentiment']:+.2f}")
c3.metric("Avg coverage", f"{metrics['avg_coverage']:.1f}")
c4.metric("Predicted to recur", metrics["predicted_to_recur"] if metrics["predicted_to_recur"] is not None else "—")

if len(chosen) < len(config["categories"]):
    st.caption(f"Showing {len(trends)} of {metrics['trends']} topics · filtered to {', '.join(chosen)}")

st.subheader(f"Trends for {pd.to_datetime(day).strftime('%d %B %Y')}")

if not trends:
    st.info("No topics match the selected categories on this day.")
    st.stop()

# --- the cards ----------------------------------------------------------------
for t in trends:
    with st.container(border=True):
        left, right = st.columns([3, 1])
        with left:
            st.markdown(f"**#{t['rank']} {t['topic']}**  `{t['category']}`")
            st.write(t["description"])
            bits = [f"Covered by {t['coverage']} source(s)"]
            if t["keywords"]:
                bits.append("Keywords: " + ", ".join(t["keywords"][:5]))
            if t["hn_points"]:
                bits.append(f"{t['hn_points']} HN points")
            st.caption(" · ".join(bits))
        with right:
            if t["prediction"]:
                st.markdown(f"### {theme.badge(t['prediction']['probability'])}")
                st.caption(f"Confidence {t['prediction']['confidence']:.0%}")
            else:
                st.caption("No prediction available")
            if t["recurred"] is not None:
                st.caption("Actually recurred ✓" if t["recurred"] else "Actually faded ✗")

# --- charts -------------------------------------------------------------------
st.divider()
frame = pd.DataFrame(trends)
left, right = st.columns(2)

with left:
    st.subheader("Sentiment by topic")
    fig = px.bar(
        frame.sort_values("sentiment"), x="sentiment", y="topic", orientation="h",
        color="sentiment", color_continuous_scale=[theme.CONTRAST, theme.FADED, theme.ACCENT],
        range_color=[-1, 1], range_x=[-1, 1],
    )
    fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0),
                      yaxis_title=None, xaxis_title="VADER compound", coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Keywords today")
    weights = {}
    for t in trends:
        for kw in t["keywords"]:
            weights[kw] = weights.get(kw, 0) + t["prominence"]
    if weights:
        cloud = WordCloud(width=800, height=420, background_color=None, mode="RGBA",
                          colormap="Blues", prefer_horizontal=0.9).generate_from_frequencies(weights)
        st.image(cloud.to_image(), width="stretch")
    else:
        st.caption("No keywords on this day.")

# --- download -----------------------------------------------------------------
st.sidebar.divider()
st.sidebar.download_button(
    "Download this day (CSV)",
    frame.to_csv(index=False).encode(),
    file_name=f"insightmetric_{day}.csv",
    mime="text/csv",
)
