# Notizen

Stand: 20. Oktober 2026. Druckdatei ist die STL. Onshape wird nicht verwendet.

## Onshape

Dokument, noch ohne Feature: https://cad.onshape.com/documents/fc5d7bf85de49888a0286a88/w/73e14840134df70a3d37bbf5/e/e28b7ed0523b5e766cbadb1d

Kein API-Aufruf, solange die Form lokal nicht freigegeben ist.

## Festgelegt

- Boden geschlossen (`bodenloch_radius_mm` = 0).
- Drucker H2D, eine Düse. Grenze 310 mm Durchmesser, 320 mm Höhe.
- Ausgangsform: Innen Ø 102 mm, Höhe 250 mm, längste Lamelle 25,2 mm, 120 Lamellen à 0,9 mm, Kernwand 4 mm.

## Verlauf

- 2026-10-20: Projekt von den Tastmodellen auf den Vasengenerator umgestellt. Referenz-STL vermessen, Plan in `docs/PLAN.md`. Alte Grundriss-Dateien aus diesem Ordner entfernt.
- 2026-10-20: Lokaler Generator `tools/vase_feature.py` und `tools/vase_generator.py`. Vorlage 250 mm hoch, 174 mm Durchmesser, geschlossen, druckbar auf dem H2D.
- 2026-10-20: STL neu gelesen. Die Form sind 120 Lamellen à 0,9 mm auf einem Kern von Radius 55 mm. Der Generator baut jetzt diesen Aufbau.
- 2026-10-20: Lamellenlänge als gemessene Funktion `vase/vorlage.json`. Ausgangspunkt Innen Ø 102 mm, Höhe 250 mm, Lamelle max 25,46 mm. Schieberegler in `vorschau.html`.
- 2026-10-20: Lamellenspitze als Halbkreis, Höhenverlauf fein aufgelöst. Knopf „Vorlage“ setzt die Regler zurück. Sinus, Spirale, Blüte, breite Kämme und gleich lange Lamellen als eigene glatte Formeln.
- 2026-10-20: Außenkante jeder Lamelle als Spline durch die Messpunkte, 200 Höhenschnitte. Keine Knicke mehr zwischen den Stützstellen.
- 2026-10-20: Vergleich mit dem STL. Der grobe Spline wich bis 5 mm ab. Die Kante steht jetzt im Halb-Millimeter-Abstand aus dem Original in `vorlage.json`. Abweichung an den Messpunkten 0 mm.
- 2026-10-20: Kleine Unterwellen waren Dreiecksrauschen. Tiefpass lässt nur die großen Wellen, Fuß und Lippe bleiben bei etwa 4 mm.
- 2026-10-20: README, `docs/PLAN.md` und `CLAUDE.md` auf den Lamellengenerator umgeschrieben.
- 2026-10-20: STL ist die Druckdatei. Der Generator schreibt `vase.stl`, die Ansicht lädt die aktuelle Reglerstellung herunter.
- 2026-10-20: Fünf weitere Formeln: Cnoidalwelle, logarithmische Spirale, goldener Winkel, Superformel, Kettenlinie. Hintergrund in `README.md`.
