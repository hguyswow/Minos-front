# Acceptance tests.
import ast, os
from editor.app import guide

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["editor/app/gui.py", "editor/app/controller.py", "editor/app/guide.py"]
BANNED = ["patch.txt", "패치", "auto.sh", "names_map", "NUL", "offset"]


def user_strings(path):
    tree = ast.parse(open(os.path.join(ROOT, path), encoding="utf-8").read())
    doc_ids = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            b = n.body
            if b and isinstance(b[0], ast.Expr) and isinstance(getattr(b[0], "value", None), ast.Constant):
                doc_ids.add(id(b[0].value))
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc_ids:
            yield n.value


def test_no_jargon_in_user_visible_strings():
    bad = []
    for f in FILES:
        for s in user_strings(f):
            for b in BANNED:
                if b in s:
                    bad.append((f, b, s[:60]))
    assert not bad, bad


def test_apply_button_is_called_apply():
    src = open(os.path.join(ROOT, "editor/app/gui.py"), encoding="utf-8").read()
    assert "적용하기" in src
    body = {x.title: x.body for x in guide.get_sections()}["적용 버튼과 기종 표시"]
    assert "적용하기" in body
