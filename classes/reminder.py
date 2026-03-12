from datetime import datetime
from typing import Optional


class Reminder:
    def __init__(self, name: str, start_date: datetime, description: Optional[str]):
        self.name = name
        self.start_date = start_date
        self.description = description
    
    #def alert(self, bot=None, chat_id=None):
    #    """
    #    Metodo pensato per integrarsi con python-telegram-bot.
    #    Per ora stampa un messaggio, ma può essere collegato al bot.
    #    """
    #    message = f"🔔 Promemoria: {self.name}\n📅 Quando: {self.start_date}\n📝 {self.description}"
    #
    #    if bot and chat_id:
    #        bot.send_message(chat_id=chat_id, text=message)
    #    else:
    #        print(message)
    
    def update_date(self, new_start_date: datetime):
        """Aggiorna la data di inizio del reminder."""
        self.start_date = new_start_date

    def update_description(self, new_description: str):
        """Aggiorna la descrizione del reminder."""
        self.description = new_description

    def __str__(self):
        return f"Reminder(name='{self.name}', start_date='{self.start_date}', description='{self.description}')"


int main():
    pass

if __name__ == "__main__":
    main()