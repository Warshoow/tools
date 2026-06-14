#!/usr/bin/env python3
"""
docs_crawler.py — Aspire la doc d'un site web en fichiers .md propres,
prêts à être indexés par grepai (ou cherchés au ripgrep).

Chaque fichier garde dans son frontmatter l'URL d'origine + le titre,
pour que l'agent qui lit un chunk sache EXACTEMENT où chercher dans la doc en ligne.

Stratégie (de la plus maline à la plus brute) :
  1. /llms.txt ou /llms-full.txt  -> liste d'URLs déjà curée par le site
  2. /sitemap.xml                 -> set d'URLs déclaré
  3. BFS sur les liens same-domain -> fallback si rien d'autre

Pour chaque page : on tente d'abord la version markdown (url + ".md", servie
par Mintlify/Docusaurus & co), sinon on extrait le contenu principal en markdown.

Usage:
    python docs_crawler.py https://docs.exemple.com --out ./docs_md --max-pages 300

Puis (grepai, 100% local via Ollama) :
    ollama pull nomic-embed-text
    cd docs_md && grepai watch --no-ui
    grepai search "comment configurer l'authentification"
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.request
import urllib.error
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

try:
    import trafilatura
except ImportError:
    sys.exit("Il manque trafilatura : pip install trafilatura")

try:
    from markdownify import markdownify as _md
except ImportError:
    _md = None  # fallback d'extraction désactivé si absent (pip install markdownify)

UA = "docs-crawler/1.0 (+local doc indexing for grepai)"
TIMEOUT = 30


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
def http_get(url: str, retries: int = 1) -> tuple[int, str, str]:
    """Retourne (status, content_type, text). status=0 en cas d'échec réseau.
    Réessaie `retries` fois sur échec (timeout, hoquet réseau)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                ctype = resp.headers.get("Content-Type", "")
                raw = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                return resp.status, ctype, raw.decode(charset, errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError):
            if attempt < retries:
                time.sleep(1.5)
                continue
            return 0, "", ""
    return 0, "", ""


# --------------------------------------------------------------------------- #
# URL discovery
# --------------------------------------------------------------------------- #
def url_of_llms_full(base: str) -> str | None:
    """llms-full.txt = TOUT le contenu concaténé en un seul fichier (pas une liste
    de liens). S'il existe, on le récupère tel quel. Retourne son URL ou None."""
    full = urljoin(base, "/llms-full.txt")
    status, _, text = http_get(full)
    if status == 200 and text.strip():
        print("  llms-full.txt trouvé : doc complète en un seul fichier")
        return full
    return None


def urls_from_llms_txt(base: str) -> list[str]:
    """llms.txt = markdown avec des liens [titre](url). On en extrait les URLs."""
    status, _, text = http_get(urljoin(base, "/llms.txt"))
    if status == 200 and text.strip():
        links = re.findall(r"\]\((https?://[^\s)]+)\)", text)
        if links:
            print(f"  llms.txt trouvé : {len(links)} liens")
            return links
    return []


def urls_from_sitemap(base: str) -> list[str]:
    """Parse sitemap.xml (et sitemap index récursif basique)."""
    out: list[str] = []
    to_visit = [urljoin(base, "/sitemap.xml")]
    seen_maps: set[str] = set()
    while to_visit:
        sm = to_visit.pop()
        if sm in seen_maps:
            continue
        seen_maps.add(sm)
        status, _, text = http_get(sm)
        if status != 200 or not text.strip():
            continue
        try:
            root = ElementTree.fromstring(text)
        except ElementTree.ParseError:
            continue
        ns = re.match(r"\{.*\}", root.tag)
        ns = ns.group(0) if ns else ""
        for loc in root.iter(ns + "loc"):
            url = (loc.text or "").strip()
            if url.endswith(".xml"):
                to_visit.append(url)        # sitemap index -> sous-sitemaps
            elif url:
                out.append(url)
    if out:
        print(f"  sitemap.xml trouvé : {len(out)} URLs")
    return out


class _LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.links.append(v)


def crawl_bfs(base: str, out_dir: Path, max_pages: int, delay: float) -> int:
    """Parcours en largeur des liens same-domain qui ÉCRIT au fil de l'eau :
    un seul fetch par page (on extrait depuis le HTML déjà en main).
    Retourne le nombre de pages écrites."""
    origin = urlparse(base)
    prefix = origin.path.rstrip("/")
    queue = [base]
    seen: set[str] = set()
    written = 0
    visited = 0
    while queue and written < max_pages:
        url = queue.pop(0).split("#")[0]
        if url in seen:
            continue
        seen.add(url)
        visited += 1
        status, ctype, html = http_get(url)
        if status != 200 or "html" not in ctype:
            print(f"  SKIP (status {status}, type '{ctype.split(';')[0]}') {url}")
            time.sleep(delay)
            continue

        # récolte les liens AVANT d'écrire (pour ne pas perdre la file si extraction rate)
        ext = _LinkExtractor()
        try:
            ext.feed(html)
        except Exception:
            pass
        for href in ext.links:
            nxt = urljoin(url, href).split("#")[0]
            p = urlparse(nxt)
            if p.netloc == origin.netloc and p.path.startswith(prefix) and nxt not in seen:
                queue.append(nxt)

        # extraction + écriture immédiate depuis le HTML déjà téléchargé
        res = extract_html(html, url)
        if res is None:
            print(f"  SKIP (rien à extraire) {url}")
            time.sleep(delay)
            continue
        title, md = res
        path = write_doc(out_dir, url, title, md)
        written += 1
        print(f"  OK   {path.name}")
        time.sleep(delay)

    print(f"\nBFS terminé : {written} pages écrites ({visited} visitées) dans {out_dir}/")
    return written


# --------------------------------------------------------------------------- #
# Fetch + extraction
# --------------------------------------------------------------------------- #
def _title_from_md(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def _looks_like_markdown(ctype: str, text: str) -> bool:
    return ("markdown" in ctype or "text/plain" in ctype
            or text.lstrip().startswith(("#", "---")))


def _title_from_html(html: str, fallback: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return fallback


def _fallback_markdown(html: str) -> str | None:
    """Plan B quand trafilatura jette une page (ex: page quasi 100% tableaux/démos).
    On isole le contenu principal et on le convertit en markdown en gardant les tableaux."""
    if _md is None:
        return None
    m = re.search(r"<(main|article)\b[^>]*>(.*?)</\1>", html, re.S | re.I)
    chunk = m.group(2) if m else html
    chunk = re.sub(r"<(script|style|nav|header|footer|aside|svg)\b.*?</\1>", " ",
                   chunk, flags=re.S | re.I)
    md = _md(chunk, heading_style="ATX")
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return md or None


def extract_html(html: str, url: str) -> tuple[str, str] | None:
    """Extrait le contenu principal d'une chaîne HTML déjà téléchargée -> (titre, md)."""
    md = trafilatura.extract(
        html, output_format="markdown",
        include_links=True, include_tables=True, favor_recall=True,
    )
    if not md or not md.strip():
        md = _fallback_markdown(html)   # pages tableaux/démos que trafilatura rejette
        if not md:
            return None
    meta = trafilatura.extract_metadata(html)
    title = meta.title if meta and meta.title else _title_from_html(html, url)
    return title, md


def fetch_as_markdown(url: str) -> tuple[str, str] | None:
    """Retourne (titre, markdown) ou None.
    A) si l'URL pointe DÉJÀ sur un .md -> on la récupère telle quelle
    B) sinon on tente la version .md servie par le site (url + ".md")
    C) sinon on extrait le contenu principal du HTML."""
    clean = url.rstrip("/")

    # A) URL déjà markdown/texte (ex: /raw/...page.md, ou /llms-full.txt)
    if clean.lower().endswith((".md", ".mdx", ".txt")):
        status, _, text = http_get(clean)
        if status == 200 and text.strip():
            return _title_from_md(text, url), text
        return None

    # B) version .md native (Mintlify/Docus servent souvent <page>.md)
    status, ctype, text = http_get(clean + ".md")
    if status == 200 and text.strip() and _looks_like_markdown(ctype, text):
        return _title_from_md(text, url), text

    # C) extraction depuis le HTML
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    return extract_html(downloaded, url)


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def slugify(url: str) -> str:
    p = urlparse(url)
    raw = (p.netloc + p.path).strip("/")
    raw = re.sub(r"\.(md|html?)$", "", raw, flags=re.I)   # évite page-accordion.md.md
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw).strip("-")
    return (slug or "index")[:120]


def write_doc(out_dir: Path, url: str, title: str, markdown: str) -> Path:
    safe_title = title.replace('"', "'").strip()
    frontmatter = f'---\nurl: "{url}"\ntitle: "{safe_title}"\nsource: crawler\n---\n\n'
    path = out_dir / (slugify(url) + ".md")
    n = 1
    while path.exists():  # évite les collisions de slug
        path = out_dir / f"{slugify(url)}-{n}.md"
        n += 1
    path.write_text(frontmatter + markdown, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def discover_urls(base: str, max_pages: int, use_full: bool = True) -> list[str]:
    """Retourne une LISTE d'URLs via llms-full.txt / llms.txt / sitemap.xml.
    Vide si aucun des trois -> l'appelant bascule sur le BFS streaming."""
    # 1) llms-full.txt : tout le contenu d'un coup (un seul "doc")
    if use_full:
        full = url_of_llms_full(base)
        if full:
            return [full]
    # 2) llms.txt : liste de liens -> crawl page par page
    urls = urls_from_llms_txt(base)
    # 3) sinon sitemap.xml
    if not urls:
        urls = urls_from_sitemap(base)
    # dédoublonne en gardant l'ordre, et restreint au même domaine
    origin = urlparse(base).netloc
    seen, out = set(), []
    for u in urls:
        u = u.split("#")[0]
        if urlparse(u).netloc == origin and u not in seen:
            seen.add(u)
            out.append(u)
    return out[:max_pages]


def main() -> None:
    ap = argparse.ArgumentParser(description="Crawle une doc web en .md pour grepai.")
    ap.add_argument("base_url", help="URL racine de la doc, ex: https://docs.exemple.com")
    ap.add_argument("--out", default="./docs_md", help="Dossier de sortie (défaut: ./docs_md)")
    ap.add_argument("--max-pages", type=int, default=500, help="Plafond de pages (défaut: 500)")
    ap.add_argument("--delay", type=float, default=0.3, help="Pause entre requêtes en s (défaut: 0.3)")
    ap.add_argument("--no-full", action="store_true",
                    help="Ignore llms-full.txt et force le crawl page par page "
                         "(garde l'URL par page dans le frontmatter)")
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Découverte des URLs sur {base} ...")
    urls = discover_urls(base, args.max_pages, use_full=not args.no_full)

    if urls:
        print(f"\nRécupération de {len(urls)} pages -> {out_dir}/")
        ok = 0
        for i, url in enumerate(urls, 1):
            res = fetch_as_markdown(url)
            if res is None:
                print(f"  [{i}/{len(urls)}] SKIP {url}")
                time.sleep(args.delay)
                continue
            title, md = res
            path = write_doc(out_dir, url, title, md)
            ok += 1
            print(f"  [{i}/{len(urls)}] OK   {path.name}")
            time.sleep(args.delay)
        print(f"\nTerminé : {ok}/{len(urls)} pages écrites dans {out_dir}/")
    else:
        print("  Ni llms-full.txt, ni llms.txt, ni sitemap.xml -> BFS (écriture au fil de l'eau)")
        if crawl_bfs(base, out_dir, args.max_pages, args.delay) == 0:
            sys.exit("Aucune page exploitable trouvée. Vérifie l'URL.")

    print("\nÉtape suivante (grepai, 100% local) :")
    print("  ollama pull nomic-embed-text")
    print(f"  cd {out_dir} && grepai watch --no-ui")
    print('  grepai search "ta question en langage naturel"')
    print("\nOu sans embeddings, juste du lexical :")
    print(f'  rg -i "mot-clé" {out_dir}/')


if __name__ == "__main__":
    main()