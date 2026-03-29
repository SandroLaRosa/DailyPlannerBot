## Daily Planner bot

Un bot di telegram dedicato alla gestione di eventi e promemoria.
Il bot include diverse funzionalità, tra cui:
- Gestione di diverse tipologie di eventi (eventi semplici, eventi ricorrenti o promemoria)
- Scheduling di Eventi
- Persistenza di eventi tramite I/O su file
- Recap impegni Giornalieri

### How to start (one-time step)

Clona il contenuto di questa repo eseguendo:

```bash
git clone git@github.com:SandroLaRosa/DailyPlannerBot.git
```

Entra nella nuova directory che è apparsa eseguendo:

```bash
cd DailyPlannerBot
```

Crea un virtualenv:

```bash
python3 -m pip install venv
python3 -m venv venv
source ./venv/bin/activate
```

Una volta eseguiti i comandi precedenti vedrai `(venv)` nel tuo terminale, se ciò accade perfetto adesso stai usando la versione di python e i pacchetti presenti in esso.

Adesso possiamo procedere con l'installazione delle dipendenze:

```bash
pip install -r requirements.txt
```

⚠️ Note: Dovrai sempre eseguire `source ./venv/bin/activate` ogni volta che aprirai un nuovo terminale per eseguire codice dal virtualenv.

Prima di continuare:
```bash
cd src
echo TOKEN= > .env && echo BOT_LANG=it >> .env && echo BOT_TZ=Europe/Rome >> .env
cd ..
```
Noterai che all'interno di src è adesso apparso un file ".env", all'interno di questo file dovrai incollare il tuo token generato da BotFather su telegram appena dopo "TOKEN="

Perfetto adesso sei pronto per poter utilizzare il bot, basta eseguire:

```bash
python3 -m src.bot
```

Finchè il processo del bot sarà attivo, potrai usare DailyPlannerBot.
Qualora il processo venisse arrestato, si suggerisce di usare il comando /restart.


### Alcuni comandi disponibili in chat:

- /start          :   Comando che avvia il bot
- /help           :   Comando che stampa un elenco dei comandi disponibili
- /crea_evento    :   Avvio di una conversazione alla fine della quale viene creato un evento di un dato tipo
- /recap          :   Avvio di una conversazione alla fine della quale viene stampata una lista degli eventi di un dato giorno
- /restart        :   Reset di una conversazione dopo che il bot è crashato

---
### Contributing

Sviluppato e mantenuto da:
Alessandro La Rosa
Flavio Miccichè