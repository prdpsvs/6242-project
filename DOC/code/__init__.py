# NOTE: This package is named 'code', which shadows Python's stdlib 'code' module.
# We re-export ALL public symbols from the real stdlib code.py so that any
# downstream code that does `import code; code.InteractiveConsole` still works.
import importlib.util as _ilu
import sys as _sys
import os as _os

_stdlib_path = _os.path.join(_os.path.dirname(_os.__file__), "code.py")
if _os.path.exists(_stdlib_path):
    # Load stdlib code.py under a private name so it doesn't recurse
    _spec = _ilu.spec_from_file_location("_stdlib_code_real", _stdlib_path)
    _mod = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
    # Temporarily hide ourselves so stdlib code.py can import codeop cleanly
    _our_mod = _sys.modules.pop("code", None)
    try:
        _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
    finally:
        if _our_mod is not None:
            _sys.modules["code"] = _our_mod
    # Re-export public stdlib symbols into this namespace
    InteractiveConsole = _mod.InteractiveConsole
    InteractiveInterpreter = _mod.InteractiveInterpreter
    interact = _mod.interact
    compile_command = _mod.compile_command
    CommandCompiler = _mod.CommandCompiler
