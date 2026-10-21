# Notizen

Stand: 21. Oktober 2026. Druckdatei ist die STL. Onshape wird nicht verwendet.

## Onshape

Dokument, noch ohne Feature: https://cad.onshape.com/documents/fc5d7bf85de49888a0286a88/w/73e14840134df70a3d37bbf5/e/e28b7ed0523b5e766cbadb1d

Kein API-Aufruf, solange die Form lokal nicht freigegeben ist.

## Festgelegt

- Boden geschlossen (`bodenloch_radius_mm` = 0).
- Drucker H2D, eine Düse. Grenze 310 mm Durchmesser, 320 mm Höhe.
- Startform: Formel `zeta`, innen Ø 102 mm, Höhe 250 mm, längste Lamelle 25 mm, 120 Lamellen à 0,9 mm, Kernwand 4 mm.
- Erster Probedruck läuft (21. Oktober 2026).

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
- 2026-10-20: Formel `zeta`: |ζ| der Riemannschen Zetafunktion auf Ellipsen im kritischen Streifen. Nullstellen als Kerbenreihe. Python und Ansicht stimmen auf 1e-14 überein.
- 2026-10-20: Überhang der Lamellenkanten gemessen. Erste Fassung von `zeta` (ln|ζ|, t 10–50) hing bis 79° über, jetzt |ζ| linear, t 12–36: höchstens 43°. Offen: `phyllotaxis` bis 62°, `kaemme` bis 75°.
- 2026-10-20: Formeln `turing_flecken` und `turing_labyrinth`: Gray-Scott-Muster, gerechnet von `tools/turing_tabelle.py`, abgelegt in `vase/turing.json`.
- 2026-10-20: Überhang der Lamellenspitzen wird gemessen. Ansicht färbt orange ab 45°, rot ab 60° (Bambu-Studio-Schwelle 30° zur Waagrechten), Generator meldet die Abschnitte, `vorschau.png` färbt die Meridiane.
- 2026-10-20: Option `ueberhang.begrenzen`, Haken in der Ansicht: Lamellen wachsen nach oben höchstens im Grenzwinkel (45°). Standard aus, die Ausgangsform bleibt unverändert.
- 2026-10-20: README um das Kapitel Mathematik erweitert: Geometrie, gemeinsame Bausteine, Herleitung jeder Formel, Numerik von ζ, cn und Gray-Scott, Überhang und Begrenzung. Lage der Zeta-Kerben korrigiert: jede Nullstelle erscheint zweimal, 7 Kerben im Körper.
- 2026-10-20: Mathematik im README nachgeprüft. Korrigiert: Überhang auf dem Netz gemessen (`kaemme` 69° statt 75°, erste `zeta`-Fassung 77° statt 79°), Turing-Wellenlänge 27 mm statt 20 mm, `ketten` ist das Profil der Kettenlinie und kein Katenoid, Formen von `bluete` und der Vorzeichenpotenz, Periode der Superformel, Kappengeometrie beim Überhang, Begrenzung kappt schmale Höcker, Mündung Ø 106 mm.
- 2026-10-20: README-Formeln für GitHub angepasst: `\operatorname` (von GitHub gesperrt) durch `\mathrm` ersetzt, Dezimalkomma als `0,\!55`, `<` und `>` als `\lt` und `\gt`.
- 2026-10-21: Referenz entfernt: `references/referenz.stl`, `tools/analyse_referenz.py`, `docs/analyse-referenz.png`, die Formel `vorlage` und `vase/vorlage.json`. Startform ist `zeta`, `L_max` 25 mm statt 25,221 mm. Ohne den Vorlage-Spline stimmen Python und Ansicht auf 1e-13 mm überein.
- 2026-10-21: README neu gegliedert: oben allgemeinverständlich mit Grundform, Zeichnung und Galerie (`docs/bilder/`), unten das Kapitel Mathematik.
- 2026-10-21: 3D-Ansicht neu gestaltet: Kacheln für die Formen, Kopf mit Idee und Formel, Kennzahlen mit Ampel, Bodenschatten, langsames Drehen, Pinch-Zoom, Dunkelmodus, Handy-Layout. Bedienung und Rechnung unverändert.
- 2026-10-21: Einführung im README und Kurzbeschreibungen der Ansicht sachlicher formuliert.
- 2026-10-21: Kapitel Mathematik um Absätze zur Geschichte jeder Funktion und eine Quellenliste ergänzt.
- 2026-10-21: Lizenzen: Code unter PolyForm Noncommercial 1.0.0 (`LICENSE.md`), Inhalte unter CC BY-NC-SA 4.0 (`LICENSE-CONTENT.txt`). Hinweis im Kopf der Code-Dateien, in der Ansicht und im STL-Kopf. Kommerzielle Nutzung nur mit schriftlicher Genehmigung von Axel Schmidt.
- 2026-10-21: Ordner `web/` für den Webserver: `index.html` (Ansicht mit About-Link), `about.html` (README als Webseite, MathJax), Bilder und Lizenzen. Gebaut von `tools/web_bauen.py`. Titelbild ohne schwarzen Rand, Knopfleiste der Ansicht mit deckendem Hintergrund.
- 2026-10-21: `CLAUDE.md` in `plan.md` umbenannt. Verweise in README und `web/about.html` angepasst.
