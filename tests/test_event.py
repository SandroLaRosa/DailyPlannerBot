from datetime import datetime

import pytest
from dateutil.relativedelta import relativedelta

from src.classes.event import (
    Event,
    RecurringEvent,
    Reminder,
    event_from_dict,
    relativedelta_from_dict,
    relativedelta_to_dict,
)
from src.modules.timezone_logics import TZ

START = datetime(2026, 6, 1, 10, 0, tzinfo=TZ)
END = datetime(2026, 6, 1, 12, 0, tzinfo=TZ)
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
    def test_fields_are_stored(self, base_event):
        assert base_event.id == "fixed-id-001"
        assert base_event.name == "Riunione"
        assert base_event.start_date == START
        assert base_event.end_date == END
        assert base_event.description == "Riunione settimanale"
        assert base_event.is_active is True

    def test_auto_uuid_when_no_id_given(self):
        e = Event("Test", START, END)
        assert e.id is not None
        assert len(e.id) == 36  # standard UUID4 length

    def test_description_defaults_to_none(self):
        e = Event("Test", START, END)
        assert e.description is None


# Event: setters
class TestEventSetters:
    def test_set_name(self, base_event):
        base_event.set_name("Nuova riunione")
        assert base_event.name == "Nuova riunione"

    def test_set_start(self, base_event):
        new_start = datetime(2026, 6, 2, 9, 0, tzinfo=TZ)
        base_event.set_start(new_start)
        assert base_event.start_date == new_start

    def test_set_end_valid(self, base_event):
        new_end = datetime(2026, 6, 1, 14, 0, tzinfo=TZ)
        base_event.set_end(new_end)
        assert base_event.end_date == new_end

    def test_set_end_raises_if_equal_to_start(self, base_event):
        with pytest.raises(ValueError):
            base_event.set_end(START)

    def test_set_end_raises_if_before_start(self, base_event):
        with pytest.raises(ValueError):
            base_event.set_end(datetime(2026, 5, 31, 9, 0, tzinfo=TZ))

    def test_expire_sets_inactive(self, base_event):
        base_event.expire()
        assert base_event.is_active is False

    def test_set_description(self, base_event):
        base_event.set_description("Nuova descrizione")
        assert base_event.description == "Nuova descrizione"

    def test_remove_description(self, base_event):
        base_event.remove_description()
        assert base_event.description is None


# Event: get_message
class TestEventGetMessage:
    def test_message_contains_name(self, base_event):
        assert "Riunione" in base_event.get_message()

    def test_message_contains_formatted_dates(self, base_event):
        msg = base_event.get_message()
        assert "01/06/2026" in msg
        assert "10:00" in msg

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

    def test_to_dict_contains_all_keys(self, base_event):
        keys = base_event.to_dict().keys()
        for expected in (
            "type",
            "id",
            "name",
            "start_date",
            "end_date",
            "description",
            "is_active",
        ):
            assert expected in keys

    def test_round_trip(self, base_event):
        restored = Event.from_dict(base_event.to_dict())
        assert restored.id == base_event.id
        assert restored.name == base_event.name
        assert restored.start_date == base_event.start_date
        assert restored.end_date == base_event.end_date
        assert restored.description == base_event.description
        assert restored.is_active == base_event.is_active


# Helper: relativedelta helpers
class TestRelativeDeltaHelpers:
    def test_round_trip(self):
        rd = relativedelta(years=1, months=2, days=3, hours=4, minutes=5, seconds=6)
        assert relativedelta_from_dict(relativedelta_to_dict(rd)) == rd

    def test_missing_keys_default_to_zero(self):
        assert relativedelta_from_dict({}) == relativedelta()


# RecurringEvent: construction
class TestRecurringEventConstruction:
    def test_fields_are_stored(self, recurring_event):
        assert recurring_event.period == DELTA
        assert recurring_event.remaining_occurrences == 3

    def test_raises_if_occurrences_less_than_one(self):
        with pytest.raises(ValueError):
            RecurringEvent("X", START, END, DELTA, remaining_occurrences=0)


# RecurringEvent: decrease_occurrences
class TestDecreaseOccurrences:
    def test_decrements_count(self, recurring_event):
        recurring_event.decrease_occurrences()
        assert recurring_event.remaining_occurrences == 2

    def test_advances_dates_by_period(self, recurring_event):
        recurring_event.decrease_occurrences()
        assert recurring_event.start_date == START + DELTA
        assert recurring_event.end_date == END + DELTA

    def test_expires_on_last_occurrence(self, recurring_event):
        for _ in range(3):
            recurring_event.decrease_occurrences()
        assert recurring_event.is_active is False

    def test_remaining_never_goes_below_one(self, recurring_event):
        for _ in range(5):
            recurring_event.decrease_occurrences()
        assert recurring_event.remaining_occurrences >= 1


# RecurringEvent: get_message
class TestRecurringEventGetMessage:
    def test_message_contains_name(self, recurring_event):
        assert "Stand-up" in recurring_event.get_message()

    def test_message_contains_remaining_count(self, recurring_event):
        assert "2" in recurring_event.get_message()

    def test_message_builds_on_base_get_message(self, recurring_event):
        assert "01/06/2026" in recurring_event.get_message()


# RecurringEvent: serialization
class TestRecurringEventSerialization:
    def test_to_dict_type_field(self, recurring_event):
        assert recurring_event.to_dict()["type"] == "recurring"

    def test_to_dict_contains_period_and_occurrences(self, recurring_event):
        d = recurring_event.to_dict()
        assert "period" in d
        assert "remaining_occurrences" in d

    def test_round_trip(self, recurring_event):
        restored = RecurringEvent.from_dict(recurring_event.to_dict())
        assert restored.id == recurring_event.id
        assert restored.period == recurring_event.period
        assert restored.remaining_occurrences == recurring_event.remaining_occurrences
        assert restored.start_date == recurring_event.start_date
        assert restored.end_date == recurring_event.end_date


# Reminder: construction
class TestReminderConstruction:
    def test_fields_are_stored(self, reminder):
        assert reminder.id == "fixed-id-003"
        assert reminder.name == "Pillola"
        assert reminder.start_date == START
        assert reminder.description == "Prendere la pillola"
        assert reminder.is_active is True

    def test_end_date_mirrors_start_date(self, reminder):
        # Reminder has no end_date; internally it is set equal to start_date
        assert reminder.end_date == reminder.start_date

    def test_set_end_raises_attribute_error(self, reminder):
        with pytest.raises(AttributeError):
            reminder.set_end(datetime(2026, 6, 2, 10, 0, tzinfo=TZ))


# Reminder: get_message
class TestReminderGetMessage:
    def test_message_contains_name(self, reminder):
        assert "Pillola" in reminder.get_message()

    def test_message_contains_formatted_start_date(self, reminder):
        assert "01/06/2026" in reminder.get_message()
        assert "10:00" in reminder.get_message()

    def test_message_contains_description(self, reminder):
        assert "Prendere la pillola" in reminder.get_message()


# Reminder: serialization
class TestReminderSerialization:
    def test_to_dict_type_field(self, reminder):
        assert reminder.to_dict()["type"] == "reminder"

    def test_to_dict_has_no_end_date_key(self, reminder):
        assert "end_date" not in reminder.to_dict()

    def test_to_dict_contains_required_keys(self, reminder):
        for key in ("type", "id", "name", "start_date", "description", "is_active"):
            assert key in reminder.to_dict()

    def test_round_trip(self, reminder):
        restored = Reminder.from_dict(reminder.to_dict())
        assert restored.id == reminder.id
        assert restored.name == reminder.name
        assert restored.start_date == reminder.start_date
        assert restored.description == reminder.description
        assert restored.is_active == reminder.is_active


# Generic: Type Assertion (EventFromDict)
class TestEventFromDict:
    def test_returns_event_for_single_time(self, base_event):
        assert isinstance(event_from_dict(base_event.to_dict()), Event) is True

    def test_returns_recurring_event_for_recurring(self, recurring_event):
        assert isinstance(event_from_dict(recurring_event.to_dict()), RecurringEvent) is True

    def test_returns_reminder_for_reminder(self, reminder):
        assert isinstance(event_from_dict(reminder.to_dict()), Reminder) is True

    def test_raises_for_unknown_type(self):
        with pytest.raises(ValueError):
            event_from_dict({"type": "unknown_type"})
