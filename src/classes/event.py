from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from dateutil.relativedelta import relativedelta

from modules.timezone_logics import TZ

class Event:
    TYPE="single_time"

    def __init__(self, name:str, start_date: datetime, end_date: datetime, description: Optional[str] = None, is_active: bool = True, event_id: Optional[str] = None):
        self.id             = event_id or str(uuid.uuid4())
        self.name           = name
        self.start_date     = start_date
        self.end_date            = end_date
        self.description    = description
        self.is_active      = is_active
    
    # setters ----------------------------------------------------------
    
    def set_name(self, new_value: str)->None:
        self.name = new_value

    def set_start(self, new_value: datetime)->None:
        self.start_date = new_value

    def set_end(self, new_value: datetime)->None:
        if new_value <= self.start_date:
            raise ValueError("An event can't end before it start.")
        self.end_date = new_value
    
    def set_description(self, new_value: str)->None:
        self.description=new_value
    
    # modifiers --------------------------------------------------------
    
    def remove_description(self)->None:
        self.description=None
    
    def expire(self):
        self.is_active=False
    
    # getter -----------------------------------------------------------

    def get_message(self)->str:
        start_str   = self.start_date.strftime("%d/%m/%Y %H:%M")
        end_str     = self.end_date.strftime("%d/%m/%Y %H:%M")
        message = [
            f"{self.name}",
            f"from:\t{start_str}\t{end_str}",
        ]
        if self.description:
            message.append(f"{self.description}")
        return "\n".join(message)
    
    def to_dict(self)-> dict:
        return {
            "type":         self.TYPE,
            "id":           self.id,
            "name":         self.name,
            "start_date":   self.start_date.isoformat(),
            "end_date":     self.end_date.isoformat(),
            "description":  self.description,
            "is_active":    self.is_active,
        }
    
    # ClassMethods ----------------------------------------------------

    @classmethod
    def from_dict(cls, data:dict)->Event:
        return cls(
            name            = data["name"],
            start_date      = datetime.fromisoformat(data["start_date"]).replace(tzinfo=TZ),
            end_date        = datetime.fromisoformat(data["end_date"]).replace(tzinfo=TZ),
            description     = data.get("description"),
            is_active       = data.get("is_active", True),
            event_id        = data["id"]
        )

# helpers specific to subclass time management-----------------

def relativedelta_to_dict(rd: relativedelta)->dict:
    return {
        "years":    rd.years,
        "months":   rd.months,
        "days":     rd.days,
        "hours":    rd.hours,
        "minutes":  rd.minutes,
        "seconds":  rd.seconds,
    }

def relativedelta_from_dict(d: dict)->relativedelta:
    return relativedelta(
        years=d.get("years", 0),
        months=d.get("months", 0),
        days=d.get("days", 0),
        hours=d.get("hours", 0),
        minutes=d.get("minutes", 0),
        seconds=d.get("seconds", 0),
    )

# Subclass ----------------------------------------------------


class RecurringEvent(Event):
    TYPE="recurring"
    
    def __init__(self, name:str, start_date: datetime, end_date: datetime,period:relativedelta, remaining_occurrences:int, description: Optional[str] = None, is_active: bool = True, event_id: Optional[str] = None):
        super().__init__(name, start_date,end_date, description, is_active, event_id)
        if remaining_occurrences <1:
            raise ValueError("remaining occurrences must be at least 1.")
        self.period                 = period
        self.remaining_occurrences  = remaining_occurrences

    # subclass main logics

    def decrease_occurrences(self)->None:       #this is the logic called after each notification is sent for a recurrent event
        if self.remaining_occurrences > 1:
            self.remaining_occurrences -= 1
            self.start_date = self.start_date + self.period
            self.end_date   = self.end_date + self.period
        else:
            self.expire()

    def get_message(self):
        baseline = super().get_message()
        return baseline + f"\n Remaining ripetition {self.remaining_occurrences-1}."

    def to_dict(self)->dict:
        data = super().to_dict()
        data["period"]                  = relativedelta_to_dict(self.period)
        data["remaining_occurrences"]   = self.remaining_occurrences
        return data
    
    @classmethod
    def from_dict(cls, data:dict)->RecurringEvent:
        return cls(
            name                   = data["name"],
            start_date             = datetime.fromisoformat(data["start_date"]).replace(tzinfo=TZ),
            end_date               = datetime.fromisoformat(data["end_date"]).replace(tzinfo=TZ),
            period                 = relativedelta_from_dict(data["period"]),
            remaining_occurrences  = data["remaining_occurrences"],
            description            = data.get("description"),
            is_active              = data.get("is_active", True),
            event_id               = data["id"]
        )

class Reminder(Event):
    TYPE = "reminder"
    def __init__(self, name:str, start_date:datetime, description:str, is_active:bool = True, event_id: Optional[str] = None):
        super().__init__(name, start_date, end_date=start_date, description=description, is_active=is_active, event_id=event_id)
    def set_end(self, new_value):
        raise AttributeError("Reminder has no end date.")
    
    def get_message(self) -> str:
        start_str = self.start_date.strftime("%d/%m/%Y %H:%M")
        return "\n".join([
            f"{self.name}",
            f"alle:\t{start_str}",
            f"{self.description}",
        ])
    
    def to_dict(self) -> dict:
        return {
            "type":         self.TYPE,
            "id":           self.id,
            "name":         self.name,
            "start_date":   self.start_date.isoformat(),
            "description":  self.description,
            "is_active":    self.is_active,
        }
 
    @classmethod
    def from_dict(cls, data: dict) -> Reminder:
        return cls(
            name        = data["name"],
            start_date  = datetime.fromisoformat(data["start_date"]).replace(tzinfo=TZ),
            description = data["description"],
            is_active   = data.get("is_active", True),
            event_id    = data["id"],
        )

# Generic event Loader from JSON

Registry: dict[str, type[Event]]={
    Event.TYPE:             Event,
    RecurringEvent.TYPE:    RecurringEvent,
    Reminder.TYPE:          Reminder
}

def event_from_dict(data: dict)->Event:
    event_cls = Registry.get(data.get("type", ""))
    if event_cls is None:
        raise ValueError(f"Unknown event type '{data.get('type')}'")
    return event_cls.from_dict(data)