#!/usr/bin/env python3
# Required Notice: Copyright 2026 Axel Schmidt (axel@schmidtlab.net)
# PolyForm Noncommercial 1.0.0, siehe LICENSE.md. Kommerzielle Nutzung nur mit schriftlicher Genehmigung.
"""Baut den Ordner web/ für einen gewöhnlichen Webserver.

    python tools/web_bauen.py [vase/config.json]

web/index.html   3D-Ansicht mit Link zur About-Seite
web/about.html   README.md als Webseite, Formeln mit MathJax
web/bilder/      Bilder aus docs/bilder/
web/LICENSE*     Lizenztexte

Der Ordner wird so, wie er ist, auf den Server geladen. Es braucht dort
kein Python, nur statische Dateien.
"""

from __future__ import annotations

import html
import re
import shutil
import sys
from pathlib import Path

import markdown
from markdown.extensions.toc import slugify_unicode

from vase_feature import Vase, VaseFehler, koerper, massen
from vase_generator import html_schreiben
import json

WURZEL = Path(__file__).resolve().parents[1]
ZIEL = WURZEL / "web"


def ansicht_schreiben(config: Path) -> None:
    vase = Vase.aus_config(json.loads(config.read_text(encoding="utf-8")))
    netz = koerper(vase)
    html_schreiben(ZIEL / "index.html", vase, netz, massen(netz, vase), about="about.html")


def formeln_schuetzen(text: str) -> tuple[str, list[str]]:
    """Ersetzt Formeln durch Platzhalter, damit Markdown sie nicht verändert."""
    formeln: list[str] = []

    def merken(tex: str, abgesetzt: bool) -> str:
        formeln.append(("\\[" + tex + "\\]") if abgesetzt else ("\\(" + tex + "\\)"))
        return f"FORMEL{len(formeln) - 1}ENDE"

    text = re.sub(r"```math\n(.*?)\n```", lambda m: "\n" + merken(m.group(1), True) + "\n", text, flags=re.S)
    teile = re.split(r"(```.*?```)", text, flags=re.S)
    for i, teil in enumerate(teile):
        if not teil.startswith("```"):
            teile[i] = re.sub(r"\$`([^`]+)`\$", lambda m: merken(m.group(1), False), teil)
    return "".join(teile), formeln


def about_schreiben() -> None:
    quelle = (WURZEL / "README.md").read_text(encoding="utf-8")
    quelle = quelle.replace("docs/bilder/", "bilder/")
    quelle = quelle.replace("(LICENSE.md)", "(LICENSE.md)").replace("(LICENSE-CONTENT.txt)", "(LICENSE-CONTENT.txt)")
    quelle, formeln = formeln_schuetzen(quelle)
    # Die erste Überschrift steht im Seitenkopf.
    quelle = re.sub(r"^# .*\n", "", quelle, count=1)
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "toc", "attr_list"],
        extension_configs={"toc": {"slugify": slugify_unicode}},
    )
    inhalt = md.convert(quelle)
    for i, tex in enumerate(formeln):
        ersatz = html.escape(tex, quote=False)
        if tex.startswith("\\["):
            inhalt = inhalt.replace(f"<p>FORMEL{i}ENDE</p>", f'<div class="formel">{ersatz}</div>')
        inhalt = inhalt.replace(f"FORMEL{i}ENDE", ersatz)
    rest = re.findall(r"FORMEL\d+ENDE", inhalt)
    if rest:
        raise SystemExit(f"Formeln nicht eingesetzt: {rest[:3]}")
    # Tabellen sind auf schmalen Bildschirmen seitlich scrollbar.
    inhalt = inhalt.replace("<table>", '<div class="tabelle"><table>').replace("</table>", "</table></div>")
    (ZIEL / "about.html").write_text(_ABOUT.replace("__INHALT__", inhalt), encoding="utf-8")


def main() -> None:
    config = Path(sys.argv[1]) if len(sys.argv) > 1 else WURZEL / "vase" / "config.json"
    if ZIEL.exists():
        shutil.rmtree(ZIEL)
    (ZIEL / "bilder").mkdir(parents=True)
    try:
        ansicht_schreiben(config)
    except VaseFehler as fehler:
        raise SystemExit(str(fehler))
    about_schreiben()
    for bild in (WURZEL / "docs" / "bilder").glob("*.png"):
        shutil.copy(bild, ZIEL / "bilder" / bild.name)
    for datei in ("LICENSE.md", "LICENSE-CONTENT.txt"):
        shutil.copy(WURZEL / datei, ZIEL / datei)
    print("Geschrieben: web/index.html, web/about.html, web/bilder/, Lizenzen")


_ABOUT = """<!DOCTYPE html>
<!--
Required Notice: Copyright 2026 Axel Schmidt (axel@schmidtlab.net)
Text und Bilder: CC BY-NC-SA 4.0, https://creativecommons.org/licenses/by-nc-sa/4.0/
-->
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>About · Mathematische Vasen</title>
<script>
  window.MathJax = { tex: { inlineMath: [["\\\\(", "\\\\)"]], displayMath: [["\\\\[", "\\\\]"]] }, chtml: { scale: 1.0 } };
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-chtml.js"></script>
<style>
  :root {
    --hg: #f7f5f0; --flaeche: #ffffff; --rand: rgba(30, 28, 24, 0.10); --chip: rgba(30, 28, 24, 0.045);
    --text: #1d1c1a; --text-2: #55514a; --text-3: #8f897f; --akzent: #2c6e6a;
  }
  @media (prefers-color-scheme: dark) {
    :root { --hg: #161719; --flaeche: #1e1f23; --rand: rgba(255, 255, 255, 0.10); --chip: rgba(255, 255, 255, 0.06);
      --text: #f1efe9; --text-2: #c4beb4; --text-3: #8a857c; --akzent: #5fb3ac; }
    img { filter: brightness(0.92); }
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; scroll-padding-top: 76px; }
  body { margin: 0; background: var(--hg); color: var(--text);
    font: 16.5px/1.65 system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif; -webkit-font-smoothing: antialiased; }
  .leiste { position: sticky; top: 0; z-index: 5; display: flex; align-items: center; justify-content: space-between; gap: 16px;
    padding: 14px 24px; background: color-mix(in srgb, var(--hg) 82%, transparent); border-bottom: 1px solid var(--rand);
    backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); }
  .marke { font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--text-3); font-weight: 600; }
  .leiste a.knopf { padding: 7px 14px; border-radius: 999px; background: var(--text); color: var(--hg); text-decoration: none;
    font-size: 13px; font-weight: 600; white-space: nowrap; }
  main { max-width: 820px; margin: 0 auto; padding: 40px 24px 80px; }
  h1.titel { font-size: 40px; line-height: 1.1; letter-spacing: -0.025em; margin: 8px 0 18px; }
  h2 { font-size: 27px; letter-spacing: -0.015em; margin: 64px 0 16px; padding-top: 24px; border-top: 1px solid var(--rand); }
  h3 { font-size: 21px; margin: 44px 0 12px; }
  h4 { font-size: 17px; margin: 36px 0 10px; }
  h2 a, h3 a, h4 a { color: inherit; }
  p, li { color: var(--text-2); }
  strong { color: var(--text); }
  a { color: var(--akzent); text-underline-offset: 3px; }
  img { max-width: 100%; height: auto; border-radius: 14px; }
  code { font: 0.86em/1.4 ui-monospace, "SF Mono", Menlo, Consolas, monospace; background: var(--chip); padding: 2px 6px; border-radius: 6px; }
  pre { background: var(--flaeche); border: 1px solid var(--rand); border-radius: 12px; padding: 14px 16px; overflow-x: auto; }
  pre code { background: none; padding: 0; font-size: 13.5px; }
  .tabelle { overflow-x: auto; margin: 18px 0; border: 1px solid var(--rand); border-radius: 12px; background: var(--flaeche); }
  table { border-collapse: collapse; width: 100%; font-size: 14.5px; }
  th, td { text-align: left; vertical-align: top; padding: 10px 14px; border-bottom: 1px solid var(--rand); }
  th { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-3); font-weight: 600; }
  tr:last-child td { border-bottom: 0; }
  td { color: var(--text-2); }
  .formel { overflow-x: auto; overflow-y: hidden; margin: 18px 0; padding: 6px 0; }
  mjx-container[display="true"] { margin: 0 !important; }
  blockquote { margin: 18px 0; padding: 4px 18px; border-left: 3px solid var(--akzent); color: var(--text-2); }
  hr { border: 0; border-top: 1px solid var(--rand); }
  footer { max-width: 820px; margin: 0 auto; padding: 24px; font-size: 13px; color: var(--text-3); border-top: 1px solid var(--rand); }
  footer a { color: inherit; }
  @media (max-width: 640px) {
    body { font-size: 15.5px; }
    main { padding: 28px 18px 60px; }
    h1.titel { font-size: 30px; }
    h2 { font-size: 23px; margin-top: 48px; }
    .leiste { padding: 12px 16px; }
  }
</style>
</head>
<body>
<div class="leiste">
  <span class="marke">Mathematische Vasen</span>
  <a class="knopf" href="index.html">Zur 3D-Ansicht</a>
</div>
<main>
<h1 class="titel">Mathematische Vasen</h1>
__INHALT__
</main>
<footer>© 2026 Axel Schmidt · Text und Bilder CC BY-NC-SA 4.0, Programm PolyForm Noncommercial 1.0.0 ·
  Kommerzielle Nutzung nur nach Absprache: <a href="mailto:axel@schmidtlab.net">axel@schmidtlab.net</a></footer>
</body>
</html>
"""


if __name__ == "__main__":
    main()
