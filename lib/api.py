"""
The API bridge — the only place the UI talks to the outside world.

Every page imports from here and nothing else. No page builds a URL, handles an HTTP
error, or knows the API exists beyond calling one of these functions. That is what keeps
the public repository free of anything private: this file knows a base URL and some path
strings, and that is the whole of its knowledge.

Configuration, in order of precedence:
  1. st.secrets["API_URL"]   — Streamlit Cloud
  2. environment variable API_URL — Render, Docker, your shell
  3. http://localhost:8000   — a core running on your own machine

Optional API_KEY (same two sources) is sent as X-API-Key when the core requires one.
"""
from __future__ import annotations

import os
from datetime import date

import requests
import streamlit as st

DEFAULT_URL = "http://localhost:8000"
TIMEOUT = 20          # seconds; a cold free-tier instance can take a while to wake
CACHE_TTL = 300       # the data changes once a day, so five minutes is generous
STALE_AFTER_DAYS = 2  # same threshold the API's /health uses for "collection has stopped"


def _config(name: str, default: str | None = None) -> str | None:
    """Secrets first, then environment. st.secrets raises when no secrets file exists,
    which is normal locally, so it is guarded rather than assumed."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.environ.get(name, default)


def base_url() -> str:
    return (_config("API_URL", DEFAULT_URL) or DEFAULT_URL).rstrip("/")


def _headers() -> dict[str, str]:
    key = _config("API_KEY")
    return {"X-API-Key": key} if key else {}


class APIError(Exception):
    """Anything that stopped us getting an answer, already phrased for a human."""


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get(path: str, **params) -> dict:
    """GET a JSON endpoint, cached for five minutes.

    Streamlit caches on the arguments, so two pages asking for the same day share one
    request. Errors are translated into one sentence a person can act on — the raw
    requests exceptions are not useful to a reader.
    """
    clean = {k: v for k, v in params.items() if v is not None}
    try:
        response = requests.get(f"{base_url()}{path}", params=clean,
                                headers=_headers(), timeout=TIMEOUT)
    except requests.Timeout as exc:
        raise APIError(
            f"The API did not respond within {TIMEOUT} seconds. Free hosting sleeps when "
            "idle, so the first request after a quiet spell can time out — try again."
        ) from exc
    except requests.ConnectionError as exc:
        raise APIError(f"Could not reach the API at {base_url()}. Check API_URL.") from exc

    if response.status_code == 401:
        raise APIError("The API rejected the key. Check API_KEY.")
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text[:200]
        raise APIError(detail or f"The API returned {response.status_code}.")
    try:
        return response.json()
    except ValueError as exc:
        raise APIError("The API returned something that was not JSON.") from exc


# ---------------------------------------------------------------------------
# endpoints
# ---------------------------------------------------------------------------
def health() -> dict:
    return get("/health")


def settings() -> dict:
    return get("/settings")


def daily(date: str | None = None, categories: list[str] | None = None) -> dict:
    return get("/trends/daily", date=date, categories=categories or None)


def weekly(week: str | None = None) -> dict:
    return get("/trends/weekly", week=week)


def releases(days: int = 30, include_prereleases: bool = False) -> dict:
    return get("/trends/releases", days=days, include_prereleases=include_prereleases)


def hacker_news(date: str | None = None) -> dict:
    return get("/trends/hn", date=date)


def compare(a: str, b: str, days: int = 30) -> dict:
    return get("/compare", a=a, b=b, days=days)


def keywords(days: int = 7, limit: int = 40, category: str | None = None) -> dict:
    return get("/keywords", days=days, limit=limit, category=category)


# ---------------------------------------------------------------------------
# page helpers — the two things every page does identically
# ---------------------------------------------------------------------------
def page(title: str | None = None) -> None:
    """Standard page setup. Uses Streamlit's own set_page_config; no custom wrapper."""
    st.set_page_config(
        page_title=f"{title} · InsightMetric" if title else "InsightMetric",
        page_icon="📈",
        layout="wide",
    )


def load(fn, *args, **kwargs):
    """Call an endpoint with a spinner, and render the error instead of crashing.

    Returns None on failure, so a page reads:

        data = api.load(api.daily, date)
        if data is None:
            st.stop()
    """
    with st.spinner("Loading…"):
        try:
            return fn(*args, **kwargs)
        except APIError as exc:
            st.error(str(exc))
            with st.expander("Connection details"):
                st.write(f"API: `{base_url()}`")
                st.caption(
                    "Set `API_URL` in Streamlit secrets or as an environment variable. "
                    "If the API is asleep, the next attempt usually succeeds."
                )
            if st.button("Try again", key=f"retry_{fn.__name__}"):
                get.clear()
                st.rerun()
            return None


def _day(iso: str | None) -> str:
    return date.fromisoformat(iso).strftime("%d %b %Y") if iso else "—"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def data_notice(h: dict) -> None:
    """A plain statement of what the data is, on every page. Warnings are not collapsible and
    not dismissible: sample data must not be mistaken for news, and old data for current."""
    days_old, newest = h.get("days_since_latest"), h.get("latest_date")
    if days_old is not None and days_old >= STALE_AFTER_DAYS:
        st.warning(f"**Stale data.** The newest data is from {_day(newest)}, {_plural(days_old, 'day')} ago. "
                   "The daily collection may have stopped, so none of this is current.")

    pred = h.get("predictions")
    if pred and not pred["available"]:
        st.info(f"**Predictions are off.** {pred['reason']}")

    q = h.get("data_quality")
    if q is None:
        st.warning("**Data origin unknown.** This API does not say whether its data is real or sample data.")
        return
    s, u, live = q["synthetic_days"], q["unverified_days"], q["live_days"]
    if not q["recorded"]:
        st.warning("**Data origin unknown.** The data carries no provenance record, "
                   "so none of it can be confirmed as real.")
    elif s:
        parts = [f"**Sample data.** {s} of {s + u + live} days (through {_day(q['synthetic_through'])}) are "
                 "synthetic: generated for development, not collected from news."]
        if u:
            parts.append(f"{_plural(u, 'day')} of unverified origin.")
        parts.append(f"{_plural(live, 'day')} collected from live feeds." if live else "No live data yet.")
        if q["latest_provenance"] != "live":
            parts.append("The newest day is not a live collection.")
        parts.append("Topics, charts and predictions for sample days do not describe real news.")
        st.warning(" ".join(parts))
    elif u:
        st.info(f"**Unverified data.** {_plural(u, 'day')} of unverified origin; "
                f"{_plural(live, 'day')} collected from live feeds.")
    else:
        st.caption(f"All {_plural(live, 'day')} were collected from live feeds.")


def predictions_on() -> bool:
    """True only when the API says its predictions can be trusted. Unknown counts as off."""
    try:
        return bool((health().get("predictions") or {}).get("available"))
    except APIError:
        return False


def sidebar_status() -> None:
    """A small freshness line in the sidebar, then the data notice. Never blocks the page if it fails."""
    try:
        h = health()
    except APIError:
        st.sidebar.caption("⚠️ API unreachable")
        return
    fresh = h.get("days_since_latest")
    icon = "🟢" if h.get("status") == "ok" else "🟡"
    st.sidebar.caption(
        f"{icon} Data to {h.get('latest_date', '—')}"
        + (" · today" if fresh == 0 else f" · {fresh}d ago" if fresh else "")
    )
    data_notice(h)
