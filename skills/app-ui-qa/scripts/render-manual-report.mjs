#!/usr/bin/env node

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const cliArgs = process.argv.slice(2);
const positionalArgs = [];
const options = {
  inlineImages: true,
  imageFormat: 'webp',
  imageQuality: 76,
  maxImageWidth: 1280,
};

function usage() {
  console.error(
    'Usage: node scripts/render-manual-report.mjs <report.md> [report.html] '
      + '[--image-format webp|original] [--image-quality 1-100] '
      + '[--max-image-width pixels] [--no-inline-images]',
  );
}

for (let index = 0; index < cliArgs.length; index += 1) {
  const arg = cliArgs[index];
  if (arg === '--no-inline-images') {
    options.inlineImages = false;
    continue;
  }
  if (arg === '--image-format') {
    options.imageFormat = cliArgs[index + 1];
    index += 1;
    continue;
  }
  if (arg === '--image-quality') {
    options.imageQuality = Number(cliArgs[index + 1]);
    index += 1;
    continue;
  }
  if (arg === '--max-image-width') {
    options.maxImageWidth = Number(cliArgs[index + 1]);
    index += 1;
    continue;
  }
  if (arg === '--help' || arg === '-h') {
    usage();
    process.exit(0);
  }
  if (arg.startsWith('--')) {
    console.error(`Unknown option: ${arg}`);
    usage();
    process.exit(2);
  }
  positionalArgs.push(arg);
}

const [inputArg, outputArg] = positionalArgs;

if (!inputArg) {
  usage();
  process.exit(1);
}

if (!['webp', 'original'].includes(options.imageFormat)) {
  console.error('--image-format must be webp or original');
  process.exit(2);
}
if (!Number.isInteger(options.imageQuality)
  || options.imageQuality < 1
  || options.imageQuality > 100) {
  console.error('--image-quality must be an integer between 1 and 100');
  process.exit(2);
}
if (!Number.isInteger(options.maxImageWidth) || options.maxImageWidth < 1) {
  console.error('--max-image-width must be a positive integer');
  process.exit(2);
}

const inputPath = path.resolve(inputArg);
const outputPath = outputArg
  ? path.resolve(outputArg)
  : inputPath.replace(/\.md$/i, '.html');

const markdown = fs.readFileSync(inputPath, 'utf8');
const inputDirectory = path.dirname(inputPath);

const mimeTypes = new Map([
  ['.avif', 'image/avif'],
  ['.gif', 'image/gif'],
  ['.jpeg', 'image/jpeg'],
  ['.jpg', 'image/jpeg'],
  ['.png', 'image/png'],
  ['.svg', 'image/svg+xml'],
  ['.webp', 'image/webp'],
]);

const imageStats = {
  tags: 0,
  uniqueFiles: 0,
  webp: 0,
  original: 0,
  sourceBytes: 0,
  embeddedBytes: 0,
};
const embeddedImageCache = new Map();
let sharpLoader;

async function loadSharp() {
  if (sharpLoader === undefined) {
    sharpLoader = import('sharp')
      .then((module) => module.default)
      .catch(() => null);
  }
  return sharpLoader;
}

function readConvertedFile(outputFile, result) {
  if (result.error || result.status !== 0 || !fs.existsSync(outputFile)) {
    return null;
  }
  const converted = fs.readFileSync(outputFile);
  return converted.length > 0 ? converted : null;
}

function convertWithCommand(inputFile, tempDirectory, command, args) {
  const outputFile = path.join(tempDirectory, `${command}.webp`);
  const result = spawnSync(command, args(outputFile), {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  return readConvertedFile(outputFile, result);
}

async function convertToWebp(inputFile) {
  if (path.extname(inputFile).toLowerCase() === '.webp') {
    return { buffer: fs.readFileSync(inputFile), converter: 'source-webp' };
  }

  const sharp = await loadSharp();
  if (sharp) {
    try {
      const buffer = await sharp(inputFile)
        .rotate()
        .resize({
          width: options.maxImageWidth,
          withoutEnlargement: true,
        })
        .webp({ quality: options.imageQuality })
        .toBuffer();
      return { buffer, converter: 'sharp' };
    } catch {
      // Try command-line converters before falling back to the source format.
    }
  }

  const tempDirectory = fs.mkdtempSync(
    path.join(os.tmpdir(), 'app-ui-qa-report-'),
  );

  try {
    const cwebp = convertWithCommand(
      inputFile,
      tempDirectory,
      'cwebp',
      (outputFile) => [
        '-quiet',
        '-q',
        String(options.imageQuality),
        inputFile,
        '-o',
        outputFile,
      ],
    );
    if (cwebp) {
      return { buffer: cwebp, converter: 'cwebp' };
    }

    const ffmpeg = convertWithCommand(
      inputFile,
      tempDirectory,
      'ffmpeg',
      (outputFile) => [
        '-v',
        'error',
        '-y',
        '-i',
        inputFile,
        '-vf',
        `scale='min(iw,${options.maxImageWidth})':-2`,
        '-c:v',
        'libwebp',
        '-quality',
        String(options.imageQuality),
        outputFile,
      ],
    );
    if (ffmpeg) {
      return { buffer: ffmpeg, converter: 'ffmpeg' };
    }

    const sips = convertWithCommand(
      inputFile,
      tempDirectory,
      'sips',
      (outputFile) => [
        '-s',
        'format',
        'webp',
        '-s',
        'formatOptions',
        String(options.imageQuality),
        '-Z',
        String(options.maxImageWidth),
        inputFile,
        '--out',
        outputFile,
      ],
    );
    if (sips) {
      return { buffer: sips, converter: 'sips' };
    }
  } finally {
    fs.rmSync(tempDirectory, { force: true, recursive: true });
  }

  return null;
}

function resolveLocalImage(source) {
  if (source.startsWith('file://')) {
    return fileURLToPath(source);
  }
  if (/^[a-z][a-z0-9+.-]*:/i.test(source)) {
    throw new Error(
      `External image is not allowed in a self-contained report: ${source}`,
    );
  }
  const decoded = decodeURIComponent(source.split(/[?#]/, 1)[0]);
  return path.resolve(inputDirectory, decoded);
}

async function makeEmbeddedSource(source) {
  if (/^data:/i.test(source)) {
    return source;
  }

  const localPath = resolveLocalImage(source);
  const cached = embeddedImageCache.get(localPath);
  if (cached) {
    return cached;
  }

  const stat = fs.statSync(localPath, { throwIfNoEntry: false });
  if (!stat?.isFile()) {
    throw new Error(`Report image not found: ${source} -> ${localPath}`);
  }

  const originalBuffer = fs.readFileSync(localPath);
  const originalMime = mimeTypes.get(path.extname(localPath).toLowerCase());
  if (!originalMime) {
    throw new Error(`Unsupported report image type: ${localPath}`);
  }

  let buffer = originalBuffer;
  let mime = originalMime;
  let format = 'original';

  if (options.imageFormat === 'webp') {
    const converted = await convertToWebp(localPath);
    if (converted) {
      buffer = converted.buffer;
      mime = 'image/webp';
      format = 'webp';
    }
  }

  const dataUri = `data:${mime};base64,${buffer.toString('base64')}`;
  embeddedImageCache.set(localPath, dataUri);
  imageStats.uniqueFiles += 1;
  imageStats.sourceBytes += originalBuffer.length;
  imageStats.embeddedBytes += buffer.length;
  imageStats[format] += 1;
  return dataUri;
}

async function embedImageTags(value) {
  const imagePattern = /<img\b[^>]*\bsrc\s*=\s*(["'])(.*?)\1[^>]*>/gi;
  const matches = [...value.matchAll(imagePattern)];
  if (!matches.length || !options.inlineImages) {
    return value;
  }

  let cursor = 0;
  let result = '';
  for (const match of matches) {
    result += value.slice(cursor, match.index);
    const source = match[2];
    const embedded = await makeEmbeddedSource(source);
    let tag = match[0].replace(source, embedded);
    if (!/\bloading\s*=/i.test(tag)) {
      tag = tag.endsWith('/>')
        ? `${tag.slice(0, -2)} loading="lazy" decoding="async" />`
        : `${tag.slice(0, -1)} loading="lazy" decoding="async">`;
    }
    result += tag;
    cursor = match.index + match[0].length;
    imageStats.tags += 1;
  }
  result += value.slice(cursor);
  return result;
}

function escapeHtml(value) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function inline(value) {
  const raw = [];
  let text = value.replace(/<img\b[^>]*>|<br\s*\/?>/gi, (match) => {
    raw.push(match);
    return `@@RAW_${raw.length - 1}@@`;
  });

  text = escapeHtml(text)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  raw.forEach((match, index) => {
    text = text.replace(`@@RAW_${index}@@`, match);
  });

  return text;
}

function renderTable(rows) {
  const [header, , ...body] = rows;
  const cells = (row) => row
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim());

  const headerHtml = cells(header).map((cell) => `<th>${inline(cell)}</th>`).join('');
  const bodyHtml = body
    .filter((row) => row.trim())
    .map((row) => `<tr>${cells(row).map((cell) => `<td>${inline(cell)}</td>`).join('')}</tr>`)
    .join('\n');

  return `<table><thead><tr>${headerHtml}</tr></thead><tbody>${bodyHtml}</tbody></table>`;
}

const lines = markdown.split(/\r?\n/);
const body = [];
let tableRows = [];
let listType = null;

function closeList() {
  if (listType) {
    body.push(`</${listType}>`);
    listType = null;
  }
}

function closeTable() {
  if (tableRows.length) {
    closeList();
    body.push(renderTable(tableRows));
    tableRows = [];
  }
}

for (const line of lines) {
  if (/^\s*\|.+\|\s*$/.test(line)) {
    closeList();
    tableRows.push(line);
    continue;
  }

  closeTable();

  if (!line.trim()) {
    closeList();
    continue;
  }

  const heading = /^(#{1,4})\s+(.+)$/.exec(line);
  if (heading) {
    closeList();
    const level = Math.min(heading[1].length, 4);
    body.push(`<h${level}>${inline(heading[2])}</h${level}>`);
    continue;
  }

  const ordered = /^\d+\.\s+(.+)$/.exec(line);
  if (ordered) {
    if (listType !== 'ol') {
      closeList();
      body.push('<ol>');
      listType = 'ol';
    }
    body.push(`<li>${inline(ordered[1])}</li>`);
    continue;
  }

  const unordered = /^-\s+(.+)$/.exec(line);
  if (unordered) {
    if (listType !== 'ul') {
      closeList();
      body.push('<ul>');
      listType = 'ul';
    }
    body.push(`<li>${inline(unordered[1])}</li>`);
    continue;
  }

  closeList();
  body.push(`<p>${inline(line)}</p>`);
}

closeTable();
closeList();

const title = (markdown.match(/^#\s+(.+)$/m)?.[1] || 'UI QA Report').trim();
const html = `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="qa-report-assets" content="${options.inlineImages ? 'inline' : 'external'}">
  <title>${escapeHtml(title)}</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --paper: #ffffff;
      --text: #17202a;
      --muted: #5c6670;
      --line: #dfe4ea;
      --accent: #1864ab;
      --risk: #b42318;
      --warn: #9a6700;
      --ok: #1a7f37;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    main {
      width: min(1160px, calc(100vw - 32px));
      margin: 32px auto;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 32px;
      box-shadow: 0 12px 30px rgba(20, 30, 40, 0.08);
    }
    h1, h2, h3, h4 { line-height: 1.25; margin: 28px 0 12px; }
    h1 { margin-top: 0; font-size: 28px; }
    h2 { padding-top: 8px; border-top: 1px solid var(--line); font-size: 22px; }
    h3 { font-size: 18px; color: var(--accent); }
    h4 { font-size: 16px; }
    p { margin: 10px 0; }
    ul, ol { margin: 8px 0 16px 24px; padding: 0; }
    li { margin: 8px 0; }
    code {
      background: #eef1f4;
      border-radius: 4px;
      padding: 2px 5px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.92em;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 14px 0 22px;
      table-layout: fixed;
    }
    th, td {
      border: 1px solid var(--line);
      padding: 9px 10px;
      vertical-align: top;
      word-break: break-word;
    }
    th {
      background: #f1f4f7;
      text-align: left;
      font-weight: 650;
    }
    img {
      display: inline-block;
      max-width: min(320px, 100%);
      height: auto;
      margin: 8px 10px 12px 0;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      box-shadow: 0 6px 18px rgba(20, 30, 40, 0.12);
      vertical-align: top;
    }
    strong { font-weight: 700; }
    h2 + p strong, h3 strong { color: var(--risk); }
    @media print {
      body { background: #fff; }
      main { width: auto; margin: 0; border: 0; box-shadow: none; }
      img { break-inside: avoid; }
    }
  </style>
</head>
<body>
  <main>
${body.join('\n')}
  </main>
</body>
</html>
`;

let finalHtml;
try {
  finalHtml = await embedImageTags(html);
} catch (error) {
  console.error(`Failed to build self-contained report: ${error.message}`);
  process.exit(1);
}

fs.writeFileSync(outputPath, finalHtml);
console.log(outputPath);
if (options.inlineImages) {
  const sourceMiB = (imageStats.sourceBytes / 1024 / 1024).toFixed(2);
  const embeddedMiB = (imageStats.embeddedBytes / 1024 / 1024).toFixed(2);
  const htmlMiB = (Buffer.byteLength(finalHtml) / 1024 / 1024).toFixed(2);
  console.log(
    `Embedded ${imageStats.tags} image tag(s) from ${imageStats.uniqueFiles} file(s): `
      + `${imageStats.webp} WebP, ${imageStats.original} original; `
      + `${sourceMiB} MiB source -> ${embeddedMiB} MiB image payload; `
      + `${htmlMiB} MiB standalone HTML.`,
  );
  if (options.imageFormat === 'webp' && imageStats.original > 0) {
    console.warn(
      'WebP conversion was unavailable for some images; they were embedded in their original '
        + 'format. Install optional dependency sharp for smaller reports.',
    );
  }
}
