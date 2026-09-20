import { App } from '@modelcontextprotocol/ext-apps';
const app = new App({ name: 'Anvil', version: '0.1.0' }, {});
const frame = document.getElementById('anvil-app');
const notice = document.getElementById('notice');
const channel = crypto.randomUUID();
let origin;
let renewTool;
let launched = false;
let ready;
window.addEventListener('message', async event => {
  if (!origin || event.source !== frame.contentWindow || event.origin !== origin) return;
  const message = event.data;
  if (message?.type !== 'anvil-mcp-request' || message.channel !== channel) return;
  const reply = { type: 'anvil-mcp-result', channel, id: message.id };
  try {
    await ready;
    const capabilities = app.getHostCapabilities();
    if (message.method === 'capabilities') {
      reply.result = { message: Boolean(capabilities?.message?.text) };
    } else if (message.method === 'context') {
      if (capabilities?.updateModelContext?.text) {
        await app.updateModelContext({ content: [{ type: 'text', text: JSON.stringify(message.params) }] });
      }
      reply.result = {};
    } else if (message.method === 'message') {
      if (!capabilities?.message?.text) throw new Error('Conversation messages unavailable');
      const result = await app.sendMessage({ role: 'user', content: [{ type: 'text', text: message.params.text }] });
      if (result.isError) throw new Error('Host rejected the message');
      reply.result = {};
    } else if (message.method === 'renew') {
      if (!renewTool) throw new Error('Reopen this view from the conversation');
      const result = await app.callServerTool({ name: renewTool, arguments: {} });
      const ticket = result._meta?.['anvil/embedTicket'];
      if (typeof ticket !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(ticket)) throw new Error('Reopen this view from the conversation');
      reply.result = ticket;
    } else return;
  } catch (error) { reply.error = error.message; }
  frame.contentWindow.postMessage(reply, origin);
});
app.ontoolresult = result => {
  if (launched) {
    frame.contentWindow?.postMessage({ type: 'anvil-mcp-refresh', channel }, origin);
    return;
  }
  try {
    const url = new URL(result._meta?.['anvil/runtimeUrl']);
    const ticket = result._meta?.['anvil/embedTicket'];
    if (url.protocol !== 'https:' || typeof ticket !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(ticket)) throw new Error();
    origin = url.origin;
    renewTool = result._meta?.['anvil/renewTool'];
    url.hash = `mcp:${channel}:${ticket}`;
    frame.src = url.href;
    launched = true;
  } catch {
    notice.textContent = 'Reopen this view from the conversation.';
  }
};
ready = app.connect();
ready.catch(() => { notice.textContent = 'Conversation bridge unavailable. Reopen this view.'; });
