"""Проверка выката шимов: каждая страница и каждая картинка глазами краулера."""
import re
import time
import urllib.request
from urllib.parse import urlparse

UA = "TelegramBot (like TwitterBot)"
APEX = "https://prosto-finance.ru"
WWW = "https://www.prosto-finance.ru"


def get(url, binary=False, retries=3):
    last = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
                return r.status, (data if binary else data.decode("utf-8", "replace"))
        except Exception as e:
            last = e
            time.sleep(2)
    raise last


sitemap = get(APEX + "/sitemap.xml")[1]
paths = [urlparse(u).path or "/" for u in re.findall(r"<loc>([^<]+)</loc>", sitemap)]

bad = []
images = set()
print(f"проверяю {len(paths)} страниц на www\n")

for path in paths:
    url = WWW + (path if path != "/" else "/")
    try:
        st, body = get(url)
    except Exception as e:
        bad.append(f"{path}: НЕДОСТУПНА ({type(e).__name__})")
        print(f"  ✗ {path}: {type(e).__name__}")
        continue

    title = re.search(r'<meta property="og:title" content="([^"]*)"', body)
    img = re.search(r'<meta property="og:image" content="([^"]*)"', body)
    ogurl = re.search(r'<meta property="og:url" content="([^"]*)"', body)

    problems = []
    if st != 200:
        problems.append(f"http={st}")
    if not title:
        problems.append("нет og:title")
    if not img:
        problems.append("нет og:image")
    elif "www.prosto-finance.ru" not in img.group(1):
        problems.append(f"og:image НЕ на www: {img.group(1)}")
    else:
        images.add(img.group(1))
    if ogurl and "www.prosto-finance.ru" not in ogurl.group(1):
        problems.append("og:url не на www")
    if "rel=\"canonical\"" in body or "rel='canonical'" in body:
        problems.append("ЕСТЬ canonical - убьёт карточку")
    if "http-equiv=\"refresh\"" in body:
        problems.append("ЕСТЬ meta refresh - убьёт карточку")
    # Единственное, что держит www вне поиска: в robots.txt запрета больше нет
    # (под запретом робот не читает noindex, и адрес оседает в индексе пустым).
    if not re.search(r'<meta\s+name="robots"\s+content="[^"]*noindex', body):
        problems.append("НЕТ noindex - страница уедет в индекс дублем апекса")

    if problems:
        bad.append(f"{path}: {', '.join(problems)}")
        print(f"  ✗ {path}: {', '.join(problems)}")
    else:
        print(f"  ✓ {path}")

print(f"\nпроверяю {len(images)} картинок на www\n")
for img in sorted(images):
    try:
        st, data = get(img, binary=True)
        is_png = data[:4] == bytes([0x89, 0x50, 0x4E, 0x47])
        if st == 200 and is_png:
            print(f"  ✓ {urlparse(img).path} ({len(data)} байт)")
        else:
            bad.append(f"{img}: http={st} png={is_png}")
            print(f"  ✗ {urlparse(img).path}: http={st} png={is_png}")
    except Exception as e:
        bad.append(f"{img}: {type(e).__name__}")
        print(f"  ✗ {urlparse(img).path}: {type(e).__name__}")

print("\n" + "=" * 55)
if bad:
    print(f"ПРОБЛЕМ: {len(bad)}")
    for b in bad:
        print("  -", b)
else:
    print("ВСЁ ЧИСТО: страницы и картинки на месте, noindex стоит, canonical и refresh нет")
