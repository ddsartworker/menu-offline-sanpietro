#!/usr/bin/env python3
"""Ricostruisce le interazioni del menu, che la cattura perde.

SingleFile rimuove gli script, quindi nello snapshot non funzionano i tab delle
macro-categorie, la ricerca e le icone allergene. Tenerli non e' un'alternativa:
provato, offline l'app Vue di Menumal si avvia, non trova Firestore e sostituisce
il menu con "404 Error Page not found".

Quindi le tre funzioni vengono riscritte qui, in JavaScript autonomo che non
dipende da nulla di Menumal e non ha bisogno di rete.
"""
import re
import sys

# Nome per esteso di ogni allergene: sotto al piatto c'e' solo un'icona, e senza
# JavaScript non compariva nulla al tocco. Sono informazioni di sicurezza, non
# decorazioni.
ALLERGENI = {
    "gluten": "Glutine",
    "crustaceans": "Crostacei",
    "egg": "Uova",
    "fish": "Pesce",
    "peanut": "Arachidi",
    "soy": "Soia",
    "milk": "Latte",
    "nuts": "Frutta a guscio",
    "celery": "Sedano",
    "mustard": "Senape",
    "sesame": "Sesamo",
    "sulfites": "Solfiti",
    "lupins": "Lupini",
    "shellfish": "Molluschi",
}

def _bandiera(corpo, viewbox):
    """Le bandiere vanno disegnate qui: la cattura conserva solo l'icona
    italiana, l'unica usata dal menu, e delle altre non resta nemmeno una regola.
    Chiedere al tema quella britannica darebbe un riquadro vuoto."""
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='%s'>%s</svg>"
           % (viewbox, corpo))
    return svg.replace("<", "%3C").replace(">", "%3E").replace("#", "%23")


BANDIERA_IT = _bandiera(
    "<rect width='3' height='2' fill='#fff'/>"
    "<rect width='1' height='2' fill='#008C45'/>"
    "<rect x='2' width='1' height='2' fill='#CD212A'/>", "0 0 3 2")

BANDIERA_GB = _bandiera(
    "<rect width='60' height='30' fill='#012169'/>"
    "<path d='M0,0 L60,30 M60,0 L0,30' stroke='#fff' stroke-width='6'/>"
    "<path d='M0,0 L60,30 M60,0 L0,30' stroke='#C8102E' stroke-width='4'/>"
    "<path d='M30,0 L30,30 M0,15 L60,15' stroke='#fff' stroke-width='10'/>"
    "<path d='M30,0 L30,30 M0,15 L60,15' stroke='#C8102E' stroke-width='6'/>",
    "0 0 60 30")

CSS = """
/* Il carosello di Vue non puo' funzionare senza il suo JavaScript: si annulla
   il ritaglio e l'affiancamento, e si mostra una macro-categoria alla volta. */
.carousel__viewport{overflow:visible!important}
.carousel__track{display:block!important;transform:none!important;width:100%!important}
/* Si spegne solo cio' che il JavaScript ha spento davvero. Nasconderle tutte da
   CSS e riaccenderne una da JavaScript sembra equivalente, ma se lo script si
   ferma il menu resta bianco: cosi' invece degrada a tutte le sezioni una sotto
   l'altra, brutto ma leggibile. */
.mm-spenta{display:none!important}
/* Niente altezze forzate: imporre height:100% qui sembrava servire a far
   scorrere la sezione, ma a scorrere e' il contenitore del carosello piu' in
   alto, mentre l'altezza fissa tagliava il contenuto delle sezioni piu' lunghe
   lasciandole vuote. */
/* La sezione deve cominciare in alto. Il carosello la centrava verticalmente e
   la rimpiccioliva (opacity e scale sulle slide non attive): su uno schermo alto
   il contenuto finiva in fondo, e sembrava che la sezione fosse vuota. */
.mm-accesa{display:block!important;width:100%!important;
  opacity:1!important;transform:none!important;
  align-items:flex-start!important;justify-content:flex-start!important;
  margin-top:0!important}
.carousel__track{align-items:flex-start!important}
div[data-section="macros"]{cursor:pointer}

/* Quale sezione si sta guardando deve essere ovvio. Scambiare le classi del
   tema non basta: il colore del tab attivo arriva da altre regole che non lo
   seguono, e restava evidenziata la prima voce qualunque cosa si scegliesse. */
button.mm-tab-scelto,button.mm-tab-scelto span{
  opacity:1!important;text-decoration:underline!important;
  text-underline-offset:7px!important;text-decoration-thickness:2px!important}
button.mm-tab-altro,button.mm-tab-altro span{
  opacity:.6!important;text-decoration:none!important}

/* Ricerca */
#mm-cerca{position:fixed;top:0;left:0;right:0;z-index:9999;display:none;
  padding:10px 14px;background:rgba(12,20,26,.97);backdrop-filter:blur(6px);
  box-shadow:0 2px 14px rgba(0,0,0,.45)}
#mm-cerca.mm-aperta{display:flex;gap:10px;align-items:center}
#mm-cerca input{flex:1;min-width:0;padding:11px 14px;border-radius:9px;border:0;
  font-size:17px;background:#fff;color:#111}
#mm-cerca button{padding:11px 15px;border:0;border-radius:9px;font-size:16px;
  background:rgba(255,255,255,.16);color:#fff}
#mm-esito{position:fixed;top:62px;left:0;right:0;z-index:9998;display:none;
  text-align:center;font-size:14px;padding:6px;color:#fff;
  background:rgba(12,20,26,.9)}
#mm-esito.mm-aperta{display:block}
.mm-nascosto{display:none!important}
.mm-vino-via{display:none!important}

/* Fascia superiore piena.
   L'intestazione e' fissa a 70px e i tab stanno poco sotto, ma fra i due resta
   una fessura trasparente: scorrendo, i piatti ci passavano dentro e si
   leggevano dietro le voci del menu. Invece di rincorrere i singoli pezzi si
   mette un fondale opaco dietro tutto il blocco, alto quanto serve.
   Il colore e' campionato dallo sfondo del menu, per non stonare. */
#mm-fondale{position:fixed;top:0;left:0;right:0;z-index:40;
  background:#3b4245;pointer-events:none}
header[data-section="header"]{z-index:60}
#tabsMenu{position:relative;z-index:60}

/* Tendina delle lingue */
#mm-lingue{position:fixed;z-index:10001;display:none;min-width:190px;
  background:#fff;border-radius:11px;overflow:hidden;
  box-shadow:0 8px 30px rgba(0,0,0,.45)}
#mm-lingue.mm-aperta{display:block}
#mm-lingue button{display:flex;align-items:center;gap:11px;width:100%;
  padding:13px 16px;border:0;background:#fff;color:#15202b;
  font-size:16px;text-align:left;cursor:pointer}
#mm-lingue button+button{border-top:1px solid #e8e8e8}
#mm-lingue button:hover{background:#f2f5f7}
#mm-lingue button .mm-fl{width:28px;height:20px;border-radius:3px;flex:none;
  background-size:cover;background-position:center;box-shadow:0 0 0 1px rgba(0,0,0,.12)}
#mm-lingue button .mm-spunta{margin-left:auto;font-weight:700;color:#2c7f92}

/* Etichetta dell'allergene al tocco */
#mm-etichetta{position:fixed;z-index:10000;display:none;padding:7px 12px;
  border-radius:8px;background:#fff;color:#111;font-size:15px;font-weight:600;
  box-shadow:0 3px 14px rgba(0,0,0,.5);pointer-events:none;transform:translate(-50%,-140%)}
#mm-etichetta.mm-aperta{display:block}
"""

JS_TEMPLATE = """
(function () {
  var ALLERGENI = %s;

  /* ---------- 1. Tab delle macro-categorie ---------- */
  var slides = document.querySelectorAll(".carousel__item");
  var tabs = document.querySelectorAll('div[data-section="macros"]');

  // Ogni sezione sta dentro un <li> del carosello. Spegnere il div interno non
  // basta: il <li> resta e continua a occupare spazio, spingendo le sezioni
  // successive fuori dallo schermo. Va spento il contenitore.
  var sezioni = [];
  for (var s = 0; s < slides.length; s++) {
    sezioni.push(slides[s].closest(".carousel__slide") || slides[s]);
  }

  // Lo stile del tab scelto sta sul <button> che lo avvolge, in classi generate
  // dal tema (underlineMacroActive contro underlineMacro). Invece di inventare
  // una sottolineatura nostra si copiano quelle esistenti dallo stato iniziale:
  // cosi' l'aspetto resta identico anche se il ristorante cambia tema.
  var bottoni = [], classiAttive = null, classiSpente = null;
  for (var b = 0; b < tabs.length; b++) {
    var bottone = tabs[b].closest("button") || tabs[b];
    bottoni.push(bottone);
    if (bottone.getAttribute("aria-selected") === "true") classiAttive = bottone.className;
    else if (classiSpente === null) classiSpente = bottone.className;
  }

  function mostraCategoria(indice) {
    for (var i = 0; i < sezioni.length; i++) {
      sezioni[i].classList.toggle("mm-spenta", i !== indice);
      sezioni[i].classList.toggle("mm-accesa", i === indice);
    }
    for (var b2 = 0; b2 < bottoni.length; b2++) {
      if (classiAttive !== null && classiSpente !== null) {
        bottoni[b2].className = (b2 === indice) ? classiAttive : classiSpente;
      }
      bottoni[b2].setAttribute("aria-selected", b2 === indice ? "true" : "false");
      bottoni[b2].classList.toggle("mm-tab-scelto", b2 === indice);
      bottoni[b2].classList.toggle("mm-tab-altro", b2 !== indice);
    }
    for (var j = 0; j < tabs.length; j++) {
      var etichetta = tabs[j].querySelector("span");
      // Stesso attributo usato dal tema per il tab attivo: cosi' si eredita la
      // sottolineatura originale invece di inventarne una.
      if (etichetta) {
        etichetta.setAttribute("data-subsection", j === indice ? "macroActive" : "macro");
      }
    }
    // Ogni categoria riparte dall'alto. Non basta azzerare la slide: a scorrere
    // e' anche il contenitore del carosello, e restando dov'era si finisce a
    // fissare il vuoto sotto una sezione piu' corta della precedente.
    var risali = slides[indice];
    while (risali && risali !== document.body) {
      if (risali.scrollTop) risali.scrollTop = 0;
      risali = risali.parentElement;
    }
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    if (window.scrollTo) window.scrollTo(0, 0);
  }

  if (slides.length && slides.length === tabs.length) {
    for (var k = 0; k < tabs.length; k++) {
      (function (indice) {
        tabs[indice].addEventListener("click", function () {
          chiudiRicerca();
          mostraCategoria(indice);
        });
      })(k);
    }
    mostraCategoria(0);
  }

  /* ---------- 1b. Chip di sottocategoria (zone dei vini) ---------- */
  // Nello snapshot i vini sono un'unica lista piatta e i chip non saprebbero
  // dove portare: il legame chip -> gruppo non esiste nell'HTML. Le ancore sono
  // state scoperte cliccando i chip sul sito vero (tools/anchors.mjs) e sono il
  // nome del primo piatto di ogni gruppo.
  var ANCORE = %s;

  // Chi scorre davvero non e' la sezione ma un suo antenato, e cambia a seconda
  // del formato dello schermo: va cercato invece che indovinato. scrollIntoView
  // da solo non basta, non muove il contenitore giusto.
  function scrollerDi(elemento) {
    var n = elemento.parentElement;
    while (n && n !== document.body) {
      var ov = getComputedStyle(n).overflowY;
      if ((ov === "auto" || ov === "scroll") && n.scrollHeight > n.clientHeight + 4) return n;
      n = n.parentElement;
    }
    return document.scrollingElement || document.documentElement;
  }


  Object.keys(ANCORE).forEach(function (m) {
    var slide = slides[m];
    if (!slide) return;
    var chips = slide.querySelectorAll('li[data-section="categories"]');
    var mappa = ANCORE[m];

    for (var c = 0; c < chips.length && c < mappa.length; c++) {
      (function (chip, voce, indiceChip) {
        chip.style.cursor = "pointer";
        chip.addEventListener("click", function () {
          // textContent e non innerText: i gruppi non scelti restano nel
          // documento ma nascosti, e di un elemento nascosto innerText e' vuoto.
          var nomi = slide.querySelectorAll("[data-tab=name]");
          var da = -1;
          for (var n = 0; n < nomi.length; n++) {
            if ((nomi[n].textContent || "").replace(/\\s+/g, " ").trim() === voce.ancora) {
              da = n; break;
            }
          }
          if (da < 0) return;
          var a = da + (voce.voci || 1);

          for (var k = 0; k < nomi.length; k++) {
            var riga = nomi[k].closest(".elementContainer") || nomi[k].parentElement;
            if (k >= da && k < a) {
              riga.classList.remove("mm-vino-via");
              // Menumal nasconde i gruppi con uno stile scritto sull'elemento:
              // una regola CSS non lo batte, va tolto quello.
              var su = nomi[k];
              while (su && su !== slide) {
                if (su.style && su.style.display === "none") su.style.display = "";
                su = su.parentElement;
              }
            } else {
              riga.classList.add("mm-vino-via");
            }
          }

          // I titoli verdi delle zone - "Rossi Stranieri", "Bianchi - Campania"
          // - sul sito originale restano visibili sopra i vini del gruppo, e
          // servono a capire cosa si sta guardando. Vanno mostrati anche qui:
          // filtrando i soli vini sparivano, lasciando un elenco senza capo.
          //
          // Un titolo appartiene al gruppo scelto se il primo vino che lo segue
          // rientra nell'intervallo: si scorre il documento in ordine tenendo il
          // conto dei vini incontrati.
          var inOrdine = slide.querySelectorAll("[data-tab=name],[data-section=subcategories]");
          var visti = 0;
          var attesa = [];
          for (var o = 0; o < inOrdine.length; o++) {
            var pezzo = inOrdine[o];
            if (pezzo.getAttribute("data-section") === "subcategories") {
              attesa.push(pezzo);
            } else {
              var dentro = visti >= da && visti < a;
              for (var w = 0; w < attesa.length; w++) {
                attesa[w].classList.toggle("mm-vino-via", !dentro);
                if (dentro) {
                  var risalita = attesa[w];
                  while (risalita && risalita !== slide) {
                    if (risalita.style && risalita.style.display === "none") {
                      risalita.style.display = "";
                    }
                    risalita = risalita.parentElement;
                  }
                }
              }
              attesa = [];
              visti++;
            }
          }
          for (var z = 0; z < attesa.length; z++) attesa[z].classList.add("mm-vino-via");

          // Il tema marca la zona scelta con la classe "active": usare quella
          // da' lo stesso riempimento delle altre invece di un bordo inventato.
          for (var t = 0; t < chips.length; t++) {
            chips[t].classList.toggle("active", t === indiceChip);
          }

          // Niente scorrimento: ora che la lista e' filtrata il gruppo comincia
          // subito sotto i chip. Scorrere faceva salire la barra delle zone
          // sopra i tab delle sezioni, sovrapponendosi.
          var sc = scrollerDi(nomi[da]);
          if (sc) sc.scrollTop = 0;
        });
      })(chips[c], mappa[c], c);
    }
  });

  /* ---------- 1c. Cambio lingua ---------- */
  // Menumal traduce con Google Translate, che ha bisogno della rete: offline la
  // bandiera non farebbe nulla. Qui la traduzione e' gia' dentro il file, presa
  // al momento della cattura. Si conservano solo i testi che cambiano davvero:
  // i nomi dei piatti restano in italiano, come sul sito.
  var TRADUZIONI = %s;
  var BANDIERA_IT = "%s";
  var BANDIERA_GB = "%s";

  (function () {
    if (!TRADUZIONI || !TRADUZIONI.voci) return;
    var elementi = document.querySelectorAll(
      "[data-tab=description],[data-section='categories'],[data-section='subcategories']," +
      "[data-section='macros'],[data-tab=name]");
    // Il confronto e' sul testo, non sulla posizione: lo snapshot non ha
    // esattamente gli stessi elementi della pagina da cui si e' tradotto.

    var bandiera = document.querySelector("#flag");
    if (!bandiera) return;
    var comando = bandiera.closest("button") || bandiera.parentElement || bandiera;
    comando.style.cursor = "pointer";

    var inglese = false;
    var originali = null;

    function applica(vuoiInglese) {
      if (vuoiInglese === inglese) return;
      if (vuoiInglese) {
        // Si salva l'HTML, non solo il testo: alcuni titoli contengono
        // un'etichetta nascosta per i lettori di schermo da ripristinare intatta.
        originali = [];
        for (var i = 0; i < elementi.length; i++) {
          originali.push(elementi[i].innerHTML);
          var testo = (elementi[i].textContent || "")
            .replace(/categoria menu:/gi, "").replace(/\\s+/g, " ").trim();
          var reso = TRADUZIONI.voci[testo];
          if (reso) elementi[i].textContent = reso;
        }
        // Non si cambia la classe: il tema non ha la bandiera britannica e
        // resterebbe un riquadro vuoto. Si sovrascrive l'immagine.
        bandiera.style.backgroundImage = sfondo(BANDIERA_GB);
        bandiera.style.backgroundSize = "cover";
        document.documentElement.setAttribute("lang", TRADUZIONI.lingua || "en");
      } else {
        for (var j = 0; j < elementi.length; j++) elementi[j].innerHTML = originali[j];
        bandiera.style.backgroundImage = "";
        document.documentElement.setAttribute("lang", "it");
      }
      inglese = vuoiInglese;
    }

    // Una tendina invece di un interruttore: con due lingue si vede subito
    // quale e' attiva, e resta il posto per aggiungerne altre.
    function sfondo(svg) { return 'url("data:image/svg+xml,' + svg + '")'; }

    var tendina = document.createElement("div");
    tendina.id = "mm-lingue";

    // Gli elementi si costruiscono uno a uno invece di comporre HTML in una
    // stringa: le bandiere sono SVG pieni di virgolette, e infilarli dentro un
    // attributo style scritto a mano chiude la stringa a meta'.
    var lingue = [["it", "Italiano", BANDIERA_IT], ["en", "English", BANDIERA_GB]];
    for (var l = 0; l < lingue.length; l++) {
      var voce = document.createElement("button");
      voce.type = "button";
      voce.setAttribute("data-lingua", lingue[l][0]);

      var fl = document.createElement("span");
      fl.className = "mm-fl";
      fl.style.backgroundImage = sfondo(lingue[l][2]);

      var nome = document.createElement("span");
      nome.textContent = lingue[l][1];

      var spunta = document.createElement("span");
      spunta.className = "mm-spunta";

      voce.appendChild(fl);
      voce.appendChild(nome);
      voce.appendChild(spunta);
      tendina.appendChild(voce);
    }
    document.body.appendChild(tendina);

    var voci = tendina.querySelectorAll("button");

    function segna() {
      for (var v = 0; v < voci.length; v++) {
        var attiva = (voci[v].getAttribute("data-lingua") === "en") === inglese;
        voci[v].querySelector(".mm-spunta").textContent = attiva ? "\\u2713" : "";
      }
    }

    function apri() {
      var r = comando.getBoundingClientRect();
      tendina.classList.add("mm-aperta");
      // Ancorata sotto la bandiera, ma senza uscire dal bordo dello schermo.
      var largh = tendina.offsetWidth;
      tendina.style.top = (r.bottom + 8) + "px";
      tendina.style.left = Math.max(8, Math.min(r.right - largh, window.innerWidth - largh - 8)) + "px";
      segna();
    }

    function chiudi() { tendina.classList.remove("mm-aperta"); }

    comando.addEventListener("click", function (ev) {
      ev.stopPropagation();
      if (tendina.classList.contains("mm-aperta")) chiudi(); else apri();
    });

    for (var w = 0; w < voci.length; w++) {
      voci[w].addEventListener("click", function (ev) {
        ev.stopPropagation();
        applica(this.getAttribute("data-lingua") === "en");
        chiudi();
      });
    }

    document.addEventListener("click", chiudi);
  })();

  /* ---------- 1d. Niente allergeni sulla carta dei vini ---------- */
  // Su una bottiglia l'unico allergene e' quasi sempre il solfito, che c'e' in
  // quasi tutti i vini: l'icona sotto ogni etichetta non informa nessuno e
  // appesantisce una lista di centinaia di voci.
  (function () {
    function eVino(testo) { return /vin|cantina|champagne|bollicine/i.test(testo || ""); }

    for (var s = 0; s < slides.length; s++) {
      var etichettaMacro = tabs[s] ? (tabs[s].textContent || "") : "";
      var tuttaLaSezione = eVino(etichettaMacro);

      // Si scorre la sezione in ordine tenendo conto di sotto quale categoria
      // ci si trova: le voci non sono annidate nel loro titolo ma gli stanno
      // semplicemente dopo, quindi va ricordato l'ultimo titolo incontrato.
      var dentroVini = tuttaLaSezione;
      var nodi = slides[s].querySelectorAll(
        "[data-section='categories'],[data-section='subcategories'],[class*='allergen-food']");

      for (var n = 0; n < nodi.length; n++) {
        var nodo = nodi[n];
        var sezione = nodo.getAttribute("data-section");
        if (sezione === "categories") {
          dentroVini = tuttaLaSezione || eVino(nodo.textContent);
        } else if (sezione !== "subcategories" && dentroVini) {
          var riga = nodo.closest(".elementContainer") || nodo;
          if (riga !== slides[s]) nodo.style.display = "none";
        }
      }
    }
  })();

  /* ---------- 1e. Fondale della fascia superiore ---------- */
  // L'altezza si misura invece di scriverla: dipende da quante righe occupano
  // i tab, che cambiano con la larghezza dello schermo e con la lingua.
  (function () {
    var fondale = document.createElement("div");
    fondale.id = "mm-fondale";
    document.body.appendChild(fondale);

    function misura() {
      var barra = document.getElementById("tabsMenu");
      var basso = barra ? barra.getBoundingClientRect().bottom : 70;
      fondale.style.height = Math.round(basso) + "px";
    }

    misura();
    window.addEventListener("resize", misura);
    // Cambiando sezione o lingua le voci possono andare a capo: si rimisura.
    window.addEventListener("orientationchange", misura);
    document.addEventListener("click", function () { setTimeout(misura, 60); });
  })();

  /* ---------- 2. Ricerca ---------- */
  var piatti = document.querySelectorAll(".elementContainer");
  var titoli = document.querySelectorAll('[data-section="categories"]');

  var barra = document.createElement("div");
  barra.id = "mm-cerca";
  barra.innerHTML = '<input type="search" placeholder="Cerca un piatto o un ingrediente" ' +
                    'autocomplete="off" autocorrect="off" spellcheck="false">' +
                    '<button type="button">Chiudi</button>';
  document.body.appendChild(barra);

  var esito = document.createElement("div");
  esito.id = "mm-esito";
  document.body.appendChild(esito);

  var campo = barra.querySelector("input");

  function normalizza(t) {
    return (t || "").toLowerCase()
      .normalize("NFD").replace(/[\\u0300-\\u036f]/g, "");  // via gli accenti
  }

  function filtra() {
    var q = normalizza(campo.value).trim();

    if (!q) {
      for (var i = 0; i < piatti.length; i++) piatti[i].classList.remove("mm-nascosto");
      for (var t = 0; t < titoli.length; t++) titoli[t].classList.remove("mm-nascosto");
      mostraCategoria(indiceAttivo());
      esito.classList.remove("mm-aperta");
      return;
    }

    // Cercando si guarda in tutto il menu, non solo nella categoria aperta:
    // il cliente non sa in quale sezione sia il piatto.
    for (var d = 0; d < sezioni.length; d++) {
      sezioni[d].classList.remove("mm-spenta");
      sezioni[d].classList.add("mm-accesa");
    }

    var trovati = 0;
    for (var p = 0; p < piatti.length; p++) {
      var testo = normalizza(piatti[p].innerText);
      var ok = testo.indexOf(q) !== -1;
      piatti[p].classList.toggle("mm-nascosto", !ok);
      if (ok) trovati++;
    }
    // Un titolo di categoria senza piatti visibili sotto e' rumore.
    for (var c = 0; c < titoli.length; c++) titoli[c].classList.add("mm-nascosto");

    esito.textContent = trovati === 0 ? "Nessun piatto trovato"
                      : trovati === 1 ? "1 piatto trovato"
                      : trovati + " piatti trovati";
    esito.classList.add("mm-aperta");
  }

  function indiceAttivo() {
    for (var i = 0; i < tabs.length; i++) {
      var e = tabs[i].querySelector("span");
      if (e && e.getAttribute("data-subsection") === "macroActive") return i;
    }
    return 0;
  }

  function chiudiRicerca() {
    barra.classList.remove("mm-aperta");
    esito.classList.remove("mm-aperta");
    campo.value = "";
    for (var i = 0; i < piatti.length; i++) piatti[i].classList.remove("mm-nascosto");
    for (var t = 0; t < titoli.length; t++) titoli[t].classList.remove("mm-nascosto");
  }

  campo.addEventListener("input", filtra);
  barra.querySelector("button").addEventListener("click", function () {
    chiudiRicerca();
    mostraCategoria(indiceAttivo());
  });

  var lente = document.querySelector(".fa-magnifying-glass");
  if (lente) {
    var bersaglio = lente.closest("[data-section=header]") || lente;
    bersaglio.style.cursor = "pointer";
    bersaglio.addEventListener("click", function () {
      barra.classList.add("mm-aperta");
      campo.focus();
    });
  }

  /* ---------- 3. Icone allergene ---------- */
  var targhetta = document.createElement("div");
  targhetta.id = "mm-etichetta";
  document.body.appendChild(targhetta);
  var timer = null;

  var icone = document.querySelectorAll('[class*="allergen-food"], .fa-snowflake, .fa-temperature-snow');
  for (var n = 0; n < icone.length; n++) {
    (function (icona) {
      var nome = "";
      var cls = (icona.className.baseVal || icona.className || "").toString();
      var m = cls.match(/fa-([a-z]+)-allergen-food/);
      if (m) nome = ALLERGENI[m[1]] || m[1];
      else if (/snow/.test(cls)) nome = "Prodotto abbattuto";
      if (!nome) return;

      icona.setAttribute("title", nome);
      icona.style.cursor = "pointer";
      icona.addEventListener("click", function (ev) {
        var r = icona.getBoundingClientRect();
        targhetta.textContent = nome;
        targhetta.style.left = (r.left + r.width / 2) + "px";
        targhetta.style.top = r.top + "px";
        targhetta.classList.add("mm-aperta");
        clearTimeout(timer);
        timer = setTimeout(function () { targhetta.classList.remove("mm-aperta"); }, 2500);
        ev.stopPropagation();
      });
    })(icone[n]);
  }
})();
"""


def inject(doc, ancore, traduzioni):
    slides = len(re.findall(r'class="[^"]*carousel__item', doc))
    dishes = len(re.findall(r"elementContainer", doc))
    icons = len(re.findall(r"allergen-food", doc))

    if slides < 2:
        sys.exit("ERRORE: %d macro-categorie trovate, struttura del menu cambiata" % slides)
    if dishes < 50:
        sys.exit("ERRORE: solo %d piatti trovati, la ricerca sarebbe inutile" % dishes)

    import json
    js = JS_TEMPLATE % (json.dumps(ALLERGENI, ensure_ascii=False),
                        json.dumps(ancore, ensure_ascii=False),
                        json.dumps(traduzioni, ensure_ascii=False),
                        BANDIERA_IT, BANDIERA_GB)
    block = "<style id='mm-stile'>%s</style><script id='mm-script'>%s</script>" % (CSS, js)

    end = re.search(r"</body\s*>", doc, re.I)
    at = end.start() if end else len(doc)
    return doc[:at] + block + doc[at:], slides, dishes, icons


if __name__ == "__main__":
    import json
    import os

    doc = open(sys.argv[1], encoding="utf-8", errors="ignore").read()

    # Le ancore sono un di piu': se la scoperta non e' andata a buon fine il menu
    # resta comunque completo e navigabile, solo i chip delle zone non portano
    # da nessuna parte. Meglio pubblicare cosi' che non pubblicare.
    ancore = {}
    if len(sys.argv) > 3 and os.path.exists(sys.argv[3]):
        try:
            ancore = json.load(open(sys.argv[3], encoding="utf-8"))
        except ValueError:
            print("  avviso: ancore illeggibili, i chip delle zone resteranno fermi")

    traduzioni = {}
    if len(sys.argv) > 4 and os.path.exists(sys.argv[4]):
        try:
            traduzioni = json.load(open(sys.argv[4], encoding="utf-8"))
        except ValueError:
            print("  avviso: traduzioni illeggibili, la bandiera restera' ferma")

    out, slides, dishes, icons = inject(doc, ancore, traduzioni)
    open(sys.argv[2], "w", encoding="utf-8").write(out)

    n = sum(len(v) for v in ancore.values())
    t = len(traduzioni.get("voci", {}))
    print("interazioni: %d macro-categorie, %d piatti ricercabili, %d icone allergene, "
          "%d zone, %d testi in inglese" % (slides, dishes, icons, n, t))
