"""Exercise registration against Anvil itself, without an Uplink connection."""
import ast
from functools import wraps
from pathlib import Path
import anvil.server

source = ast.parse((Path(__file__).parents[1] / 'server_code/app.py').read_text())
function = next(node for node in source.body if isinstance(node, ast.FunctionDef) and node.name == 'register_callable')
namespace = {'anvil': __import__('anvil'), 'wraps': wraps}
exec(compile(ast.Module(body=[function], type_ignores=[]), 'app.py', 'exec'), namespace)
namespace['register_callable']('registration_contract', lambda: None, require_user=lambda user: bool(user))
print('PASS protected callable registration against Anvil library')
