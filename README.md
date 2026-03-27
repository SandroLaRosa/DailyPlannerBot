# Daily Planner Bot

## Descrizione:
Un bot di telegram dedicato alla gestione di eventi e promemoria.
Il bot include diverse funzionalità, tra cui:
- Gestione di diverse tipologie di eventi (semplici eventi, eventi ricorrenti o promemoria)
- Scheduling di Eventi
- Persistenza degli eventi tramite I/O su file
- Recap Impegni Giornalieri

### Guida all'installazione:
Per il corretto funzionamento del bot occorre creare un file .env all'interno del folder.
Esiste a tal proposito un file .env* che è un file contenente tutti i campi richiesti dal bot
per funzionare, in particolare, occorre inserire il proprio token di telegram prodotto da
@BotFather nel campo Token.
È inoltre consigliato l'utilizzo degli altri due campi di .env (anche se il bot prevede meccanismi
di fallback a settaggi standard) è comodo poter variare la propria timezone e la lingua dal file di
configurazione.

Si suggerisce l'utilizzo di un virtual environment, all'interno del quale è necessario installare le
dipendenze incluse nel file requirements.txt

### Guida all'utilizzo
Per attivare il bot, basta semplicemente eseguire lo script bot.py sul proprio device.
Finché lo script rimarrà in esecuzione il bot funzionerà correttamente.
In caso il processo del bot venga arrestato, basta farlo ripartire e in chat eseguire il comando /start.

#### Credits:
Sviluppato e mantenuto da:
Alessandro La Rosa
Flavio Miccichè