#!/usr/bin/env bash
# Pubblica lo snapshot sul branch `pages`, ma solo se il menu e' cambiato.
#
# Il branch viene ricreato da zero a ogni pubblicazione e forzato: la storia non
# si accumula, quindi il repo resta piccolo anche pubblicando 1,5 MB al giorno
# per anni. E se il menu non e' cambiato non si pubblica nulla, cosi' il tablet
# non scarica nulla.
set -euo pipefail

DIST="${OUT_DIR:-dist}"
: "${GITHUB_REPOSITORY:?serve GITHUB_REPOSITORY}"
: "${GITHUB_TOKEN:?serve GITHUB_TOKEN}"

BOT_NAME="menu-bot"
BOT_MAIL="menu-bot@users.noreply.github.com"

# checkout e' shallow e non porta gli altri branch; al primo giro `pages` non
# esiste ancora, quindi l'errore va ignorato.
git fetch --depth=1 origin pages:refs/remotes/origin/pages 2>/dev/null || true

new_sha=$(jq -r .sha256 "$DIST/version.json")
old_sha=$(git show refs/remotes/origin/pages:version.json 2>/dev/null | jq -r .sha256 || echo "")

if [ "$new_sha" = "$old_sha" ]; then
  echo "Menu invariato ($(echo "$new_sha" | cut -c1-12)...), niente da pubblicare."
  exit 0
fi
echo "Menu cambiato: ${old_sha:0:12}${old_sha:+...} -> ${new_sha:0:12}..."

cd "$DIST"
touch .nojekyll

# Si aggiunge un commit sopra la storia esistente invece di ricreare il branch e
# forzarlo: riscrivere la storia a ogni pubblicazione manda in errore la
# ricostruzione di GitHub Pages. Il repo non cresce comunque, perche' i font
# incorporati - 1,5 MB su 1,8 - sono identici a ogni giro e git li comprime via.
REMOTE="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"

rm -rf .git
git init -q -b pages
# Il repo appena creato non eredita l'identita' di quello esterno: va passata
# esplicitamente, altrimenti il commit fallisce con "empty ident name".
git config user.name "$BOT_NAME"
git config user.email "$BOT_MAIL"
git add -A

if git fetch -q --depth=1 "$REMOTE" pages 2>/dev/null; then
  # I file restano quelli nuovi, ma il commit si aggancia a quello pubblicato.
  git reset -q --soft FETCH_HEAD
  git add -A
fi

git commit -q -m "Menu aggiornato $(date -u '+%F %H:%M') UTC"
git push -q "$REMOTE" pages

echo "Pubblicato: $(( $(wc -c < menu.html) / 1024 )) KB"
