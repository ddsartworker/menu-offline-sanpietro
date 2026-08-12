#!/usr/bin/env bash
# Porta avanti gli strumenti di cattura da solo, ma li adotta solo se il menu
# che producono e' buono.
#
# Le versioni sono fissate perche' un aggiornamento pubblicato a monte non possa
# fermare il menu del locale. Fissate e basta pero' invecchiano: prima o poi il
# Chrome del runner non parlera' piu' con un single-file di due anni fa, e
# saremmo fermi per il motivo opposto. Quindi una volta a settimana si prova la
# versione nuova su una cattura vera - stessi controlli di sempre, allergeni
# compresi - e la si tiene solo se passa. Se non passa, resta quella di prima e
# non se ne parla: non c'e' niente da decidere per nessuno.
set -uo pipefail

: "${GITHUB_REPOSITORY:?serve GITHUB_REPOSITORY}"
: "${GITHUB_TOKEN:?serve GITHUB_TOKEN}"

TRACCIATI=(package.json package-lock.json .nvmrc)
prova=$(mktemp -d -t strumenti-XXXXXX)
trap 'rm -rf "$prova"' EXIT

precedente=$(node -p "const p=require('./package.json').dependencies; Object.entries(p).map(([k,v])=>k+'@'+v).join(', ')")

# La versione di Node e' quella che il workflow ha messo sul PATH: la LTS del
# momento. Si annota in .nvmrc perche' e' quella su cui sto per provare, e se la
# prova va bene diventa quella con cui il menu si cattura da domani.
nuovo_node=$(node -v); nuovo_node=${nuovo_node#v}; nuovo_node=${nuovo_node%%.*}
echo "$nuovo_node" > .nvmrc

npm install --save-exact --no-audit --no-fund \
  single-file-cli@latest puppeteer-core@latest >/dev/null 2>&1 || {
  echo "npm non e' riuscito a installare le versioni nuove, resta tutto com'e'."
  git checkout -- "${TRACCIATI[@]}" 2>/dev/null || true
  exit 0
}

successivo=$(node -p "const p=require('./package.json').dependencies; Object.entries(p).map(([k,v])=>k+'@'+v).join(', ')")

if git diff --quiet -- "${TRACCIATI[@]}"; then
  echo "Gia' aggiornati: Node $nuovo_node, $successivo"
  exit 0
fi

echo "Da provare: Node $nuovo_node, $successivo"
echo "   al posto di: $precedente"

if ! OUT_DIR="$prova" bash tools/capture.sh; then
  echo ""
  echo "La versione nuova non produce un menu valido: si resta su quella fissata."
  echo "Non e' un guasto - il menu continua a pubblicarsi come prima - e fra una"
  echo "settimana si riprova con quella che ci sara' allora."
  git checkout -- "${TRACCIATI[@]}" 2>/dev/null || true
  exit 0
fi

echo ""
echo "Cattura di prova riuscita: $(( $(wc -c < "$prova/menu.html") / 1024 )) KB. Adotto le versioni nuove."

git config user.name "menu-bot"
git config user.email "menu-bot@users.noreply.github.com"
git add "${TRACCIATI[@]}"
git commit -q -m "Strumenti di cattura aggiornati

Provati su una cattura vera prima di adottarli.

Node $nuovo_node
$successivo"

git push -q "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" HEAD:main
echo "Fatto."
