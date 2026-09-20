"""Credential issuance cannot widen scopes or cross user boundaries."""
import importlib.util
from pathlib import Path
import unittest
import anvil.server

spec = importlib.util.spec_from_file_location('access_impl', Path(__file__).parents[1]/'server_code/access.py')
access_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(access_module)


class Row(dict):
    def __init__(self, ident, **values): super().__init__(values); self.ident = ident
    def get_id(self): return self.ident


class Table:
    def __init__(self): self.rows = []
    def add_row(self, **values):
        row = Row(str(len(self.rows)), **values); self.rows.append(row); return row
    def get(self, **values): return next((r for r in self.rows if all(r[k] == v for k,v in values.items())), None)
    def get_by_id(self, ident): return next((r for r in self.rows if r.get_id() == ident), None)
    def search(self): return self.rows


class Connections(unittest.TestCase):
    def setUp(self):
        self.table = Table()
        self.access = access_module.Access(self.table, lambda subject: subject in ('alice', 'bob'))

    def test_issue_hash_list_scope_validation_and_revoke(self):
        self.assertFalse(self.access.create_connection('alice', 'Agent', ['admin'], allowed={'read': 'Read'})['ok'])
        issued = self.access.create_connection('alice', 'Agent', ['read'], allowed={'read': 'Read'})
        self.assertTrue(issued['ok'])
        self.assertNotIn(issued['token'], repr(self.table.rows))
        principal = self.access.authenticate('Bearer ' + issued['token'])
        self.assertEqual(principal['subject'], 'alice')
        self.assertEqual(principal['scopes'], ['read'])
        self.assertNotIn('token', self.access.connections('alice')[0])
        self.assertEqual(self.access.connections('bob'), [])
        self.assertFalse(self.access.revoke_connection('bob', issued['id'])['ok'])
        self.assertTrue(self.access.revoke_connection('alice', issued['id'])['ok'])
        self.assertIsNone(self.access.authenticate('Bearer ' + issued['token']))

    def test_disabled_subject_cannot_issue(self):
        with self.assertRaises(PermissionError):
            self.access.create_connection('disabled', 'Agent', ['read'], allowed={'read': 'Read'})
        self.assertEqual(self.table.rows, [])


if __name__ == '__main__': unittest.main()
