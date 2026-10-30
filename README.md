import re

from src.scraper import normalize_tag, _collect_from_html


def test_normalize_tag_basic():
    assert normalize_tag("  Hello World!  ") == "hello_world"
    assert normalize_tag("twin_tails") == "twin_tails"
    assert normalize_tag("meta") == ""


def test_collect_from_html_works_for_keywords_and_tag_links():
    sample = """
    <html>
      <head>
        <meta name="keywords" content="maid, blue eyes, schoolgirl" />
      </head>
      <body>
        <a href="/tags/maid?foo=bar">Maid</a>
        <div class="tag">blue eyes</div>
        <span data-tag-name="schoolgirl">schoolgirl</span>
      </body>
    </html>
    """
    tags = _collect_from_html(sample)
    assert "maid" in tags
    assert "blue_eyes" in tags
    assert "schoolgirl" in tags
