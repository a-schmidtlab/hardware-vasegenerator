# Parametrischer Vasengenerator

Diese Datei gilt für jede Sitzung in diesem Ordner.

## 1. Ziel

Eine Vase aus einem zylindrischen Kern und radialen Lamellen. Die Lamellenlänge ist eine mathematische Formel. Innenraum, Höhe und die größte Länge sind Parameter. Grundform und Formeln stehen in `docs/PLAN.md`, die Herleitungen im README, Kapitel Mathematik.

Die Druckdatei ist eine STL aus `vase_generator.py` oder aus dem Knopf in `vase/vorschau.html`. Onshape ist kein Schritt in diesem Ablauf.

## 2. Umgebung

| Komponente | Details |
|---|---|
| Python | numpy, pillow, markdown, siehe `tools/requirements.txt` |
| Ansicht | `vase/vorschau.html`, WebGL, STL-Download |
| Drucker | Bambu Lab H2D, eine Düse: 325 × 320 mm, Höhe 320 mm (linke Düse) |

```bash
python3 -m venv .venv && .venv/bin/pip install -r tools/requirements.txt
```

## 3. Ordner

```
├── plan.md
├── README.md                 Anleitung
├── LICENSE.md                Code: PolyForm Noncommercial 1.0.0
├── LICENSE-CONTENT.txt       Inhalte: CC BY-NC-SA 4.0
├── docs/PLAN.md              Form, Formeln, Grenzen
├── docs/bilder/              Bilder für das README
├── tools/
│   ├── vase_feature.py       Formel und Körper
│   ├── turing_tabelle.py     Gray-Scott → vase/turing.json
│   ├── web_bauen.py          README und Ansicht → web/
│   └── vase_generator.py     config → STL, HTML, PNG
└── vase/
    ├── config.json           Parameter, Startwerte der Regler
    ├── turing.json           gerechnete Muster der Formeln turing_*
    ├── notizen.md
    ├── vorschau.html         generiert, Regler rechnen im Browser
    ├── vorschau.png          generiert
    └── vase.stl              generiert
web/                          generiert, statische Webseite für den Server
```

Weitere Varianten: eigener Ordner mit eigener `config.json`. Die Formel bleibt in `tools/vase_feature.py`.

## 4. Arbeitsablauf

An den Phasengrenzen anhalten, außer der Auftrag geht ausdrücklich durch.

### Phase 1

Erledigt. Änderungen an der Formel zuerst in `docs/PLAN.md` festlegen.

### Phase 2

1. `python tools/vase_generator.py vase/config.json` schreibt STL, `vorschau.html` und `vorschau.png`.
2. Dieselbe Längenformel steht in `vase_feature.py` und im Skript der HTML-Datei. Wer eine Seite ändert, ändert die andere mit.
3. `turing.json` entsteht aus `tools/turing_tabelle.py` und wird nicht von Hand bearbeitet.
4. Maße über dem H2D-Bauraum weist der Generator ab. Überhang über `drucker.stuetze_ab_grad` meldet er, die Ansicht färbt ihn rot.
5. Die Ansicht ist prüfbar. Die STL aus der Ansicht oder aus dem Generator ist die Druckdatei.
6. Nach Änderungen an Formeln, Ansicht oder README `python tools/web_bauen.py` laufen lassen, damit `web/` aktuell bleibt.

### Phase 3

Rückmeldungen vom Druck in `config.json`, `docs/PLAN.md` und `vase/notizen.md`. Geometrieänderungen laufen über den Generator.

## 5. Verhalten

- Geometrie aus `vase_feature.py`, `vase/config.json` und `vase/turing.json`.
- Den Namen der ursprünglichen Vorlage nicht in Code, Dateinamen oder Dokumentation schreiben.
- Neue Code-Dateien bekommen oben den Hinweis „Required Notice: Copyright 2026 Axel Schmidt“ und den Verweis auf `LICENSE.md`.
- Jede Änderung kurz in `vase/notizen.md` festhalten.
- Antworten kurz: Ergebnis, offene Fragen, nächster Schritt.
