"""Transport contracts exercised through the production HTTP handler."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace, ModuleType
import unittest

anvil = ModuleType('anvil'); anvil.server = ModuleType('anvil.server')
anvil.server.HttpResponse = lambda status, body, headers: SimpleNamespace(status=status, body=body, headers=headers)
sys.modules['anvil'] = anvil; sys.modules['anvil.server'] = anvil.server
spec = importlib.util.spec_from_file_location('transport', Path(__file__).parents[1] / 'server_code/mcp.py')
transport = importlib.util.module_from_spec(spec); spec.loader.exec_module(transport)


class Transport(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.server = transport.Server('test', lambda token: {'scopes': ['read']} if token == 'Bearer valid' else None,
                                       origin='https://example.anvil.app', wrapper='<html></html>')
        @self.server.tool(scope='read', schema={'type': 'object', 'properties': {'value': {'type': 'integer'}}, 'required': ['value'], 'additionalProperties': False})
        def echo(principal, value):
            self.calls.append(value)
            return {'value': value}
        @self.server.tool(scope='write')
        def forbidden(principal):
            self.fail('Unauthorized function executed')

    def request(self, message, *, token='Bearer valid', origin=None, method='POST', protocol='2025-11-25'):
        headers = {'authorization': token, 'content-type': 'application/json', 'mcp-protocol-version': protocol}
        if origin is not None: headers['origin'] = origin
        anvil.server.request = SimpleNamespace(headers=headers, method=method,
            body=SimpleNamespace(get_bytes=lambda: json.dumps(message).encode()))
        return self.server.handle()

    def rpc(self, method, params=None):
        return {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}}

    def test_authentication_and_origin_before_dispatch(self):
        call = self.rpc('tools/call', {'name': 'echo', 'arguments': {'value': 1}})
        self.assertEqual(self.request(call, token='').status, 401)
        self.assertEqual(self.request(call, origin='https://evil.example').status, 403)
        self.assertEqual(self.calls, [])

    def test_scope_applies_to_discovery_and_execution(self):
        result = json.loads(self.request(self.rpc('tools/list')).body)['result']
        self.assertEqual([t['name'] for t in result['tools']], ['echo'])
        result = json.loads(self.request(self.rpc('tools/call', {'name': 'forbidden'})).body)
        self.assertEqual(result['error']['code'], -32602)

    def test_validation_rejects_extra_fields_without_invocation(self):
        result = self.request(self.rpc('tools/call', {'name': 'echo', 'arguments': {'value': 1, 'approve': True}}))
        self.assertEqual(json.loads(result.body)['error']['code'], -32602)
        self.assertEqual(self.calls, [])
        result = self.request(self.rpc('tools/call', {'name': 'echo', 'arguments': {'value': 2}}))
        self.assertEqual(json.loads(result.body)['result']['structuredContent'], {'value': 2})
        self.assertEqual(self.calls, [2])

    def test_notifications_never_execute_tools(self):
        request = self.rpc('tools/call', {'name': 'echo', 'arguments': {'value': 1}})
        del request['id']
        self.assertEqual(self.request(request).status, 202)
        self.assertEqual(self.calls, [])

    def test_json_transport_and_resource_metadata(self):
        self.assertEqual(self.request(self.rpc('ping'), method='GET').status, 405)
        self.assertEqual(self.request(self.rpc('ping'), protocol='unknown').status, 400)
        reply = self.request(self.rpc('resources/read', {'uri': transport.UI_URI}))
        content = json.loads(reply.body)['result']['contents'][0]
        self.assertEqual(content['_meta']['ui']['csp']['frameDomains'], ['https://example.anvil.app'])
        self.assertEqual(reply.headers['Cache-Control'], 'no-store')


if __name__ == '__main__': unittest.main()
