# Vasengenerator

Parametrische Vase für den 3D-Druck. Ein zylindrischer Kern trägt 120 radiale Lamellen. Die Länge jeder Lamelle folgt einer Wellenformel. Innenraum, Höhe und die größte Lamellenlänge sind Schieberegler. Die Druckdatei ist eine STL, direkt aus dem Generator oder aus der 3D-Ansicht.

Die Ausgangsform ist aus `references/referenz.stl` vermessen. Sie ist 250 mm hoch, der Innendurchmesser ist 102 mm, die längste Lamelle misst 25,2 mm. Der Außendurchmesser liegt dann bei 160 mm.

![Seitenansicht und Querschnitt](vase/vorschau.png)

## Aufbau

Wasser hält der Kern. Die Lamellen sind die äußere Form und bleiben außen am Kern.

| Teil | Ausgangswert | Bedeutung |
|---|---|---|
| Bohrung | Ø 102 mm | zylindrisch, an der Mündung 2 mm weiter |
| Kernwand | 4 mm | Außenradius des Kerns = Innenradius + 4 mm |
| Boden | 2 mm, geschlossen | die Referenz hatte ein Loch, das Modell nicht |
| Lamellen | 120 Stück, 0,9 mm dick | Teilung 3°, Spitze ein Halbkreis |
| Kürzeste Lamelle | etwa 4 mm | Fuß und Lippe, Anteil 0,158 von `L_max` |
| Längste Lamelle | 25,2 mm | die großen Wellen der Referenz |

Die Länge an der Stelle `(z, θ)` ist

```
s = z / Höhe
länge = L_max · f(s, θ)
Spitze = Innenradius + Kernwand + länge
```

`f` liegt zwischen 0 und 1. Für die Formel `vorlage` ist `f` die gemessene Kante aus `vase/vorlage.json`: alle 0,5 mm eine Stützstelle je Lamelle, dazwischen ein Spline. Kurze Zacken aus dem Dreiecksnetz der Referenz sind herausgefiltert, die großen Wellen bleiben. Der Höchstwert von `f` ist 1, damit `L_max` die längste Lamelle ist.

## Schnellstart

```bash
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/vase_generator.py vase/config.json
```

Danach `vase/vorschau.html` im Browser öffnen. Daneben liegen `vase/vase.stl` für den Slicer und `vase/vorschau.png`.

Python 3 reicht mit den Paketen aus `tools/requirements.txt` (numpy, pillow). Die Vorschau rechnet im Browser und braucht dafür kein Python.

## 3D-Ansicht

Ziehen dreht, das Mausrad zoomt. Der Rahmen ist der nutzbare Bauraum des Druckers.

| Regler | Bereich | Start |
|---|---|---|
| Innendurchmesser | 40–180 mm | 102 mm |
| Höhe | 80–320 mm | 250 mm |
| Lamellenlänge max | 4–70 mm | 25,2 mm |
| Wellenformel | siehe unten | Vorlage, gemessen |

Der Knopf **Vorlage** setzt alle vier Regler auf diese Startwerte zurück. Unter den Reglern stehen Lamellenzahl, Dicke, Kernwand, der errechnete Außendurchmesser und ob das Teil auf den Drucker passt.

Die Regler ändern die Ansicht sofort. **STL speichern** lädt das gerade gezeigte Modell herunter, in Millimetern, bereit für den Slicer. Der Dateiname nennt Formel, Höhe und Innendurchmesser.

Dieselbe Ausgangsform schreibt der Generator als `vase/vase.stl`, wenn `vase/config.json` die Startwerte enthält.

## Wellenformeln

Alle Formeln außer `vorlage` teilen sich dieselbe Hülle: auf den ersten und letzten 16 % der Höhe läuft die Welle ein und aus. Der kurze Rest an Fuß und Lippe bleibt, die Lamellen verschwinden dort nicht. Der Höchstwert jeder Formel ist 1.

| Wert | In der Ansicht | Form |
|---|---|---|
| `vorlage` | Vorlage, gemessen | die Kante aus der Referenz |
| `sinus` | Sinus, zwei Loben | zwei weiche Bäuche, 100° Drehung über die ganze Höhe |
| `spirale` | Spirale | laufende Welle, 1,25 Perioden in der Höhe, drei Perioden im Umfang |
| `bluete` | Blüte, fünf Blätter | fünf breite Blätter, ohne Drehung |
| `kaemme` | Breite Kämme | zwei breite Kämme, 90° Drehung in der oberen Hälfte |
| `gleich` | Gleich lang | alle Lamellen gleich, nur ein Bauch über die Höhe |
| `cnoidal` | Cnoidalwelle | breite Wasserwellen-Kämme, schmale Täler |
| `logspirale` | Logarithmische Spirale | zwei Bänder, die sich selbstähnlich nach oben winden |
| `phyllotaxis` | Goldener Winkel | versetzte Höcker wie bei einer Sonnenblume |
| `super` | Superformel | fünf gerundete Blätter aus einer einzigen Formel |
| `ketten` | Kettenlinie | enge Taille, weite Ringe, wie eine Seifenhaut |
| `zeta` | Riemannsche Zetafunktion | wogende Bänder, eine Naht aus Kerben an den Nullstellen |

### Cnoidalwelle

Flache Wasserwellen gehorchen der Gleichung von Korteweg und de Vries. Ihre periodische Lösung ist keine Sinuswelle, sondern eine cnoidal wave: das Quadrat der Jacobischen elliptischen Funktion `cn(u, k)`.

`cn` verallgemeinert den Kosinus. Der Modul `k` steuert die Form. Bei `k = 0` ist `cn(u, 0) = cos(u)`, die Welle ist sinusförmig. Geht `k` gegen 1, bleiben die Kämme lang oben und die Übergänge in die Täler werden schmal. Im Grenzfall bleibt ein einzelner Soliton, eine Welle, die ihre Form behält. Hier ist `k² = 0,85`: die Kämme sind breit und rund, die Täler deutlich schmaler, die Welle ist noch periodisch.

Das vollständige elliptische Integral `K(k)` ist die Viertelperiode. Es wird über das arithmetisch-geometrische Mittel berechnet, `K = π / (2 · agm(1, √(1−k²)))`. Zwei Kämme auf dem Umfang entstehen, indem der Winkel `θ` so gestreckt wird, dass ein halber Umlauf genau eine Periode von `cn²` ist:

```text
u = (2K / π) · (θ + 0,45 · s)
f = cn(u, k)²
```

`cn²` liegt von selbst zwischen 0 und 1.

### Logarithmische Spirale

Die logarithmische Spirale, von Jakob Bernoulli *spira mirabilis* genannt, ist die Kurve, die bei jeder Vergrößerung dieselbe Gestalt behält: `r = a · e^(bφ)`. Der Winkel des Kamms auf der Vase folgt derselben Beziehung, mit der Höhe als Maßstab:

```text
φ(s) = 0,9 · ln(s + 0,08)
```

Zwei Arme liegen sich gegenüber. Die Lamellenlänge fällt seitlich als Gaußglocke mit der Breite `σ = 0,42` im Bogenmaß ab. Ein Band langer Lamellen windet sich nach oben und wird dabei weiter, ohne seine Form zu ändern.

### Goldener Winkel

Der goldene Schnitt `φ = (1+√5)/2` liefert den Winkel `2π/φ² ≈ 137,5°`. Dreht man jeden nächsten Punkt um genau diesen Winkel, füllt sich der Kreis so gleichmäßig, dass sich das Muster nie wiederholt. Das ist die Anordnung der Sonnenblume und der Tannenzapfen (Phyllotaxis). Auf der Vase sitzt der Höcker `n` bei der Höhe `(n+½)/42` und dem Winkel `n · 137,5°`. Jeder Höcker ist eine Gaußglocke in Höhe und Winkel. Die langen Lamellen bilden die schrägen Spiralen, die man an der Blüte sieht, und keine senkrechten Streifen.

### Superformel

Johan Gielis hat 2003 die Superellipse von Lamé zu einer Formel erweitert, die viele Umrisse aus der Botanik mit denselben vier Zahlen beschreibt:

```text
ρ(θ) = ( |cos(mθ/4)|^n₂ + |sin(mθ/4)|^n₃ )^(−1/n₁)
```

`m` ist die Zahl der Symmetrien. Die Exponenten runden oder schärfen die Ecken. Hier ist `m = 5`, `n₁ = 0,9`, `n₂ = n₃ = 1,5`: fünf weiche Blätter. `ρ` wird auf den Bereich 0…1 gezogen, damit die längste Lamelle bei `L_max` liegt. Andere Zahlen in derselben Formel geben Sterne, Schalen oder Quadrate.

### Kettenlinie

Ein frei hängendes Seil folgt `y = a · cosh(x/a)`, der Kettenlinie. Dreht man sie um die senkrechte Achse, entsteht das Katenoid. Es ist die einzige rotationssymmetrische Minimalfläche: die Form einer Seifenhaut zwischen zwei Ringen. Die Lamellenlänge ist dieses Profil, normiert auf 0 in der Taille und 1 an den beiden Ringen:

```text
f(s) = ( cosh((s−½)/a) − 1 ) / ( cosh(1/(2a)) − 1 )
```

mit `a = 0,62`. Die Taille bleibt beim kurzen Rest, Fuß und Lippe tragen die längsten Lamellen. Diese Formel benutzt die Ein- und Ausblendung der anderen Wellen nicht, sonst würde die Seifenhaut an den Ringen wieder verschwinden.

### Riemannsche Zetafunktion

`ζ(s) = Σ 1/nˢ`, fortgesetzt auf die ganze komplexe Ebene. Die Riemannsche Vermutung sagt, dass alle nichttrivialen Nullstellen auf der kritischen Linie `σ = ½` liegen. Die ersten liegen bei `t` = 14,13, 21,02, 25,01, 30,42, 32,94, 37,59, 40,92, 43,33, 48,01, 49,77.

Die Vase ist ein Stück des kritischen Streifens. Die Höhe läuft die imaginäre Achse von `t = 12` bis `36` hinauf. Jeder Höhenschnitt ist eine Ellipse um den Punkt `½ + it`:

```text
σ(θ) = ½ + 0,45 · cos θ
t(s, θ) = 12 + 24 · s + 2,5 · sin θ
f = |ζ(σ + it)| / |ζ|max
```

Bei `θ = ±90°` kreuzt die Ellipse die kritische Linie. Dort, wo sie eine Nullstelle trifft, fällt `|ζ|` auf null und die Lamellen werden kurz: eine senkrechte Reihe von Kerben, eine je Nullstelle. Zwischen den Nullstellen wölbt sich `|ζ|` zu Bändern, die durch den Hub in `t` schräg um die Vase laufen. Im Körper liegen die Nullstellen 21,02, 25,01 und 30,42, in der Ein- und Ausblendung 14,13 und 32,94. Ein längerer `t`-Bereich oder `ln|ζ|` gäbe mehr und schärfere Kerben, aber Lamellenkanten, die steiler als 45° überhängen. Mit diesen Werten bleibt der Überhang bei den Startwerten unter 43°.

`ζ` wird über die Euler-Maclaurin-Summe mit 24 Gliedern und sieben Bernoullizahlen berechnet, im Streifen auf etwa 10⁻⁷ genau.

## Konfiguration

`vase/config.json` ist die Quelle für STL und für die Startwerte der Ansicht.

```json
"proportion": {
  "innendurchmesser_mm": 102,
  "hoehe_mm": 250,
  "lamelle_max_mm": 25.221
}
```

Weitere feste Werte:

| Schlüssel | Wert | Wirkung |
|---|---|---|
| `kern.wand_mm` | 4 | Wandstärke des wasserführenden Kerns |
| `lamellen.anzahl` | 120 | Zahl der Lamellen |
| `lamellen.dicke_mm` | 0,9 | Dicke, die Spitze ist ein Halbkreis dieser Dicke |
| `hohlraum.boden_dicke_mm` | 2 | geschlossener Boden |
| `hohlraum.muendung_zugabe_mm` | 2 | die Bohrung öffnet sich an der Lippe um diesen Betrag |
| `welle.funktion` | `vorlage` | eine der sechs Formeln |
| `aufloesung.schnitte` | 200 | Höhenschnitte des Netzes |
| `aufloesung.punkte_je_schnitt` | 2 | Zwischenpunkte auf dem Kern zwischen zwei Lamellen |

Liegt die Höhe über 320 mm oder der Außendurchmesser über 310 mm, bricht der Generator ab und schreibt keine Dateien. In der Ansicht bleibt das Modell sichtbar, der Statustext meldet, dass es nicht auf den Drucker passt.

## Druck

Drucker ist ein Bambu Lab H2D mit einer Düse 0,4 mm. Eine Düse erreicht 325 × 320 mm in der Fläche. Die linke Düse druckt 320 mm hoch, die rechte 325 mm. Der Generator nimmt den kleineren Wert, damit das Teil auf beiden Düsen liegt: höchstens 310 mm Durchmesser (320 mm Bettiefe abzüglich 5 mm Rand) und 320 mm Höhe. Die Kernwand muss mindestens 1,2 mm bleiben, der Boden mindestens 0,8 mm. Die Lamellen der Ausgangsform sind 0,9 mm dick.

Quellen: [Technische Daten des H2D](https://bambulab.com/en/h2d/tech-specs), [Druckbereich der beiden Düsen](https://wiki.bambulab.com/en/h2/manual/printable-range-for-dual-nozzles).

Die STL in den Slicer laden und aufrecht stellen. Der Boden ist geschlossen, Stützen sind für die Ausgangsform nicht vorgesehen.

## Ordner

```
├── README.md                 diese Anleitung
├── CLAUDE.md                 Arbeitsanweisung für den Agenten
├── docs/
│   ├── PLAN.md               Form, Formeln, Druckgrenzen, Phasen
│   └── analyse-referenz.png  Schnitte durch die Referenz
├── references/
│   └── referenz.stl          vermessenes Netz, wird nicht verändert
├── tools/
│   ├── vase_feature.py       Formel und Körper
│   ├── vase_generator.py     config → STL, HTML, PNG
│   ├── analyse_referenz.py   schreibt das Schnittbild neu
│   └── requirements.txt
└── vase/
    ├── config.json           Parameter und Startwerte
    ├── vorlage.json          gemessene Lamellenkante
    ├── notizen.md            Stand und Verlauf
    ├── vorschau.html         3D-Ansicht, generiert
    ├── vorschau.png          Seitenansicht und Querschnitt, generiert
    └── vase.stl              Drucknetz, generiert
```

Eine weitere Variante bekommt einen eigenen Ordner neben `vase/` mit eigener `config.json`. Die Formel bleibt in `tools/vase_feature.py`. Die gemessene Kante liegt in `vase/vorlage.json` und gilt für die Formel `vorlage`.

## Referenz neu vermessen

`tools/analyse_referenz.py` liest `references/referenz.stl` und schreibt `docs/analyse-referenz.png` neu: vier Meridiane und vier Querschnitte. Die Lamellenkante in `vase/vorlage.json` entsteht nicht aus diesem Skript. Sie ist die bereits gefilterte Messung, aus der der Generator liest.

```bash
.venv/bin/python tools/analyse_referenz.py
```

Der fachliche Stand steht in `docs/PLAN.md`. Die Druckdatei kommt aus diesem Ordner, ein CAD-System ist dafür nicht nötig.
