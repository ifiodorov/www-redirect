"""Генератор og-шимов на www (GitHub Pages).

Зачем: краулер Telegram не достаёт до апекса на Timeweb (доказано 21.07,
plans/2026-07-15-telegram-og-preview-ne-podtyagivaetsya.md). www живёт на
GitHub Pages, куда краулер достаёт. Значит превью строим с www.

Два правила, нарушение которых ломает превью (проверено в бою):
  1. никакого canonical/meta refresh на апекс - краулер уходит туда и молчит;
  2. og:image обязан лежать на www, ссылка на апекс не сработает.
"""
import html
import os
import re
import urllib.request
from urllib.parse import urlparse

UA = "TelegramBot (like TwitterBot)"
APEX = "https://prosto-finance.ru"
WWW = "https://www.prosto-finance.ru"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OG_FIELDS = [
    "og:title", "og:description", "og:type", "og:site_name", "og:locale",
    "og:image", "og:image:width", "og:image:height", "og:image:alt",
]


def fetch(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")


def og_of(page_html):
    out = {}
    for prop in OG_FIELDS:
        m = re.search(
            r'<meta\s+property="%s"\s+content="([^"]*)"' % re.escape(prop), page_html
        )
        if m:
            out[prop] = html.unescape(m.group(1))
    return out


def shim(og, path):
    """path - как в sitemap: '/', '/uslugi', '/stati/xxx'."""
    www_url = WWW + (path if path != "/" else "/")
    apex_url = APEX + (path if path != "/" else "/")

    lines = [
        "<!doctype html>",
        '<html lang="ru">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>{html.escape(og.get('og:title', 'пРОСТо Финансы'))}</title>",
        "",
        "<!-- og-теги для мессенджеров. Апекс краулеру Telegram недоступен,",
        "     поэтому карточка строится отсюда. НЕ добавлять canonical и",
        "     meta refresh на апекс: краулер уходит по ним и карточка пропадает. -->",
    ]
    for prop in OG_FIELDS:
        if prop not in og:
            continue
        val = og[prop]
        if prop == "og:image":
            val = WWW + urlparse(val).path  # зеркало на www
        lines.append(f'<meta property="{prop}" content="{html.escape(val)}"/>')

    lines += [
        f'<meta property="og:url" content="{html.escape(www_url)}"/>',
        "",
        "<script>",
        f'  location.replace("{apex_url}" + location.search + location.hash);',
        "</script>",
        "</head>",
        "<body>",
        f'  <a href="{apex_url}">{html.escape(og.get("og:title", "пРОСТо Финансы"))}</a>',
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(lines)


def main():
    sitemap = fetch(APEX + "/sitemap.xml")
    urls = re.findall(r"<loc>([^<]+)</loc>", sitemap)
    print(f"страниц в sitemap: {len(urls)}")

    images = set()
    made = 0
    for url in urls:
        path = urlparse(url).path or "/"
        try:
            og = og_of(fetch(url))
        except Exception as e:
            print(f"  ПРОПУСК {path}: {type(e).__name__}")
            continue
        if "og:title" not in og:
            print(f"  ПРОПУСК {path}: нет og:title")
            continue
        if "og:image" in og:
            images.add(urlparse(og["og:image"]).path)

        rel = "index.html" if path == "/" else path.strip("/") + "/index.html"
        dest = os.path.join(REPO, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(shim(og, path))
        made += 1
        print(f"  шим {rel}")

    print(f"\nшимов: {made}, картинок к зеркалированию: {len(images)}")
    for img in sorted(images):
        dest = os.path.join(REPO, img.lstrip("/"))
        if os.path.exists(dest):
            print(f"  уже есть {img}")
            continue
        try:
            data = fetch(APEX + img, binary=True)
        except Exception as e:
            print(f"  ОШИБКА {img}: {type(e).__name__}")
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        print(f"  зеркало {img} ({len(data)} байт)")


if __name__ == "__main__":
    main()
