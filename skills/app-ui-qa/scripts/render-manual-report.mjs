#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const [, , inputArg, outputArg] = process.argv;

if (!inputArg) {
  console.error('Usage: node scripts/render-manual-report.mjs <report.md> [report.html]');
  process.exit(1);
}

const inputPath = path.resolve(inputArg);
const outputPath = outputArg
  ? path.resolve(outputArg)
  : inputPath.replace(/\.md$/i, '.html');

const markdown = fs.readFileSync(inputPath, 'utf8');

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

fs.writeFileSync(outputPath, html);
console.log(outputPath);
