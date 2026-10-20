#!/usr/bin/env python3
"""Schreibt vase/turing.json: Gray-Scott-Muster für die Formeln turing_*.

    python tools/turing_tabelle.py

Reaktion und Diffusion zweier Stoffe u und v auf dem abgewickelten Kern:

    du/dt = Du·Δu − u·v² + F·(1 − u)
    dv/dt = Dv·Δv + u·v² − (F + k)·v

Das Gitter ist im Umfang periodisch und oben und unten offen (Neumann-Rand).
Eine Zelle ist auf dem Kern der Ausgangsform etwa 2,3 mm groß, in beiden
Richtungen gleich, damit das Muster nicht verzerrt wird. Der Zufall hat einen
festen Startwert, die Tabelle ist reproduzierbar.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

ZIEL = Path(__file__).resolve().parents[1] / "vase" / "turing.json"
BREITE = 150                       # Zellen im Umfang
UMFANG_MM = math.tau * 55.0        # Kern der Ausgangsform
HOEHE_MM = 250.0
DU, DV = 0.16, 0.08
SCHRITTE = 25000
MUSTER = {
    # Name: (F, k), nach Pearson 1993
    "flecken": (0.0367, 0.0649),
    "labyrinth": (0.029, 0.057),
}


def simulieren(f: float, k: float, breite: int, hoehe: int, seed: int = 7) -> np.ndarray:
    zufall = np.random.default_rng(seed)
    u = np.ones((hoehe, breite))
    v = np.zeros((hoehe, breite))
    for _ in range(40):
        y, x = zufall.integers(3, hoehe - 3), zufall.integers(0, breite)
        spalten = np.arange(x - 2, x + 3) % breite
        u[y - 2:y + 3][:, spalten] = 0.5
        v[y - 2:y + 3][:, spalten] = 0.25
    u += 0.02 * zufall.random((hoehe, breite))
    v += 0.02 * zufall.random((hoehe, breite))
    for _ in range(SCHRITTE):
        ur = np.pad(u, ((1, 1), (0, 0)), mode="edge")
        vr = np.pad(v, ((1, 1), (0, 0)), mode="edge")
        lu = ur[:-2] + ur[2:] + np.roll(u, 1, 1) + np.roll(u, -1, 1) - 4 * u
        lv = vr[:-2] + vr[2:] + np.roll(v, 1, 1) + np.roll(v, -1, 1) - 4 * v
        uvv = u * v * v
        u += DU * lu - uvv + f * (1 - u)
        v += DV * lv + uvv - (f + k) * v
    return (v - v.min()) / (v.max() - v.min())


def main() -> None:
    hoehe = round(BREITE * HOEHE_MM / UMFANG_MM)
    tafel = {"breite": BREITE, "hoehe": hoehe, "muster": {}}
    for name, (f, k) in MUSTER.items():
        tafel["muster"][name] = np.round(simulieren(f, k, BREITE, hoehe), 3).tolist()
        print(f"{name}: F {f}, k {k}, {BREITE} x {hoehe} Zellen")
    ZIEL.write_text(json.dumps(tafel, separators=(",", ":")), encoding="utf-8")
    print(f"Geschrieben: {ZIEL.relative_to(ZIEL.parents[1])}")


if __name__ == "__main__":
    main()
