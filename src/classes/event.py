from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from dateutil.relativedelta import relativedelta

class Event:
    TYPE="single_time"

    def __init__(self, name:str, start_date: datetime, end_date: datetime, description: Optional[str] = None, is_active: bool = True, event_id: Optional[str] = None):
        self.id             = event_id or str(uuid.uuid4())
        self.name           = name
        self.start_date     = start_date
        end_date            = end_date
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
            event_id        = data["id"],
            name            = data["name"],
            start_date      = datetime.fromisoformat(data["start_date"]),
            end_date        = datetime.fromisoformat(data["end_date"]),
            description     = data.get("description"),
            is_active       = data.get("is_active", True)
        )
    
# TODO :    Refactor the logic to handle recurrent events
#           Write the subclass Recurrent Events and their logics
#           Test the I/O from files of both classes