"""
Unit tests for src.classes.event
"""

from __future__ import annotations

import importlib
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

import src.classes.event as _event_module
from src.classes.event import (
    Event,
    RecurringEvent,
    Reminder,
    event_from_dict,
    relativedelta_from_dict,
    relativedelta_to_dict,
)

_TZ = ZoneInfo("Europe/Rome")
_tz_stub = type(sys)("src.modules.timezone_logics")
_tz_stub.TZ = _TZ  # type: ignore
sys.modules["src.modules.timezone_logics"] = _tz_stub


@pytest.fixture(autouse=True)
def _reload_event_module():
    importlib.reload(_event_module)
    global Event, RecurringEvent, Reminder  # noqa: PLW0603
    global event_from_dict, relativedelta_from_dict, relativedelta_to_dict
    Event = _event_module.Event
    RecurringEvent = _event_module.RecurringEvent
    Reminder = _event_module.Reminder
    event_from_dict = _event_module.event_from_dict
    relativedelta_from_dict = _event_module.relativedelta_from_dict
    relativedelta_to_dict = _event_module.relativedelta_to_dict


# Shared constants

START = datetime(2026, 6, 1, 10, 0, tzinfo=_TZ)
END = datetime(2026, 6, 1, 12, 0, tzinfo=_TZ)
DELTA = relativedelta(weeks=1)


# Fixtures


@pytest.fixture(name="base_event")
def fixture_base_event():
    return Event(
        name="Riunione",
        start_date=START,
        end_date=END,
        description="Riunione settimanale",
        event_id="fixed-id-001",
    )


@pytest.fixture(name="recurring_event")
def fixture_recurring_event():
    return RecurringEvent(
        name="Stand-up",
        start_date=START,
        end_date=END,
        period=DELTA,
        remaining_occurrences=3,
        event_id="fixed-id-002",
    )


@pytest.fixture(name="reminder")
def fixture_reminder():
    return Reminder(
        name="Pillola",
        start_date=START,
        description="Prendere la pillola",
        event_id="fixed-id-003",
    )


# Event: construction


class TestEventConstruction:

    def test_fields_stored_with_explicit_id(self, base_event):
        assert base_event.id == "fixed-id-001"
        assert base_event.name == "Riunione"
        assert base_event.start_date == START
        assert base_event.end_date == END
        assert base_event.description == "Riunione settimanale"
        assert base_event.is_active is True

    def test_auto_uuid_assigned_when_no_id_given(self):
        e = Event("Test", START, END)
        assert e.id is not None
        assert len(e.id) == 36

    def test_description_defaults_to_none(self):
        assert Event("Test", START, END).description is None

    def test_is_active_defaults_to_true(self):
        assert Event("Test", START, END).is_active is True

    def test_is_active_can_be_set_false_at_construction(self):
        assert Event("Test", START, END, is_active=False).is_active is False


# Event: setters


class TestEventSetters:

    def test_set_name(self, base_event):
        base_event.set_name("Nuova riunione")
        assert base_event.name == "Nuova riunione"

    def test_set_start(self, base_event):
        new_start = datetime(2026, 6, 2, 9, 0, tzinfo=_TZ)
        base_event.set_start(new_start)
        assert base_event.start_date == new_start

    def test_set_end_valid(self, base_event):
        new_end = datetime(2026, 6, 1, 14, 0, tzinfo=_TZ)
        base_event.set_end(new_end)
        assert base_event.end_date == new_end

    def test_set_end_raises_if_equal_to_start(self, base_event):
        with pytest.raises(ValueError):
            base_event.set_end(START)

    def test_set_end_raises_if_before_start(self, base_event):
        with pytest.raises(ValueError):
            base_event.set_end(datetime(2026, 5, 31, 9, 0, tzinfo=_TZ))

    def test_expire_sets_is_active_false(self, base_event):
        base_event.expire()
        assert base_event.is_active is False

    def test_set_description(self, base_event):
        base_event.set_description("Nuova descrizione")
        assert base_event.description == "Nuova descrizione"

    def test_remove_description_sets_none(self, base_event):
        base_event.remove_description()
        assert base_event.description is None


# Event: get_message


class TestEventGetMessage:

    def test_message_contains_name(self, base_event):
        assert "Riunione" in base_event.get_message()

    def test_message_contains_formatted_start_date(self, base_event):
        msg = base_event.get_message()
        assert "01/06/2026" in msg
        assert "10:00" in msg

    def test_message_contains_formatted_end_date(self, base_event):
        assert "12:00" in base_event.get_message()

    def test_message_contains_description_when_present(self, base_event):
        assert "Riunione settimanale" in base_event.get_message()

    def test_message_omits_description_when_absent(self):
        e = Event("Test", START, END)
        msg = e.get_message()
        assert "None" not in msg
        assert "Test" in msg


# Event: serialization


class TestEventSerialization:

    def test_to_dict_type_field(self, base_event):
        assert base_event.to_dict()["type"] == "single_time"

    def test_to_dict_contains_all_expected_keys(self, base_event):
        d = base_event.to_dict()
        for key in (
            "type",
            "id",
            "name",
            "start_date",
            "end_date",
            "description",
            "is_active",
        ):
            assert key in d

    def test_round_trip_preserves_all_fields(self, base_event):
        restored = Event.from_dict(base_event.to_dict())
        assert restored.id == base_event.id
        assert restored.name == base_event.name
        assert restored.start_date == base_event.start_date
        assert restored.end_date == base_event.end_date
        assert restored.description == base_event.description
        assert restored.is_active == base_event.is_active

    def test_from_dict_is_active_defaults_to_true_when_key_missing(self):
        d = Event("X", START, END).to_dict()
        d.pop("is_active")
        assert Event.from_dict(d).is_active is True

    def test_from_dict_description_is_none_when_key_missing(self):
        d = Event("X", START, END).to_dict()
        d.pop("description")
        assert Event.from_dict(d).description is None


# relativedelta helpers


class TestRelativeDeltaHelpers:

    def test_round_trip_with_all_units(self):
        rd = relativedelta(years=1, months=2, days=3, hours=4, minutes=5, seconds=6)
        assert relativedelta_from_dict(relativedelta_to_dict(rd)) == rd

    def test_to_dict_contains_all_unit_keys(self):
        d = relativedelta_to_dict(relativedelta(days=1))
        for key in ("years", "months", "days", "hours", "minutes", "seconds"):
            assert key in d

    def test_from_dict_empty_dict_gives_zero_delta(self):
        assert relativedelta_from_dict({}) == relativedelta()

    def test_from_dict_partial_dict(self):
        assert relativedelta_from_dict({"days": 3}) == relativedelta(days=3)


# RecurringEvent: construction


class TestRecurringEventConstruction:

    def test_fields_stored(self, recurring_event):
        assert recurring_event.period == DELTA
        assert recurring_event.remaining_occurrences == 3

    def test_raises_on_zero_occurrences(self):
        with pytest.raises(ValueError):
            RecurringEvent("X", START, END, DELTA, remaining_occurrences=0)

    def test_raises_on_negative_occurrences(self):
        with pytest.raises(ValueError):
            RecurringEvent("X", START, END, DELTA, remaining_occurrences=-1)

    def test_description_defaults_to_none(self):
        assert (
            RecurringEvent("X", START, END, DELTA, remaining_occurrences=2).description
            is None
        )


# RecurringEvent: decrease_occurrences


class TestDecreaseOccurrences:

    def test_decrements_remaining_count(self, recurring_event):
        recurring_event.decrease_occurrences()
        assert recurring_event.remaining_occurrences == 2

    def test_advances_start_date_by_period(self, recurring_event):
        recurring_event.decrease_occurrences()
        assert recurring_event.start_date == START + DELTA

    def test_advances_end_date_by_period(self, recurring_event):
        recurring_event.decrease_occurrences()
        assert recurring_event.end_date == END + DELTA

    def test_expires_after_last_occurrence(self, recurring_event):
        for _ in range(3):
            recurring_event.decrease_occurrences()
        assert recurring_event.is_active is False

    def test_remaining_does_not_go_below_one(self, recurring_event):
        for _ in range(5):
            recurring_event.decrease_occurrences()
        assert recurring_event.remaining_occurrences >= 1

    def test_dates_do_not_advance_after_expiry(self, recurring_event):
        for _ in range(3):
            recurring_event.decrease_occurrences()
        frozen_start = recurring_event.start_date
        recurring_event.decrease_occurrences()
        assert recurring_event.start_date == frozen_start


# RecurringEvent: get_message


class TestRecurringEventGetMessage:

    def test_message_contains_name(self, recurring_event):
        assert "Stand-up" in recurring_event.get_message()

    def test_message_shows_remaining_minus_one(self, recurring_event):
        assert "2" in recurring_event.get_message()

    def test_message_inherits_dates_from_base(self, recurring_event):
        assert "01/06/2026" in recurring_event.get_message()


# RecurringEvent: serialization


class TestRecurringEventSerialization:

    def test_to_dict_type_field(self, recurring_event):
        assert recurring_event.to_dict()["type"] == "recurring"

    def test_to_dict_has_period_and_occurrences(self, recurring_event):
        d = recurring_event.to_dict()
        assert "period" in d
        assert "remaining_occurrences" in d

    def test_round_trip_preserves_all_fields(self, recurring_event):
        restored = RecurringEvent.from_dict(recurring_event.to_dict())
        assert restored.id == recurring_event.id
        assert restored.period == recurring_event.period
        assert restored.remaining_occurrences == recurring_event.remaining_occurrences
        assert restored.start_date == recurring_event.start_date
        assert restored.end_date == recurring_event.end_date

    def test_from_dict_is_active_defaults_to_true_when_key_missing(self):
        d = RecurringEvent("X", START, END, DELTA, 2).to_dict()
        d.pop("is_active")
        assert RecurringEvent.from_dict(d).is_active is True

    def test_from_dict_description_is_none_when_key_missing(self):
        d = RecurringEvent("X", START, END, DELTA, 2).to_dict()
        d.pop("description", None)
        assert RecurringEvent.from_dict(d).description is None


# Reminder: construction


class TestReminderConstruction:

    def test_fields_stored(self, reminder):
        assert reminder.id == "fixed-id-003"
        assert reminder.name == "Pillola"
        assert reminder.start_date == START
        assert reminder.description == "Prendere la pillola"
        assert reminder.is_active is True

    def test_end_date_mirrors_start_date(self, reminder):
        assert reminder.end_date == reminder.start_date

    def test_set_end_raises_attribute_error(self, reminder):
        with pytest.raises(AttributeError):
            reminder.set_end(datetime(2026, 6, 2, 10, 0, tzinfo=_TZ))

    def test_auto_uuid_when_no_id_given(self):
        assert len(Reminder("X", START, "desc").id) == 36


# Reminder: get_message


class TestReminderGetMessage:

    def test_message_contains_name(self, reminder):
        assert "Pillola" in reminder.get_message()

    def test_message_contains_formatted_start_date(self, reminder):
        msg = reminder.get_message()
        assert "01/06/2026" in msg
        assert "10:00" in msg

    def test_message_contains_description(self, reminder):
        assert "Prendere la pillola" in reminder.get_message()

    def test_message_does_not_contain_end_time(self, reminder):
        assert "12:00" not in reminder.get_message()


# Reminder: serialization


class TestReminderSerialization:

    def test_to_dict_type_field(self, reminder):
        assert reminder.to_dict()["type"] == "reminder"

    def test_to_dict_has_no_end_date_key(self, reminder):
        assert "end_date" not in reminder.to_dict()

    def test_to_dict_contains_required_keys(self, reminder):
        d = reminder.to_dict()
        for key in ("type", "id", "name", "start_date", "description", "is_active"):
            assert key in d

    def test_round_trip_preserves_all_fields(self, reminder):
        restored = Reminder.from_dict(reminder.to_dict())
        assert restored.id == reminder.id
        assert restored.name == reminder.name
        assert restored.start_date == reminder.start_date
        assert restored.description == reminder.description
        assert restored.is_active == reminder.is_active

    def test_from_dict_is_active_defaults_to_true_when_key_missing(self):
        d = Reminder("X", START, "desc").to_dict()
        d.pop("is_active")
        assert Reminder.from_dict(d).is_active is True


# event_from_dict: registry dispatch


class TestEventFromDict:

    def test_returns_event_for_single_time(self, base_event):
        assert isinstance(event_from_dict(base_event.to_dict()), Event)

    def test_returns_recurring_event_for_recurring(self, recurring_event):
        assert isinstance(event_from_dict(recurring_event.to_dict()), RecurringEvent)

    def test_returns_reminder_for_reminder(self, reminder):
        assert isinstance(event_from_dict(reminder.to_dict()), Reminder)

    def test_raises_value_error_for_unknown_type(self):
        with pytest.raises(ValueError):
            event_from_dict({"type": "unknown_type"})

    def test_raises_value_error_when_type_key_missing(self):
        with pytest.raises(ValueError):
            event_from_dict({})
