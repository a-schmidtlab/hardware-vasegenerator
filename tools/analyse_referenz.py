#!/usr/bin/env python3
"""Misst die Referenzvase und schreibt docs/analyse-referenz.png.

Die STL wird als Dreiecksnetz gelesen. Aussen- und Innenfläche werden über
die radiale Normale getrennt. Ausgabe sind die Kennzahlen, auf denen
vase/config.json beruht.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
STL = ROOT / "references" / "referenz.stl"
BILD = ROOT / "docs" / "analyse-referenz.png"

# Schwerpunkt der Grundfläche, aus der ersten Messung. Liegt nicht im Ursprung.
CX, CY = 175.00032, 159.99859


def dreiecke(pfad):
    dtype = np.dtype([
        ("n", "<f4", (3,)),
        ("v", "<f4", (3, 3)),
        ("attr", "<u2"),
    ])
    return np.memmap(pfad, dtype=dtype, mode="r", offset=84)


def flaechen(mm, step=3):
    n = mm["n"][::step].astype(np.float64)
    c = mm["v"][::step].mean(axis=1).astype(np.float64)
    x = c[:, 0] - CX
    y = c[:, 1] - CY
    z = c[:, 2]
    r = np.hypot(x, y)
    ux = x / np.maximum(r, 1e-6)
    uy = y / np.maximum(r, 1e-6)
    nr = n[:, 0] * ux + n[:, 1] * uy
    th = np.arctan2(y, x)
    return r, z, th, nr


def meridian(r, z, th, mask, th0, nb_z=100, dth=np.deg2rad(3.5)):
    d = np.arctan2(np.sin(th - th0), np.cos(th - th0))
    m = mask & (np.abs(d) < dth)
    kanten = np.linspace(0, 250, nb_z + 1)
    mitte = 0.5 * (kanten[:-1] + kanten[1:])
    rs = np.full(nb_z, np.nan)
    for i in range(nb_z):
        sel = m & (z >= kanten[i]) & (z < kanten[i + 1])
        if np.count_nonzero(sel) > 4:
            rs[i] = np.percentile(r[sel], 90)
    gut = np.isfinite(rs)
    rs = np.interp(np.arange(nb_z), np.flatnonzero(gut), rs[gut])
    return mitte, rs


def main():
    mm = dreiecke(STL)
    r, z, th, nr = flaechen(mm)
    aussen = (nr > 0.55) & (r > 56)
    kamm = np.deg2rad(97.5)
    winkel = [0, 45, 90, 135]
    profile = [meridian(r, z, th, aussen, kamm + np.deg2rad(a)) for a in winkel]

    print(f"Dreiecke: {len(mm)}")
    print(f"Hoehe: {z.min():.1f} .. {z.max():.1f} mm")
    print(f"Aussenradius max: {r[aussen].max():.1f} mm")
    innen = nr < -0.5
    print(f"Bohrung Radius Median: {np.median(r[innen]):.1f} mm")

    zeichne(profile)
    print(f"Bild: {BILD}")


def zeichne(profile):
    breite, hoehe = 1400, 900
    bild = Image.new("RGB", (breite, hoehe), (250, 248, 242))
    stift = ImageDraw.Draw(bild)

    def rahmen(x0, y0, x1, y1, titel):
        stift.rounded_rectangle([x0, y0, x1, y1], radius=12, fill=(255, 255, 255), outline=(220, 214, 204))
        stift.text((x0 + 16, y0 + 12), titel, fill=(40, 40, 40))

    rahmen(24, 24, 700, 860, "Seitenansicht, vier Meridiane")
    links, oben, rechts, unten = 70, 78, 670, 820

    def sx(radius):
        return links + (radius + 90) / 180 * (rechts - links)

    def sy(hoehe_mm):
        return unten - hoehe_mm / 250 * (unten - oben)

    stift.line([(sx(0), oben), (sx(0), unten)], fill=(220, 220, 220))
    stift.line([(sx(-90), sy(0)), (sx(90), sy(0))], fill=(180, 180, 180))
    farben = [(20, 90, 160), (200, 90, 40), (30, 130, 80), (140, 50, 140)]
    namen = ["Kamm, 0 Grad", "45 Grad", "90 Grad", "135 Grad"]
    for (_, rs), farbe in zip(profile, farben):
        stift.line([(sx(rv), sy(zv)) for zv, rv in zip(profile[0][0], rs)], fill=farbe, width=2)
        stift.line([(sx(-rv), sy(zv)) for zv, rv in zip(profile[0][0], rs)], fill=farbe, width=2)
    stift.line(
        [(sx(51), sy(2)), (sx(51), sy(248)), (sx(-51), sy(248)), (sx(-51), sy(2))],
        fill=(160, 160, 160),
        width=2,
    )
    stift.text((sx(6), sy(140)), "Bohrung r = 51", fill=(120, 120, 120))
    y = 78
    for name, farbe in zip(namen, farben):
        stift.rectangle([520, y, 540, y + 10], fill=farbe)
        stift.text((546, y - 2), name, fill=(40, 40, 40))
        y += 18

    rahmen(720, 24, 1376, 860, "Querschnitte der Aussenflaeche")
    mm = dreiecke(STL)
    r, z, th, nr = flaechen(mm, step=2)
    aussen = (nr > 0.55) & (r > 56)
    for (cx, cy), zs in zip([(880, 240), (1220, 240), (880, 630), (1220, 630)], [50, 110, 160, 210]):
        m = aussen & (np.abs(z - zs) < 2.5)
        nb = 90
        mx = np.full(nb, -1.0)
        ti = np.clip(((th[m] + np.pi) / (2 * np.pi) * nb).astype(int), 0, nb - 1)
        np.maximum.at(mx, ti, r[m])
        gut = mx > 0
        mx = np.interp(np.arange(nb), np.flatnonzero(gut), mx[gut])
        massstab = 2.15
        punkte = []
        for i, rv in enumerate(mx):
            a = -np.pi + (i + 0.5) / nb * 2 * np.pi
            punkte.append((cx + rv * np.cos(a) * massstab, cy - rv * np.sin(a) * massstab))
        punkte.append(punkte[0])
        stift.line(punkte, fill=(20, 90, 160), width=2)
        bohr = 51 * massstab
        stift.ellipse([cx - bohr, cy - bohr, cx + bohr, cy + bohr], outline=(170, 170, 170), width=2)
        stift.text((cx - 46, cy + 108), f"z = {zs} mm", fill=(40, 40, 40))

    stift.text((40, 872), "Referenz. Grau ist die zylindrische Bohrung.", fill=(80, 80, 80))
    BILD.parent.mkdir(parents=True, exist_ok=True)
    bild.save(BILD)


if __name__ == "__main__":
    main()
