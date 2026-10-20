#!/usr/bin/env python3
"""Erzeugt aus einer config.json das lokale Vasenmodell.

    python tools/vase_generator.py vase/config.json

Schreibt neben die Config eine STL fuer den Slicer, eine HTML-Datei mit
drehbarer 3D-Ansicht und eine technische Vorschau. Onshape wird nicht
aufgerufen.
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from vase_feature import (
    Vase, VaseFehler, aussen_polygon, aussen_radius, bett_linien, koerper, massen, wasserdicht,
    _CNOIDAL_M, _CNOIDAL_K, _PHYLLO_MAX, _SUPER_MIN, _SUPER_MAX, _KETTEN_A, _ZETA_MAX,
)


def stl_schreiben(pfad: Path, netz: dict) -> None:
    dreiecke = netz["dreiecke"]
    punkte = netz["positionen"]
    with pfad.open("wb") as datei:
        datei.write(b"Vase generiert, Einheiten mm".ljust(80, b"\0"))
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


def vorschau_png(pfad: Path, vase: Vase, info: dict) -> None:
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
    farben = [(20, 90, 160), (200, 90, 40), (30, 130, 80), (140, 50, 140)]
    schritte = 80
    for nummer, farbe in enumerate(farben):
        theta = nummer * 3.14159265 / 4
        kurve = []
        for i in range(schritte + 1):
            z = vase.hoehe * i / schritte
            radius = aussen_radius(z, theta, vase)
            kurve.append((sx(radius), sy(z)))
        stift.line(kurve, fill=farbe, width=2)
        kurve_links = [(sx(-aussen_radius(vase.hoehe * i / schritte, theta, vase)), sy(vase.hoehe * i / schritte)) for i in range(schritte + 1)]
        stift.line(kurve_links, fill=farbe, width=2)
    stift.line([(sx(vase.bohrung), sy(vase.boden)), (sx(vase.bohrung), sy(vase.hoehe)), (sx(-vase.bohrung), sy(vase.hoehe)), (sx(-vase.bohrung), sy(vase.boden)), (sx(vase.bohrung), sy(vase.boden))], fill=(150, 150, 150), width=2)
    stift.text((80, 710), "Grau: H2D-Bauraum und Bohrung. Farbe: vier Meridiane.", fill=(90, 90, 90))

    mitte_x, mitte_y, massstab = 860, 400, 280 / radius_achse
    stift.ellipse(
        [mitte_x - vase.bett_y * 0.5 * massstab, mitte_y - vase.bett_x * 0.5 * massstab,
         mitte_x + vase.bett_y * 0.5 * massstab, mitte_y + vase.bett_x * 0.5 * massstab],
        outline=(210, 206, 198),
    )
    z = vase.hoehe * 0.5
    kontur = aussen_polygon(z, vase)
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
    vorlage = json.loads((pfad.parent / "vorlage.json").read_text(encoding="utf-8"))
    daten = {
        "name": vase.name,
        "s": vorlage["s"],
        "f": vorlage["f"],
        "a": vorlage["a"],
        "b": vorlage["b"],
        "alpha": vorlage["alpha"],
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
    }
    roh = json.dumps(daten, separators=(",", ":")).replace("<", "\\u003c")
    pfad.write_text(_HTML.replace("__DATEN__", roh), encoding="utf-8")


_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Vase</title>
<style>
  html, body { margin: 0; height: 100%; background: #f4f1ea; font-family: Georgia, serif; }
  canvas { display: block; width: 100%; height: 100%; }
  #regler { position: fixed; left: 16px; top: 14px; width: 280px; color: #2a2a2a; line-height: 1.35;
    background: rgba(255,255,255,0.88); border-radius: 12px; padding: 12px 14px; }
  #regler label { display: block; margin: 8px 0 2px; font-size: 14px; }
  #regler input[type=range] { width: 100%; }
  #regler select, #regler button { width: 100%; margin-top: 8px; }
  #regler button { padding: 6px 8px; }
  #status { margin: 8px 0 0; font-size: 13px; color: #444; }
  #hinweis { position: fixed; left: 20px; bottom: 16px; color: #6d675f; font-size: 14px; }
</style>
</head>
<body>
<canvas id="bild"></canvas>
<div id="regler">
  <b id="titel"></b>
  <label>Innendurchmesser <output id="oD"></output> mm<input id="d" type="range" min="40" max="180" step="1"></label>
  <label>Hoehe <output id="oH"></output> mm<input id="h" type="range" min="80" max="320" step="1"></label>
  <label>Lamellenlaenge max <output id="oL"></output> mm<input id="l" type="range" min="4" max="70" step="0.1"></label>
  <label>Wellenformel
    <select id="formel">
      <option value="vorlage">Vorlage, gemessen</option>
      <option value="sinus">Sinus, zwei Loben</option>
      <option value="spirale">Spirale</option>
      <option value="bluete">Bluete, fuenf Blaetter</option>
      <option value="kaemme">Breite Kaemme</option>
      <option value="gleich">Gleich lang</option>
      <option value="cnoidal">Cnoidalwelle</option>
      <option value="logspirale">Logarithmische Spirale</option>
      <option value="phyllotaxis">Goldener Winkel</option>
      <option value="super">Superformel</option>
      <option value="ketten">Kettenlinie</option>
      <option value="zeta">Riemannsche Zetafunktion</option>
    </select>
  </label>
  <button id="zurueck" type="button">Vorlage</button>
  <button id="stl" type="button">STL speichern</button>
  <p id="status"></p>
</div>
<div id="hinweis">Ziehen dreht, Scrollen zoomt. Der Rahmen ist der Bauraum der H2D, eine Duese.</div>
<script id="daten" type="application/json">__DATEN__</script>
<script>
const daten = JSON.parse(document.getElementById("daten").textContent);
document.getElementById("titel").textContent = daten.name;
document.getElementById("d").value = daten.start.innendurchmesser;
document.getElementById("h").value = daten.start.hoehe;
document.getElementById("l").value = daten.start.lamelleMax;
document.getElementById("formel").value = daten.start.funktion;

const canvas = document.getElementById("bild");
const gl = canvas.getContext("webgl", { antialias: true });
if (!gl) {
  document.getElementById("status").textContent = "WebGL fehlt in diesem Browser.";
  throw new Error("WebGL fehlt");
}

const vs = `
attribute vec3 aPos;
attribute vec3 aNrm;
uniform mat4 uMvp;
varying vec3 vN;
varying vec3 vPos;
void main() {
  vPos = aPos;
  vN = aNrm;
  gl_Position = uMvp * vec4(aPos, 1.0);
}`;
const fs = `
precision mediump float;
varying vec3 vN;
varying vec3 vPos;
uniform vec3 uEye;
void main() {
  vec3 n = normalize(vN);
  vec3 licht = normalize(vec3(0.35, -0.45, 0.75));
  vec3 fuellung = normalize(vec3(-0.5, 0.2, 0.2));
  float diffus = max(dot(n, licht), 0.0);
  float weich = max(dot(n, fuellung), 0.0);
  vec3 blick = normalize(uEye - vPos);
  float glanz = pow(max(dot(n, normalize(licht + blick)), 0.0), 48.0);
  vec3 farbe = vec3(0.93, 0.89, 0.82);
  vec3 innen = vec3(0.78, 0.74, 0.68);
  vec3 grund = gl_FrontFacing ? farbe : innen;
  vec3 farb = grund * (0.46 + 0.5 * diffus + 0.16 * weich) + vec3(glanz) * 0.12;
  gl_FragColor = vec4(farb, 1.0);
}`;
const linienVs = `
attribute vec3 aPos;
uniform mat4 uMvp;
void main() { gl_Position = uMvp * vec4(aPos, 1.0); }`;
const linienFs = `
precision mediump float;
void main() { gl_FragColor = vec4(0.62, 0.58, 0.52, 1.0); }`;

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

function puffer(ziel, werte, typ) {
  const p = gl.createBuffer();
  gl.bindBuffer(ziel, p);
  gl.bufferData(ziel, new typ(werte), gl.STATIC_DRAW);
  return p;
}
const TAU = Math.PI * 2;
function stelle(s) {
  const achse = daten.s;
  s = Math.min(1, Math.max(0, s));
  let oben = 1;
  while (oben < achse.length - 1 && achse[oben] < s) oben++;
  const unten = oben - 1;
  const spanne = achse[oben] - achse[unten];
  return [unten, oben, spanne === 0 ? 0 : (s - achse[unten]) / spanne];
}
function lerpReihe(s, werte) {
  const [u, o, b] = stelle(s);
  return werte[u] * (1 - b) + werte[o] * b;
}
function reihe(index, theta) {
  const tafel = daten.f;
  index = Math.max(0, Math.min(tafel.length - 1, index));
  const n = tafel[0].length;
  const lage = ((theta % TAU) + TAU) % TAU / TAU * n;
  const links = Math.floor(lage) % n;
  const rechts = (links + 1) % n;
  const k = lage - Math.floor(lage);
  return tafel[index][links] * (1 - k) + tafel[index][rechts] * k;
}
function catmull(p0, p1, p2, p3, t) {
  const t2 = t * t, t3 = t2 * t;
  return 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3);
}
function anteilVorlage(s, theta) {
  const [u, o, b] = stelle(s);
  return Math.max(0, catmull(reihe(u - 1, theta), reihe(u, theta), reihe(o, theta), reihe(o + 1, theta), b));
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
  const w = zeta([0.5 + 0.45 * Math.cos(theta), 10 + 40 * s + 3 * Math.sin(theta)]);
  const log = Math.log(Math.max(Math.hypot(w[0], w[1]), 1e-12));
  return Math.min(1, Math.max(0, (log + 1) / (daten.zetaMax + 1)));
}
function laengenanteil(z, theta, p) {
  const s = z / p.hoehe;
  if (p.funktion === "vorlage") return anteilVorlage(s, theta);
  return formelAnteil(s, theta, p.funktion);
}
function netzAus(p) {
  const positionen = [], dreiecke = [];
  const hinzu = (x, y, z) => { positionen.push(x, y, z); return positionen.length / 3 - 1; };
  const kern = p.innendurchmesser / 2 + daten.wand;
  const halb = daten.dicke / 2;
  const n = daten.lamellen;
  const polygon = (z) => {
    const ecken = [];
    for (let i = 0; i < n; i++) {
      const theta = TAU * i / n;
      const cos = Math.cos(theta), sin = Math.sin(theta);
      const tx = -sin, ty = cos;
      const spitze = kern + p.lamelleMax * laengenanteil(z, theta, p);
      const kappe = Math.min(halb, Math.max(0, spitze - kern));
      const innenVor = [kern * cos - kappe * tx, kern * sin - kappe * ty];
      const innenNach = [kern * cos + kappe * tx, kern * sin + kappe * ty];
      const mitteR = Math.max(kern, spitze - kappe);
      const mitte = [mitteR * cos, mitteR * sin];
      const bogen = [];
      for (let k = 0; k <= 8; k++) {
        const phi = theta - Math.PI / 2 + k / 8 * Math.PI;
        bogen.push([mitte[0] + kappe * Math.cos(phi), mitte[1] + kappe * Math.sin(phi)]);
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
        punkte.push([kern * Math.cos(w), kern * Math.sin(w)]);
      }
      punkte.push(eintritt, ...ecken[i][1], ecken[i][2]);
    }
    return punkte;
  };
  const zs = [];
  for (let i = 0; i < daten.schnitte; i++) zs.push(p.hoehe * i / (daten.schnitte - 1));
  const innenZ = [daten.boden].concat(zs.filter((z) => z > daten.boden + 1e-6));
  if (Math.abs(innenZ[innenZ.length - 1] - p.hoehe) > 1e-6) innenZ.push(p.hoehe);
  const innenTeil = Math.max(n * 2, 180);
  const aussen = zs.map((z) => polygon(z).map(([x, y]) => hinzu(x, y, z)));
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
  return { positionen, normalen, dreiecke, radius };
}
let netz = null, pos, nrm, idx, anzahl = 0, indexTyp = gl.UNSIGNED_SHORT, indexKlasse = Uint16Array;
if (gl.getExtension("OES_element_index_uint")) { indexTyp = gl.UNSIGNED_INT; indexKlasse = Uint32Array; }
const lin = puffer(gl.ARRAY_BUFFER, daten.linien, Float32Array);
const linienAnzahl = daten.linien.length / 3;
function zeige(p) {
  netz = netzAus(p);
  pos = puffer(gl.ARRAY_BUFFER, netz.positionen, Float32Array);
  nrm = puffer(gl.ARRAY_BUFFER, netz.normalen, Float32Array);
  idx = puffer(gl.ELEMENT_ARRAY_BUFFER, netz.dreiecke, indexKlasse);
  anzahl = netz.dreiecke.length;
  const durchmesser = 2 * netz.radius;
  const passt = p.hoehe <= daten.grenzeHoehe && durchmesser <= daten.grenzeDurchmesser;
  document.getElementById("oD").textContent = p.innendurchmesser.toFixed(0);
  document.getElementById("oH").textContent = p.hoehe.toFixed(0);
  document.getElementById("oL").textContent = p.lamelleMax.toFixed(1);
  document.getElementById("status").textContent =
    daten.lamellen + " Lamellen, " + daten.dicke + " mm, Kernwand " + daten.wand
    + " mm. Aussendurchmesser " + durchmesser.toFixed(0) + " mm. "
    + (passt ? "Passt auf den H2D." : "Groesser als der H2D.");
}
function parameter() {
  return {
    innendurchmesser: Number(document.getElementById("d").value),
    hoehe: Number(document.getElementById("h").value),
    lamelleMax: Number(document.getElementById("l").value),
    funktion: document.getElementById("formel").value,
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
document.getElementById("zurueck").addEventListener("click", () => {
  document.getElementById("d").value = daten.start.innendurchmesser;
  document.getElementById("h").value = daten.start.hoehe;
  document.getElementById("l").value = daten.start.lamelleMax;
  document.getElementById("formel").value = "vorlage";
  zeige(parameter());
});
function stlSpeichern() {
  const p = netz.positionen;
  const dreiecke = netz.dreiecke;
  const n = dreiecke.length / 3;
  const puff = new ArrayBuffer(84 + n * 50);
  const sicht = new DataView(puff);
  const kopf = new TextEncoder().encode("vase mm");
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
let ziehen = false, letzteX = 0, letzteY = 0;
canvas.addEventListener("pointerdown", (e) => {
  ziehen = true; letzteX = e.clientX; letzteY = e.clientY;
  try { canvas.setPointerCapture(e.pointerId); } catch (err) {}
});
canvas.addEventListener("pointerup", () => { ziehen = false; });
canvas.addEventListener("pointermove", (e) => {
  if (!ziehen) return;
  yaw += (e.clientX - letzteX) * 0.008;
  pitch += (e.clientY - letzteY) * 0.008;
  pitch = Math.max(-1.15, Math.min(1.15, pitch));
  letzteX = e.clientX; letzteY = e.clientY;
});
canvas.addEventListener("wheel", (e) => {
  e.preventDefault();
  dist *= Math.exp(e.deltaY * 0.001);
  dist = Math.max(parameter().hoehe * 0.4, Math.min(daten.grenzeHoehe * 4, dist));
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
  gl.viewport(0, 0, canvas.width, canvas.height);
  gl.clearColor(0.957, 0.945, 0.918, 1);
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
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idx);
  gl.drawElements(gl.TRIANGLES, anzahl, indexTyp, 0);

  gl.useProgram(linienProgramm);
  gl.uniformMatrix4fv(gl.getUniformLocation(linienProgramm, "uMvp"), false, mvp);
  gl.bindBuffer(gl.ARRAY_BUFFER, lin);
  const lPos = gl.getAttribLocation(linienProgramm, "aPos");
  gl.enableVertexAttribArray(lPos);
  gl.vertexAttribPointer(lPos, 3, gl.FLOAT, false, 0, 0);
  gl.drawArrays(gl.LINES, 0, linienAnzahl);
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
    if info["hoehe"] > vase.bett_z + 0.05 or info["durchmesser"] > info["durchmesser_grenze"] + 0.05:
        raise VaseFehler([
            f"Die Vase misst {info['durchmesser']:.1f} x {info['hoehe']:.1f} mm und passt nicht "
            f"in den nutzbaren H2D-Bauraum {info['durchmesser_grenze']:.0f} mm Durchmesser, "
            f"{info['hoehe_grenze']:.0f} mm Hoehe."
        ])
    ziel = config_pfad.parent
    stl_schreiben(ziel / "vase.stl", netz)
    vorschau_png(ziel / "vorschau.png", vase, info)
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
    print("Geschrieben: vase.stl, vorschau.html, vorschau.png")


if __name__ == "__main__":
    main()
