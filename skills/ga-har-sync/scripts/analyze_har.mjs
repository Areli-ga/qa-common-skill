#!/usr/bin/env node
import { readFile, readdir, writeFile, mkdir } from 'node:fs/promises';
import { basename, dirname, resolve } from 'node:path';

const sensitiveKey = /authorization|authtoken|token|password|secret|cookie|email|phone|deviceid|regid/i;
const costlyPath = /\/api\/(?:ai|poster|voice-clone|voice-pack|upload|download)/i;
const suspiciousGet = /(?:fix|delete|reset|grant|claim|upload|redeem|draw|exchange|backfill)/i;

function argumentsOf(values) {
  const result = {};
  for (let index = 0; index < values.length; index += 1) {
    const key = values[index];
    if (!key.startsWith('--')) throw new Error(`未知参数：${key}`);
    const value = values[index + 1];
    if (!value || value.startsWith('--')) throw new Error(`参数 ${key} 缺少值`);
    result[key.slice(2)] = value;
    index += 1;
  }
  return result;
}

function unique(values) {
  return [...new Set(values.filter((value) => value !== undefined && value !== null && value !== ''))].sort();
}

function safeDecode(value) {
  try { return decodeURIComponent(value); } catch { return value; }
}

function normalizePath(value) {
  return safeDecode(String(value || ''))
    .replace(/\{\{[^}]+\}\}/g, '{id}')
    .replace(/\{[^}]+\}/g, '{id}')
    .replace(/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/gi, '{uuid}')
    .replace(/\b[0-9a-f]{24,64}\b/gi, '{hex}')
    .replace(/\/\d{9,}(?=\/|$)/g, '/{id}')
    .replace(/\/$/, '') || '/';
}

function labeledKeys(values) {
  return unique(values).map((key) => sensitiveKey.test(key) ? `${key} (sensitive)` : key);
}

function bodyKeys(entry) {
  const text = entry.request?.postData?.text;
  if (!text) return [];
  try {
    const value = JSON.parse(text);
    if (value && typeof value === 'object' && !Array.isArray(value)) return Object.keys(value);
  } catch {
    return (entry.request?.postData?.params || []).map((item) => item.name);
  }
  return [];
}

function businessCode(entry) {
  const text = entry.response?.content?.text;
  if (!text) return undefined;
  try {
    const decoded = entry.response.content.encoding === 'base64' ? Buffer.from(text, 'base64').toString('utf8') : text;
    const value = JSON.parse(decoded);
    return typeof value?.code === 'string' || typeof value?.code === 'number' ? value.code : undefined;
  } catch {
    return undefined;
  }
}

function riskOf(method, path) {
  if (costlyPath.test(path)) return 'costly';
  if (method !== 'GET') return 'stateful';
  if (suspiciousGet.test(path)) return 'manual-review';
  return 'safe-read-candidate';
}

function fingerprint(method, path, queryKeys) {
  return `${method} ${normalizePath(path)} ?${unique(queryKeys).join('&')}`;
}

async function existingFingerprints(project) {
  const directory = resolve(project, 'config/scenarios');
  const files = (await readdir(directory)).filter((file) => file.endsWith('.json'));
  const result = new Set();
  for (const file of files) {
    const scenario = JSON.parse(await readFile(resolve(directory, file), 'utf8'));
    for (const step of scenario.steps || []) {
      result.add(fingerprint(String(step.method || 'GET').toUpperCase(), step.path, Object.keys(step.query || {})));
    }
  }
  return result;
}

const args = argumentsOf(process.argv.slice(2));
if (!args.har) {
  console.error('Usage: node analyze_har.mjs --har /absolute/capture.har [--project /absolute/project] [--output /tmp/analysis.json] [--domains host1,host2]');
  process.exit(1);
}

const project = resolve(args.project || process.cwd());
const domains = new Set((args.domains || 'creator.giggleacademy.com.cn,creator.giggleacademy.com').split(',').map((item) => item.trim()).filter(Boolean));
const har = JSON.parse(await readFile(resolve(args.har), 'utf8'));
const entries = Array.isArray(har.log?.entries) ? har.log.entries : [];
const existing = await existingFingerprints(project);
const grouped = new Map();

for (const entry of entries) {
  let url;
  try { url = new URL(entry.request?.url); } catch { continue; }
  if (!domains.has(url.hostname) || !url.pathname.startsWith('/api/')) continue;
  const method = String(entry.request?.method || 'GET').toUpperCase();
  if (method === 'OPTIONS') continue;
  const queryKeys = unique([...url.searchParams.keys(), ...(entry.request?.queryString || []).map((item) => item.name)]);
  const path = normalizePath(url.pathname);
  const key = fingerprint(method, path, queryKeys);
  const current = grouped.get(key) || {
    fingerprint: key,
    method,
    pathTemplate: path,
    queryKeys: labeledKeys(queryKeys),
    bodyKeys: [],
    requestHeaderKeys: [],
    hosts: [],
    httpStatuses: [],
    businessCodes: [],
    contentTypes: [],
    count: 0,
    firstSeen: entry.startedDateTime,
    lastSeen: entry.startedDateTime,
    existing: existing.has(key),
    risk: riskOf(method, path)
  };
  current.bodyKeys.push(...bodyKeys(entry));
  current.requestHeaderKeys.push(...(entry.request?.headers || []).map((item) => item.name));
  current.hosts.push(url.hostname);
  current.httpStatuses.push(entry.response?.status);
  current.businessCodes.push(businessCode(entry));
  current.contentTypes.push(entry.response?.content?.mimeType);
  current.count += 1;
  current.lastSeen = entry.startedDateTime || current.lastSeen;
  grouped.set(key, current);
}

const inventory = [...grouped.values()]
  .map((item) => ({
    ...item,
    bodyKeys: labeledKeys(item.bodyKeys),
    requestHeaderKeys: labeledKeys(item.requestHeaderKeys),
    hosts: unique(item.hosts),
    httpStatuses: unique(item.httpStatuses),
    businessCodes: unique(item.businessCodes),
    contentTypes: unique(item.contentTypes)
  }))
  .sort((a, b) => a.pathTemplate.localeCompare(b.pathTemplate) || a.method.localeCompare(b.method));
const candidates = inventory.filter((item) => !item.existing);
const methodCounts = Object.fromEntries(unique(inventory.map((item) => item.method)).map((method) => [method, inventory.filter((item) => item.method === method).length]));
const riskCounts = Object.fromEntries(unique(candidates.map((item) => item.risk)).map((risk) => [risk, candidates.filter((item) => item.risk === risk).length]));
const result = {
  generatedAt: new Date().toISOString(),
  source: { fileName: basename(args.har), harEntries: entries.length },
  filters: { domains: [...domains].sort(), pathPrefix: '/api/', optionsExcluded: true },
  summary: {
    matchingRequests: inventory.reduce((sum, item) => sum + item.count, 0),
    uniqueRequestFingerprints: inventory.length,
    alreadyCovered: inventory.length - candidates.length,
    newCandidates: candidates.length,
    methods: methodCounts,
    candidateRisks: riskCounts
  },
  note: 'Contains endpoint templates and field names only. Request/response values and authentication material are intentionally omitted.',
  candidates,
  inventory
};

const serialized = JSON.stringify(result, null, 2) + '\n';
if (args.output) {
  const output = resolve(args.output);
  await mkdir(dirname(output), { recursive: true });
  await writeFile(output, serialized, 'utf8');
  console.log(JSON.stringify({ output, ...result.summary }));
} else {
  process.stdout.write(serialized);
}
