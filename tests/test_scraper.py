import html

from src.scraper import normalize_tag


def test_normalize_tag_cleaning():
    assert normalize_tag("  Hello World!  ") == "hello_world"
    assert normalize_tag("artist:tag") == "artist_tag"
    assert normalize_tag("meta") == ""


def test_normalize_tag_keeps_valid_names():
    assert normalize_tag("twin_tails") == "twin_tails"
    assert normalize_tag("low-waist") == "low-waist"


def test_collect_from_html_example():
    sample = """
    <html>
      <head>
        <meta name="keywords" content="maid, schoolgirl, blue eyes" />
      </head>
      <body>
        <a href="/tags/maid?foo=bar">Maid</a>
        <div class="tag">blue eyes</div>
        <span data-tag-name="schoolgirl">schoolgirl</span>
      </body>
    </html>
    """
    from src.scraper import _collect_from_html

    tags = _collect_from_html(sample)
    assert "maid" in tags
    assert "schoolgirl" in tags
    assert "blue_eyes" in tags
