import ast
from pathlib import Path

ROOT_PACKAGE = "retail_analyst"
SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / ROOT_PACKAGE


def imported_paths(tree, package_parts):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")
        elif isinstance(node, ast.ImportFrom) and node.level:
            base = list(package_parts[: len(package_parts) - node.level + 1])
            yield base + (node.module.split(".") if node.module else [])
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module.split(".")


def deep_import_violations(source_root):
    violations = []
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(source_root).parent.parts
        package_parts = (source_root.name, *relative)
        own_module = package_parts[1] if len(package_parts) > 1 else None
        tree = ast.parse(path.read_text())
        for parts in imported_paths(tree, package_parts):
            reaches_into_other_module = (
                parts[0] == source_root.name and len(parts) >= 3 and parts[1] != own_module
            )
            if reaches_into_other_module:
                violations.append(f"{path.relative_to(source_root)}: {'.'.join(parts)}")
    return violations


def write_tree(root, files):
    for name, content in files.items():
        target = root / ROOT_PACKAGE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    return root / ROOT_PACKAGE


def test_modules_import_each_other_via_index_only():
    assert deep_import_violations(SOURCE_ROOT) == []


def test_absolute_deep_import_into_another_module_is_flagged(tmp_path):
    root = write_tree(
        tmp_path,
        {
            "__init__.py": "",
            "a/__init__.py": "",
            "a/inner.py": "",
            "b/__init__.py": "from retail_analyst.a.inner import helper\n",
        },
    )
    assert deep_import_violations(root) == ["b/__init__.py: retail_analyst.a.inner"]


def test_relative_deep_import_into_another_module_is_flagged(tmp_path):
    root = write_tree(
        tmp_path,
        {
            "__init__.py": "",
            "a/__init__.py": "",
            "a/inner.py": "",
            "b/__init__.py": "",
            "b/use.py": "from ..a.inner import helper\n",
        },
    )
    assert deep_import_violations(root) == ["b/use.py: retail_analyst.a.inner"]


def test_index_imports_and_own_module_imports_are_allowed(tmp_path):
    root = write_tree(
        tmp_path,
        {
            "__init__.py": "",
            "a/__init__.py": "from .inner import helper\n",
            "a/inner.py": "",
            "b/__init__.py": "from retail_analyst.a import helper\n",
            "b/use.py": "from retail_analyst.b.other import thing\nfrom . import other\n",
            "b/other.py": "",
            "cli.py": "from retail_analyst.a import helper\n",
        },
    )
    assert deep_import_violations(root) == []
