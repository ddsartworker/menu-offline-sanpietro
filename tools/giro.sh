#!/usr/bin/env bash
# Un giro completo: cattura il menu e lo pubblica se e' cambiato.
#
# La parte interessante e' cosa succede quando va storto. Menumal ogni tanto
# non risponde, il runner ogni tanto e' lento: sono buchi che si richiudono da
# soli al giro dopo. Se ognuno di quelli accendesse un allarme, l'allarme
# diventerebbe rumore - ed e' esattamente com'e' andata: ad agosto 2026 il menu
# e' rimasto fermo sei giorni dentro una mail di fallimento ogni quarto d'ora,
# indistinguibile dalle altre.
#
# Quindi la regola non e' "questo giro e' andato male" ma "il menu sul tablet e'
# vecchio". Un giro storto con un menu fresco alle spalle passa in silenzio; un
# menu fermo da ore fa fallire il workflow, e la sentinella (tools/guardia.sh)
# apre una segnalazione che si vede.
set -uo pipefail

TOLLERANZA=${TOLLERANZA:-10800}   # 3 ore, cioe' dodici giri mancati di fila

if bash tools/capture.sh && bash tools/publish.sh; then
  exit 0
fi

eta=$(bash tools/eta.sh) || {
  echo "ERRORE: giro fallito e non riesco nemmeno a leggere l'eta' del menu pubblicato" >&2
  exit 1
}

if [ "$eta" -lt "$TOLLERANZA" ]; then
  echo "Giro storto, ma il menu pubblicato ha $((eta / 60)) minuti: si riprova al prossimo."
  exit 0
fi

echo "ERRORE: menu pubblicato fermo da $((eta / 3600))h $(((eta % 3600) / 60))m e il giro non lo rinnova" >&2
exit 1
