// Renderiza apresentacao-animada.html para MP4 (1920x1080) com relógio virtual:
// para cada quadro chama window.renderAt(t), tira um print e manda para o ffmpeg.
// Nenhum quadro depende do tempo real, então o vídeo sai igual em qualquer máquina.
//
// Uso (na pasta docs/apresentacao, depois de `npm install` e `python3 build.py`):
//   node render.mjs --partes abertura,arquitetura --saida abertura.mp4
//   node render.mjs --saida motion.mp4                 (todas as partes)
//   node render.mjs --quadros 3,20,95 --pasta frames   (só PNGs nesses segundos)
// Opções: --fps 30, --de 0 --ate 10 (segundos, em vez de --partes), --navegador <caminho>
import { chromium } from "playwright-core";
import { spawn } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, xs) => {
  if (a.startsWith("--")) acc.push([a.slice(2), xs[i + 1] && !xs[i + 1].startsWith("--") ? xs[i + 1] : true]);
  return acc;
}, []));
const fps = Number(args.fps || 30);
const html = path.join(aqui, "apresentacao-animada.html");
const navegadores = [args.navegador, process.env.NAVEGADOR,
  "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"].filter(Boolean);
const exe = navegadores.find(p => existsSync(p));
if (!existsSync(html)) { console.error("Falta apresentacao-animada.html: rode python3 build.py antes."); process.exit(1); }
if (!exe) { console.error("Nenhum navegador Chromium encontrado (Brave ou Chrome). Use --navegador <caminho>."); process.exit(1); }

const browser = await chromium.launch({
  executablePath: exe, headless: true,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--hide-scrollbars", "--force-color-profile=srgb"],
});
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
const erros = [];
page.on("pageerror", e => erros.push(String(e)));
page.on("console", m => { if (m.type() === "error") erros.push(m.text()); });
await page.goto(pathToFileURL(html).href + "?render");
await page.waitForFunction(() => window.pronto === true, null, { timeout: 60000 });
const { partes, total } = await page.evaluate(() => ({ partes: window.PARTES, total: window.TOTAL }));
if (erros.length) console.warn("Avisos da página:\n  " + erros.join("\n  "));

// ---- só alguns quadros em PNG (para revisar o layout) ----
if (args.quadros) {
  const pasta = path.resolve(aqui, args.pasta || "frames");
  mkdirSync(pasta, { recursive: true });
  for (const s of String(args.quadros).split(",").map(Number)) {
    await page.evaluate(t => window.renderAt(t), s);
    const arq = path.join(pasta, `t${String(s.toFixed(1)).padStart(5, "0")}.png`);
    await page.screenshot({ path: arq, type: "png" });
    console.log(arq);
  }
  await browser.close();
  process.exit(erros.length ? 2 : 0);
}

// ---- intervalos a renderizar ----
let intervalos;
if (args.partes) {
  intervalos = String(args.partes).split(",").map(id => {
    const p = partes.find(x => x.id === id.trim());
    if (!p) { console.error(`Parte desconhecida: ${id}. Partes: ${partes.map(x => x.id).join(", ")}`); process.exit(1); }
    return [p.ini, p.ini + p.dur];
  });
} else intervalos = [[Number(args.de || 0), Number(args.ate || total)]];
const tempos = [];
for (const [a, b] of intervalos) for (let i = 0; a + i / fps < b - 1e-9; i++) tempos.push(a + i / fps);

const saida = path.resolve(aqui, args.saida || "motion.mp4");
const ff = spawn("ffmpeg", ["-y", "-hide_banner", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "mjpeg", "-i", "-",
  "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p", "-color_range", "tv", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", String(fps), "-movflags", "+faststart", saida],
  { stdio: ["pipe", "inherit", "inherit"] });
const fimFF = new Promise((ok, falha) => ff.on("close", c => c === 0 ? ok() : falha(new Error("ffmpeg saiu com " + c))));
const escrever = buf => new Promise(ok => ff.stdin.write(buf) ? ok() : ff.stdin.once("drain", ok));

const t0 = Date.now();
for (let i = 0; i < tempos.length; i++) {
  await page.evaluate(t => window.renderAt(t), tempos[i]);
  let quadro;
  for (let tentativa = 1; ; tentativa++) {   // o Chromium às vezes falha um print isolado: tenta de novo
    try { quadro = await page.screenshot({ type: "jpeg", quality: 95 }); break; }
    catch (e) { if (tentativa >= 3) throw e; await page.waitForTimeout(500); }
  }
  await escrever(quadro);
  if (i % fps === 0 || i === tempos.length - 1) {
    const seg = (Date.now() - t0) / 1000;
    process.stdout.write(`\r${i + 1}/${tempos.length} quadros · ${(seg ? (i + 1) / seg : 0).toFixed(1)} q/s · ${seg.toFixed(0)} s   `);
  }
}
ff.stdin.end();
await fimFF;
await browser.close();
console.log(`\n${saida} · ${tempos.length} quadros · ${(tempos.length / fps).toFixed(1)} s de vídeo · ${((Date.now() - t0) / 1000).toFixed(0)} s para renderizar`);
if (erros.length) process.exit(2);
