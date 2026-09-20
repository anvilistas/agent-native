// A channel binds this Form to its immediate MCP wrapper. Pin the parent's
// browser origin on its first channel-matched response before sending content.
const [channel, initialTicket = ''] = location.hash.slice('#mcp:'.length).split(':');
let launchTicket = initialTicket;
let parentOrigin;
const pending = new Map();
let nextId = 0;
let refresh;
export function takeTicket() {
  const ticket = launchTicket;
  launchTicket = '';
  history.replaceState(null, '', location.pathname + location.search + '#mcp:' + channel);
  return ticket;
}
export function isEmbedded() { return window.parent !== window; }
export function appUrl() { return location.origin + location.pathname; }
window.addEventListener('message', event => {
  if (event.source !== window.parent || event.data?.channel !== channel) return;
  if (parentOrigin !== undefined && event.origin !== parentOrigin) return;
  parentOrigin = event.origin;
  const message = event.data;
  if (message.type === 'anvil-mcp-refresh') { refresh?.(); return; }
  if (message.type !== 'anvil-mcp-result') return;
  const request = pending.get(message.id);
  if (!request) return;
  pending.delete(message.id);
  clearTimeout(request.timer);
  message.error ? request.reject(new Error(message.error)) : request.resolve(message.result);
});
function request(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error('Conversation bridge timed out')); }, 15000);
    pending.set(id, { resolve, reject, timer });
    window.parent.postMessage({ type: 'anvil-mcp-request', channel, id, method, params },
      parentOrigin && parentOrigin !== 'null' ? parentOrigin : '*');
  });
}
export function onRefresh(callback) { refresh = callback; }
export function capabilities() { return request('capabilities'); }
export function context(value) { return request('context', value); }
export function sendMessage(text) { return request('message', { text }); }
export function renew() { return request('renew'); }
export function loadLocal(key) { return sessionStorage.getItem(key) || '{}'; }
export function saveLocal(key, value) { sessionStorage.setItem(key, value); }
