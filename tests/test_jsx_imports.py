"""SPA static gate: every JSX component used must be imported.

Live-reported (2026-11-18): /chat and /studio went BLANK after the
creation click — "Uncaught ReferenceError: ShareButton is not defined".
Root cause: a wiring script's import anchor didn't match ChatPage/
StudioPage (they import { Masthead } without `reduced`), the plain
str.replace no-op'd silently, and the JS bundler does NOT error on an
undefined JSX identifier — the build stayed green while the runtime
crashed the result views. This test parses every page's REAL imports
(default, named, multi-line) and asserts every <Capitalized> JSX tag
resolves, so the whole blank-screen class is unshippable.
"""

import os
import re
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_every_used_jsx_component_is_imported():
    src_dir = Path(os.path.join(REPO, "web", "src"))
    files = list(src_dir.rglob("*.jsx"))
    assert files, "no JSX sources found"

    def imports_of(src):
        names = set()
        for stmt in re.findall(
            r'import\s+([^;]+?)\s+from\s*["\'][^"\']+["\']', src, re.S
        ):
            m = re.match(r"(\w+)?\s*,?\s*\{(.*)\}", stmt.strip(), re.S)
            if m:
                if m.group(1):
                    names.add(m.group(1))
                for n in m.group(2).split(","):
                    n = n.strip()
                    if n:
                        names.add(n.split(" as ")[-1].strip())
            else:
                w = stmt.strip().split(",")[0].strip()
                if re.fullmatch(r"\w+", w):
                    names.add(w)
        return names

    problems = []
    for f in files:
        src = f.read_text()
        have = imports_of(src)
        # components defined in the same file (QrIcon, SealedScreen, ...)
        have |= set(re.findall(r"(?:function|const)\s+([A-Z]\w+)", src))
        used = set(re.findall(r"<([A-Z]\w+)", src))
        missing = sorted(u for u in used if u not in have)
        if missing:
            problems.append(f"{f.name}: {missing}")

    assert not problems, (
        "JSX components used but never imported (the blank-screen class: "
        "build stays green, runtime ReferenceError crashes the tree): "
        + "; ".join(problems)
    )
