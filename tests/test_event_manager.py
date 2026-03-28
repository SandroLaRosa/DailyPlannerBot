"""
Unit tests for src.classes.event_manager
"""

import json
from datetime import datetime, timedelta

import pytest
from dateutil.relativedelta import relativedelta

import src.classes.event_manager as em
from src.classes.event import Event, RecurringEvent
from src.classes.event_manager import EventManager
from src.modules.timezone_logics import TZ


@pytest.fixture(name="manager")
def fixture_manager(tmp_path, monkeypatch):
    base = tmp_path / "data"
    base.mkdir()

    monkeypatch.setattr("src.classes.event_manager.DATA_DIRECTORY", str(base))
    monkeypatch.setattr(
        "src.classes.event_manager.ONGOING_FILE", str(base / "ongoing.json")
    )
    monkeypatch.setattr(
        "src.classes.event_manager.EXPIRED_FILE", str(base / "expired.json")
    )
    monkeypatch.setattr(
        "src.classes.event_manager.MISSED_FILE", str(base / "missed.json")
    )

    return EventManager()


# Fixtures


class MockApp:
    def __init__(self):
        self.job_calls = []

    def run_once(self, callback, when, name, data, chat_id, job_kwargs):
        self.job_calls.append(
            {
                "callback": callback,
                "when": when,
                "name": name,
                "data": data,
                "chat_id": chat_id,
                "job_kwargs": job_kwargs,
            }
        )
        return "job"

    def get_jobs_by_name(self, _name):
        return []

    @property
    def job_queue(self):
        return self


@pytest.fixture(name="app")
def fixture_app():
    return MockApp()


# Test1 : load_ongoing


def test_load_ongoing_persists_missed(manager, _tmp_path):
    now = datetime.now(TZ)

    past = Event("past", now - timedelta(minutes=10), now - timedelta(minutes=5))
    future = Event("future", now + timedelta(minutes=10), now + timedelta(minutes=15))

    with open(em.ONGOING_FILE, "w", encoding="utf-8") as f:
        json.dump([past.to_dict(), future.to_dict()], f)

    ongoing, missed = manager.load_ongoing()

    assert len(ongoing) == 1
    assert len(missed) == 1
    assert ongoing[0].id == future.id
    assert missed[0].id == past.id

    with open(em.MISSED_FILE, encoding="utf-8") as f:
        assert len(json.load(f)) == 1

    with open(em.ONGOING_FILE, encoding="utf-8") as f:
        assert len(json.load(f)) == 1


# Test 2: schedule (past event -> delay 1s)


def test_schedule_past_event_delayed(manager, app):
    now = datetime.now(TZ)
    event = Event("e", now - timedelta(minutes=1), now + timedelta(minutes=1))

    manager.schedule(event, app, callback=lambda *_: None, chat_id=123)

    assert len(app.job_calls) == 1
    call = app.job_calls[0]

    assert call["name"] == event.id
    assert call["job_kwargs"]["misfire_grace_time"] == 60
    assert call["job_kwargs"]["coalesce"] is True
    assert call["when"] > now


# Test 3: recurring event


def test_expire_recurring(manager, app):
    start = datetime.now(TZ) + timedelta(minutes=1)
    end = start + timedelta(minutes=5)

    recurring = RecurringEvent(
        "rec",
        start,
        end,
        period=relativedelta(minutes=1),
        remaining_occurrences=2,
    )

    manager.events[recurring.id] = recurring

    manager.expire_event(recurring.id, app=app, callback=lambda *_: None)
    assert recurring.remaining_occurrences == 1
    assert recurring.is_active

    manager.expire_event(recurring.id, app=app, callback=lambda *_: None)
    assert recurring.is_active is False
