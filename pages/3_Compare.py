"""InsightMetric — Category Comparison."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from lib import api, theme

api.page("Compare")
api.sidebar_status()

st.title("Category Comparison")
st.caption("Two categories side by side: volume, tone and persistence are three different questions.")

config = api.load(api.settings)
if config is None:
    st.stop()

cats = config["categories"]
c1, c2, c3 = st.columns([2, 2, 1])
a = c1.selectbox("Category A", cats, index=cats.index("AI") if "AI" in cats else 0)
b_options = [c for c in cats if c != a]
default_b = b_options.index("Cybersecurity") if "Cybersecurity" in b_options else 0
b = c2.selectbox("Category B", b_options, index=default_b)
days = c3.number_input("Days", min_value=7, max_value=365, value=30, step=7)

data = api.load(api.compare, a=a, b=b, days=int(days))
if data is None:
    st.stop()

# --- headline numbers ---------------------------------------------------------
sa, sb = data["a"], data["b"]
m1, m2, m3 = st.columns(3)
m1.metric(f"Trend-days · {a} vs {b}", f"{sa['total_trend_days']} vs {sb['total_trend_days']}",
          delta=sa["total_trend_days"] - sb["total_trend_days"])
m2.metric("Avg sentiment", f"{sa['avg_sentiment']:+.2f} vs {sb['avg_sentiment']:+.2f}",
          delta=round(sa["avg_sentiment"] - sb["avg_sentiment"], 2))
if sa["recurrence_rate"] is not None and sb["recurrence_rate"] is not None:
    m3.metric("Recurrence", f"{sa['recurrence_rate']:.0%} vs {sb['recurrence_rate']:.0%}",
              delta=f"{(sa['recurrence_rate'] - sb['recurrence_rate']):+.0%}")

# --- three stacked panels on a shared date axis --------------------------------
fa, fb = pd.DataFrame(sa["series"]), pd.DataFrame(sb["series"])
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07,
                    subplot_titles=("Trend-days per day", "Average sentiment", "Recurrence rate"))

for frame, name, colour in ((fa, a, theme.ACCENT), (fb, b, theme.CONTRAST)):
    roll = frame.set_index("date").rolling(7, min_periods=1).mean().reset_index()
    for row, column in ((1, "trends"), (2, "avg_sentiment"), (3, "recurrence_rate")):
        fig.add_trace(go.Scatter(x=frame["date"], y=frame[column], name=name, legendgroup=name,
                                 showlegend=False, mode="lines", opacity=0.22,
                                 line=dict(color=colour, width=1)), row=row, col=1)
        fig.add_trace(go.Scatter(x=roll["date"], y=roll[column], name=name, legendgroup=name,
                                 showlegend=(row == 1), mode="lines",
                                 line=dict(color=colour, width=2.5)), row=row, col=1)

fig.update_yaxes(title_text="count", row=1, col=1)
fig.update_yaxes(title_text="sentiment", range=[-1, 1], row=2, col=1)
fig.update_yaxes(title_text="share", tickformat=".0%", row=3, col=1)
fig.update_layout(height=720, margin=dict(l=0, r=0, t=40, b=0), hovermode="x unified",
                  legend=dict(orientation="h", y=1.06))
st.plotly_chart(fig, width="stretch")
st.caption("Faint lines are daily values; bold lines are seven-day rolling means. "
           "Recurrence is undefined on the newest day — tomorrow has not happened yet.")

# --- most persistent topics ----------------------------------------------------
left, right = st.columns(2)
for column, side in ((left, sa), (right, sb)):
    with column:
        st.subheader(f"Most persistent · {side['category']}")
        if side["top_topics"]:
            for i, topic in enumerate(side["top_topics"], 1):
                st.write(f"{i}. {topic}")
        else:
            st.caption("No topics in this window.")
