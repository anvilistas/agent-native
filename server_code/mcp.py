"""Request/response MCP transport for Anvil HTTP endpoints."""
import json
from urllib.parse import urlsplit

import anvil.server
from jsonschema import Draft202012Validator, ValidationError

PROTOCOLS = ('2025-11-25', '2025-06-18', '2025-03-26')
UI_URI = 'ui://agent-native/app.html'
EMPTY = {'type': 'object', 'properties': {}, 'additionalProperties': False}


class Server:
    def __init__(self, name, authenticate, *, instructions='', wrapper=None, origin=None):
        self.name = name
        self.authenticate = authenticate
        self.instructions = instructions
        if wrapper is None:
            from ._assets import WRAPPER
            wrapper = WRAPPER
        self.wrapper = wrapper
        self.origin = origin
        self.tools = {}

    def tool(self, *, schema=EMPTY, scope, description=None, view=False, read_only=False, app_only=False):
        Draft202012Validator.check_schema(schema)
        def register(fn):
            if fn.__name__ in self.tools:
                raise ValueError('Duplicate tool: ' + fn.__name__)
            info = {'name': fn.__name__, 'description': description or fn.__doc__ or '',
                    'inputSchema': schema, 'annotations': {'readOnlyHint': read_only,
                    'destructiveHint': False, 'openWorldHint': False}}
            if view:
                info['_meta'] = {'ui': {'resourceUri': UI_URI}}
            if app_only:
                info.setdefault('_meta', {}).setdefault('ui', {})['visibility'] = ['app']
            self.tools[fn.__name__] = (fn, scope, Draft202012Validator(schema), info)
            return fn
        return register

    def handle(self):
        request = anvil.server.request
        origin = request.headers.get('origin')
        expected = self.origin or anvil.server.get_app_origin()
        expected = '{0.scheme}://{0.netloc}'.format(urlsplit(expected))
        if origin is not None and origin != expected:
            return response(403, {'error': 'Origin not allowed'})
        principal = self.authenticate(request.headers.get('authorization', ''))
        if principal is None:
            return response(401, {'error': 'Authentication required'}, {'WWW-Authenticate': 'Bearer'})
        if request.method != 'POST':
            return response(405, None, {'Allow': 'POST'})
        if request.headers.get('content-type', '').split(';')[0] != 'application/json':
            return response(415, {'error': 'Expected application/json'})
        if request.headers.get('mcp-protocol-version', PROTOCOLS[0]) not in PROTOCOLS:
            return response(400, {'error': 'Unsupported MCP protocol version'})
        raw = request.body.get_bytes()  # pyright: ignore[reportAttributeAccessIssue]  # HTTP body is Media at runtime.
        if len(raw) > 256_000:
            return response(413, {'error': 'Request too large'})
        try:
            message = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            return response(400, error(None, -32700, 'Invalid JSON'))
        return self.dispatch(message, principal)

    def dispatch(self, message, principal):
        if not isinstance(message, dict) or message.get('jsonrpc') != '2.0' or not isinstance(message.get('method'), str):
            return response(400, error(None, -32600, 'Invalid JSON-RPC request'))
        ident = message.get('id')
        if 'id' in message and (isinstance(ident, bool) or not isinstance(ident, (str, int))):
            return response(400, error(None, -32600, 'Invalid request id'))
        method, params = message['method'], message.get('params', {})
        if not isinstance(params, dict):
            return response(400, error(ident, -32602, 'Expected object parameters'))
        if 'id' not in message:
            # Notifications never invoke application tools.
            return response(202, None)
        if method == 'initialize':
            version = params.get('protocolVersion')
            result = {'protocolVersion': version if version in PROTOCOLS else PROTOCOLS[0],
                      'serverInfo': {'name': self.name, 'version': '0.1.0'},
                      'capabilities': {'tools': {}, 'resources': {}}, 'instructions': self.instructions}
        elif method == 'ping':
            result = {}
        elif method == 'tools/list':
            result = {'tools': [info for fn, scope, validator, info in self.tools.values() if scope in principal['scopes']]}
        elif method == 'tools/call':
            tool = self.tools.get(params.get('name')) if isinstance(params.get('name'), str) else None
            if tool is None or tool[1] not in principal['scopes']:
                return response(200, error(ident, -32602, 'Tool unavailable'))
            fn, scope, validator, info = tool
            arguments = params.get('arguments', {})
            try:
                validator.validate(arguments)
            except ValidationError as exc:
                # Never include the submitted value in an error.
                return response(200, error(ident, -32602, 'Invalid arguments at ' + '.'.join(map(str, exc.path))))
            value = fn(principal, **arguments)
            result = value if isinstance(value, ToolResult) else ToolResult(value)
        elif method == 'resources/list':
            result = {'resources': [{'uri': UI_URI, 'name': 'Anvil app', 'mimeType': 'text/html;profile=mcp-app'}] if self.wrapper else []}
        elif method == 'resources/read':
            if params.get('uri') != UI_URI or not self.wrapper:
                return response(200, error(ident, -32602, 'Resource unavailable'))
            origin = self.origin or anvil.server.get_app_origin()
            origin = '{0.scheme}://{0.netloc}'.format(urlsplit(origin))
            result = {'contents': [{'uri': UI_URI, 'mimeType': 'text/html;profile=mcp-app', 'text': self.wrapper,
                      '_meta': {'ui': {'prefersBorder': True, 'csp': {'frameDomains': [origin]}}}}]}
        elif method == 'resources/templates/list':
            result = {'resourceTemplates': []}
        else:
            return response(200, error(ident, -32601, 'Method not found'))
        return response(200, {'jsonrpc': '2.0', 'id': ident, 'result': result})


class ToolResult(dict):
    def __init__(self, data, *, meta=None):
        super().__init__(content=[{'type': 'text', 'text': json.dumps(data)}], structuredContent=data)
        if meta is not None:
            self['_meta'] = meta


def error(ident, code, message):
    return {'jsonrpc': '2.0', 'id': ident, 'error': {'code': code, 'message': message}}


def response(status, data, headers=None):
    return anvil.server.HttpResponse(status, '' if data is None else json.dumps(data),
        {'Content-Type': 'application/json', 'Cache-Control': 'no-store', **(headers or {})})
