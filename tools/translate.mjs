// Raccoglie la versione inglese del menu.
//
// Menumal traduce con il widget di Google Translate, che ha bisogno della rete:
// sul tablet offline non tradurrebbe nulla. La traduzione va quindi cotta dentro
// lo snapshot al momento della cattura.
//
// Non si salva una seconda copia del menu: si salva solo la coppia
// italiano/inglese di ogni testo che cambia. Sono poche decine di KB invece di
// raddoppiare un file da 1,8 MB, e i font restano condivisi.
//
// I nomi dei piatti hanno la classe notranslate e restano in italiano: e' una
// scelta di Menumal, e ha senso - "Mezzi Calamari Veraci" non si traduce.
import puppeteer from "puppeteer-core";
import { writeFileSync } from "node:fs";

const URL = process.env.MENU_URL || "https://menu.menumal.com/sanpietrobistrotdelmare";
const CHROME = process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const DEST = process.argv[2] || "dist/translations.json";
const LINGUA = process.argv[3] || "en";

const attesa = (ms) => new Promise((r) => setTimeout(r, ms));

// Gli elementi che portano testo traducibile, in un ordine che resta lo stesso
// prima e dopo la traduzione: Google riscrive il contenuto dentro l'elemento,
// non l'elenco degli elementi.
const SELETTORE = [
  "[data-tab=description]",
  '[data-section="categories"]',
  '[data-section="subcategories"]',
  '[data-section="macros"]',
  "[data-tab=name]",
].join(",");

const leggi = () => {
  const elementi = document.querySelectorAll(
    "[data-tab=description],[data-section='categories'],[data-section='subcategories']," +
    "[data-section='macros'],[data-tab=name]");
  return Array.from(elementi).map((e) =>
    (e.textContent || "").replace(/categoria menu:/gi, "").replace(/\s+/g, " ").trim());
};

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
});

try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 1800 });
  await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 90000 });
  await attesa(15000);

  const frame = page.frames().find((f) => f !== page.mainFrame());
  if (!frame) throw new Error("iframe del menu non trovato");

  const italiano = await frame.evaluate(leggi);
  console.error(`testi in italiano: ${italiano.length}`);

  const acceso = await frame.evaluate(async (lingua) => {
    const sel = document.querySelector(".goog-te-combo");
    if (!sel) return false;
    sel.value = lingua;
    sel.dispatchEvent(new Event("change"));
    await new Promise((r) => setTimeout(r, 9000));
    return document.documentElement.classList.contains("translated-ltr");
  }, LINGUA);

  if (!acceso) throw new Error("Google Translate non si e' attivato");

  const inglese = await frame.evaluate(leggi);
  if (inglese.length !== italiano.length) {
    throw new Error(`elenco cambiato: ${italiano.length} -> ${inglese.length}`);
  }

  const voci = {};
  for (let i = 0; i < italiano.length; i++) {
    if (italiano[i] && inglese[i] && italiano[i] !== inglese[i]) voci[i] = inglese[i];
  }

  const tradotti = Object.keys(voci).length;
  if (tradotti < 10) throw new Error(`solo ${tradotti} testi tradotti, traduzione non riuscita`);

  writeFileSync(DEST, JSON.stringify({ lingua: LINGUA, totale: italiano.length, voci }));
  console.error(`tradotti ${tradotti} testi su ${italiano.length} (${Math.round(
    JSON.stringify(voci).length / 1024)} KB)`);
} finally {
  await browser.close();
}
