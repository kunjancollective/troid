#!/usr/bin/env node
"use strict";
/* When troid's Anthropic API keys expire (launch handoff 2026-09-26, 5.4: the production key possibly about 23 October,
 * the evaluation key about 24 October). A regular key can't read its own expiry, and an expired key answers every call
 * with 401 and can't be reactivated; the Admin API lists each key in the organisation with its expires_at, null for a key
 * that never expires (platform.claude.com/docs/en/manage-claude/admin-api, "API keys"). Run by the owner:
 *
 *   ANTHROPIC_ADMIN_KEY=sk-ant-admin... node web/key_expiry.js [--days 14]
 *
 * Prints each active key: its name, where it works, the Console's hint of it, when it expires (UTC) and the days left.
 * Exits 1 when an active key has expired or expires within --days (default 14), 2 when the Admin API can't be read, so it
 * can gate a check. Never prints a key; the admin key comes from the environment and goes to api.anthropic.com only.
 * Record the production and evaluation keys' dates in Vercel as ANTHROPIC_API_KEY_EXPIRES and
 * ANTHROPIC_API_KEY_EVAL_EXPIRES: ask troid's GET /api/troid then reports their days left and warns from 14 days out.
 */
function local(u) {
  try { const h = new URL(u).hostname; return h === "127.0.0.1" || h === "localhost"; } catch (e) { return false; }
}

async function list(key, base) {
  const out = [];
  let after = null;
  for (let page = 0; page < 100; page++) {
    const u = new URL("/v1/organizations/api_keys", base);
    u.searchParams.set("limit", "100"); u.searchParams.set("status", "active");
    if (after) u.searchParams.set("after_id", after);
    const r = await fetch(u, { headers: { "x-api-key": key, "anthropic-version": "2023-06-01" }, signal: AbortSignal.timeout(20000) });
    const j = await r.json().catch(() => null);
    if (!r.ok || !j || !Array.isArray(j.data)) {
      throw new Error(`the Admin API answered ${r.status}` + (j && j.error && j.error.type ? ` (${j.error.type})` : ""));
    }
    out.push(...j.data);
    if (!j.has_more || !j.last_id) break;
    after = j.last_id;
  }
  return out;
}

function days(expires, now) {
  const t = Date.parse(expires);
  return expires && Number.isFinite(t) ? Math.floor((t - now) / 86400e3) : null;
}

function where(k) {
  const s = k.scope || {};
  return s.type === "organization" ? "any workspace" : s.workspace_id || k.workspace_id || "the Default Workspace";
}

async function main(argv, env, write) {
  const i = argv.indexOf("--days"), warn = i >= 0 ? Number(argv[i + 1]) : 14;
  const key = env.ANTHROPIC_ADMIN_KEY || "";
  if (!key) { write("Set ANTHROPIC_ADMIN_KEY (an Admin API key, from the Console) in the environment. Nothing is read from a file.\n"); return 2; }
  const base = env.ANTHROPIC_ADMIN_BASE_URL || "https://api.anthropic.com";          // another address: the local test only
  if (env.ANTHROPIC_ADMIN_BASE_URL && !local(base)) { write("ANTHROPIC_ADMIN_BASE_URL is for the local test only.\n"); return 2; }
  if (!Number.isFinite(warn) || warn < 0) { write("--days takes a number of days.\n"); return 2; }
  let keys;
  try { keys = await list(key, base); } catch (e) { write(`Can't read the keys: ${e.message}.\n`); return 2; }
  const now = Date.now(), rows = keys.map((k) => ({ name: k.name || k.id, where: where(k), hint: k.partial_key_hint || "",
    expires: k.expires_at ? new Date(k.expires_at).toISOString().replace("T", " ").slice(0, 16) + " UTC" : "never",
    left: days(k.expires_at, now) }));
  rows.sort((a, b) => (a.left == null) - (b.left == null) || (a.left - b.left));
  const due = rows.filter((r) => r.left != null && r.left <= warn);
  write(`${rows.length} active API key${rows.length === 1 ? "" : "s"} in the organisation:\n`);
  for (const r of rows) {
    const flag = r.left == null ? "" : r.left < 0 ? "  EXPIRED" : r.left <= warn ? "  ROTATE" : "";
    write(`  ${r.name}  ·  ${r.where}  ·  ${r.hint || "no hint"}  ·  expires ${r.expires}${r.left == null ? "" : `  ·  ${r.left} day${r.left === 1 ? "" : "s"} left`}${flag}\n`);
  }
  write(due.length ? `${due.length} key${due.length === 1 ? "" : "s"} to rotate within ${warn} days.\n` : `None expires within ${warn} days.\n`);
  return due.length ? 1 : 0;
}

module.exports = { main, list, days };
if (require.main === module) main(process.argv.slice(2), process.env, (s) => process.stdout.write(s)).then((c) => { process.exitCode = c; });
