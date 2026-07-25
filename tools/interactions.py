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
.mm-accesa{display:block!important;width:100%!important}
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


def inject(doc):
    slides = len(re.findall(r'class="[^"]*carousel__item', doc))
    dishes = len(re.findall(r"elementContainer", doc))
    icons = len(re.findall(r"allergen-food", doc))

    if slides < 2:
        sys.exit("ERRORE: %d macro-categorie trovate, struttura del menu cambiata" % slides)
    if dishes < 50:
        sys.exit("ERRORE: solo %d piatti trovati, la ricerca sarebbe inutile" % dishes)

    import json
    js = JS_TEMPLATE % json.dumps(ALLERGENI, ensure_ascii=False)
    block = "<style id='mm-stile'>%s</style><script id='mm-script'>%s</script>" % (CSS, js)

    end = re.search(r"</body\s*>", doc, re.I)
    at = end.start() if end else len(doc)
    return doc[:at] + block + doc[at:], slides, dishes, icons


if __name__ == "__main__":
    doc = open(sys.argv[1], encoding="utf-8", errors="ignore").read()
    out, slides, dishes, icons = inject(doc)
    open(sys.argv[2], "w", encoding="utf-8").write(out)
    print("interazioni: %d macro-categorie, %d piatti ricercabili, %d icone allergene"
          % (slides, dishes, icons))
