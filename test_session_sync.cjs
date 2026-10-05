/* Browser regression tests against an isolated chatbot frontend + auth APIs.
 * Set PLAYWRIGHT_MODULE if playwright is installed outside this directory.
 * Start test_session_backend.py for system on 8131 and chatbot on 8130.
 * Run a chatbot frontend on 4130 with /chatbot and
 * SYSTEM_SSO_ORIGINS=http://127.0.0.1:4131.
 * The system browser harness executes the repository's actual auth API code.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const http = require('node:http');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const ts = require(path.join(root, 'system_olpai2026/frontend/node_modules/typescript'));
const chatbot = 'http://127.0.0.1:4130/chatbot';
const system = 'http://127.0.0.1:4131';
const authKey = 'chatbot-auth:v3';
const revisionKey = 'chatbot-auth:revision:v1';
const password = 'Session-password-2026';
const compile = (file) => ts.transpileModule(fs.readFileSync(path.join(root, file), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const sessionCode = compile('system_olpai2026/frontend/src/lib/chatbotSession.ts');
const apiCode = compile('system_olpai2026/frontend/src/lib/api.ts');

function harness(destination, enabled = true) {
  return `<!doctype html><html><body><h1>System auth regression harness</h1>
<input id="username" aria-label="Username"><button id="login">Login</button>
<button id="logout">Logout</button><button id="chatbot">Chatbot</button><output id="status"></output>
<script>
window.process = {env: ${JSON.stringify({ NEXT_PUBLIC_CHATBOT_SSO_ENABLED: enabled ? 'true' : 'false', NEXT_PUBLIC_CHATBOT_URL: destination })}};
const sessions = {}; (function(exports) {${sessionCode}})(sessions);
const api = {}; (function(exports, require) {${apiCode}})(api, () => sessions);
const status = document.getElementById('status');
document.getElementById('login').onclick = async () => {
  try { const user = await api.loginUser(document.getElementById('username').value, ${JSON.stringify(password)}); status.textContent = user.email; } catch (e) { status.textContent = e.message; }
};
document.getElementById('logout').onclick = async () => { await api.logoutUser(); status.textContent = 'logged out'; };
document.getElementById('chatbot').onclick = async () => {
  const tab = window.open('about:blank'); tab.opener = null;
  const token = api.getAuthToken();
  const ticket = await api.createChatbotTicket();
  if (!token || api.getAuthToken() !== token) { tab.close(); return; }
  tab.location.replace(${JSON.stringify(destination)} + '/sso#ticket=' + encodeURIComponent(ticket));
};
</script></body></html>`;
}

async function waitSession(page, email) {
  await page.waitForFunction(({ key, email }) => {
    const session = JSON.parse(localStorage.getItem(key) || 'null');
    return email ? session?.user.email === email : session === null;
  }, { key: authKey, email });
}

async function systemLogin(page, username) {
  await page.locator('#username').fill(username);
  await page.locator('#login').click();
  await page.locator('#status').filter({ hasText: username === 'session_a' ? 'session.a@example.com' : 'session.b@example.com' }).waitFor();
  await page.waitForFunction(() => document.querySelectorAll('iframe').length === 0);
}

async function openSso(context, page) {
  const opened = context.waitForEvent('page');
  await page.locator('#chatbot').click();
  const tab = await opened;
  await tab.waitForURL(`${chatbot}/chat`);
  await tab.locator('.sidebar-user').waitFor();
  assert.equal(await tab.evaluate(() => location.hash), '');
  assert.equal(await tab.evaluate(() => window.opener), null);
  return tab;
}

async function main() {
  // A standalone system must leave chatbot's session alone.
  const standalone = { exports: {}, process: { env: {} }, window: {} };
  vm.runInNewContext(sessionCode, standalone);
  standalone.exports.resetChatbotSession();
  const bridgeCode = compile('chatbot_oplai2026/chat_bot_allforn/frontend/app/session-bridge/route.ts');
  const bridge = { exports: {}, process: { env: {} }, Response, require: () => ({ AUTH_STORAGE_KEY: authKey, AUTH_REVISION_KEY: revisionKey }) };
  vm.runInNewContext(bridgeCode, bridge);
  assert.equal(bridge.exports.GET().status, 404);
  console.log('PASS: standalone session synchronization disabled');

  // Serve the parent document over real HTTP so the browser can determine its
  // address space correctly when loading an iframe on another localhost port.
  const server = http.createServer((_request, response) => {
    response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    response.end(harness(chatbot));
  });
  await new Promise(resolve => server.listen(4131, '127.0.0.1', resolve));
  const browser = await chromium.launch();
  try {
    const context = await browser.newContext();
    const errors = [];
    context.on('page', page => {
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => { if (message.type() === 'error') console.error('Browser:', message.text()); });
    });
    await context.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.pathname.startsWith('/api/')) {
        const response = await route.fetch({ url: 'http://127.0.0.1:8131' + url.pathname + url.search });
        return route.fulfill({ response });
      }
      if (url.origin !== system && url.pathname.endsWith('/system-session-test')) {
        return route.fulfill({ contentType: 'text/html', body: harness(chatbot) });
      }
      return route.continue();
    });
    const sys = await context.newPage();
    await sys.goto(system + '/system-session-test');
    await systemLogin(sys, 'session_a');
    const old = await context.newPage();
    await old.goto(chatbot + '/login');
    await old.getByRole('textbox', { name: 'Email' }).fill('session.b@example.com');
    await old.getByRole('textbox', { name: 'Mật khẩu' }).fill(password);
    await old.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    await old.waitForURL(chatbot + '/chat');
    const a = await openSso(context, sys);
    await waitSession(a, 'session.a@example.com');
    await old.locator('.sidebar-user').filter({ hasText: 'session.a@example.com' }).waitFor();
    console.log('PASS: SSO replaces a valid old account and updates other chatbot tabs');

    await sys.locator('#logout').click();
    await sys.locator('#status').filter({ hasText: 'logged out' }).waitFor();
    await sys.waitForFunction(() => document.querySelectorAll('iframe').length === 0);
    await a.waitForURL(chatbot + '/login');
    await old.waitForURL(chatbot + '/login');
    await waitSession(a, null);
    console.log('PASS: system logout clears chatbot and redirects both tabs across ports');

    await systemLogin(sys, 'session_b');
    const b = await openSso(context, sys);
    await waitSession(b, 'session.b@example.com');
    console.log('PASS: logging into another system account opens the matching chatbot account');

    // Use the actual system auth code at chatbot's origin to cover the gateway.
    const sameOrigin = await context.newPage();
    await sameOrigin.goto('http://127.0.0.1:4130/system-session-test');
    await sameOrigin.locator('#logout').click();
    await b.waitForURL(chatbot + '/login');
    await waitSession(b, null);
    console.log('PASS: same-origin logout clears an already-open chatbot tab immediately');

    // A logout during the SSO request must not resurrect the pending session.
    await systemLogin(sys, 'session_a');
    let release;
    let markStarted;
    const held = new Promise(resolve => { release = resolve; });
    const started = new Promise(resolve => { markStarted = resolve; });
    await context.route('**/chatbot/api/auth/system-sso', async route => {
      markStarted(); await held; await route.continue();
    });
    const pendingPage = context.waitForEvent('page');
    await sys.locator('#chatbot').click();
    const pending = await pendingPage;
    await started;
    await sys.locator('#logout').click();
    await sys.waitForFunction(() => document.querySelectorAll('iframe').length === 0);
    release();
    await pending.getByRole('alert').filter({ hasText: 'Phiên đăng nhập đã thay đổi' }).waitFor();
    await waitSession(pending, null);
    await context.unroute('**/chatbot/api/auth/system-sso');
    console.log('PASS: a late SSO response cannot restore a logged-out session');

    await systemLogin(sys, 'session_a');
    const staleTab = await openSso(context, sys);
    let releaseProfile;
    let startedProfile;
    const heldProfile = new Promise(resolve => { releaseProfile = resolve; });
    const profileStarted = new Promise(resolve => { startedProfile = resolve; });
    let profileHeld = false;
    await context.route('**/chatbot/api/users/me', async route => {
      if (route.request().frame().page() === staleTab && !profileHeld) {
        profileHeld = true; startedProfile(); await heldProfile;
        return route.fulfill({ status: 401, contentType: 'application/json', body: '{"detail":"Old session expired"}' });
      }
      return route.continue();
    });
    await staleTab.reload({ waitUntil: 'domcontentloaded' });
    await profileStarted;
    await systemLogin(sys, 'session_b');
    const freshTab = await openSso(context, sys);
    await waitSession(freshTab, 'session.b@example.com');
    releaseProfile();
    await staleTab.locator('.sidebar-user').filter({ hasText: 'session.b@example.com' }).waitFor();
    await waitSession(freshTab, 'session.b@example.com');
    await context.unroute('**/chatbot/api/users/me');
    console.log('PASS: a delayed 401 from the old account does not clear the new account');

    const unauthorized = await context.request.get(chatbot + '/session-bridge');
    assert.equal(unauthorized.status(), 200);
    assert.match(unauthorized.headers()['content-security-policy'], /frame-ancestors http:\/\/127\.0\.0\.1:4131/);
    assert.equal(unauthorized.headers()['cache-control'], 'no-store');
    assert.deepEqual(errors, []);
    console.log('PASS: bridge origin restrictions, no-store response and no browser JavaScript errors');
    await context.close();
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
