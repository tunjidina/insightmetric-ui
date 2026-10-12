"""The data notice shown on every page: what is sample data, what is live, and when data is stale."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import api  # noqa: E402

QUALITY = {"recorded": True, "synthetic_days": 45, "unverified_days": 1, "live_days": 1, "synthetic_rows": 450,
           "unverified_rows": 10, "live_rows": 10, "synthetic_through": "2026-09-08", "latest_provenance": "live"}


def health(**over):
    return {"status": "ok", "latest_date": "2026-10-12", "days_since_latest": 0, "model_available": True,
            "problems": [], "data_quality": {**QUALITY, **over.pop("quality", {})}, **over}


def render(monkeypatch, payload):
    """Run a page that only calls api.sidebar_status(), against a canned /health answer."""
    def script():
        from lib import api
        api.sidebar_status()
    monkeypatch.setattr(api, "health", payload if callable(payload) else (lambda: payload))
    at = AppTest.from_function(script).run()
    assert not at.exception
    return at


def test_sample_data_warning_states_the_real_counts(monkeypatch):
    at = render(monkeypatch, health())
    text = at.warning[0].value
    assert "45 of 47 days" in text and "08 Sep 2026" in text and "synthetic" in text
    assert "1 day of unverified origin" in text and "1 day collected from live feeds" in text
    assert len(at.warning) == 1                       # fresh data: no stale warning


def test_stale_warning_appears_with_the_age_and_cannot_be_hidden(monkeypatch):
    at = render(monkeypatch, health(days_since_latest=5, latest_date="2026-10-07"))
    stale = [w.value for w in at.warning if "Stale" in w.value]
    assert stale and "07 Oct 2026" in stale[0] and "5 days ago" in stale[0]
    assert len(at.expander) == 0


def test_one_day_old_is_not_stale(monkeypatch):
    assert not [w for w in render(monkeypatch, health(days_since_latest=1)).warning if "Stale" in w.value]


def test_newest_day_not_live_is_said_outright(monkeypatch):
    at = render(monkeypatch, health(quality={"live_days": 0, "latest_provenance": "synthetic"}))
    assert "No live data yet" in at.warning[0].value and "newest day is not a live collection" in at.warning[0].value


def test_all_live_data_gets_no_warning(monkeypatch):
    at = render(monkeypatch, health(quality={"synthetic_days": 0, "unverified_days": 0, "live_days": 30}))
    assert not at.warning and "All 30 days were collected from live feeds" in at.main.caption[0].value


def test_unverified_only_is_flagged_not_hidden(monkeypatch):
    at = render(monkeypatch, health(quality={"synthetic_days": 0}))
    assert "Unverified data" in at.info[0].value


def test_api_that_does_not_report_provenance_is_called_out(monkeypatch):
    payload = health()
    del payload["data_quality"]
    assert "Data origin unknown" in render(monkeypatch, payload).warning[0].value


def test_data_without_a_provenance_record_is_called_out(monkeypatch):
    at = render(monkeypatch, health(quality={"recorded": False, "synthetic_days": 0, "unverified_days": 47, "live_days": 0}))
    assert "Data origin unknown" in at.warning[0].value


def test_predictions_off_is_stated_on_every_page(monkeypatch):
    at = render(monkeypatch, health(predictions={"available": False, "reason": "Not validated on real data."}))
    assert any("Predictions are off" in i.value and "Not validated on real data." in i.value for i in at.info)


def test_predictions_available_adds_no_notice(monkeypatch):
    at = render(monkeypatch, health(predictions={"available": True, "reason": None}))
    assert not at.info


def test_predictions_on_is_false_unless_the_api_says_so(monkeypatch):
    monkeypatch.setattr(api, "health", lambda: health(predictions={"available": True, "reason": None}))
    assert api.predictions_on() is True
    monkeypatch.setattr(api, "health", lambda: health())          # older API: field absent
    assert api.predictions_on() is False


def test_unreachable_api_still_renders(monkeypatch):
    def down():
        raise api.APIError("down")
    at = render(monkeypatch, down)
    assert "API unreachable" in at.sidebar.caption[0].value
