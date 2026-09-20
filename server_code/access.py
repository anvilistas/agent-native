"""Revocable credentials and one-use embed tickets stored in a consumer table.

The supplied table has string `key` and simpleObject `snapshot` columns, with
client access disabled. Identity checks are supplied by the consuming app.
"""
import hashlib
import secrets
import time

import anvil.server
import anvil.tables

PREFIX = 'agent-native/'


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Access:
    def __init__(self, table, enabled):
        self.table = table
        self.enabled = enabled

    def principal(self, credential_id):
        row = self.table.get(key=PREFIX + 'credential/' + credential_id)
        value = row['snapshot'] if row else None
        if not value or not value.get('enabled') or not self.enabled(value['subject']):
            return None
        return {'credential_id': credential_id, 'subject': value['subject'], 'scopes': value['scopes']}

    def authenticate(self, header):
        if not header.startswith('Bearer '):
            return None
        token = header[7:]
        if len(token) != 43:
            return None
        return self.principal(digest(token))

    def ticket(self, principal, view):
        token = secrets.token_urlsafe(32)
        self.table.add_row(key=PREFIX + 'ticket/' + digest(token), snapshot={
            'credential_id': principal['credential_id'], 'view': view, 'expires': time.time() + 90})
        return token

    @anvil.tables.in_transaction
    def claim(self, token, view, *, scope=None):
        existing = self.grant(view)
        if existing and (scope is None or scope in existing['scopes']):
            return {'ok': True}
        if not isinstance(token, str) or len(token) != 43:
            return {'ok': False, 'message': 'Reopen this view from the conversation.'}
        row = self.table.get(key=PREFIX + 'ticket/' + digest(token))
        value = row['snapshot'] if row else None
        if row:
            row.delete()
        principal = self.principal(value['credential_id']) if value else None
        if not value or value['expires'] <= time.time() or value['view'] != view or not principal or (scope is not None and scope not in principal['scopes']):
            return {'ok': False, 'message': 'Review access expired. Reopen it from the conversation.'}
        anvil.server.session[PREFIX + 'grant'] = dict(value, expires=time.time() + 900)  # pyright: ignore[reportGeneralTypeIssues, reportInvalidTypeArguments]
        return {'ok': True}

    def grant(self, view):
        value = anvil.server.session.get(PREFIX + 'grant')
        if not value or value['expires'] <= time.time() or value['view'] != view:
            return None
        return self.principal(value['credential_id'])

    def require_view(self, view):
        principal = self.grant(view)
        if principal is None:
            raise PermissionError('Review access expired. Reopen it from the conversation.')
        return principal


    def connections(self, subject):
        result = []
        for row in self.table.search():
            if not row['key'].startswith(PREFIX + 'credential/'):
                continue
            value = row['snapshot']
            if value['subject'] == subject:
                result.append({'id': row.get_id(), 'label': value.get('label', 'Existing connection'),
                               'scopes': value['scopes'], 'enabled': value['enabled']})
        return result

    def create_connection(self, subject, label, scopes, *, allowed):
        if not isinstance(label, str) or not label.strip() or len(label.strip()) > 80:
            return {'ok': False, 'message': 'Give this connection a name, up to 80 characters.'}
        if not isinstance(scopes, list) or not scopes or any(not isinstance(scope, str) or scope not in allowed for scope in scopes):
            return {'ok': False, 'message': 'Choose at least one listed permission.'}
        if not self.enabled(subject):
            raise PermissionError('This account cannot create connections.')
        token = secrets.token_urlsafe(32)
        row = self.table.add_row(key=PREFIX + 'credential/' + digest(token), snapshot={
            'subject': subject, 'label': label.strip(), 'scopes': list(dict.fromkeys(scopes)),
            'enabled': True, 'created': time.time()})
        return {'ok': True, 'id': row.get_id(), 'token': token}

    def revoke_connection(self, subject, connection_id):
        if not isinstance(connection_id, str):
            return {'ok': False, 'message': 'Connection not found.'}
        row = self.table.get_by_id(connection_id)
        if row is None or not row['key'].startswith(PREFIX + 'credential/') or row['snapshot']['subject'] != subject:
            return {'ok': False, 'message': 'Connection not found.'}
        row['snapshot'] = dict(row['snapshot'], enabled=False)
        return {'ok': True}
