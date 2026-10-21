#!/usr/bin/env python3
# Required Notice: Copyright 2026 Axel Schmidt (axel@schmidtlab.net)
# PolyForm Noncommercial 1.0.0, siehe LICENSE.md. Kommerzielle Nutzung nur mit schriftlicher Genehmigung.
"""Erzeugt aus einer config.json das lokale Vasenmodell.

    python tools/vase_generator.py vase/config.json

Schreibt neben die Config eine STL fuer den Slicer, eine HTML-Datei mit
drehbarer 3D-Ansicht und eine technische Vorschau.
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from vase_feature import (
    Vase, VaseFehler, aussen_polygon, bett_linien, koerper, massen, schnitt_hoehen, ueberhaenge, wasserdicht,
    _CNOIDAL_M, _CNOIDAL_K, _PHYLLO_MAX, _SUPER_MIN, _SUPER_MAX, _KETTEN_A, _ZETA_MAX, _TURING,
)


STL_KOPF = b"Vase, mm. (c) 2026 Axel Schmidt, CC BY-NC-SA 4.0, axel@schmidtlab.net"


def stl_schreiben(pfad: Path, netz: dict) -> None:
    dreiecke = netz["dreiecke"]
    punkte = netz["positionen"]
    with pfad.open("wb") as datei:
        datei.write(STL_KOPF.ljust(80, b"\0"))
        datei.write(struct.pack("<I", len(dreiecke)))
        for a, b, c in dreiecke:
            pa, pb, pc = punkte[a], punkte[b], punkte[c]
            ux, uy, uz = pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]
            vx, vy, vz = pc[0] - pa[0], pc[1] - pa[1], pc[2] - pa[2]
            nx = uy * vz - uz * vy
            ny = uz * vx - ux * vz
            nz = ux * vy - uy * vx
            laenge = (nx * nx + ny * ny + nz * nz) ** 0.5 or 1.0
            datei.write(struct.pack(
                "<12fH",
                nx / laenge, ny / laenge, nz / laenge,
                pa[0], pa[1], pa[2],
                pb[0], pb[1], pb[2],
                pc[0], pc[1], pc[2],
                0,
            ))


UEBERHANG_ORANGE = (235, 150, 40)
UEBERHANG_ROT = (210, 40, 30)


def vorschau_png(pfad: Path, vase: Vase, netz: dict, info: dict) -> None:
    bild = Image.new("RGB", (1100, 780), (250, 248, 242))
    stift = ImageDraw.Draw(bild)
    stift.rounded_rectangle([24, 24, 620, 740], radius=12, fill=(255, 255, 255), outline=(220, 214, 204))
    stift.rounded_rectangle([644, 24, 1076, 740], radius=12, fill=(255, 255, 255), outline=(220, 214, 204))
    stift.text((40, 36), "Seitenansicht", fill=(40, 40, 40))
    stift.text((660, 36), "Querschnitt auf halber Hoehe", fill=(40, 40, 40))

    radius_achse = info["durchmesser_grenze"] * 0.5
    links, rechts, oben, unten = 70, 590, 80, 700

    def sx(radius):
        return links + (radius + radius_achse) / (2 * radius_achse) * (rechts - links)

    def sy(z):
        return unten - z / vase.bett_z * (unten - oben)

    stift.rectangle([sx(-vase.bett_x * 0.5), sy(vase.bett_z), sx(vase.bett_x * 0.5), sy(0)], outline=(210, 206, 198))
    stift.line([(sx(0), oben), (sx(0), unten)], fill=(230, 230, 230))
    farben = [(20, 90, 160), (20, 150, 160), (30, 130, 80), (140, 50, 140)]
    zs = schnitt_hoehen(vase)
    radien = netz["radien"]
    winkel = ueberhaenge(vase, radien)
    for nummer, farbe in enumerate(farben):
        # Meridian bei nummer · 45° und gegenüber, jeweils die Lamelle auf diesem Winkel.
        for seite, lamelle in ((1, round(nummer * vase.lamellen / 8)), (-1, round((nummer + 4) * vase.lamellen / 8))):
            lamelle %= vase.lamellen
            for k in range(len(zs) - 1):
                grad = winkel[k][lamelle]
                stueck = UEBERHANG_ROT if grad > vase.stuetze_grad else UEBERHANG_ORANGE if grad > vase.warnung_grad else farbe
                stift.line(
                    [(sx(seite * radien[k][lamelle]), sy(zs[k])), (sx(seite * radien[k + 1][lamelle]), sy(zs[k + 1]))],
                    fill=stueck, width=3 if stueck != farbe else 2,
                )
    stift.line([(sx(vase.bohrung), sy(vase.boden)), (sx(vase.bohrung), sy(vase.hoehe)), (sx(-vase.bohrung), sy(vase.hoehe)), (sx(-vase.bohrung), sy(vase.boden)), (sx(vase.bohrung), sy(vase.boden))], fill=(150, 150, 150), width=2)
    stift.text((80, 710), "Grau: H2D-Bauraum und Bohrung. Farbe: vier Meridiane.", fill=(90, 90, 90))
    stift.text(
        (80, 724),
        f"Orange: Ueberhang ueber {vase.warnung_grad:.0f} Grad. Rot: ueber {vase.stuetze_grad:.0f} Grad, braucht Stuetzen.",
        fill=(90, 90, 90),
    )

    mitte_x, mitte_y, massstab = 860, 400, 280 / radius_achse
    stift.ellipse(
        [mitte_x - vase.bett_y * 0.5 * massstab, mitte_y - vase.bett_x * 0.5 * massstab,
         mitte_x + vase.bett_y * 0.5 * massstab, mitte_y + vase.bett_x * 0.5 * massstab],
        outline=(210, 206, 198),
    )
    mitte = (len(zs) - 1) // 2
    kontur = aussen_polygon(zs[mitte], vase, radien[mitte])
    punkte = [(mitte_x + x * massstab, mitte_y - y * massstab) for x, y in kontur]
    punkte.append(punkte[0])
    stift.line(punkte, fill=(20, 90, 160), width=1)
    bohr = vase.bohrung * massstab
    stift.ellipse([mitte_x - bohr, mitte_y - bohr, mitte_x + bohr, mitte_y + bohr], outline=(150, 150, 150), width=2)
    stift.text((670, 680), f"Hoehe {info['hoehe']:.0f} mm, Durchmesser {info['durchmesser']:.0f} mm", fill=(40, 40, 40))
    stift.text((670, 700), f"H2D nutzbar: {info['durchmesser_grenze']:.0f} mm x {info['hoehe_grenze']:.0f} mm", fill=(40, 40, 40))
    bild.save(pfad)


def math_cos(wert: float) -> float:
    import math
    return math.cos(wert)


def math_sin(wert: float) -> float:
    import math
    return math.sin(wert)


def html_schreiben(pfad: Path, vase: Vase, netz: dict, info: dict) -> None:
    daten = {
        "name": vase.name,
        "lamellen": vase.lamellen,
        "dicke": vase.dicke,
        "wand": vase.wand,
        "boden": vase.boden,
        "muendung_zugabe": vase.muendung - vase.bohrung,
        "schnitte": vase.schnitte,
        "bogen": vase.punkte,
        "loben": vase.loben,
        "potenz": vase.potenz,
        "oberwelle": vase.oberwelle_loben,
        "oberAnteil": vase.oberwelle_anteil,
        "linien": [round(wert, 2) for wert in bett_linien(vase)],
        "start": {
            "innendurchmesser": vase.innendurchmesser,
            "hoehe": vase.hoehe,
            "lamelleMax": vase.lamelle_max,
            "funktion": vase.funktion,
            "begrenzen": vase.begrenzen,
        },
        "grenzeDurchmesser": info["durchmesser_grenze"],
        "grenzeHoehe": info["hoehe_grenze"],
        "cnoidalM": _CNOIDAL_M,
        "cnoidalK": _CNOIDAL_K,
        "phylloMax": _PHYLLO_MAX,
        "superMin": _SUPER_MIN,
        "superMax": _SUPER_MAX,
        "kettenA": _KETTEN_A,
        "zetaMax": _ZETA_MAX,
        "turing": _TURING["muster"],
        "begrenzungGrad": vase.begrenzung_grad,
        "warnungGrad": vase.warnung_grad,
        "stuetzeGrad": vase.stuetze_grad,
    }
    roh = json.dumps(daten, separators=(",", ":")).replace("<", "\\u003c")
    pfad.write_text(_HTML.replace("__DATEN__", roh), encoding="utf-8")


_HTML = """<!DOCTYPE html>
<!--
Required Notice: Copyright 2026 Axel Schmidt (axel@schmidtlab.net)
Programm: PolyForm Noncommercial License 1.0.0, https://polyformproject.org/licenses/noncommercial/1.0.0
Erzeugte Modelle: CC BY-NC-SA 4.0, https://creativecommons.org/licenses/by-nc-sa/4.0/
Kommerzielle Nutzung, auch der Verkauf gedruckter Vasen, nur mit schriftlicher Genehmigung.
-->
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Mathematische Vasen</title>
<style>
  :root {
    --hg-1: #f7f5f0; --hg-2: #e7e2d7;
    --flaeche: rgba(255, 255, 255, 0.78); --rand: rgba(30, 28, 24, 0.08);
    --text: #1d1c1a; --text-2: #6b665d; --text-3: #9a948a;
    --akzent: #2c6e6a; --akzent-text: #ffffff; --chip: rgba(30, 28, 24, 0.05);
    --gut: #3f8f5a; --warn: #e0912f; --rot: #c8352a;
    --schatten: 0 1px 2px rgba(0,0,0,0.04), 0 12px 32px rgba(40, 32, 20, 0.10);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --hg-1: #24262a; --hg-2: #121315;
      --flaeche: rgba(30, 31, 35, 0.82); --rand: rgba(255, 255, 255, 0.08);
      --text: #f1efe9; --text-2: #b0aaa0; --text-3: #7c776f;
      --akzent: #5fb3ac; --akzent-text: #0e1a19; --chip: rgba(255, 255, 255, 0.06);
      --schatten: 0 1px 2px rgba(0,0,0,0.3), 0 12px 32px rgba(0, 0, 0, 0.35);
    }
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; }
  body {
    font: 15px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    color: var(--text); background: radial-gradient(120% 90% at 35% 30%, var(--hg-1), var(--hg-2));
    display: grid; grid-template-columns: 1fr 360px; overflow: hidden;
    -webkit-font-smoothing: antialiased;
  }
  .buehne { position: relative; min-width: 0; min-height: 0; height: 100vh; display: flex; flex-direction: column; }
  .flaeche3d { position: relative; flex: 1; min-height: 0; }
  canvas { position: absolute; inset: 0; width: 100%; height: 100%; display: block; touch-action: none; cursor: grab; }
  canvas:active { cursor: grabbing; }
  .kopf { padding: 28px 32px 0; max-width: 720px; }
  .marke { font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--text-3); font-weight: 600; }
  .kopf h1 { margin: 6px 0 6px; font-size: 30px; line-height: 1.15; font-weight: 650; letter-spacing: -0.02em; }
  .kopf p { margin: 0 0 10px; color: var(--text-2); }
  .kopf code { display: inline-block; font: 13px/1.4 ui-monospace, "SF Mono", Menlo, Consolas, monospace; color: var(--text-2);
    background: var(--chip); border-radius: 8px; padding: 4px 8px; }
  .leiste { position: absolute; left: 24px; bottom: 22px; display: flex; gap: 10px; align-items: center; }
  .leiste button { border: 1px solid var(--rand); background: var(--flaeche); color: var(--text); border-radius: 999px;
    padding: 7px 14px; font: inherit; font-size: 13px; cursor: pointer; backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
  .leiste button[aria-pressed="true"] { color: var(--akzent); }
  #hinweis { font-size: 13px; color: var(--text-3); }
  #regler { height: 100vh; overflow-y: auto; padding: 22px 20px 24px; background: var(--flaeche); border-left: 1px solid var(--rand);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); }
  #regler { display: flex; flex-direction: column; padding-bottom: 0; }
  #regler section { padding: 14px 0; border-bottom: 1px solid var(--rand); }
  #regler section:last-of-type { border-bottom: 0; }
  #regler section:first-of-type { padding-top: 0; }
  #regler h2 { margin: 0 0 12px; font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-3); font-weight: 600; }
  .chips { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .chips button { text-align: left; border: 1px solid transparent; background: var(--chip); color: var(--text); border-radius: 10px;
    padding: 7px 10px; font: inherit; font-size: 13px; cursor: pointer; transition: background .15s, border-color .15s;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .chips button:hover { border-color: var(--rand); }
  .chips button[aria-pressed="true"] { background: var(--akzent); color: var(--akzent-text); font-weight: 600; }
  .versteckt { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
  .regler { display: block; margin: 0 0 14px; }
  .regler:last-child { margin-bottom: 0; }
  .regler .zeile { display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 6px; }
  .regler output { font-variant-numeric: tabular-nums; color: var(--text-2); }
  input[type=range] { -webkit-appearance: none; appearance: none; width: 100%; height: 22px; background: transparent; margin: 0; }
  input[type=range]::-webkit-slider-runnable-track { height: 4px; border-radius: 4px; background: var(--rand); }
  input[type=range]::-moz-range-track { height: 4px; border-radius: 4px; background: var(--rand); }
  input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 18px; height: 18px; margin-top: -7px; border-radius: 50%;
    background: var(--akzent); border: 3px solid var(--flaeche); box-shadow: 0 1px 4px rgba(0,0,0,0.25); }
  input[type=range]::-moz-range-thumb { width: 14px; height: 14px; border-radius: 50%; background: var(--akzent);
    border: 3px solid var(--flaeche); box-shadow: 0 1px 4px rgba(0,0,0,0.25); }
  .schalter { display: flex; align-items: center; gap: 10px; font-size: 14px; cursor: pointer; }
  .schalter input { position: absolute; opacity: 0; pointer-events: none; }
  .schalter .spur { flex: none; width: 36px; height: 22px; border-radius: 999px; background: var(--rand); position: relative; transition: background .15s; }
  .schalter .spur::after { content: ""; position: absolute; left: 3px; top: 3px; width: 16px; height: 16px; border-radius: 50%;
    background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.3); transition: transform .15s; }
  .schalter input:checked + .spur { background: var(--akzent); }
  .schalter input:checked + .spur::after { transform: translateX(14px); }
  .schalter input:focus-visible + .spur { outline: 2px solid var(--akzent); outline-offset: 2px; }
  .werte { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .werte div { background: var(--chip); border-radius: 12px; padding: 10px; }
  .werte span { display: block; font-size: 11px; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.08em; }
  .werte strong { display: flex; align-items: center; gap: 6px; font-size: 17px; font-weight: 650; font-variant-numeric: tabular-nums; margin-top: 2px; }
  .punkt { width: 8px; height: 8px; border-radius: 50%; background: var(--gut); flex: none; }
  .punkt.warn { background: var(--warn); } .punkt.rot { background: var(--rot); }
  #ueberhang { margin: 12px 0 0; font-size: 13px; color: var(--text-2); }
  #ueberhang.rot { color: var(--rot); }
  #status { margin: 6px 0 0; font-size: 12px; color: var(--text-3); }
  .lizenz { margin: 12px 0 0; font-size: 11px; line-height: 1.5; color: var(--text-3); }
  .lizenz a { color: inherit; }
  .legende { display: flex; gap: 14px; margin: 10px 0 0; padding: 0; list-style: none; font-size: 12px; color: var(--text-3); }
  .legende li { display: flex; align-items: center; gap: 6px; }
  .knoepfe { display: grid; grid-template-columns: 1fr 1.4fr; gap: 8px; position: sticky; bottom: 0; margin: auto -20px 0;
    padding: 14px 20px 20px; background: linear-gradient(to bottom, transparent, var(--flaeche) 30%); }
  .knoepfe button { border-radius: 12px; padding: 11px 12px; font: inherit; font-weight: 600; cursor: pointer; border: 1px solid var(--rand);
    background: transparent; color: var(--text); }
  .knoepfe button.primaer { background: var(--text); color: var(--hg-1); border-color: transparent; }
  .knoepfe button:hover { filter: brightness(1.08); }
  button:focus-visible { outline: 2px solid var(--akzent); outline-offset: 2px; }
  @media (max-width: 760px) {
    body { display: block; overflow: auto; height: auto; }
    .buehne { height: auto; }
    .flaeche3d { height: 52svh; flex: none; }
    .kopf { padding: 18px 18px 0; }
    .kopf h1 { font-size: 22px; }
    .kopf p { font-size: 13px; }
    .leiste { left: 14px; bottom: 12px; }
    #hinweis { display: none; }
    .knoepfe { position: static; margin: 0; padding: 16px 0 0; background: none; }
    #regler { height: auto; border-left: 0; border-top: 1px solid var(--rand); border-radius: 20px 20px 0 0; margin-top: -16px;
      position: relative; box-shadow: var(--schatten); padding-bottom: calc(24px + env(safe-area-inset-bottom)); }
  }
</style>
</head>
<body>
<main class="buehne">
  <header class="kopf">
    <div class="marke">Mathematische Vasen</div>
    <h1 id="name"></h1>
    <p id="idee"></p>
    <code id="formelzeile"></code>
  </header>
  <div class="flaeche3d">
    <canvas id="bild" aria-label="3D-Ansicht der Vase"></canvas>
    <div class="leiste">
      <button id="drehen" type="button" aria-pressed="true">Drehen</button>
      <span id="hinweis">Ziehen dreht · Scrollen zoomt · Rahmen = Bauraum des H2D</span>
    </div>
  </div>
</main>
<aside id="regler">
  <span id="titel" class="versteckt"></span>
  <section>
    <h2>Form</h2>
    <div class="chips" id="chips"></div>
    <select id="formel" class="versteckt" aria-hidden="true" tabindex="-1">
      <option value="zeta">Riemannsche Zetafunktion</option>
      <option value="cnoidal">Cnoidalwelle</option>
      <option value="logspirale">Logarithmische Spirale</option>
      <option value="phyllotaxis">Goldener Winkel</option>
      <option value="super">Superformel</option>
      <option value="ketten">Kettenlinie</option>
      <option value="turing_flecken">Turing, Flecken</option>
      <option value="turing_labyrinth">Turing, Labyrinth</option>
      <option value="sinus">Sinus</option>
      <option value="spirale">Spirale</option>
      <option value="bluete">Blüte</option>
      <option value="kaemme">Kämme</option>
      <option value="gleich">Klassisch</option>
    </select>
  </section>
  <section>
    <h2>Maße</h2>
    <label class="regler"><span class="zeile">Innendurchmesser <output id="oD"></output></span><input id="d" type="range" min="40" max="180" step="1"></label>
    <label class="regler"><span class="zeile">Höhe <output id="oH"></output></span><input id="h" type="range" min="80" max="320" step="1"></label>
    <label class="regler"><span class="zeile">Lamellenlänge max. <output id="oL"></output></span><input id="l" type="range" min="4" max="70" step="0.1"></label>
  </section>
  <section>
    <h2>Druck</h2>
    <label class="schalter"><input id="begrenzen" type="checkbox"><span class="spur"></span><span>Überhang auf <span id="oB"></span>° begrenzen</span></label>
    <div class="werte" style="margin-top: 14px">
      <div><span>Außen-Ø</span><strong id="wD"></strong></div>
      <div><span>Überhang</span><strong><i class="punkt" id="wPunkt"></i><span id="wU" style="all: unset"></span></strong></div>
      <div><span>H2D</span><strong id="wP"></strong></div>
    </div>
    <p id="ueberhang"></p>
    <ul class="legende"><li><i class="punkt warn"></i>über 45°, kann hängen</li><li><i class="punkt rot"></i>über 60°, Stützen</li></ul>
    <p id="status"></p>
    <p class="lizenz">© 2026 Axel Schmidt · frei für nicht-kommerzielle Nutzung
      (<a href="https://polyformproject.org/licenses/noncommercial/1.0.0" target="_blank" rel="noopener">Programm</a>,
      <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank" rel="noopener">Modelle</a>).
      Kommerzielle Nutzung nur nach Absprache: <a href="mailto:axel@schmidtlab.net">axel@schmidtlab.net</a></p>
  </section>
  <div class="knoepfe">
    <button id="zurueck" type="button">Startwerte</button>
    <button id="stl" type="button" class="primaer">STL herunterladen</button>
  </div>
</aside>
<script id="daten" type="application/json">__DATEN__</script>
<script>
const daten = JSON.parse(document.getElementById("daten").textContent);
document.getElementById("titel").textContent = daten.name;
document.getElementById("d").value = daten.start.innendurchmesser;
document.getElementById("h").value = daten.start.hoehe;
document.getElementById("l").value = daten.start.lamelleMax;
document.getElementById("formel").value = daten.start.funktion;
document.getElementById("begrenzen").checked = daten.start.begrenzen;
document.getElementById("oB").textContent = daten.begrenzungGrad.toFixed(0);
const FORMEN = {
  zeta: ["Riemannsche Zetafunktion", "Betrag von ζ auf Ellipsen im kritischen Streifen. Nullstellen erscheinen als Einkerbungen.", "|ζ(σ + it)|,  σ = ½ + 0,45 cos θ,  t = 12 + 24 s + 2,5 sin θ"],
  cnoidal: ["Cnoidalwelle", "Periodische Lösung der Korteweg-de-Vries-Gleichung: breite Kämme, schmale Täler.", "cn²( 2K/π · (θ + 0,45 s) | m = 0,85 )"],
  logspirale: ["Logarithmische Spirale", "Zwei Bänder entlang einer logarithmischen Spirale, nach oben langsamer drehend.", "φ(s) = 0,9 · ln(s + 0,08)"],
  phyllotaxis: ["Goldener Winkel", "Erhebungen im goldenen Winkel von 137,5° (Phyllotaxis).", "θₙ = n · 2π/φ²,  sₙ = (n + ½)/42"],
  super: ["Superformel", "Fünfzähliger Querschnitt nach der Superformel von Gielis.", "( |cos 5θ/4|^1,5 + |sin 5θ/4|^1,5 )^(−1/0,9)"],
  ketten: ["Kettenlinie", "Rotationssymmetrisches cosh-Profil mit Taille in der Mitte.", "cosh( (s − ½) / 0,62 )"],
  turing_flecken: ["Turing · Flecken", "Gray-Scott-Modell, Parameter für Flecken.", "∂v/∂t = Dᵥ Δv + u v² − (F + k) v,  F = 0,0367,  k = 0,0649"],
  turing_labyrinth: ["Turing · Labyrinth", "Gray-Scott-Modell, Parameter für labyrinthartige Streifen.", "∂v/∂t = Dᵥ Δv + u v² − (F + k) v,  F = 0,029,  k = 0,057"],
  sinus: ["Sinus", "Zwei Ausbuchtungen, um 100° über die Höhe verdreht.", "½ + ½ cos 2(θ + 100° · s)"],
  spirale: ["Spirale", "Dreigängige Schraubenwelle.", "½ + ½ sin(2,5π s + 3θ)"],
  bluete: ["Blüte", "Fünf breite Segmente mit steilen Übergängen, ohne Verdrehung.", "sgn(c) |c|^0,45,  c = cos 5θ"],
  kaemme: ["Kämme", "Zwei breite Kämme, zwischen 32 % und 68 % der Höhe um 90° gedreht.", "cos 2(θ + 90° · S(s)),  Drehung zwischen 32 % und 68 %"],
  gleich: ["Klassisch", "Rotationssymmetrisch, eine Ausbauchung in halber Höhe.", "sin(π s)^1,15"],
};
const chips = document.getElementById("chips");
for (const opt of document.getElementById("formel").options) {
  const knopf = document.createElement("button");
  knopf.type = "button";
  knopf.dataset.formel = opt.value;
  knopf.textContent = FORMEN[opt.value][0].replace("Riemannsche ", "");
  knopf.addEventListener("click", () => {
    document.getElementById("formel").value = opt.value;
    document.getElementById("formel").dispatchEvent(new Event("input"));
  });
  chips.appendChild(knopf);
}
function formKopf(f) {
  document.getElementById("name").textContent = FORMEN[f][0];
  document.getElementById("idee").textContent = FORMEN[f][1];
  document.getElementById("formelzeile").textContent = FORMEN[f][2];
  for (const k of chips.children) k.setAttribute("aria-pressed", String(k.dataset.formel === f));
}

const canvas = document.getElementById("bild");
const gl = canvas.getContext("webgl", { antialias: true, alpha: true });
if (!gl) {
  document.getElementById("status").textContent = "WebGL fehlt in diesem Browser.";
  throw new Error("WebGL fehlt");
}

const vs = `
attribute vec3 aPos;
attribute vec3 aNrm;
attribute float aGrad;
uniform mat4 uMvp;
varying vec3 vN;
varying vec3 vPos;
varying float vGrad;
void main() {
  vPos = aPos;
  vN = aNrm;
  vGrad = aGrad;
  gl_Position = uMvp * vec4(aPos, 1.0);
}`;
const fs = `
precision mediump float;
varying vec3 vN;
varying vec3 vPos;
varying float vGrad;
uniform vec3 uEye;
uniform float uWarnung;
uniform float uStuetze;
void main() {
  vec3 n = normalize(vN);
  if (!gl_FrontFacing) n = -n;
  vec3 blick = normalize(uEye - vPos);
  vec3 licht = normalize(vec3(0.45, -0.55, 0.70));
  vec3 fuellung = normalize(vec3(-0.6, 0.35, 0.15));
  float diffus = max(dot(n, licht), 0.0);
  float weich = max(dot(n, fuellung), 0.0);
  float himmel = 0.5 + 0.5 * n.z;
  float glanz = pow(max(dot(n, normalize(licht + blick)), 0.0), 40.0);
  float rand = pow(1.0 - max(dot(n, blick), 0.0), 3.0);
  vec3 farbe = vec3(0.94, 0.91, 0.86);
  if (vGrad > uWarnung + 0.01) farbe = vec3(0.92, 0.57, 0.18);
  if (vGrad > uStuetze + 0.01) farbe = vec3(0.80, 0.21, 0.16);
  vec3 grund = gl_FrontFacing ? farbe : farbe * 0.82;
  vec3 umgebung = mix(vec3(0.42, 0.40, 0.38), vec3(0.62, 0.62, 0.64), himmel);
  vec3 farb = grund * (umgebung + 0.55 * diffus + 0.12 * weich) + vec3(glanz) * 0.10 + vec3(rand) * 0.08;
  gl_FragColor = vec4(farb, 1.0);
}`;
const linienVs = `
attribute vec3 aPos;
uniform mat4 uMvp;
void main() { gl_Position = uMvp * vec4(aPos, 1.0); }`;
const linienFs = `
precision mediump float;
uniform vec4 uFarbe;
void main() { gl_FragColor = uFarbe; }`;
const schattenVs = `
attribute vec3 aPos;
uniform mat4 uMvp;
uniform float uRadius;
varying vec2 vXY;
void main() { vXY = aPos.xy; gl_Position = uMvp * vec4(aPos.xy * uRadius, -0.3, 1.0); }`;
const schattenFs = `
precision mediump float;
varying vec2 vXY;
uniform float uStaerke;
void main() {
  float d = length(vXY);
  float a = uStaerke * (1.0 - smoothstep(0.55, 1.0, d));
  gl_FragColor = vec4(0.0, 0.0, 0.0, a);
}`;

function shader(typ, quelle) {
  const s = gl.createShader(typ);
  gl.shaderSource(s, quelle);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
  return s;
}
function programm(vertex, fragment) {
  const p = gl.createProgram();
  gl.attachShader(p, shader(gl.VERTEX_SHADER, vertex));
  gl.attachShader(p, shader(gl.FRAGMENT_SHADER, fragment));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  return p;
}
const material = programm(vs, fs);
const linienProgramm = programm(linienVs, linienFs);
const schattenProgramm = programm(schattenVs, schattenFs);
const dunkel = window.matchMedia("(prefers-color-scheme: dark)");

function puffer(ziel, werte, typ) {
  const p = gl.createBuffer();
  gl.bindBuffer(ziel, p);
  gl.bufferData(ziel, new typ(werte), gl.STATIC_DRAW);
  return p;
}
const TAU = Math.PI * 2;
function catmull(p0, p1, p2, p3, t) {
  const t2 = t * t, t3 = t2 * t;
  return 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3);
}
function normiert(x) { return 0.5 * (Math.max(-1, Math.min(1, x)) + 1); }
function huelle(s) {
  const glatt = (t) => { t = Math.min(1, Math.max(0, t)); return t * t * (3 - 2 * t); };
  return glatt(s / 0.16) * glatt((1 - s) / 0.16);
}
function formelAnteil(s, theta, funktion) {
  const rest = 0.158;
  const h = huelle(s);
  if (funktion === "sinus") {
    const w = 0.5 + 0.5 * Math.cos(2 * (theta + s * 100 * Math.PI / 180));
    return rest + (1 - rest) * h * w;
  }
  if (funktion === "spirale") {
    const w = 0.5 + 0.5 * Math.sin(2 * Math.PI * 1.25 * s + 3 * theta);
    return rest + (1 - rest) * h * w;
  }
  if (funktion === "bluete") {
    const c = Math.cos(5 * theta);
    const w = normiert(Math.sign(c) * Math.abs(c) ** 0.45);
    return rest + (1 - rest) * h * w;
  }
  if (funktion === "kaemme") {
    const t = Math.min(1, Math.max(0, (s - 0.32) / 0.36));
    const dreh = (t * t * (3 - 2 * t)) * 90 * Math.PI / 180;
    const c = Math.cos(2 * (theta + dreh));
    const w = normiert(Math.sign(c) * Math.abs(c) ** 0.55);
    return rest + (1 - rest) * h * w;
  }
  if (funktion === "cnoidal") return rest + (1 - rest) * h * cnoidal(s, theta);
  if (funktion === "logspirale") return rest + (1 - rest) * h * logspirale(s, theta);
  if (funktion === "phyllotaxis") return rest + (1 - rest) * h * (phyllotaxis(s, theta) / daten.phylloMax);
  if (funktion === "super") return rest + (1 - rest) * h * superformel(theta);
  if (funktion === "ketten") return rest + (1 - rest) * kettenlinie(s);
  if (funktion === "zeta") return rest + (1 - rest) * h * zetaform(s, theta);
  if (funktion.startsWith("turing_")) return rest + (1 - rest) * h * turing(s, theta, funktion.slice(7));
  return rest + (1 - rest) * Math.sin(Math.PI * s) ** 1.15;
}
function jacobiCn(u, m) {
  if (m <= 0) return Math.cos(u);
  if (m >= 1) return 1 / Math.cosh(u);
  const a = [1], b = [Math.sqrt(1 - m)], c = [Math.sqrt(m)];
  while (Math.abs(c[c.length - 1]) > 1e-14 && a.length < 32) {
    a.push(0.5 * (a[a.length - 1] + b[b.length - 1]));
    b.push(Math.sqrt(a[a.length - 2] * b[b.length - 1]));
    c.push(0.5 * (a[a.length - 2] - b[b.length - 2]));
  }
  const stufe = a.length - 1;
  let phi = (2 ** stufe) * a[stufe] * u;
  for (let i = stufe; i > 0; i--) {
    const sinus = Math.max(-1, Math.min(1, c[i] * Math.sin(phi) / a[i]));
    phi = 0.5 * (phi + Math.asin(sinus));
  }
  return Math.cos(phi);
}
function cnoidal(s, theta) {
  const wert = jacobiCn((2 * daten.cnoidalK / Math.PI) * (theta + 0.45 * s), daten.cnoidalM);
  return wert * wert;
}
function winkelAbstand(a, b) {
  let d = (a - b + Math.PI) % TAU;
  if (d < 0) d += TAU;
  return Math.abs(d - Math.PI);
}
function logspirale(s, theta) {
  const winkel = 0.9 * Math.log(s + 0.08);
  const nahe = Math.min(winkelAbstand(theta, winkel), winkelAbstand(theta, winkel + Math.PI));
  return Math.exp(-0.5 * (nahe / 0.42) ** 2);
}
function phyllotaxis(s, theta) {
  const gold = TAU / ((1 + Math.sqrt(5)) / 2) ** 2;
  const sigmaS = 0.030, sigmaT = 0.22, anzahl = 42;
  let summe = 0;
  for (let n = 0; n < anzahl; n++) {
    const ds = (s - (n + 0.5) / anzahl) / sigmaS;
    const dt = winkelAbstand(theta, n * gold) / sigmaT;
    summe += Math.exp(-0.5 * (ds * ds + dt * dt));
  }
  return summe;
}
function superRho(theta) {
  const t = 5 * theta / 4;
  return (Math.abs(Math.cos(t)) ** 1.5 + Math.abs(Math.sin(t)) ** 1.5) ** (-1 / 0.9);
}
function superformel(theta) {
  return (superRho(theta) - daten.superMin) / (daten.superMax - daten.superMin);
}
function kettenlinie(s) {
  const rand = Math.cosh(0.5 / daten.kettenA);
  return (Math.cosh((s - 0.5) / daten.kettenA) - 1) / (rand - 1);
}
const BERNOULLI = [1 / 6, -1 / 30, 1 / 42, -1 / 30, 5 / 66, -691 / 2730, 7 / 6];
function cmul(a, b) { return [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]]; }
function cdiv(a, b) {
  const n = b[0] * b[0] + b[1] * b[1];
  return [(a[0] * b[0] + a[1] * b[1]) / n, (a[1] * b[0] - a[0] * b[1]) / n];
}
function cpot(k, s) {
  // k^s für reelles k > 0
  const l = Math.log(k), r = Math.exp(s[0] * l);
  return [r * Math.cos(s[1] * l), r * Math.sin(s[1] * l)];
}
function zeta(s) {
  const n = 24;
  let summe = [0, 0];
  for (let k = 1; k < n; k++) {
    const w = cpot(k, [-s[0], -s[1]]);
    summe = [summe[0] + w[0], summe[1] + w[1]];
  }
  const ende = cdiv(cpot(n, [1 - s[0], -s[1]]), [s[0] - 1, s[1]]);
  const halb = cpot(n, [-s[0], -s[1]]);
  summe = [summe[0] + ende[0] + 0.5 * halb[0], summe[1] + ende[1] + 0.5 * halb[1]];
  let faktor = cmul(s, cpot(n, [-s[0] - 1, -s[1]]));
  let fakultaet = 2;
  for (let k = 1; k <= BERNOULLI.length; k++) {
    const b = BERNOULLI[k - 1] / fakultaet;
    summe = [summe[0] + b * faktor[0], summe[1] + b * faktor[1]];
    const m = cmul([s[0] + 2 * k - 1, s[1]], [s[0] + 2 * k, s[1]]);
    faktor = cmul(faktor, [m[0] / (n * n), m[1] / (n * n)]);
    fakultaet *= (2 * k + 1) * (2 * k + 2);
  }
  return summe;
}
function zetaform(s, theta) {
  const w = zeta([0.5 + 0.45 * Math.cos(theta), 12 + 24 * s + 2.5 * Math.sin(theta)]);
  return Math.min(1, Math.hypot(w[0], w[1]) / daten.zetaMax);
}
function turing(s, theta, name) {
  const tafel = daten.turing[name], zeilen = tafel.length, breite = tafel[0].length;
  const lage = Math.min(1, Math.max(0, s)) * (zeilen - 1);
  const unten = Math.min(zeilen - 2, Math.floor(lage)), bruch = lage - unten;
  let spalte = (theta % TAU) / TAU * breite;
  if (spalte < 0) spalte += breite;
  const links = Math.floor(spalte) % breite, rechts = (links + 1) % breite, kante = spalte - Math.floor(spalte);
  const zeile = (i) => {
    const reihe = tafel[Math.max(0, Math.min(zeilen - 1, i))];
    return reihe[links] * (1 - kante) + reihe[rechts] * kante;
  };
  const wert = catmull(zeile(unten - 1), zeile(unten), zeile(unten + 1), zeile(unten + 2), bruch);
  return Math.min(1, Math.max(0, wert));
}
function laengenanteil(z, theta, p) {
  const s = z / p.hoehe;
  return formelAnteil(s, theta, p.funktion);
}
function netzAus(p) {
  const positionen = [], dreiecke = [];
  const hinzu = (x, y, z) => { positionen.push(x, y, z); return positionen.length / 3 - 1; };
  const kern = p.innendurchmesser / 2 + daten.wand;
  const halb = daten.dicke / 2;
  const n = daten.lamellen;
  const zs = [];
  for (let i = 0; i < daten.schnitte; i++) zs.push(p.hoehe * i / (daten.schnitte - 1));
  // Spitzenradius je Schnitt und Lamelle, wahlweise auf den Grenzwinkel begrenzt.
  const radien = zs.map((z) => {
    const reihe = [];
    for (let i = 0; i < n; i++) reihe.push(kern + p.lamelleMax * laengenanteil(z, TAU * i / n, p));
    return reihe;
  });
  if (p.begrenzen) {
    const steigung = Math.tan(daten.begrenzungGrad * Math.PI / 180);
    for (let k = 1; k < zs.length; k++) {
      const erlaubt = steigung * (zs[k] - zs[k - 1]);
      for (let i = 0; i < n; i++) radien[k][i] = Math.min(radien[k][i], radien[k - 1][i] + erlaubt);
    }
  }
  // Überhang der Spitze zwischen zwei Schnitten, Grad zur Senkrechten.
  const winkel = [];
  for (let k = 0; k < zs.length - 1; k++) {
    winkel.push(radien[k].map((r, i) => Math.atan2(Math.max(0, radien[k + 1][i] - r), zs[k + 1] - zs[k]) * 180 / Math.PI));
  }
  const polygon = (k) => {
    const ecken = [];
    for (let i = 0; i < n; i++) {
      const theta = TAU * i / n;
      const cos = Math.cos(theta), sin = Math.sin(theta);
      const tx = -sin, ty = cos;
      const spitze = radien[k][i];
      const kappe = Math.min(halb, Math.max(0, spitze - kern));
      const innenVor = [kern * cos - kappe * tx, kern * sin - kappe * ty, -1];
      const innenNach = [kern * cos + kappe * tx, kern * sin + kappe * ty, -1];
      const mitteR = Math.max(kern, spitze - kappe);
      const mitte = [mitteR * cos, mitteR * sin];
      const bogen = [];
      for (let k = 0; k <= 8; k++) {
        const phi = theta - Math.PI / 2 + k / 8 * Math.PI;
        bogen.push([mitte[0] + kappe * Math.cos(phi), mitte[1] + kappe * Math.sin(phi), i]);
      }
      ecken.push([innenVor, bogen, innenNach]);
    }
    const punkte = [];
    for (let i = 0; i < n; i++) {
      const vorher = ecken[(i - 1 + n) % n][2];
      const eintritt = ecken[i][0];
      let w0 = Math.atan2(vorher[1], vorher[0]);
      let w1 = Math.atan2(eintritt[1], eintritt[0]);
      let delta = (w1 - w0) % TAU; if (delta < 0) delta += TAU;
      for (let schritt = 1; schritt <= daten.bogen; schritt++) {
        const w = w0 + delta * schritt / (daten.bogen + 1);
        punkte.push([kern * Math.cos(w), kern * Math.sin(w), -1]);
      }
      punkte.push(eintritt, ...ecken[i][1], ecken[i][2]);
    }
    return punkte;
  };
  const innenZ = [daten.boden].concat(zs.filter((z) => z > daten.boden + 1e-6));
  if (Math.abs(innenZ[innenZ.length - 1] - p.hoehe) > 1e-6) innenZ.push(p.hoehe);
  const innenTeil = Math.max(n * 2, 180);
  const grad = [];
  const aussen = zs.map((z, k) => polygon(k).map(([x, y, i]) => {
    const id = hinzu(x, y, z);
    // Ecke der Spitze: der steilere der beiden angrenzenden Abschnitte.
    grad[id] = i < 0 ? 0 : Math.max(k > 0 ? winkel[k - 1][i] : 0, k < winkel.length ? winkel[k][i] : 0);
    return id;
  }));
  let ueberhangMax = 0, stuetze = 0, warnung = 0;
  for (const reihe of winkel) for (const w of reihe) {
    ueberhangMax = Math.max(ueberhangMax, w);
    if (w > daten.stuetzeGrad + 1e-6) stuetze++;
    else if (w > daten.warnungGrad + 1e-6) warnung++;
  }
  const innenR = (z) => {
    const laenge = Math.min(30, p.hoehe - daten.boden);
    if (z <= p.hoehe - laenge) return p.innendurchmesser / 2;
    const t = (z - (p.hoehe - laenge)) / laenge;
    const s = t * t * (3 - 2 * t);
    return p.innendurchmesser / 2 + daten.muendung_zugabe * s;
  };
  const innen = innenZ.map((z) => {
    const r = innenR(z);
    const ring = [];
    for (let i = 0; i < innenTeil; i++) ring.push(hinzu(r * Math.cos(TAU * i / innenTeil), r * Math.sin(TAU * i / innenTeil), z));
    return ring;
  });
  const wand = (ringe, aussenwärts) => {
    for (let e = 0; e < ringe.length - 1; e++) {
      const unten = ringe[e], oben = ringe[e + 1], m = unten.length;
      for (let i = 0; i < m; i++) {
        const j = (i + 1) % m;
        const a = unten[i], b = unten[j], c = oben[i], d = oben[j];
        if (aussenwärts) { dreiecke.push(a, b, d, a, d, c); }
        else { dreiecke.push(a, c, d, a, d, b); }
      }
    }
  };
  wand(aussen, true);
  wand(innen, false);
  const mitteBoden = hinzu(0, 0, 0);
  for (let i = 0; i < aussen[0].length; i++) dreiecke.push(mitteBoden, aussen[0][(i + 1) % aussen[0].length], aussen[0][i]);
  const mitteInnen = hinzu(0, 0, daten.boden);
  for (let i = 0; i < innenTeil; i++) dreiecke.push(mitteInnen, innen[0][i], innen[0][(i + 1) % innenTeil]);
  const oben = aussen[aussen.length - 1], innenOben = innen[innen.length - 1];
  for (let i = 0; i < oben.length; i++) {
    const j = (i + 1) % oben.length;
    const ax = positionen[oben[i] * 3], ay = positionen[oben[i] * 3 + 1];
    const bx = positionen[oben[j] * 3], by = positionen[oben[j] * 3 + 1];
    const ia = Math.round((((Math.atan2(ay, ax) % TAU) + TAU) % TAU) / TAU * innenTeil) % innenTeil;
    const ib = Math.round((((Math.atan2(by, bx) % TAU) + TAU) % TAU) / TAU * innenTeil) % innenTeil;
    dreiecke.push(oben[i], oben[j], innenOben[ib]);
    let cursor = ib;
    while (cursor !== ia) {
      const zurueck = (cursor - 1 + innenTeil) % innenTeil;
      dreiecke.push(oben[i], innenOben[cursor], innenOben[zurueck]);
      cursor = zurueck;
    }
  }
  const normalen = new Array(positionen.length).fill(0);
  for (let t = 0; t < dreiecke.length; t += 3) {
    const a = dreiecke[t], b = dreiecke[t + 1], c = dreiecke[t + 2];
    const ax = positionen[a*3], ay = positionen[a*3+1], az = positionen[a*3+2];
    const bx = positionen[b*3]-ax, by = positionen[b*3+1]-ay, bz = positionen[b*3+2]-az;
    const cx = positionen[c*3]-ax, cy = positionen[c*3+1]-ay, cz = positionen[c*3+2]-az;
    const nx = by*cz-bz*cy, ny = bz*cx-bx*cz, nz = bx*cy-by*cx;
    for (const k of [a, b, c]) { normalen[k*3]+=nx; normalen[k*3+1]+=ny; normalen[k*3+2]+=nz; }
  }
  for (let i = 0; i < normalen.length; i += 3) {
    const g = Math.hypot(normalen[i], normalen[i+1], normalen[i+2]) || 1;
    normalen[i]/=g; normalen[i+1]/=g; normalen[i+2]/=g;
  }
  let radius = 0;
  for (let i = 0; i < positionen.length; i += 3) radius = Math.max(radius, Math.hypot(positionen[i], positionen[i+1]));
  const grade = new Float32Array(positionen.length / 3);
  for (let i = 0; i < grade.length; i++) grade[i] = grad[i] || 0;
  return { positionen, normalen, dreiecke, radius, grade, ueberhangMax, stuetze, warnung };
}
let netz = null, pos, nrm, grd, idx, anzahl = 0, indexTyp = gl.UNSIGNED_SHORT, indexKlasse = Uint16Array;
if (gl.getExtension("OES_element_index_uint")) { indexTyp = gl.UNSIGNED_INT; indexKlasse = Uint32Array; }
const lin = puffer(gl.ARRAY_BUFFER, daten.linien, Float32Array);
const linienAnzahl = daten.linien.length / 3;
const boden = puffer(gl.ARRAY_BUFFER, [-1, -1, 0, 1, -1, 0, -1, 1, 0, 1, 1, 0], Float32Array);
function zeige(p) {
  netz = netzAus(p);
  pos = puffer(gl.ARRAY_BUFFER, netz.positionen, Float32Array);
  nrm = puffer(gl.ARRAY_BUFFER, netz.normalen, Float32Array);
  grd = puffer(gl.ARRAY_BUFFER, netz.grade, Float32Array);
  idx = puffer(gl.ELEMENT_ARRAY_BUFFER, netz.dreiecke, indexKlasse);
  anzahl = netz.dreiecke.length;
  const durchmesser = 2 * netz.radius;
  const passt = p.hoehe <= daten.grenzeHoehe && durchmesser <= daten.grenzeDurchmesser;
  const zahl = (x, n) => x.toFixed(n).replace(".", ",");
  formKopf(p.funktion);
  document.getElementById("oD").textContent = zahl(p.innendurchmesser, 0) + " mm";
  document.getElementById("oH").textContent = zahl(p.hoehe, 0) + " mm";
  document.getElementById("oL").textContent = zahl(p.lamelleMax, 1) + " mm";
  document.getElementById("wD").textContent = zahl(durchmesser, 0) + " mm";
  document.getElementById("wU").textContent = zahl(netz.ueberhangMax, 0) + "°";
  document.getElementById("wPunkt").className = "punkt" + (netz.stuetze ? " rot" : netz.warnung ? " warn" : "");
  document.getElementById("wP").textContent = passt ? "passt" : "zu groß";
  document.getElementById("wP").style.color = passt ? "" : "var(--rot)";
  document.getElementById("status").textContent =
    daten.lamellen + " Lamellen · " + zahl(daten.dicke, 1) + " mm · Kernwand " + zahl(daten.wand, 0) + " mm";
  const ueber = document.getElementById("ueberhang");
  ueber.className = netz.stuetze ? "rot" : "";
  ueber.textContent = netz.stuetze
    ? netz.stuetze + " Abschnitte über " + daten.stuetzeGrad + "° brauchen Stützen. Begrenzung einschalten oder Lamellen kürzen."
    : netz.warnung
      ? "Ohne Stützen druckbar. " + netz.warnung + " Abschnitte über " + daten.warnungGrad + "° können hängen."
      : "Ohne Stützen druckbar.";
}
function parameter() {
  return {
    innendurchmesser: Number(document.getElementById("d").value),
    hoehe: Number(document.getElementById("h").value),
    lamelleMax: Number(document.getElementById("l").value),
    funktion: document.getElementById("formel").value,
    begrenzen: document.getElementById("begrenzen").checked,
  };
}
let geplant = false;
function planen() {
  if (geplant) return;
  geplant = true;
  requestAnimationFrame(() => { geplant = false; zeige(parameter()); });
}
zeige(parameter());
for (const id of ["d", "h", "l", "formel"]) document.getElementById(id).addEventListener("input", planen);
document.getElementById("begrenzen").addEventListener("change", planen);
document.getElementById("zurueck").addEventListener("click", () => {
  document.getElementById("d").value = daten.start.innendurchmesser;
  document.getElementById("h").value = daten.start.hoehe;
  document.getElementById("l").value = daten.start.lamelleMax;
  document.getElementById("formel").value = daten.start.funktion;
  document.getElementById("begrenzen").checked = daten.start.begrenzen;
  zeige(parameter());
});
function stlSpeichern() {
  const p = netz.positionen;
  const dreiecke = netz.dreiecke;
  const n = dreiecke.length / 3;
  const puff = new ArrayBuffer(84 + n * 50);
  const sicht = new DataView(puff);
  const kopf = new TextEncoder().encode("Vase, mm. (c) 2026 Axel Schmidt, CC BY-NC-SA 4.0, axel@schmidtlab.net");
  new Uint8Array(puff, 0, 80).set(kopf);
  sicht.setUint32(80, n, true);
  let o = 84;
  for (let i = 0; i < n; i++) {
    const a = dreiecke[i * 3], b = dreiecke[i * 3 + 1], c = dreiecke[i * 3 + 2];
    const ax = p[a * 3], ay = p[a * 3 + 1], az = p[a * 3 + 2];
    const bx = p[b * 3] - ax, by = p[b * 3 + 1] - ay, bz = p[b * 3 + 2] - az;
    const cx = p[c * 3] - ax, cy = p[c * 3 + 1] - ay, cz = p[c * 3 + 2] - az;
    let nx = by * cz - bz * cy, ny = bz * cx - bx * cz, nz = bx * cy - by * cx;
    const laenge = Math.hypot(nx, ny, nz) || 1;
    sicht.setFloat32(o, nx / laenge, true); o += 4;
    sicht.setFloat32(o, ny / laenge, true); o += 4;
    sicht.setFloat32(o, nz / laenge, true); o += 4;
    for (const wert of [ax, ay, az, ax + bx, ay + by, az + bz, ax + cx, ay + cy, az + cz]) {
      sicht.setFloat32(o, wert, true); o += 4;
    }
    sicht.setUint16(o, 0, true); o += 2;
  }
  const par = parameter();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([puff], { type: "model/stl" }));
  link.download = "vase-" + par.funktion + "-" + par.hoehe + "h-" + par.innendurchmesser + "d.stl";
  link.click();
  URL.revokeObjectURL(link.href);
}
document.getElementById("stl").addEventListener("click", stlSpeichern);

let yaw = 0.7, pitch = 0.22, dist = daten.start.hoehe * 2.15;
let ziehen = false, letzteX = 0, letzteY = 0, dreht = true, letzteZeit = 0;
const finger = new Map();
let fingerAbstand = 0;
const drehKnopf = document.getElementById("drehen");
function drehenSetzen(an) { dreht = an; drehKnopf.setAttribute("aria-pressed", String(an)); }
drehKnopf.addEventListener("click", () => drehenSetzen(!dreht));
function zoomen(faktor) {
  dist = Math.max(parameter().hoehe * 0.4, Math.min(daten.grenzeHoehe * 4, dist * faktor));
}
canvas.addEventListener("pointerdown", (e) => {
  finger.set(e.pointerId, [e.clientX, e.clientY]);
  ziehen = finger.size === 1; letzteX = e.clientX; letzteY = e.clientY;
  if (finger.size === 2) { const [a, b] = [...finger.values()]; fingerAbstand = Math.hypot(a[0] - b[0], a[1] - b[1]); }
  drehenSetzen(false);
  try { canvas.setPointerCapture(e.pointerId); } catch (err) {}
});
const loslassen = (e) => { finger.delete(e.pointerId); ziehen = false; };
canvas.addEventListener("pointerup", loslassen);
canvas.addEventListener("pointercancel", loslassen);
canvas.addEventListener("pointermove", (e) => {
  if (!finger.has(e.pointerId)) return;
  finger.set(e.pointerId, [e.clientX, e.clientY]);
  if (finger.size === 2) {
    const [a, b] = [...finger.values()];
    const abstand = Math.hypot(a[0] - b[0], a[1] - b[1]);
    if (fingerAbstand > 0) zoomen(fingerAbstand / abstand);
    fingerAbstand = abstand;
    return;
  }
  if (!ziehen) return;
  yaw += (e.clientX - letzteX) * 0.008;
  pitch += (e.clientY - letzteY) * 0.008;
  pitch = Math.max(-1.15, Math.min(1.15, pitch));
  letzteX = e.clientX; letzteY = e.clientY;
});
canvas.addEventListener("wheel", (e) => {
  e.preventDefault();
  zoomen(Math.exp(e.deltaY * 0.001));
}, { passive: false });

function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
function kreuz(a, b) {
  return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
}
function punkt(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
function normieren(v) {
  const l = Math.hypot(v[0], v[1], v[2]) || 1;
  return [v[0] / l, v[1] / l, v[2] / l];
}
function lookAt(auge, ziel) {
  const f = normieren(sub(ziel, auge));
  const s = normieren(kreuz(f, [0, 0, 1]));
  const u = kreuz(s, f);
  return new Float32Array([
    s[0], u[0], -f[0], 0,
    s[1], u[1], -f[1], 0,
    s[2], u[2], -f[2], 0,
    -punkt(s, auge), -punkt(u, auge), punkt(f, auge), 1
  ]);
}
function perspektive(grad, seiten, nah, fern) {
  const f = 1 / Math.tan(grad * Math.PI / 360);
  const nf = 1 / (nah - fern);
  return new Float32Array([
    f / seiten, 0, 0, 0,
    0, f, 0, 0,
    0, 0, (fern + nah) * nf, -1,
    0, 0, 2 * fern * nah * nf, 0
  ]);
}
function mal(a, b) {
  const c = new Float32Array(16);
  for (let spalte = 0; spalte < 4; spalte++) {
    for (let zeile = 0; zeile < 4; zeile++) {
      c[spalte * 4 + zeile] =
        a[zeile] * b[spalte * 4] +
        a[4 + zeile] * b[spalte * 4 + 1] +
        a[8 + zeile] * b[spalte * 4 + 2] +
        a[12 + zeile] * b[spalte * 4 + 3];
    }
  }
  return c;
}

function rahmen() {
  const dpr = window.devicePixelRatio || 1;
  const breite = canvas.clientWidth, hoehe = canvas.clientHeight;
  if (breite < 2 || hoehe < 2) { requestAnimationFrame(rahmen); return; }
  if (canvas.width !== Math.floor(breite * dpr) || canvas.height !== Math.floor(hoehe * dpr)) {
    canvas.width = Math.floor(breite * dpr);
    canvas.height = Math.floor(hoehe * dpr);
  }
  const jetzt = performance.now();
  if (dreht && letzteZeit) yaw += Math.min(50, jetzt - letzteZeit) * 0.00018;
  letzteZeit = jetzt;
  gl.viewport(0, 0, canvas.width, canvas.height);
  gl.clearColor(0, 0, 0, 0);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  gl.enable(gl.DEPTH_TEST);
  const ziel = [0, 0, parameter().hoehe * 0.48];
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  const auge = [
    ziel[0] + dist * cp * Math.sin(yaw),
    ziel[1] + dist * cp * Math.cos(yaw),
    ziel[2] + dist * sp
  ];
  const sicht = lookAt(auge, ziel);
  const proj = perspektive(36, canvas.width / canvas.height, dist * 0.02, dist * 20);
  const mvp = mal(proj, sicht);

  // Weicher Schatten auf dem Bett, vor der Vase und ohne Tiefe.
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  gl.depthMask(false);
  gl.useProgram(schattenProgramm);
  gl.uniformMatrix4fv(gl.getUniformLocation(schattenProgramm, "uMvp"), false, mvp);
  gl.uniform1f(gl.getUniformLocation(schattenProgramm, "uRadius"), netz.radius * 1.9);
  gl.uniform1f(gl.getUniformLocation(schattenProgramm, "uStaerke"), dunkel.matches ? 0.45 : 0.22);
  gl.bindBuffer(gl.ARRAY_BUFFER, boden);
  const sPos = gl.getAttribLocation(schattenProgramm, "aPos");
  gl.enableVertexAttribArray(sPos);
  gl.vertexAttribPointer(sPos, 3, gl.FLOAT, false, 0, 0);
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  gl.disableVertexAttribArray(sPos);
  gl.depthMask(true);
  gl.disable(gl.BLEND);

  gl.useProgram(material);
  gl.uniformMatrix4fv(gl.getUniformLocation(material, "uMvp"), false, mvp);
  gl.uniform3f(gl.getUniformLocation(material, "uEye"), auge[0], auge[1], auge[2]);
  gl.bindBuffer(gl.ARRAY_BUFFER, pos);
  const aPos = gl.getAttribLocation(material, "aPos");
  gl.enableVertexAttribArray(aPos);
  gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);
  gl.bindBuffer(gl.ARRAY_BUFFER, nrm);
  const aNrm = gl.getAttribLocation(material, "aNrm");
  gl.enableVertexAttribArray(aNrm);
  gl.vertexAttribPointer(aNrm, 3, gl.FLOAT, false, 0, 0);
  gl.bindBuffer(gl.ARRAY_BUFFER, grd);
  const aGrad = gl.getAttribLocation(material, "aGrad");
  gl.enableVertexAttribArray(aGrad);
  gl.vertexAttribPointer(aGrad, 1, gl.FLOAT, false, 0, 0);
  gl.uniform1f(gl.getUniformLocation(material, "uWarnung"), daten.warnungGrad);
  gl.uniform1f(gl.getUniformLocation(material, "uStuetze"), daten.stuetzeGrad);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idx);
  gl.drawElements(gl.TRIANGLES, anzahl, indexTyp, 0);
  gl.disableVertexAttribArray(aNrm);
  gl.disableVertexAttribArray(aGrad);

  gl.enable(gl.BLEND);
  gl.useProgram(linienProgramm);
  gl.uniformMatrix4fv(gl.getUniformLocation(linienProgramm, "uMvp"), false, mvp);
  const deckung = 0.28;
  const ton = dunkel.matches ? 0.75 : 0.35;
  gl.uniform4f(gl.getUniformLocation(linienProgramm, "uFarbe"), ton * deckung, ton * deckung, ton * deckung, deckung);
  gl.bindBuffer(gl.ARRAY_BUFFER, lin);
  const lPos = gl.getAttribLocation(linienProgramm, "aPos");
  gl.enableVertexAttribArray(lPos);
  gl.vertexAttribPointer(lPos, 3, gl.FLOAT, false, 0, 0);
  gl.drawArrays(gl.LINES, 0, linienAnzahl);
  gl.disable(gl.BLEND);
  requestAnimationFrame(rahmen);
}
requestAnimationFrame(rahmen);
</script>
</body>
</html>
"""


def erzeugen(config_pfad: Path) -> dict:
    daten = json.loads(config_pfad.read_text(encoding="utf-8"))
    vase = Vase.aus_config(daten)
    netz = koerper(vase)
    dicht, volumen = wasserdicht(netz)
    if not dicht:
        raise VaseFehler(["Das erzeugte Netz ist nicht geschlossen oder die Normalen zeigen nach innen."])
    info = massen(netz, vase)
    info["volumen_cm3"] = volumen / 1000.0
    info["warnung_grad"] = vase.warnung_grad
    info["stuetze_grad"] = vase.stuetze_grad
    if info["hoehe"] > vase.bett_z + 0.05 or info["durchmesser"] > info["durchmesser_grenze"] + 0.05:
        raise VaseFehler([
            f"Die Vase misst {info['durchmesser']:.1f} x {info['hoehe']:.1f} mm und passt nicht "
            f"in den nutzbaren H2D-Bauraum {info['durchmesser_grenze']:.0f} mm Durchmesser, "
            f"{info['hoehe_grenze']:.0f} mm Hoehe."
        ])
    ziel = config_pfad.parent
    stl_schreiben(ziel / "vase.stl", netz)
    vorschau_png(ziel / "vorschau.png", vase, netz, info)
    html_schreiben(ziel / "vorschau.html", vase, netz, info)
    info["wasserdicht"] = True
    return info


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Aufruf: python tools/vase_generator.py <config.json>")
    try:
        info = erzeugen(Path(sys.argv[1]))
    except VaseFehler as fehler:
        print(fehler)
        raise SystemExit(1)
    print(
        f"Hoehe {info['hoehe']:.1f} mm, Durchmesser {info['durchmesser']:.1f} mm, "
        f"Wand min {info['wand_min_gemessen']:.2f} mm, Volumen {info['volumen_cm3']:.0f} cm³"
    )
    print(
        f"H2D eine Duese, nutzbar {info['durchmesser_grenze']:.0f} mm Durchmesser, "
        f"{info['hoehe_grenze']:.0f} mm Hoehe. Druckbar."
    )
    print(f"Netz geschlossen, {info['dreiecke']} Dreiecke.")
    if info["ueberhang_stuetze"]:
        print(
            f"Ueberhang bis {info['ueberhang_max']:.0f} Grad. {info['ueberhang_stuetze']} Abschnitte der Lamellenkanten "
            f"liegen ueber {info['stuetze_grad']:.0f} Grad und brauchen Stuetzen."
        )
    elif info["ueberhang_warnung"]:
        print(
            f"Ueberhang bis {info['ueberhang_max']:.0f} Grad. Ohne Stuetzen druckbar, "
            f"{info['ueberhang_warnung']} Abschnitte ueber {info['warnung_grad']:.0f} Grad koennen haengen."
        )
    else:
        print(f"Ueberhang bis {info['ueberhang_max']:.0f} Grad. Ohne Stuetzen druckbar.")
    print("Geschrieben: vase.stl, vorschau.html, vorschau.png")


if __name__ == "__main__":
    main()
