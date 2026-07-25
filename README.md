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

1. **GitHub Actions**, ogni ora, apre il menu con Chrome headless, aspetta che
   Firestore consegni i dati e salva uno snapshot autoconsistente — CSS, font e
   immagini incorporati, **zero richieste esterne**.
2. Lo snapshot viene ripulito dei font inutilizzati e pubblicato su GitHub Pages
   insieme a un `version.json` con il suo hash. Se il menu non è cambiato, non
   si pubblica nulla.
3. **L'app sul tablet** mostra sempre la copia locale. Quando ha rete scarica
   `version.json` (200 byte) e, solo se l'hash è cambiato, il nuovo snapshot.

Il tablet non dipende mai dalla rete per *mostrare* il menu. La rete serve solo,
quando c'è, per *aggiornarlo*.

### Il vincolo da tenere presente

Nessuna tecnologia può portare su un tablet una modifica fatta cinque minuti fa
se quel tablet non ha connessione. Quello che l'app garantisce è: mostra sempre
l'ultima versione che è riuscita a scaricare, e si aggiorna da sola appena vede
una qualunque connessione, senza che nessuno debba toccare niente.

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
| Snapshot | 9,74 MB | **1,51 MB** |
| Trasferito (gzip) | 6,5 MB | **0,77 MB** |
| Prezzi | 274 | 274 |
| Risorse esterne | 0 | **0** |

Lo script fallisce di proposito se una famiglia effettivamente usata sparisse,
invece di pubblicare un menu con i font rotti.

## Uso

**Rigenerare lo snapshot in locale** (serve Chrome e Node):

```bash
bash tools/capture.sh          # produce dist/menu.html e dist/version.json
```

**Forzare un aggiornamento subito**: Actions → *Snapshot menu* → *Run workflow*.

**Ricompilare l'APK**: Actions → *Build APK* → *Run workflow*. Il file finisce
nella release `apk-latest`, scaricabile direttamente dal browser del tablet.

## Installazione sul tablet

1. Impostazioni → Sicurezza → consenti installazione da origini sconosciute.
2. Apri la release `apk-latest` dal browser del tablet e installa.
3. Primo avvio **con connessione**: scarica il menu. Da lì in poi funziona anche
   senza.
4. Consigliato: Impostazioni → Display → sospensione schermo mai, e blocco
   schermo su "nessuno".

## Struttura

```
tools/capture.sh       orchestra i 5 passi, con controlli anti-pagina-vuota
tools/extract.py       estrae il menu dalla cornice del finto tablet
tools/slim.py          rimozione font inutilizzati, con rete di sicurezza
tools/icons.py         reintegra le regole icone, sostituisce i glifi mancanti
tools/coverage.py      legge la cmap dei font: quali glifi ci sono davvero
tools/verify.py        controllo finale sul file che va sul tablet
.github/workflows/     snapshot orario + build APK
android/               app Kotlin: WebView su file locale + sync WorkManager
```

Serve `fonttools` e `brotli` (`pip install fonttools brotli`) per leggere i font.

## Note

- L'APK è firmato con la chiave di debug: va benissimo per installazione
  manuale su tablet propri. Per il Play Store servirebbe una chiave di release.
- Se il menu resta invariato per 60 giorni GitHub sospende i workflow a
  schedulazione: manda un'email, si riattiva con un click.
