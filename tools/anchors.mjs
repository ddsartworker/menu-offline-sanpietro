// Scopre dove porta ogni chip di sottocategoria.
//
// Nella sezione vini i chip (Champagne, Bianchi Italiani, ...) portano al gruppo
// corrispondente, ma il legame chip -> gruppo non e' scritto da nessuna parte
// nell'HTML: l'id del chip compare solo dentro il chip stesso. Nello snapshot i
// vini sono un'unica lista piatta e i chip non saprebbero dove andare.
//
// Qui un browser vero apre il menu, clicca ogni chip e annota il nome del primo
// piatto che compare. Il nome e' un'ancora stabile: nello snapshot si ritrova
// l'elemento con quel testo e ci si porta sopra. Se il sommelier aggiunge una
// zona, la cattura successiva la scopre da sola.
import puppeteer from "puppeteer-core";
import { writeFileSync } from "node:fs";

const URL = process.env.MENU_URL || "https://menu.menumal.com/sanpietrobistrotdelmare";
const CHROME = process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const DEST = process.argv[2] || "dist/anchors.json";

const attesa = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
});

try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 1800 });
  // networkidle0 non arriva mai: Firestore tiene aperta una connessione.
  await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 90000 });
  await attesa(14000);

  const frame = page.frames().find((f) => f !== page.mainFrame());
  if (!frame) throw new Error("iframe del menu non trovato");

  const nMacro = await frame.evaluate(
    () => document.querySelectorAll('div[data-section="macros"]').length);
  const ancore = {};

  for (let m = 0; m < nMacro; m++) {
    await frame.evaluate((i) => {
      document.querySelectorAll('div[data-section="macros"]')[i].click();
    }, m);
    await attesa(2500);

    const nChip = await frame.evaluate((i) => {
      const slide = document.querySelectorAll(".carousel__item")[i];
      if (!slide) return 0;
      return slide.querySelectorAll('li[data-section="categories"]').length;
    }, m);

    if (nChip < 2) {
      console.error(`macro ${m}: ${nChip} chip, niente da mappare`);
      continue;
    }

    ancore[m] = [];
    for (let c = 0; c < nChip; c++) {
      const risultato = await frame.evaluate((i, k) => {
        const slide = document.querySelectorAll(".carousel__item")[i];
        const chips = slide.querySelectorAll('li[data-section="categories"]');
        if (!chips[k]) return null;
        const etichetta = (chips[k].innerText || "").replace(/categoria menu:/gi, "").trim();
        chips[k].click();
        return new Promise((res) => setTimeout(() => {
          // Solo cio' che e' davvero visibile: gli altri gruppi restano nel DOM.
          const nomi = Array.from(slide.querySelectorAll("[data-tab=name]"))
            .filter((e) => e.offsetParent !== null)
            .map((e) => (e.innerText || "").trim())
            .filter(Boolean);
          res({ etichetta, primo: nomi[0] || null, visibili: nomi.length });
        }, 1500));
      }, m, c);

      if (risultato && risultato.primo) {
        ancore[m].push({
          chip: risultato.etichetta,
          ancora: risultato.primo,
          voci: risultato.visibili,
        });
        console.error(`  ${risultato.etichetta} -> "${risultato.primo}" (${risultato.visibili} voci)`);
      } else {
        console.error(`  chip ${c}: nessun piatto visibile, saltato`);
      }
    }
  }

  writeFileSync(DEST, JSON.stringify(ancore));
  const tot = Object.values(ancore).reduce((n, v) => n + v.length, 0);
  console.error(`mappate ${tot} ancore in ${DEST}`);
} finally {
  await browser.close();
}
