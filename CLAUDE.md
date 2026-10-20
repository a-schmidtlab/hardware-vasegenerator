# Parametrischer Vasengenerator

Diese Datei gilt für jede Sitzung in diesem Ordner.

## 1. Ziel

Eine Vase aus einem zylindrischen Kern und radialen Lamellen. Die Lamellenlänge ist eine Wellenformel. Innenraum, Höhe und die größte Länge sind Parameter.

Die Referenz ist vermessen, siehe `docs/PLAN.md`, `references/referenz.stl` und `vase/vorlage.json`. Die STL wird nicht verändert und nicht nachgebaut. Die Kante in `vorlage.json` ist die bereits gefilterte Messung.

Die Druckdatei ist eine STL aus `vase_generator.py` oder aus dem Knopf in `vase/vorschau.html`. Onshape ist kein Schritt in diesem Ablauf.

## 2. Umgebung

| Komponente | Details |
|---|---|
| Python | numpy, pillow, siehe `tools/requirements.txt` |
| Ansicht | `vase/vorschau.html`, WebGL, STL-Download |
| Drucker | Bambu Lab H2D, eine Düse: 325 × 320 mm, Höhe 320 mm (linke Düse) |

```bash
python3 -m venv .venv && .venv/bin/pip install -r tools/requirements.txt
```

## 3. Ordner

```
├── CLAUDE.md
├── README.md                 Anleitung
├── docs/PLAN.md              Form, Formeln, Grenzen
├── docs/analyse-referenz.png
├── references/referenz.stl   nicht verändern
├── tools/
│   ├── analyse_referenz.py   Schnittbild der Referenz
│   ├── vase_feature.py       Formel und Körper
│   └── vase_generator.py     config → STL, HTML, PNG
└── vase/
    ├── config.json           Parameter, Startwerte der Regler
    ├── vorlage.json          gemessene Kante der Formel vorlage
    ├── notizen.md
    ├── vorschau.html         generiert, Regler rechnen im Browser
    ├── vorschau.png          generiert
    └── vase.stl              generiert
```

Weitere Varianten: eigener Ordner mit eigener `config.json`. Die Formel bleibt in `tools/vase_feature.py`.

## 4. Arbeitsablauf

An den Phasengrenzen anhalten, außer der Auftrag geht ausdrücklich durch.

### Phase 1

Erledigt. Änderungen an der Formel zuerst in `docs/PLAN.md` festlegen.

### Phase 2

1. `python tools/vase_generator.py vase/config.json` schreibt STL, `vorschau.html` und `vorschau.png`.
2. Dieselbe Längenformel steht in `vase_feature.py` und im Skript der HTML-Datei. Wer eine Seite ändert, ändert die andere mit.
3. `vorlage.json` ist die gemessene Kante. Neue Messungen ersetzen die Tabelle, sie erfinden keine Wellen.
4. Maße über dem H2D-Bauraum weist der Generator ab.
5. Die Ansicht ist prüfbar. Die STL aus der Ansicht oder aus dem Generator ist die Druckdatei.

### Phase 3

Rückmeldungen vom Druck in `config.json`, `docs/PLAN.md` und `vase/notizen.md`. Geometrieänderungen laufen über den Generator.

## 5. Verhalten

- Geometrie aus `vase_feature.py`, `vase/config.json` und `vase/vorlage.json`.
- `references/referenz.stl` nicht verändern.
- Namen der ursprünglichen Referenzdatei nicht wieder in Code, Dateinamen oder Dokumentation schreiben.
- Jede Änderung kurz in `vase/notizen.md` festhalten.
- Antworten kurz: Ergebnis, offene Fragen, nächster Schritt.
