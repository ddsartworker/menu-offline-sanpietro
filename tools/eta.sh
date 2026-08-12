#!/usr/bin/env bash
# Stampa da quanti secondi non cambia il menu che il tablet vede davvero.
# In caso di dubbio non stampa niente: meglio nessuna risposta che una sbagliata.
#
# Si guarda il sito pubblicato, non il branch `pages`: fra i due c'e' la
# ricostruzione di GitHub Pages, che ogni tanto fallisce per conto suo. Se
# quella si inceppa il branch e' aggiornato e il tablet no, ed e' il tablet che
# conta. Il branch resta come seconda strada, per quando la rete non collabora.
set -uo pipefail

repo="${GITHUB_REPOSITORY:-ddsartworker/menu-offline-sanpietro}"
proprietario="${repo%%/*}"
nome="${repo##*/}"
SITO="${MENU_PAGES_URL:-https://${proprietario}.github.io/${nome}}"

# `date` non parla la stessa lingua sui due sistemi: GNU sui runner, BSD sul
# portatile. Nessuna delle due forma funziona su entrambi, quindi si prova.
epoca_di() {
  date -u -d "$1" +%s 2>/dev/null && return 0
  date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$1" +%s 2>/dev/null && return 0
  return 1
}

quando=$(
  curl -sf --max-time 30 -H 'Cache-Control: no-cache' "${SITO%/}/version.json" 2>/dev/null |
    jq -r '.updated // empty' 2>/dev/null
)

if [ -z "${quando:-}" ]; then
  git fetch -q --depth=1 origin pages:refs/remotes/origin/pages 2>/dev/null || true
  quando=$(
    git show refs/remotes/origin/pages:version.json 2>/dev/null |
      jq -r '.updated // empty' 2>/dev/null
  )
fi

[ -z "${quando:-}" ] && exit 1

epoca=$(epoca_di "$quando") || exit 1
echo $(( $(date -u +%s) - epoca ))
