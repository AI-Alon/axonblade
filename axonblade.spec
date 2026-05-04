# axonblade.spec — PyInstaller build spec for the `ablade` binary.
#
# Build:
#   pyinstaller axonblade.spec
#
# Output: dist/ablade  (or dist/ablade.exe on Windows)

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        # Bundle all stdlib .axb files so uselib works without Python installed.
        ("stdlib/*.axb", "stdlib"),
    ],
    hiddenimports=[
        # Core pipeline
        "core.lexer",
        "core.tokens",
        "core.parser",
        "core.ast_nodes",
        "core.opcodes",
        "core.code_object",
        "core.compiler",
        "core.vm",
        "core.serializer",
        "core.runtime",
        "core.environment",
        "core.errors",
        "core.module_loader",
        "core.formatter",
        # Grid
        "grid.grid_object",
        "grid.renderer_term",
        # Stdlib / tools
        "stdlib.builtins",
        "tools.linter",
        "tools.test_runner",
        # REPL
        "repl",
        # Third-party used by stdlib builtins
        "requests",
        "requests.adapters",
        "requests.auth",
        "requests.cookies",
        "requests.exceptions",
        "requests.models",
        "requests.sessions",
        "urllib3",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "http.server",
        "xmlrpc",
        "pydoc",
        "doctest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ablade",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
