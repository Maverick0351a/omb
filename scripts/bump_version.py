import sys, re, pathlib

if len(sys.argv) != 2:
    print("usage: bump_version.py <new_version>")
    raise SystemExit(1)
new_version = sys.argv[1]
root = pathlib.Path(__file__).resolve().parent.parent
pkg_init = root / 'packages' / 'omb_py' / 'omb' / '__init__.py'
pyproject = root / 'packages' / 'omb_py' / 'pyproject.toml'

# Update __init__
init_text = pkg_init.read_text()
init_text = re.sub(r"__version__ = '([^']+)'", f"__version__ = '{new_version}'", init_text)
pkg_init.write_text(init_text)

# Update pyproject
py_text = pyproject.read_text()
py_text = re.sub(r"version = \"[^\"]+\"", f"version = \"{new_version}\"", py_text)
pyproject.write_text(py_text)

print(f"Bumped version to {new_version}")
