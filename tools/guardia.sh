#!/usr/bin/env bash
# La sentinella: controlla che il menu sul tablet non sia vecchio, e se lo e'
# apre una segnalazione.
#
# Serve una cosa sola che non c'era: un avviso che si distingua. Le mail di
# fallimento di GitHub Actions arrivavano gia', ma quattro all'ora anche per i
# buchi che si richiudono da soli, quindi non le guardava piu' nessuno. Qui la
# segnalazione e' una issue, se ne apre una sola per volta e si richiude da sola
# quando il menu riparte: se ne arriva la mail, e' successo qualcosa davvero.
set -uo pipefail

SOGLIA=${SOGLIA:-10800}      # 3 ore senza un aggiornamento pubblicato
ETICHETTA="menu-fermo"
TITOLO="Il menu sul tablet non si aggiorna piu'"

# Su Actions arriva dall'ambiente; lanciandolo dal portatile per provare, no.
repo="${GITHUB_REPOSITORY:-ddsartworker/menu-offline-sanpietro}"

eta=$(bash tools/eta.sh) || {
  # Nemmeno leggere version.json: puo' essere la rete del runner. Fra un'ora si
  # riprova; se e' davvero giu', il giro dopo se ne accorge lo stesso.
  echo "Eta' del menu non leggibile, riprovo al prossimo giro."
  exit 0
}

ore=$((eta / 3600))
minuti=$(((eta % 3600) / 60))

gh label create "$ETICHETTA" --color B60205 \
  --description "Il menu pubblicato non si rinnova" >/dev/null 2>&1 || true

aperta=$(gh issue list --label "$ETICHETTA" --state open --json number --jq '.[0].number // empty')

if [ "$eta" -lt "$SOGLIA" ]; then
  echo "Menu aggiornato ${ore}h ${minuti}m fa: tutto a posto."
  if [ -n "$aperta" ]; then
    gh issue close "$aperta" \
      --comment "Il menu ha ripreso ad aggiornarsi: ultimo snapshot ${ore}h ${minuti}m fa. Chiudo da sola."
    echo "Segnalazione #$aperta chiusa."
  fi
  exit 0
fi

# Il testo si scrive su un file invece che dentro `corpo=$(cat <<EOF ...)`: il
# bash 3.2 del portatile non sa contare le parentesi dei link markdown dentro
# una sostituzione di comando e si ferma con un errore di sintassi. Sui runner
# (bash 5) andrebbe, ma uno script che gira solo meta' delle volte non serve.
corpo=$(mktemp -t guardia-XXXXXX)
trap 'rm -f "$corpo"' EXIT

cat > "$corpo" <<EOF
Il menu pubblicato non cambia da **${ore}h ${minuti}m**. Il tablet in sala non e'
in pagina bianca - mostra l'ultima copia scaricata - ma quella copia sta
invecchiando, e chi ordina legge prezzi e piatti vecchi.

**Dove guardare**

- Esecuzioni della cattura: [Snapshot menu](../../actions/workflows/snapshot.yml) e [Ciclo menu](../../actions/workflows/ciclo.yml)
- Menu vero: <https://menu.menumal.com/sanpietrobistrotdelmare>
- Copia pubblicata: [version.json](https://${repo%%/*}.github.io/${repo##*/}/version.json)

**Le due cose che vale la pena escludere per prime**

1. Un aggiornamento degli strumenti di cattura che non gira sul Node fissato in
   \`.nvmrc\` - e' quello che e' successo ad agosto 2026. Il log della cattura lo
   dice a chiare lettere.
2. Un cambio di struttura della pagina Menumal, che fa fallire l'estrazione
   invece della cattura.

Questa segnalazione si chiude da sola appena riparte la pubblicazione.
EOF

if [ -n "$aperta" ]; then
  # Si aggiorna il testo invece di commentare: la segnalazione resta una sola e
  # non arriva una mail all'ora a ripetere la stessa cosa.
  gh issue edit "$aperta" --body-file "$corpo" >/dev/null
  echo "Menu fermo da ${ore}h ${minuti}m: segnalazione #$aperta gia' aperta, aggiornata."
else
  gh issue create --title "$TITOLO" --label "$ETICHETTA" --body-file "$corpo"
  echo "Menu fermo da ${ore}h ${minuti}m: segnalazione aperta."
fi
