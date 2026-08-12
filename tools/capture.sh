#!/usr/bin/env bash
# Fotografa il menu live e produce uno snapshot autoconsistente + version.json.
#
# Il menu e' una SPA Nuxt in client-side rendering che legge da Cloud Firestore,
# senza service worker ne' persistenza offline: serve un browser vero che aspetti
# l'idratazione, non un semplice download dell'HTML.
set -euo pipefail

MENU_URL="${MENU_URL:-https://menu.menumal.com/sanpietrobistrotdelmare}"
OUT_DIR="${OUT_DIR:-dist}"
CHROME="${CHROME_PATH:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

mkdir -p "$OUT_DIR"
work=$(mktemp -d -t menu-XXXXXX)
trap 'rm -rf "$work"' EXIT

echo "==> 1/8 Cattura $MENU_URL"

# Gli strumenti si installano dal lockfile, non con `npx -y` che prende sempre
# l'ultima versione pubblicata. Il 5 agosto 2026 alle 23:20 UTC e' uscita
# simple-cdp 1.10, che usa CloseEvent: da quel minuto ogni cattura e' morta e
# il tablet ha mostrato lo stesso menu per sei giorni, senza che nessuno qui
# avesse toccato niente. Le versioni le muove tools/strumenti.sh, dopo averle
# provate su una cattura vera.
SINGLE_FILE="node_modules/.bin/single-file"
if [ ! -x "$SINGLE_FILE" ]; then
  npm ci --silent --no-audit --no-fund >/dev/null 2>&1 ||
    npm install --silent --no-audit --no-fund >/dev/null 2>&1
fi

# Sui runner CI Chrome gira da root senza namespace utente e la sandbox lo
# blocca all'avvio: senza --no-sandbox la cattura fallisce con "fetch failed".
scatta() {
  # Il comando arriva da fuori perche' l'ultimo tentativo usa un'altra versione.
  "$@" \
    --browser-executable-path="$CHROME" \
    --browser-args='["--no-sandbox","--disable-dev-shm-usage","--disable-gpu"]' \
    --browser-wait-until=networkidle0 \
    --browser-wait-delay=8000 \
    --browser-width=1280 --browser-height=1800 \
    --load-deferred-images=true \
    --remove-hidden-elements=false \
    "$MENU_URL" "$work/page.html" || true
}

# Menumal ogni tanto rifiuta la richiesta dal runner e single-file riporta solo
# un generico "fetch failed": un tentativo isolato non basta a dire che il sito
# e' irraggiungibile.
for tentativo in 1 2 3; do
  scatta "$SINGLE_FILE"

  [ -s "$work/page.html" ] && break

  if [ "$tentativo" -lt 3 ]; then
    echo "    tentativo $tentativo fallito, riprovo fra $((tentativo * 20))s"
    sleep $((tentativo * 20))
  fi
done

# Fissare le versioni protegge da un aggiornamento rotto, non dall'invecchiare:
# prima o poi un Chrome nuovo sul runner non parlera' piu' con un single-file
# vecchio. Prima di arrendersi si prova l'ultima pubblicata; se e' lei a
# funzionare, il giro settimanale di tools/strumenti.sh la promuove.
#
# L'installazione va in una cartella a parte e non con `npx single-file-cli@latest`:
# npx, trovando il comando gia' in node_modules, riusa quello - cioe' proprio la
# copia che non funziona. Provato: il ripiego sembrava partire e ripescava
# l'eseguibile rotto.
if [ ! -s "$work/page.html" ]; then
  echo "    la versione fissata non ce la fa, provo con l'ultima pubblicata"
  if npm install --silent --no-audit --no-fund \
    --prefix "$work/ultima" single-file-cli@latest >/dev/null 2>&1; then
    scatta "$work/ultima/node_modules/.bin/single-file"
  else
    echo "    non riesco nemmeno a scaricarla"
  fi
fi

if [ ! -s "$work/page.html" ]; then
  echo "ERRORE: cattura fallita dopo 3 tentativi" >&2
  exit 1
fi

# Un rendering fallito produce un guscio Nuxt vuoto di pochi KB: meglio abortire
# che pubblicare un menu vuoto sul tablet.
bytes=$(wc -c < "$work/page.html")
if [ "$bytes" -lt 200000 ]; then
  echo "ERRORE: cattura di soli $bytes byte, rendering fallito" >&2
  exit 1
fi
echo "pagina catturata: $((bytes / 1048576)),$(( (bytes % 1048576) * 100 / 1048576 )) MB"

# L'URL pubblico e' una vetrina che incornicia il menu in un finto tablet.
# Il menu vero e' il documento dentro l'iframe.
echo "==> 2/8 Estrazione del menu dalla cornice"
python3 tools/extract.py "$work/page.html" "$work/menu.html"

echo "==> 3/8 Rimozione font inutilizzati"
python3 tools/slim.py "$work/menu.html" "$work/slim.html"

echo "==> 4/8 Reintegro regole icone"
python3 tools/icons.py "$work/slim.html" "$work/icone.html" "$MENU_URL"

echo "==> 5/8 Scoperta ancore delle zone"
# Facoltativo: se fallisce il menu resta completo, solo i chip delle zone dei
# vini non portano da nessuna parte. Non vale bloccare la pubblicazione.
# puppeteer-core arriva dal lockfile insieme a single-file, installato sopra.
node tools/anchors.mjs "$work/anchors.json" || echo "    ancore non scoperte, si prosegue"

echo "==> 6/8 Raccolta della versione inglese"
# Facoltativa come le ancore: se non riesce, il menu resta in italiano.
node tools/translate.mjs "$work/translations.json" || echo "    traduzioni non raccolte, si prosegue"

echo "==> 7/8 Ricostruzione interazioni"
python3 tools/interactions.py "$work/icone.html" "$OUT_DIR/menu.html" \
  "$work/anchors.json" "$work/translations.json"

echo "==> 8/8 Verifica del file finale"
python3 tools/verify.py "$OUT_DIR/menu.html"

# Gli allergeni sono obbligatori per legge: se mancano non si pubblica.
allergens=$(grep -o 'allergen-food' "$OUT_DIR/menu.html" | wc -l | tr -d ' ')
if [ "$allergens" -lt 20 ]; then
  echo "ERRORE: solo $allergens riferimenti allergene nel menu finale" >&2
  exit 1
fi

sha=$(shasum -a 256 "$OUT_DIR/menu.html" | cut -d' ' -f1)
size=$(wc -c < "$OUT_DIR/menu.html" | tr -d ' ')
stamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

cat > "$OUT_DIR/version.json" <<EOF
{
  "sha256": "$sha",
  "size": $size,
  "updated": "$stamp",
  "source": "$MENU_URL"
}
EOF

echo "==> Fatto: $((size / 1024)) KB | allergeni: $allergens | sha ${sha:0:12}..."
