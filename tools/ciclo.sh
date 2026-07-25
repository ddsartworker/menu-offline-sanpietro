#!/usr/bin/env bash
# Cattura il menu ogni quarto d'ora restando acceso per ore.
#
# GitHub limita le esecuzioni programmate - ne chiedevamo quattro all'ora e ne
# arrivava una - ma non limita la durata di una singola esecuzione, che puo'
# arrivare a sei ore. Invece di farsi svegliare da fuori, quindi, si resta
# accesi e si cattura a intervalli regolari. Sui repository pubblici i minuti
# di esecuzione sono gratuiti.
#
# Niente `set -e`: un giro andato male non deve spegnere il ciclo. Se Menumal
# non risponde adesso, fra un quarto d'ora ci riprova.
set -uo pipefail

INTERVALLO=${INTERVALLO:-900}      # 15 minuti
DURATA=${DURATA:-19200}            # 5h20m: sta dentro il limite di 6 ore con margine

scadenza=$(( $(date +%s) + DURATA ))
giro=0
riusciti=0
falliti=0

echo "Ciclo avviato: un giro ogni $((INTERVALLO / 60)) minuti per $((DURATA / 3600))h circa"

while [ "$(date +%s)" -lt "$scadenza" ]; do
  giro=$((giro + 1))
  inizio=$(date +%s)
  echo ""
  echo "########## giro $giro - $(date -u '+%F %H:%M:%S') UTC ##########"

  if bash tools/capture.sh; then
    if bash tools/publish.sh; then
      riusciti=$((riusciti + 1))
    else
      falliti=$((falliti + 1))
      echo "!! pubblicazione non riuscita, si riprova al prossimo giro"
    fi
  else
    falliti=$((falliti + 1))
    echo "!! cattura non riuscita, si riprova al prossimo giro"
  fi

  # L'attesa tiene conto del tempo gia' speso: un giro dura qualche minuto e
  # dormire sempre 15 minuti pieni sfalserebbe la cadenza.
  speso=$(( $(date +%s) - inizio ))
  resta=$(( INTERVALLO - speso ))
  rimanente=$(( scadenza - $(date +%s) ))

  # Se non c'e' tempo per un altro giro intero, meglio chiudere e lasciare che
  # riparta l'esecuzione successiva, invece di farsi interrompere a meta'.
  if [ "$rimanente" -lt $(( INTERVALLO + 600 )) ]; then
    echo "tempo quasi esaurito, il ciclo si chiude qui"
    break
  fi

  if [ "$resta" -gt 0 ]; then
    echo "prossimo giro fra $((resta / 60)) minuti"
    sleep "$resta"
  fi
done

echo ""
echo "Ciclo concluso: $giro giri, $riusciti riusciti, $falliti falliti"
