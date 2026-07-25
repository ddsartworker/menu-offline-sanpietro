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

echo "==> 1/6 Cattura $MENU_URL"
# Sui runner CI Chrome gira da root senza namespace utente e la sandbox lo
# blocca all'avvio: senza --no-sandbox la cattura fallisce con "fetch failed".
# Menumal ogni tanto rifiuta la richiesta dal runner e single-file riporta solo
# un generico "fetch failed": un tentativo isolato non basta a dire che il sito
# e' irraggiungibile.
for tentativo in 1 2 3; do
  npx -y single-file-cli \
    --browser-executable-path="$CHROME" \
    --browser-args='["--no-sandbox","--disable-dev-shm-usage","--disable-gpu"]' \
    --browser-wait-until=networkidle0 \
    --browser-wait-delay=8000 \
    --browser-width=1280 --browser-height=1800 \
    --load-deferred-images=true \
    --remove-hidden-elements=false \
    "$MENU_URL" "$work/page.html" || true

  [ -s "$work/page.html" ] && break

  if [ "$tentativo" -lt 3 ]; then
    echo "    tentativo $tentativo fallito, riprovo fra $((tentativo * 20))s"
    sleep $((tentativo * 20))
  fi
done

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

# L'URL pubblico e' una vetrina che incornicia il menu in un finto tablet.
# Il menu vero e' il documento dentro l'iframe.
echo "==> 2/6 Estrazione del menu dalla cornice"
python3 tools/extract.py "$work/page.html" "$work/menu.html"

echo "==> 3/6 Rimozione font inutilizzati"
python3 tools/slim.py "$work/menu.html" "$work/slim.html"

echo "==> 4/6 Reintegro regole icone"
python3 tools/icons.py "$work/slim.html" "$work/icone.html" "$MENU_URL"

echo "==> 5/6 Ricostruzione interazioni"
python3 tools/interactions.py "$work/icone.html" "$OUT_DIR/menu.html"

echo "==> 6/6 Verifica del file finale"
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
