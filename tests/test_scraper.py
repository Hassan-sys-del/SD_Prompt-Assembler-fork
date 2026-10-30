import html
import re
from typing import List

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
IGNORED_TAGS = {
    "", "a", "an", "and", "the", "for", "from", "with", "html", "body", "meta",
    "script", "div", "img", "title", "page", "posts", "index", "post", "view",
    "tag", "tags", "artist", "copyright", "character", "general", "meta",
}


def normalize_tag(tag: str) -> str:
    cleaned = html.unescape((tag or "").strip()).lower()
    cleaned = cleaned.replace("&amp;", "and")
    cleaned = cleaned.replace("/", "_")
    cleaned = cleaned.replace(" ", "_")
    cleaned = re.sub(r"[^a-z0-9_\-]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    cleaned = cleaned.strip("_-")
    if not cleaned or cleaned in IGNORED_TAGS:
        return ""
    return cleaned


def _split_tag_candidates(value: str) -> List[str]:
    if not value:
        return []

    parts: List[str] = []
    for raw_part in re.split(r"[\s,|/&]+", html.unescape(value)):
        cleaned = raw_part.strip("[](){}<>\"'`")
        if not cleaned:
            continue
        for sub in cleaned.split("&"):
            tag = normalize_tag(sub)
            if tag and tag not in parts:
                parts.append(tag)
    return parts


def fetch_page(url: str) -> str:
    response = requests.get(url, timeout=20, headers={"User-Agent": USER_AGENT}, allow_redirects=True)
    response.raise_for_status()
    return response.text


def _extract_from_href(href: str) -> List[str]:
    if not href:
        return []
    found: List[str] = []
    for key in ("tags", "tag", "tag_name", "tag_name[]"):
        match = re.search(rf"(?:^|[?&]){key}=(.+?)(?:&|$)", href, flags=re.IGNORECASE)
        if match:
            found.extend(_split_tag_candidates(match.group(1)))
    return found


def _extract_from_meta(html_text: str) -> List[str]:
    found: List[str] = []
    pattern = r"(?:name|property)\s*=\s*['\"](?:keywords|article:tag|og:tags|tags)['\"]\s+content\s*=\s*['\"]([^'\"]+)['\"]"
    for match in re.findall(pattern, html_text, flags=re.IGNORECASE):
        found.extend(_split_tag_candidates(match))
    return found


def _collect_from_html(html_text: str) -> List[str]:
    soup = BeautifulSoup(html_text, "html.parser")
    found: set[str] = set()

    for selector in [
        "[data-tag-name]",
        "[data-name]",
        ".tag",
        ".tag-link",
        ".tag-type-general",
        ".tag-type-artist",
        ".tag-type-character",
        ".tag-type-copyright",
        ".tag-type-meta",
        "a[rel='tag']",
        "a[rel=tag]",
        "a[href*='tag']",
        "a[href*='tags']",
        "a[href*='?tags=']",
        "a[href*='tag_name']",
    ]:
        for node in soup.select(selector):
            for value in (
                node.get("data-tag-name"),
                node.get("data-name"),
                node.get("title"),
                node.get_text(" ", strip=True),
            ):
                if value:
                    found.update(_split_tag_candidates(value))
            href = node.get("href")
            if href:
                found.update(_extract_from_href(href))

    for anchor in soup.find_all("a", href=True):
        text = anchor.get_text(" ", strip=True)
        href = anchor.get("href", "")
        if text:
            found.update(_split_tag_candidates(text))
        if href:
            found.update(_extract_from_href(href))

    found.update(_extract_from_meta(html_text))

    for key in ("keywords", "tags"):
        match = re.search(rf"\b{key}\b\s*[:=]\s*['\"]([^'\"]+)['\"]", html_text, flags=re.IGNORECASE)
        if match:
            found.update(_split_tag_candidates(match.group(1)))

    for match in re.findall(r"(?:tag[s]?|tags)\s*[:=]\s*\[([^\]]+)\]", html_text, flags=re.IGNORECASE):
        found.update(_split_tag_candidates(match))

    for match in re.findall(r"['\"](?:tags|keywords)['\"]\s*:\s*['\"]([^'\"]+)['\"]", html_text, flags=re.IGNORECASE):
        found.update(_split_tag_candidates(match))

    if not found:
        for token in re.findall(r"[A-Za-z0-9_\-]{3,}", html_text):
            tag = normalize_tag(token)
            if tag:
                found.add(tag)

    return sorted(found)


def extract_tags_from_url(url: str) -> List[str]:
    try:
        html_text = fetch_page(url)
    except (requests.RequestException, ValueError):
        return []
    return _collect_from_html(html_text)


if __name__ == "__main__":
    print(extract_tags_from_url("https://danbooru.donmai.us/posts/1")[:20])
