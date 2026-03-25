from __future__ import annotations

import json
import os

from datetime import datetime
from typing import Callable

from telegram.ext import Application

from classes.event import Event, RecurringEvent, event_from_dict

#File Management

DATA_DIRECTORY  = os.path.join(os.path.dirname(__file__), "..", "data")
ONGOING_FILE    = os.path.join(DATA_DIRECTORY, "ongoing_events.json")
EXPIRED_FILE    = os.path.join(DATA_DIRECTORY, "expired_events.json")
MISSED_FILE     = os.path.join(DATA_DIRECTORY, "missed_events.json")

def ensure_data_dir() -> None:
    os.makedirs(DATA_DIRECTORY, exist_ok=True)

def load_json(fpath: str) -> list[dict]:
    if not os.path.exists(fpath):
        return []
    with open(fpath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_json(events: list[Event], fpath: str) -> None:
    ensure_data_dir()
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump([e.to_dict() for e in events], f, indent=2, ensure_ascii=False)

def append_json(event: Event, fpath: str) -> None:
    record = load_json(fpath)
    record.append(event.to_dict())
    ensure_data_dir()
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(record,f,indent=2,ensure_ascii=False)

# Class

class EventManager:
    
    def __init__(self) -> None:
        self.events: dict[str, Event] = {}
    
    def load_ongoing(self) -> tuple[list[Event], list[Event]]:
        now = datetime.now()
        missed: list[Event] = []
        ongoing: list[Event] = []

        for obj in load_json(ONGOING_FILE):
            try:
               instance=event_from_dict(obj)
            except (KeyError, ValueError):
                continue

            if instance.start_date <= now:
                missed.append(instance)
            else:
                ongoing.append(instance)
                self.events[instance.id] = instance
        
        for instance in missed:
            append_json(instance, MISSED_FILE)
   
        save_json(ongoing, ONGOING_FILE)
        return ongoing, missed
    
    def save_ongoing(self)->None:
        save_json(list(self.events.values()), ONGOING_FILE)
    
    def move_to_expired(self, event:Event)->None:
        self.events.pop(event.id, None)
        append_json(event, EXPIRED_FILE)
        self.save_ongoing()
    
    def schedule(self, event:Event, app:Application, callback:Callable)->None:
        app.job_queue.run_once(
            callback,
            when=event.start_date,
            name=event.id,
            data=event.id,
        )

    def deschedule(self, event:Event, app:Application)->None:
        for job in app.job_queue.get_jobs_by_name(event.id):
            job.schedule_removal()
    
    def add_event(self, event:Event, app:Application, callback:Callable) -> None:
        self.events[event.id] = event
        self.schedule(event, app, callback)
        self.save_ongoing()
    
    def expire_event(self, event_id: str) -> None:
        event = self.events.get(event_id)
        if event is None:
            return
        if isinstance(event, RecurringEvent):
            event.decrease_occurrences()
            if event.is_active:
                self.save_ongoing()
                return
        event.expire()
        self.move_to_expired(event)

    def update_event(self, event_id:str, new_start:datetime, new_end:datetime, app:Application, callback:Callable)->None:
        event=self.events[event_id]
        self.deschedule(event, app)
        event.set_start(new_start)
        event.set_end(new_end)
        self.schedule(event, app, callback)
        self.save_ongoing()
    
    def remove_event(self, event_id:str, app:Application)->None:
        event=self.events.get(event_id)
        if event is None:
            return
        self.deschedule(event,app)
        self.events.pop(event_id)
        self.save_ongoing()