# Menu San Pietro — versione offline per tablet

Il menu digitale di Menumal non funziona senza connessione. Questo progetto lo
rende utilizzabile su un tablet in un locale dove il 4G va e viene.

## Perché non bastava un APK che apre l'URL

La pagina `menu.menumal.com/sanpietrobistrotdelmare` è una SPA Nuxt in
client-side rendering che legge i dati da Cloud Firestore. Verificato sul bundle:

| Meccanismo offline | Presente |
| --- | --- |
| Service worker / PWA | no |
| SSR (HTML pre-renderizzato) | no — `data-ssr="false"` |
| Firestore offline persistence | no — mancano gli object-store IndexedDB |

L'HTML servito è un guscio vuoto di 6 KB. Ogni ricaricamento senza rete dà una
pagina bianca — ed è esattamente quello che succede quando il tablet va in
standby e Android scarica la scheda del browser dalla memoria.

Un APK che incapsula l'URL è solo un browser con un'altra icona: stessa pagina
bianca. Il livello di cache va costruito fuori dalla pagina.

## Come funziona

1. **GitHub Actions**, ogni quarto d'ora, apre il menu con Chrome headless,
   aspetta che Firestore consegni i dati e salva uno snapshot autoconsistente —
   CSS, font e immagini incorporati, **zero richieste esterne**.
2. Lo snapshot viene ripulito dei font inutilizzati e pubblicato su GitHub Pages
   insieme a un `version.json` con il suo hash. Se il menu non è cambiato, non
   si pubblica nulla.
3. **L'app sul tablet** mostra sempre la copia locale. Ogni quarto d'ora, a ogni
   apertura e a ogni pressione del pulsante in sala scarica `version.json`
   (200 byte) e, solo se l'hash è cambiato, il nuovo snapshot.

Da una modifica su Menumal al tablet passano di solito venti minuti scarsi, poco
più di mezz'ora nel caso peggiore: quindici minuti di attesa della cattura,
quattro di elaborazione, e il controllo successivo del tablet.

Il tablet non dipende mai dalla rete per *mostrare* il menu. La rete serve solo,
quando c'è, per *aggiornarlo*.

### Il vincolo da tenere presente

Nessuna tecnologia può portare su un tablet una modifica fatta cinque minuti fa
se quel tablet non ha connessione. Quello che l'app garantisce è: mostra sempre
l'ultima versione che è riuscita a scaricare, e si aggiorna da sola appena vede
una qualunque connessione, senza che nessuno debba toccare niente.

## Quando la catena si rompe

Il 5 agosto 2026 alle 23:20 UTC è uscita una versione nuova di una libreria che
`single-file-cli` usa per pilotare Chrome. Da quel minuto ogni cattura è morta
con `ReferenceError: CloseEvent is not defined` e il tablet ha continuato a
mostrare il menu di quel giorno per sei giorni. Qui nessuno aveva toccato
niente.

Le mail di fallimento arrivavano: quattro all'ora, uguali a quelle dei buchi di
rete che si richiudono da soli al giro dopo. È il motivo per cui non le leggeva
più nessuno — un avviso che arriva sempre non dice niente. Se n'è accorto un
cameriere, guardando il tablet.

Le tre correzioni contano più della riga cambiata:

**Le versioni sono fissate** — `package.json`, `package-lock.json`, `.nvmrc`.
Prima `npx -y` prendeva sempre l'ultima pubblicata: comodo, finché qualcuno a
monte non pubblica qualcosa di rotto un mercoledì sera.

**Restare fermi però è l'altro modo di rompersi**: prima o poi il Chrome del
runner non parlerà più con un single-file di due anni fa. Quindi ogni lunedì
`tools/strumenti.sh` prova le versioni nuove su una cattura vera e le adotta
solo se il menu che producono passa i controlli di sempre, allergeni compresi.
Se non passano, resta quella di prima e non c'è niente da decidere per nessuno.

**L'allarme adesso si distingue dal rumore.** Un giro storto con un menu fresco
alle spalle passa in silenzio; se invece il menu pubblicato non si rinnova da
tre ore, `tools/guardia.sh` apre una segnalazione — una sola, che si richiude da
sola appena riparte. Se arriva quella mail, è successo qualcosa davvero.

## Due trappole trovate lungo la strada

**L'URL pubblico non è il menu.** È una vetrina che incornicia il menu dentro un
finto tablet disegnato, con header Menumal e pulsante "Accedi". Fotografarla
darebbe un menu piccolo dentro un tablet finto dentro un tablet vero. Il menu
vero è il documento che l'app inietta nell'iframe via `srcdoc`, e non ha un URL
proprio: `tools/extract.py` lo tira fuori da lì.

**Gli allergeni sparivano.** Font Awesome mappa classi e glifi con CSS caricati
a runtime (`pro.min.css`, `custom-icons.css`) che la cattura non segue: senza,
le 85 icone allergene del menu diventano quadratini vuoti — su un menu sono
obbligatorie per il Reg. UE 1169/2011. `tools/icons.py` le reintegra leggendo il
kit dalla pagina live, senza token scritti a mano.

Restano quattro icone il cui glifo manca proprio dai dati del font, perché Font
Awesome spezza i font per intervallo Unicode e la cattura ne incorpora solo una
parte. Vengono sostituite con SVG equivalenti. Quali siano non è una lista
scritta a mano: `tools/coverage.py` legge la tabella cmap dei font incorporati e
lo stabilisce a ogni esecuzione, così se il menu cambia non invecchia in
silenzio.

> Verificare dal browser non funziona: `document.fonts.check` risponde di sì
> anche quando il glifo non c'è, e le larghezze su canvas non sono confrontabili
> perché i font Font Awesome popolano quasi tutta l'area privata Unicode.

## Peso degli aggiornamenti

Menumal precarica ~65 famiglie Google Fonts, di cui questo menu ne usa cinque.
`tools/slim.py` rimuove le altre e i subset non latini:

| | pagina intera | menu estratto e ripulito |
| --- | --- | --- |
| Snapshot | 8,77 MB | **1,64 MB** |
| Trasferito (gzip) | 6,05 MB | **0,80 MB** |
| Prezzi | 408 | 408 |
| Risorse esterne | 0 | **0** |

Lo script fallisce di proposito se una famiglia effettivamente usata sparisse,
invece di pubblicare un menu con i font rotti.

## Uso

**Rigenerare lo snapshot in locale** (serve Chrome e Node):

```bash
bash tools/capture.sh          # produce dist/menu.html e dist/version.json
```

**Forzare un aggiornamento subito**: dal tablet basta il pulsante in basso a
sinistra. Da GitHub: Actions → *Snapshot menu* → *Run workflow*.

**Ricompilare l'APK**: Actions → *Build APK* → *Run workflow*. Il file finisce
nella release `apk-latest`, scaricabile direttamente dal browser del tablet.

**Sapere se la catena è viva**: Actions → *Guardia menu* → *Run workflow*.
Risponde con l'età del menu pubblicato senza toccare niente. È la stessa cosa
che dice il pulsante sul tablet, e gira comunque da sola ogni ora.

## Installazione sul tablet

1. Impostazioni → Sicurezza → consenti installazione da origini sconosciute.
2. Apri la release `apk-latest` dal browser del tablet e installa.
3. Primo avvio **con connessione**: scarica il menu. Da lì in poi funziona anche
   senza.
4. Consigliato: Impostazioni → Display → sospensione schermo mai, e blocco
   schermo su "nessuno".

## Il pulsante in sala

In basso a sinistra c'è una freccia circolare, piccola e semitrasparente. Chi
lavora in sala sa dov'è, chi legge il menu non la nota, e se la preme un cliente
al massimo parte un controllo in più.

Premendola il tablet guarda subito se c'è un menu nuovo, invece di aspettare il
controllo del quarto d'ora, e se lo trova lo applica sul momento. La risposta
dice sempre **quanto è vecchia la copia online**, non solo se il tablet è
allineato:

- *Menu aggiornato* — c'era una versione nuova, è già a schermo
- *Già aggiornato — il menu online è di 12 minuti fa* — tutto a posto
- *Già aggiornato — il menu online è di 3 giorni fa* — il tablet è a posto ma la
  catena a monte è ferma: è il caso in cui serve guardare le segnalazioni
- *Nessuna connessione — resta il menu di un'ora fa* — niente rete adesso

La differenza fra le due righe di mezzo è tutto il punto. Ad agosto il tablet
era perfettamente allineato a un menu fermo da sei giorni, e dallo schermo non
c'era modo di accorgersene.

## Struttura

```
tools/giro.sh          un giro intero: cattura, pubblica, e decide se il buco
                       merita un allarme o si richiude da solo
tools/capture.sh       orchestra gli 8 passi, con controlli anti-pagina-vuota
tools/extract.py       estrae il menu dalla cornice del finto tablet
tools/slim.py          rimozione font inutilizzati, con rete di sicurezza
tools/icons.py         reintegra le regole icone, sostituisce i glifi mancanti
tools/coverage.py      legge la cmap dei font: quali glifi ci sono davvero
tools/verify.py        controllo finale sul file che va sul tablet
tools/eta.sh           da quanto non cambia il menu che il tablet vede davvero
tools/guardia.sh       la sentinella: apre una segnalazione sola, e la richiude
tools/strumenti.sh     prova le versioni nuove, le adotta solo se reggono
package.json .nvmrc    versioni fissate degli strumenti di cattura
.github/workflows/     ciclo di cattura, guardia, strumenti, build APK
android/               app Kotlin: WebView su file locale + sync WorkManager
```

Serve `fonttools` e `brotli` (`pip install fonttools brotli`) per leggere i font.

## Note

- L'APK è firmato con la chiave di debug: va benissimo per installazione
  manuale su tablet propri. Per il Play Store servirebbe una chiave di release.
- Se il menu resta invariato per 60 giorni GitHub sospende i workflow a
  schedulazione: manda un'email, si riattiva con un click.
