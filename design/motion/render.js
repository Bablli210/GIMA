#!/usr/bin/env node
/*
  Renders motion.html to an MP4, one frame at a time.

    node render.js                       full film → gima-website-direction.mp4
    node render.js --stills 3,12.5,40    single frames → stills/t-<sec>.jpg
    node render.js --from 20 --to 30     part of the film (for checking)
    node render.js --audio score.wav     full film with the soundtrack (python3 score.py writes score.wav)

  Needs Playwright (with Chromium) and ffmpeg. Set FFMPEG=/path/to/ffmpeg if it is not on PATH.
  Set LOCAL_ASSETS=/dir to serve Google Fonts and three.js from local copies when offline:
    <dir>/fonts/fonts.css, <dir>/fonts/<path with / replaced by _>, <dir>/three.min.js
*/
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn, execSync } = require('child_process');

let playwright;
try { playwright = require('playwright'); }
catch (e) { playwright = require(path.join(execSync('npm root -g').toString().trim(), 'playwright')); }

const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf('--' + name); return i < 0 ? def : args[i + 1]; };
const ROOT = path.resolve(__dirname, '..');            // serve design/ so ../moodboard/assets resolves
const FPS = +opt('fps', 30);
const OUT = path.resolve(__dirname, opt('out', 'gima-website-direction.mp4'));
const LOCAL = process.env.LOCAL_ASSETS;
const FFMPEG = process.env.FFMPEG || 'ffmpeg';
const AUDIO = opt('audio') && path.resolve(opt('audio'));

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.jpg': 'image/jpeg', '.png': 'image/png', '.css': 'text/css' };
const server = http.createServer((req, res) => {
  const file = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});

(async () => {
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const url = `http://127.0.0.1:${server.address().port}/motion/motion.html`;
  const browser = await playwright.chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--font-render-hinting=none'] });
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  if (LOCAL) {
    await ctx.route('https://fonts.googleapis.com/**', r => r.fulfill({ path: path.join(LOCAL, 'fonts/fonts.css'), contentType: 'text/css' }));
    await ctx.route('https://fonts.gstatic.com/**', r => {
      const f = r.request().url().replace('https://fonts.gstatic.com/', '').replace(/\//g, '_');
      r.fulfill({ path: path.join(LOCAL, 'fonts', f), contentType: 'font/woff2', headers: { 'access-control-allow-origin': '*' } });
    });
    await ctx.route('https://cdnjs.cloudflare.com/**', r => r.fulfill({ path: path.join(LOCAL, 'three.min.js'), contentType: 'application/javascript' }));
  }
  const page = await ctx.newPage();
  page.on('console', m => { if (m.type() === 'error') console.error('page:', m.text()); });
  page.on('pageerror', e => console.error('page error:', e.message));
  await page.goto(url, { waitUntil: 'networkidle' });
  const info = await page.evaluate(() => window.ready);
  const DUR = await page.evaluate(() => window.DURATION);
  console.log('ready', info, 'duration', DUR);

  const shot = async t => {
    await page.evaluate(t => window.render(t), t);
    return page.screenshot({ type: 'jpeg', quality: 94, clip: { x: 0, y: 0, width: 1920, height: 1080 } });
  };

  const stills = opt('stills');
  if (stills) {
    const dir = path.join(__dirname, 'stills'); fs.mkdirSync(dir, { recursive: true });
    for (const s of stills.split(',')) { fs.writeFileSync(path.join(dir, `t-${s}.jpg`), await shot(+s)); console.log('still', s); }
  } else {
    const from = +opt('from', 0), to = +opt('to', DUR);
    const n0 = Math.round(from * FPS), n1 = Math.round(to * FPS);
    const audio = AUDIO ? ['-ss', String(from), '-t', String(to - from), '-i', AUDIO, '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '256k'] : [];
    const ff = spawn(FFMPEG, ['-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', ...audio,
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'slow', '-profile:v', 'high', '-movflags', '+faststart', OUT], { stdio: ['pipe', 'inherit', 'inherit'] });
    const t0 = Date.now();
    for (let n = n0; n < n1; n++) {
      const buf = await shot(n / FPS);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (n % 60 === 0) console.log(`frame ${n}/${n1}  ${((Date.now() - t0) / 1000).toFixed(0)} s`);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    console.log('wrote', OUT);
  }
  await browser.close();
  server.close();
})().catch(e => { console.error(e); process.exit(1); });
