import pytest

from app.domains.seo_article.services.article_agent_service import (
    AppContext,
    apply_patch_to_fs,
)
from app.domains.seo_article.services.codex_patch import (
    PatchError,
    apply_hunk,
    parse_apply_patch,
)


def test_parse_requires_hunk_header_strict():
    patch = """*** Begin Patch
*** Update File: article.html
- old line
+ new line
*** End Patch
"""
    with pytest.raises(PatchError) as excinfo:
        parse_apply_patch(patch, strict=True)
    assert "Missing @@ header" in str(excinfo.value)


def test_apply_hunk_with_eof_anchor():
    patch = """*** Begin Patch
*** Update File: article.html
@@ -1 +1 @@
-old
+new
*** End of File
*** End Patch
"""
    sections = parse_apply_patch(patch)
    hunk = sections.sections[0].hunks[0]
    updated, added, deleted = apply_hunk(["old"], hunk, file_path="article.html")
    assert updated == ["new"]
    assert added == 1
    assert deleted == 1


def test_apply_patch_to_fs_enforces_trailing_newline(tmp_path):
    root = tmp_path
    target = root / "article.html"
    target.write_text("<p>old</p>", encoding="utf-8")
    ctx = AppContext(
        root=root,
        target_path=target,
        article_path=target,
    )
    patch = """*** Begin Patch
*** Update File: article.html
@@ -1 +1 @@
-<p>old</p>
+<p>new</p>
*** End of File
*** End Patch
"""
    parsed = parse_apply_patch(patch)
    result = apply_patch_to_fs(ctx, parsed)
    assert result.updated == ["article.html"]
    raw = target.read_bytes()
    assert raw.endswith(b"\n")
    assert b"<p>new</p>" in raw


def test_apply_patch_to_fs_reports_context_failure(tmp_path):
    root = tmp_path
    target = root / "article.html"
    target.write_text("<p>unchanged</p>\n", encoding="utf-8")
    ctx = AppContext(
        root=root,
        target_path=target,
        article_path=target,
    )
    patch = """*** Begin Patch
*** Update File: article.html
@@ -1 +1 @@
-<p>does-not-exist</p>
+<p>replacement</p>
*** End Patch
"""
    parsed = parse_apply_patch(patch)
    with pytest.raises(PatchError) as excinfo:
        apply_patch_to_fs(ctx, parsed)
    msg = str(excinfo.value)
    assert "apply_patch verification failed" in msg
    assert "article.html" in msg
