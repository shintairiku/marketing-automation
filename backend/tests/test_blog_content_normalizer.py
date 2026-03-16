# -*- coding: utf-8 -*-
import json

from app.domains.blog.agents import tools


def test_normalize_html_content_removes_noise_and_keeps_body_text() -> None:
    html = '''
    <section>
      <header class="site-header">header</header>
      <div class="mainVisual02">hero</div>
      <ul id="pagePath02"><li>breadcrumb</li></ul>
      <p>本文です。</p>
      <p>　</p>
      <p></p>
      <ul><li></li><li>項目</li></ul>
      <div class="c-author">author</div>
      <script>alert(1)</script>
      <style>.x{}</style>
      <img class="wp-image-1" loading="lazy" decoding="async" width="10" height="20" srcset="a 1x" sizes="100vw" src="/a.jpg" alt="alt text">
    </section>
    '''

    normalized = tools._normalize_html_content(html)

    assert "site-header" not in normalized
    assert "mainVisual02" not in normalized
    assert "pagePath02" not in normalized
    assert "c-author" not in normalized
    assert "<script" not in normalized
    assert "<style" not in normalized
    assert "本文です。" in normalized
    assert "<li>項目</li>" in normalized
    assert 'src="/a.jpg"' in normalized
    assert 'alt="alt text"' in normalized
    assert "loading=" not in normalized
    assert "decoding=" not in normalized
    assert "srcset=" not in normalized
    assert "sizes=" not in normalized
    assert "width=" not in normalized
    assert "height=" not in normalized



def test_normalize_html_content_removes_acf_author_comment() -> None:
    html = '<p>本文</p><!-- wp:acf/author {"name":"acf/author"} /-->'

    normalized = tools._normalize_html_content(html)

    assert "acf/author" not in normalized
    assert "本文" in normalized



def test_normalize_json_result_string_only_touches_html_fields() -> None:
    payload = {
        "post_id": 1,
        "title": "sample",
        "raw_content": '<header>header</header><p>本文</p>',
        "rendered_content": '<div class="c-author">author</div><p>表示本文</p>',
        "acf_fields": {"note": "plain text"},
        "items": [
            {"innerHTML": '<script>1</script><p>ブロック本文</p>'},
            {"title": "そのまま"},
        ],
    }

    normalized = tools._normalize_json_result_string(json.dumps(payload, ensure_ascii=False))
    parsed = json.loads(normalized)

    assert parsed["post_id"] == 1
    assert parsed["title"] == "sample"
    assert "<header" not in parsed["raw_content"]
    assert "本文" in parsed["raw_content"]
    assert "c-author" not in parsed["rendered_content"]
    assert "表示本文" in parsed["rendered_content"]
    assert parsed["acf_fields"] == {"note": "plain text"}
    assert "<script" not in parsed["items"][0]["innerHTML"]
    assert "ブロック本文" in parsed["items"][0]["innerHTML"]
    assert parsed["items"][1]["title"] == "そのまま"
