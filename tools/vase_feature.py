"""Lokale Entsprechung des späteren Onshape-Features „Vase“.

Die Vase ist ein Zylinder. Die Form machen radiale Lamellen, deren Länge
eine Wellenfunktion ist. `profil`, `amplitude` und `welle` beschreiben die
Spitze jeder Lamelle und können nach FeatureScript wandern:

    spitze = profil(z) + amplitude(z) * welle(theta, z)

`koerper` baut daraus das Netz: Kernzylinder, Lamellen, Boden, Bohrung.
Längen sind Millimeter, Winkel in den Parametern Grad.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path


class VaseFehler(Exception):
    def __init__(self, meldungen: list[str]):
        self.meldungen = meldungen
        super().__init__("\n".join(meldungen))


@dataclass
class Vase:
    name: str
    hoehe: float
    radius_fuss: float
    radius_bauch: float
    bauch_lage: float
    radius_lippe: float
    kern_aussen: float
    wand: float
    innendurchmesser: float
    lamelle_max: float
    lamellen: int
    dicke: float
    bohrung: float
    boden: float
    muendung: float
    bodenloch: float
    funktion: str
    loben: int
    amplitude: float
    drehung_grad: float
    drehung_von: float
    drehung_bis: float
    einblendung_unten: float
    einblendung_oben: float
    oberwelle_loben: int
    oberwelle_anteil: float
    potenz: float
    schnitte: int
    punkte: int
    bett_x: float
    bett_y: float
    bett_z: float
    rand: float
    wand_min: float
    boden_min: float
    begrenzen: bool
    begrenzung_grad: float
    warnung_grad: float
    stuetze_grad: float

    @classmethod
    def aus_config(cls, daten: dict) -> "Vase":
        proportion = daten["proportion"]
        kern = daten["kern"]
        lamellen = daten["lamellen"]
        hohl = daten["hohlraum"]
        welle = daten["welle"]
        auf = daten["aufloesung"]
        drucker = daten["drucker"]
        ueberhang = daten.get("ueberhang", {})
        innen_d = float(proportion["innendurchmesser_mm"])
        wand = float(kern["wand_mm"])
        bohrung = innen_d / 2.0
        return cls(
            name=str(daten.get("name", "vase")),
            hoehe=float(proportion["hoehe_mm"]),
            radius_fuss=0.0,
            radius_bauch=0.0,
            bauch_lage=0.5,
            radius_lippe=0.0,
            kern_aussen=bohrung + wand,
            wand=wand,
            innendurchmesser=innen_d,
            lamelle_max=float(proportion["lamelle_max_mm"]),
            lamellen=int(lamellen["anzahl"]),
            dicke=float(lamellen["dicke_mm"]),
            bohrung=bohrung,
            boden=float(hohl["boden_dicke_mm"]),
            muendung=bohrung + float(hohl["muendung_zugabe_mm"]),
            bodenloch=float(hohl["bodenloch_radius_mm"]),
            funktion=str(welle["funktion"]).lower(),
            loben=int(welle["loben"]),
            amplitude=float(welle["amplitude_mm"]),
            drehung_grad=float(welle["drehung_grad"]),
            drehung_von=float(welle["drehung_von"]),
            drehung_bis=float(welle["drehung_bis"]),
            einblendung_unten=float(welle["einblendung_unten_mm"]),
            einblendung_oben=float(welle["einblendung_oben_mm"]),
            oberwelle_loben=int(welle["oberwelle_loben"]),
            oberwelle_anteil=float(welle["oberwelle_anteil"]),
            potenz=float(welle.get("potenz", 1)),
            schnitte=int(auf["schnitte"]),
            punkte=int(auf["punkte_je_schnitt"]),
            bett_x=float(drucker["x_mm"]),
            bett_y=float(drucker["y_mm"]),
            bett_z=float(drucker["z_mm"]),
            rand=float(drucker["rand_mm"]),
            wand_min=float(drucker["wand_min_mm"]),
            boden_min=float(drucker["boden_min_mm"]),
            begrenzen=bool(ueberhang.get("begrenzen", False)),
            begrenzung_grad=float(ueberhang.get("winkel_grad", 45)),
            warnung_grad=float(drucker.get("ueberhang_warnung_grad", 45)),
            stuetze_grad=float(drucker.get("stuetze_ab_grad", 60)),
        )


FUNKTIONEN = (
    "vorlage", "sinus", "spirale", "bluete", "kaemme", "gleich",
    "cnoidal", "logspirale", "phyllotaxis", "super", "ketten", "zeta",
    "turing_flecken", "turing_labyrinth",
)
RUNDUNG = 8
_VORLAGE = json.loads((Path(__file__).resolve().parents[1] / "vase" / "vorlage.json").read_text(encoding="utf-8"))
_TURING = json.loads((Path(__file__).resolve().parents[1] / "vase" / "turing.json").read_text(encoding="utf-8"))


def pruefen(vase: Vase) -> None:
    """Precondition, analog zum FeatureScript-Block `precondition`."""
    fehler = []
    if vase.hoehe <= 0:
        fehler.append("Hoehe muss groesser als 0 sein.")
    if vase.bett_z <= 0 or vase.bett_x <= 0 or vase.bett_y <= 0:
        fehler.append("Bauraum des Druckers ist ungueltig.")
    if vase.hoehe > vase.bett_z:
        fehler.append(
            f"Hoehe {vase.hoehe:.1f} mm liegt ueber der H2D-Grenze {vase.bett_z:.0f} mm "
            "(linke Duese). Die rechte Duese reicht bis 325 mm."
        )
    if vase.innendurchmesser <= 0 or vase.lamelle_max <= 0 or vase.wand <= 0:
        fehler.append("Innendurchmesser, Wand und Lamellenlaenge muessen groesser als 0 sein.")
    if vase.boden <= 0:
        fehler.append("Boden muss eine Dicke haben, der Boden ist geschlossen.")
    if vase.boden < vase.boden_min:
        fehler.append(
            f"Bodendicke {vase.boden:.2f} mm liegt unter der druckbaren Mindeststaerke {vase.boden_min:.2f} mm."
        )
    if vase.boden >= vase.hoehe:
        fehler.append("Bodendicke liegt ueber der Hoehe.")
    if vase.bohrung <= 0 or vase.muendung <= 0:
        fehler.append("Bohrung und Muendung brauchen einen Radius groesser als 0.")
    if vase.bodenloch < 0:
        fehler.append("Bodenloch darf nicht negativ sein.")
    if vase.bodenloch >= vase.bohrung:
        fehler.append("Bodenloch muss kleiner als die Bohrung sein.")
    if vase.bodenloch > 0:
        fehler.append("Der Boden ist geschlossen.")
    if vase.kern_aussen <= vase.bohrung:
        fehler.append("Der Kern muss ausserhalb der Bohrung liegen.")
    kernwand = vase.kern_aussen - max(vase.bohrung, vase.muendung)
    if kernwand < vase.wand_min:
        fehler.append(
            f"Kernwand {kernwand:.1f} mm liegt unter der druckbaren Mindeststaerke {vase.wand_min:.1f} mm."
        )
    if vase.lamellen < 12:
        fehler.append("Es braucht mindestens 12 Lamellen.")
    if vase.dicke < 0.4:
        fehler.append("Lamellen unter 0.4 mm sind mit der 0,4-mm-Duese nicht druckbar.")
    teilung = math.tau * vase.kern_aussen / vase.lamellen
    if vase.dicke >= teilung * 0.9:
        fehler.append(
            f"Lamellen {vase.dicke:.2f} mm sind breiter als der Abstand {teilung:.2f} mm und laufen ineinander."
        )
    if vase.funktion not in FUNKTIONEN:
        fehler.append(f"Wellenfunktion muss eine von {', '.join(FUNKTIONEN)} sein.")
    if vase.funktion not in ("vorlage", "aus"):
        if vase.loben < 2:
            fehler.append("Loben muessen mindestens 2 sein.")
        if vase.potenz <= 0:
            fehler.append("Potenz muss groesser als 0 sein.")
        if not 0 <= vase.oberwelle_anteil <= 1:
            fehler.append("Oberwellen-Anteil muss zwischen 0 und 1 liegen.")
        if vase.oberwelle_loben < 2:
            fehler.append("Oberwellen-Loben muessen mindestens 2 sein.")
    if not 0 <= vase.drehung_von < vase.drehung_bis <= 1:
        fehler.append("Drehung von/bis muss 0 <= von < bis <= 1 erfuellen.")
    if vase.einblendung_unten < 0 or vase.einblendung_oben < 0:
        fehler.append("Einblendung darf nicht negativ sein.")
    if vase.einblendung_unten + vase.einblendung_oben >= vase.hoehe:
        fehler.append("Die beiden Einblendungen zusammen sind laenger als die Vase.")
    if not 10 <= vase.begrenzung_grad <= 80:
        fehler.append("Der Grenzwinkel fuer den Ueberhang muss zwischen 10 und 80 Grad liegen.")
    if vase.schnitte < 12 or vase.punkte < 0:
        fehler.append("Aufloesung zu grob: mindestens 12 Schnitte.")
    if fehler:
        raise VaseFehler(fehler)
    groesster = radius_max(vase)
    grenze = durchmesser_grenze(vase)
    if 2 * groesster > grenze:
        raise VaseFehler([
            f"Durchmesser {2 * groesster:.1f} mm passt nicht in den H2D "
            f"(nutzbar {grenze:.0f} mm, Bett {vase.bett_x:.0f} x {vase.bett_y:.0f} mm, Rand {vase.rand:.0f} mm)."
        ])


def durchmesser_grenze(vase: Vase) -> float:
    """Nutzbarer Durchmesser: die schmalere Bettseite, abzueglich Rand fuer den Randwulst."""
    return min(vase.bett_x, vase.bett_y) - 2 * vase.rand


def radius_max(vase: Vase) -> float:
    """Groesster Aussenradius, abgetastet. Die Welle kann den Bauch ueberragen."""
    groesster = 0.0
    winkel = max(vase.loben * 12, vase.oberwelle_loben * 8, 24)
    for i in range(36):
        z = vase.hoehe * i / 35
        for j in range(winkel):
            groesster = max(groesster, aussen_radius(z, math.tau * j / winkel, vase))
    return groesster


def smoothstep(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def _stelle(s: float) -> tuple[int, int, float]:
    achse = _VORLAGE["s"]
    s = min(1.0, max(0.0, s))
    oben = 1
    while oben < len(achse) - 1 and achse[oben] < s:
        oben += 1
    unten = oben - 1
    spanne = achse[oben] - achse[unten]
    bruch = 0.0 if spanne == 0 else (s - achse[unten]) / spanne
    return unten, oben, bruch


def _lerp_reihe(s: float, werte: list[float]) -> float:
    unten, oben, bruch = _stelle(s)
    return werte[unten] * (1.0 - bruch) + werte[oben] * bruch


def _catmull(p0: float, p1: float, p2: float, p3: float, t: float) -> float:
    """Glatter Bogen durch p1 und p2. An den Stützstellen liegt er exakt auf."""
    t2 = t * t
    t3 = t2 * t
    return 0.5 * (
        2.0 * p1
        + (-p0 + p2) * t
        + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
        + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
    )


def _reihe(index: int, theta: float) -> float:
    tafel = _VORLAGE["f"]
    index = max(0, min(len(tafel) - 1, index))
    anzahl = len(tafel[0])
    lage = (theta % math.tau) / math.tau * anzahl
    links = int(lage) % anzahl
    rechts = (links + 1) % anzahl
    kante = lage - int(lage)
    return tafel[index][links] * (1.0 - kante) + tafel[index][rechts] * kante


def anteil_vorlage(s: float, theta: float) -> float:
    """Gemessener Längenanteil. Die Außenkante einer Lamelle ist ein Spline."""
    unten, oben, bruch = _stelle(s)
    return max(0.0, _catmull(
        _reihe(unten - 1, theta),
        _reihe(unten, theta),
        _reihe(oben, theta),
        _reihe(oben + 1, theta),
        bruch,
    ))


def _normiert(wert: float) -> float:
    return 0.5 * (max(-1.0, min(1.0, wert)) + 1.0)


def _huelle(s: float) -> float:
    """Geht an Fuß und Lippe auf null und ist im Körper eins."""
    return smoothstep(s / 0.16) * smoothstep((1.0 - s) / 0.16)


def _elliptisches_k(m: float) -> float:
    """Vollständiges elliptisches Integral K(k), m = k², über das arithmetisch-geometrische Mittel."""
    a, b = 1.0, math.sqrt(max(0.0, 1.0 - m))
    for _ in range(40):
        a, b = 0.5 * (a + b), math.sqrt(a * b)
        if abs(a - b) < 1e-15:
            break
    return math.pi / (2.0 * a)


def _jacobi_cn(u: float, m: float) -> float:
    """Jacobische elliptische Funktion cn(u, k), m = k². Für m = 0 ist das der Kosinus."""
    if m <= 0.0:
        return math.cos(u)
    if m >= 1.0:
        return 1.0 / math.cosh(u)
    a = [1.0]
    b = [math.sqrt(1.0 - m)]
    c = [math.sqrt(m)]
    while abs(c[-1]) > 1e-14 and len(a) < 32:
        a.append(0.5 * (a[-1] + b[-1]))
        b.append(math.sqrt(a[-2] * b[-1]))
        c.append(0.5 * (a[-2] - b[-2]))
    stufe = len(a) - 1
    phi = (2.0 ** stufe) * a[stufe] * u
    for i in range(stufe, 0, -1):
        sinus = max(-1.0, min(1.0, c[i] * math.sin(phi) / a[i]))
        phi = 0.5 * (phi + math.asin(sinus))
    return math.cos(phi)


# Modul der Cnoidalwelle: breite Kämme, schmale Täler, noch keine einzelnen Solitonen.
_CNOIDAL_M = 0.85
_CNOIDAL_K = _elliptisches_k(_CNOIDAL_M)
_GOLDENER_WINKEL = 2.0 * math.pi / ((1.0 + math.sqrt(5.0)) / 2.0) ** 2
_PHYLLO_ANZAHL = 42
_SUPER_M, _SUPER_N1, _SUPER_N2, _SUPER_N3 = 5.0, 0.9, 1.5, 1.5
_KETTEN_A = 0.62


def _cnoidal(s: float, theta: float) -> float:
    # Zwei Kämme auf dem Umfang: θ um π schiebt das Argument um 2K, eine Periode von cn².
    argument = (2.0 * _CNOIDAL_K / math.pi) * (theta + 0.45 * s)
    wert = _jacobi_cn(argument, _CNOIDAL_M)
    return wert * wert


def _logspirale(s: float, theta: float) -> float:
    """Zwei Arme einer logarithmischen Spirale, seitlich als Gaußglocke abfallend."""
    winkel = 0.9 * math.log(s + 0.08)

    def abstand(ziel: float) -> float:
        return abs((theta - ziel + math.pi) % math.tau - math.pi)

    naehe = min(abstand(winkel), abstand(winkel + math.pi))
    sigma = 0.42
    return math.exp(-0.5 * (naehe / sigma) ** 2)


def _phyllotaxis_roh(s: float, theta: float) -> float:
    """Summe von Gaußglocken auf dem Gitter des goldenen Winkels."""
    sigma_s, sigma_theta = 0.030, 0.22
    summe = 0.0
    for n in range(_PHYLLO_ANZAHL):
        hoehe = (n + 0.5) / _PHYLLO_ANZAHL
        winkel = n * _GOLDENER_WINKEL
        ds = (s - hoehe) / sigma_s
        d_theta = ((theta - winkel + math.pi) % math.tau - math.pi) / sigma_theta
        summe += math.exp(-0.5 * (ds * ds + d_theta * d_theta))
    return summe


def _phyllotaxis_max() -> float:
    groesste = 0.0
    for n in range(8, _PHYLLO_ANZAHL - 8):
        s = (n + 0.5) / _PHYLLO_ANZAHL
        theta = n * _GOLDENER_WINKEL
        groesste = max(groesste, _phyllotaxis_roh(s, theta))
    return groesste


_PHYLLO_MAX = _phyllotaxis_max()


def _super_rho(theta: float) -> float:
    t = _SUPER_M * theta / 4.0
    cosinus = abs(math.cos(t)) ** _SUPER_N2
    sinus = abs(math.sin(t)) ** _SUPER_N3
    return (cosinus + sinus) ** (-1.0 / _SUPER_N1)


_SUPER_WERTE = [_super_rho(i / 720.0 * math.tau) for i in range(720)]
_SUPER_MIN = min(_SUPER_WERTE)
_SUPER_MAX = max(_SUPER_WERTE)


def _superformel(theta: float) -> float:
    rho = _super_rho(theta)
    return (rho - _SUPER_MIN) / (_SUPER_MAX - _SUPER_MIN)


def _kettenlinie(s: float) -> float:
    """Katenoid: engste Stelle in der Mitte, weit an den beiden Ringen."""
    rand = math.cosh(0.5 / _KETTEN_A)
    form = (math.cosh((s - 0.5) / _KETTEN_A) - 1.0) / (rand - 1.0)
    return form


# Bernoullizahlen B2 bis B14 für den Rest der Euler-Maclaurin-Summe.
_BERNOULLI = (1 / 6, -1 / 30, 1 / 42, -1 / 30, 5 / 66, -691 / 2730, 7 / 6)
# t-Bereich und Hub so gewählt, dass keine Lamellenkante steiler als 45° überhängt.
_ZETA_T0, _ZETA_T1, _ZETA_SIGMA, _ZETA_HUB = 12.0, 36.0, 0.45, 2.5


def _zeta(s: complex, n: int = 24) -> complex:
    """Riemannsche Zetafunktion über Euler-Maclaurin, im Streifen 0 < σ < 1 auf 1e-7 genau."""
    summe = sum(k ** -s for k in range(1, n))
    summe += n ** (1 - s) / (s - 1) + 0.5 * n ** -s
    faktor = s * n ** (-s - 1)
    fakultaet = 2.0
    for k, b in enumerate(_BERNOULLI, start=1):
        summe += b / fakultaet * faktor
        faktor *= (s + 2 * k - 1) * (s + 2 * k) / (n * n)
        fakultaet *= (2 * k + 1) * (2 * k + 2)
    return summe


def _zeta_betrag(s: float, theta: float) -> float:
    """|ζ| auf einer Ellipse im kritischen Streifen. Die Höhe läuft entlang der imaginären Achse."""
    punkt = complex(
        0.5 + _ZETA_SIGMA * math.cos(theta),
        _ZETA_T0 + (_ZETA_T1 - _ZETA_T0) * s + _ZETA_HUB * math.sin(theta),
    )
    return abs(_zeta(punkt))


_ZETA_MAX = max(_zeta_betrag(i / 80, math.tau * j / 72) for i in range(81) for j in range(72))


def _zetaform(s: float, theta: float) -> float:
    return min(1.0, _zeta_betrag(s, theta) / _ZETA_MAX)


def _turing(s: float, theta: float, name: str) -> float:
    """Gray-Scott-Muster aus vase/turing.json. Spline in der Höhe, linear und periodisch im Umfang."""
    tafel = _TURING["muster"][name]
    zeilen = len(tafel)
    breite = len(tafel[0])
    lage = min(1.0, max(0.0, s)) * (zeilen - 1)
    unten = min(zeilen - 2, int(lage))
    bruch = lage - unten
    spalte = (theta % math.tau) / math.tau * breite
    links = int(spalte) % breite
    rechts = (links + 1) % breite
    kante = spalte - int(spalte)

    def zeile(index: int) -> float:
        reihe = tafel[max(0, min(zeilen - 1, index))]
        return reihe[links] * (1.0 - kante) + reihe[rechts] * kante

    wert = _catmull(zeile(unten - 1), zeile(unten), zeile(unten + 1), zeile(unten + 2), bruch)
    return min(1.0, max(0.0, wert))


def formel_anteil(s: float, theta: float, funktion: str) -> float:
    """Länge als Anteil von L_max. Der Höchstwert jeder Formel ist 1.

    Der kurze Rest an Fuß und Lippe ist derselbe Anteil wie in der Vorlage,
    damit die Lamellen dort nicht verschwinden.
    """
    rest = 0.158
    huelle = _huelle(s)
    if funktion == "sinus":
        welle = 0.5 + 0.5 * math.cos(2.0 * (theta + s * math.radians(100.0)))
    elif funktion == "spirale":
        welle = 0.5 + 0.5 * math.sin(2.0 * math.pi * 1.25 * s + 3.0 * theta)
    elif funktion == "bluete":
        kosinus = math.cos(5.0 * theta)
        welle = _normiert(math.copysign(abs(kosinus) ** 0.45, kosinus))
    elif funktion == "kaemme":
        dreh = smoothstep((s - 0.32) / 0.36) * math.radians(90.0)
        kosinus = math.cos(2.0 * (theta + dreh))
        welle = _normiert(math.copysign(abs(kosinus) ** 0.55, kosinus))
    elif funktion == "cnoidal":
        welle = _cnoidal(s, theta)
    elif funktion == "logspirale":
        welle = _logspirale(s, theta)
    elif funktion == "phyllotaxis":
        welle = _phyllotaxis_roh(s, theta) / _PHYLLO_MAX
    elif funktion == "super":
        welle = _superformel(theta)
    elif funktion == "zeta":
        welle = _zetaform(s, theta)
    elif funktion.startswith("turing_"):
        welle = _turing(s, theta, funktion[len("turing_"):])
    elif funktion == "ketten":
        return rest + (1.0 - rest) * _kettenlinie(s)
    else:
        return rest + (1.0 - rest) * math.sin(math.pi * s) ** 1.15
    return rest + (1.0 - rest) * huelle * welle


def laengenanteil(z: float, theta: float, vase: Vase) -> float:
    """Anteil der maximalen Lamellenlänge. 1 ist die längste Lamelle."""
    s = 0.0 if vase.hoehe <= 0 else z / vase.hoehe
    if vase.funktion == "vorlage":
        return anteil_vorlage(s, theta)
    return formel_anteil(s, theta, vase.funktion)


def aussen_radius(z: float, theta: float, vase: Vase) -> float:
    """Radius der Lamellenspitze."""
    return vase.kern_aussen + vase.lamelle_max * laengenanteil(z, theta, vase)


def schnitt_hoehen(vase: Vase) -> list[float]:
    return [vase.hoehe * i / (vase.schnitte - 1) for i in range(vase.schnitte)]


def spitzen(vase: Vase) -> list[list[float]]:
    """Radius jeder Lamellenspitze auf jedem Höhenschnitt, [schnitt][lamelle].

    Mit `ueberhang.begrenzen` wächst eine Lamelle von Schnitt zu Schnitt
    höchstens um tan(winkel) · Δz nach außen. Kürzer werden darf sie beliebig
    schnell, das hängt nicht über.
    """
    winkel = [math.tau * i / vase.lamellen for i in range(vase.lamellen)]
    zs = schnitt_hoehen(vase)
    radien = [[aussen_radius(z, theta, vase) for theta in winkel] for z in zs]
    if vase.begrenzen:
        steigung = math.tan(math.radians(vase.begrenzung_grad))
        for k in range(1, len(zs)):
            erlaubt = steigung * (zs[k] - zs[k - 1])
            radien[k] = [min(r, vorher + erlaubt) for r, vorher in zip(radien[k], radien[k - 1])]
    return radien


def ueberhaenge(vase: Vase, radien: list[list[float]]) -> list[list[float]]:
    """Überhang der Lamellenspitze zwischen zwei Schnitten in Grad zur Senkrechten, [abschnitt][lamelle].

    Nur wachsende Lamellen hängen über. Die Seiten der Lamellen und der Kern
    stehen senkrecht.
    """
    zs = schnitt_hoehen(vase)
    return [
        [math.degrees(math.atan2(max(0.0, oben - unten), zs[k + 1] - zs[k])) for unten, oben in zip(radien[k], radien[k + 1])]
        for k in range(len(zs) - 1)
    ]


def innen_radius(z: float, vase: Vase) -> float:
    """Bohrung, an der Lippe auf den Muendungsradius geoeffnet."""
    laenge = min(vase.einblendung_oben, vase.hoehe - vase.boden)
    if laenge <= 0 or z <= vase.hoehe - laenge:
        return vase.bohrung
    t = smoothstep((z - (vase.hoehe - laenge)) / laenge)
    return vase.bohrung + (vase.muendung - vase.bohrung) * t


def _kreuz(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _lamelle(theta: float, kern: float, halb: float, spitze: float) -> tuple[tuple[float, float], list[tuple[float, float]], tuple[float, float]]:
    """Parallele Seiten. Die Spitze ist ein Halbkreis und endet bei spitze."""
    cosinus, sinus = math.cos(theta), math.sin(theta)
    tx, ty = -sinus, cosinus
    kappe = min(halb, max(0.0, spitze - kern))
    innen_vor = (kern * cosinus - kappe * tx, kern * sinus - kappe * ty)
    innen_nach = (kern * cosinus + kappe * tx, kern * sinus + kappe * ty)
    mitte_radius = max(kern, spitze - kappe)
    mitte = (mitte_radius * cosinus, mitte_radius * sinus)
    bogen = []
    for schritt in range(RUNDUNG + 1):
        phi = theta - math.pi / 2 + schritt / RUNDUNG * math.pi
        bogen.append((mitte[0] + kappe * math.cos(phi), mitte[1] + kappe * math.sin(phi)))
    return innen_vor, bogen, innen_nach


def aussen_polygon(z: float, vase: Vase, radien: list[float] | None = None) -> list[tuple[float, float]]:
    """Querschnitt: runder Kern, jede Lamelle mit rundem Ende. `radien` ersetzt die Formel."""
    anzahl = vase.lamellen
    halb = vase.dicke * 0.5
    kern = vase.kern_aussen
    if radien is None:
        radien = [aussen_radius(z, math.tau * i / anzahl, vase) for i in range(anzahl)]
    lamellen = [_lamelle(math.tau * i / anzahl, kern, halb, radien[i]) for i in range(anzahl)]
    punkte: list[tuple[float, float]] = []
    schritte = vase.punkte
    for i in range(anzahl):
        vorher = lamellen[i - 1][2]
        eintritt, bogen, austritt = lamellen[i]
        winkel_0 = math.atan2(vorher[1], vorher[0])
        winkel_1 = math.atan2(eintritt[1], eintritt[0])
        delta = (winkel_1 - winkel_0) % math.tau
        for schritt in range(1, schritte + 1):
            winkel = winkel_0 + delta * schritt / (schritte + 1)
            punkte.append((kern * math.cos(winkel), kern * math.sin(winkel)))
        punkte.append(eintritt)
        punkte.extend(bogen)
        punkte.append(austritt)
    return punkte


def koerper(vase: Vase) -> dict:
    """Kernzylinder mit Lamellen, geschlossener Boden, zylindrische Bohrung.

    Der Querschnitt ist auf jeder Hoehe dasselbe Polygon: der Kern, und daran
    die Lamellen. Daraus wird die Aussenwand geloftet. Die Bohrung wird als
    Innenzylinder abgesetzt, der Boden schliesst sie.
    """
    pruefen(vase)
    zs = schnitt_hoehen(vase)
    radien = spitzen(vase)
    innen_z = [vase.boden] + [z for z in zs if z > vase.boden + 1e-6]
    if abs(innen_z[-1] - vase.hoehe) > 1e-6:
        innen_z.append(vase.hoehe)
    innen_teilung = max(vase.lamellen * 2, 180)

    positionen: list[tuple[float, float, float]] = []
    dreiecke: list[tuple[int, int, int]] = []

    def hinzu(x: float, y: float, z: float) -> int:
        positionen.append((x, y, z))
        return len(positionen) - 1

    def ring_aus_polygon(k: int) -> list[int]:
        return [hinzu(x, y, zs[k]) for x, y in aussen_polygon(zs[k], vase, radien[k])]

    def ring_innen(z: float) -> list[int]:
        radius = innen_radius(z, vase)
        return [
            hinzu(radius * math.cos(math.tau * i / innen_teilung), radius * math.sin(math.tau * i / innen_teilung), z)
            for i in range(innen_teilung)
        ]

    def wand(ringe: list[list[int]], nach_aussen: bool) -> None:
        for unten, oben in zip(ringe, ringe[1:]):
            anzahl = len(unten)
            for i in range(anzahl):
                j = (i + 1) % anzahl
                a, b, c, d = unten[i], unten[j], oben[i], oben[j]
                if nach_aussen:
                    dreiecke.append((a, b, d))
                    dreiecke.append((a, d, c))
                else:
                    dreiecke.append((a, c, d))
                    dreiecke.append((a, d, b))

    aussen = [ring_aus_polygon(k) for k in range(len(zs))]
    innen = [ring_innen(z) for z in innen_z]
    wand(aussen, nach_aussen=True)
    wand(innen, nach_aussen=False)

    # Boden, volle Aussenflaeche, Normale nach unten.
    mitte_boden = hinzu(0.0, 0.0, 0.0)
    boden_ring = aussen[0]
    for i in range(len(boden_ring)):
        dreiecke.append((mitte_boden, boden_ring[(i + 1) % len(boden_ring)], boden_ring[i]))

    # Innenboden, Normale nach oben in die Bohrung.
    mitte_innen = hinzu(0.0, 0.0, vase.boden)
    for i in range(innen_teilung):
        dreiecke.append((mitte_innen, innen[0][i], innen[0][(i + 1) % innen_teilung]))

    # Mündung: Aussenpolygon auf den Innenkreis. Innenpunkte werden geteilt.
    oben = aussen[-1]
    innen_oben = innen[-1]
    for i in range(len(oben)):
        j = (i + 1) % len(oben)
        ax, ay = positionen[oben[i]][0], positionen[oben[i]][1]
        bx, by = positionen[oben[j]][0], positionen[oben[j]][1]
        ia = int(round((math.atan2(ay, ax) % math.tau) / math.tau * innen_teilung)) % innen_teilung
        ib = int(round((math.atan2(by, bx) % math.tau) / math.tau * innen_teilung)) % innen_teilung
        dreiecke.append((oben[i], oben[j], innen_oben[ib]))
        cursor = ib
        while cursor != ia:
            zurueck = (cursor - 1) % innen_teilung
            dreiecke.append((oben[i], innen_oben[cursor], innen_oben[zurueck]))
            cursor = zurueck

    normalen = [[0.0, 0.0, 0.0] for _ in positionen]
    for a, b, c in dreiecke:
        pa, pb, pc = positionen[a], positionen[b], positionen[c]
        kante_b = (pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2])
        kante_c = (pc[0] - pa[0], pc[1] - pa[1], pc[2] - pa[2])
        normale = _kreuz(kante_b, kante_c)
        for index in (a, b, c):
            normalen[index][0] += normale[0]
            normalen[index][1] += normale[1]
            normalen[index][2] += normale[2]
    for normale in normalen:
        laenge = math.sqrt(normale[0] ** 2 + normale[1] ** 2 + normale[2] ** 2)
        if laenge > 0:
            normale[0] /= laenge
            normale[1] /= laenge
            normale[2] /= laenge

    return {
        "positionen": positionen,
        "normalen": normalen,
        "dreiecke": dreiecke,
        "radien": radien,
    }


def wand_min(vase: Vase) -> float:
    """Dünnste Wand des Kerns. Die Lamellen stehen ausserhalb und halten kein Wasser."""
    return vase.kern_aussen - max(vase.bohrung, vase.muendung)


def massen(netz: dict, vase: Vase) -> dict:
    xs, ys, zs = zip(*netz["positionen"])
    radius = max(math.hypot(x, y) for x, y in zip(xs, ys))
    wand = wand_min(vase)
    winkel = [w for reihe in ueberhaenge(vase, netz["radien"]) for w in reihe]
    return {
        "ueberhang_max": max(winkel),
        "ueberhang_warnung": sum(vase.warnung_grad + 1e-6 < w <= vase.stuetze_grad + 1e-6 for w in winkel),
        "ueberhang_stuetze": sum(w > vase.stuetze_grad + 1e-6 for w in winkel),
        "hoehe": max(zs) - min(zs),
        "durchmesser": 2 * radius,
        "radius_max": radius,
        "wand_min_gemessen": wand,
        "dreiecke": len(netz["dreiecke"]),
        "durchmesser_grenze": durchmesser_grenze(vase),
        "hoehe_grenze": vase.bett_z,
    }


def wasserdicht(netz: dict) -> tuple[bool, float]:
    """Jede Kante genau zwei Dreiecke, Volumen positiv bei Aussen-Normalen."""
    kanten: dict[tuple[int, int], int] = {}
    volumen = 0.0
    for a, b, c in netz["dreiecke"]:
        for kante in ((a, b), (b, c), (c, a)):
            schluessel = (kante[0], kante[1]) if kante[0] < kante[1] else (kante[1], kante[0])
            kanten[schluessel] = kanten.get(schluessel, 0) + 1
        pa, pb, pc = (netz["positionen"][i] for i in (a, b, c))
        volumen += pa[0] * (pb[1] * pc[2] - pb[2] * pc[1])
        volumen += pa[1] * (pb[2] * pc[0] - pb[0] * pc[2])
        volumen += pa[2] * (pb[0] * pc[1] - pb[1] * pc[0])
    geschlossen = all(anzahl == 2 for anzahl in kanten.values())
    return geschlossen and volumen > 0, volumen / 6.0


def bett_linien(vase: Vase) -> list[float]:
    """Drahtmodell des nutzbaren H2D-Bauraums, Vase in der Mitte."""
    hx = vase.bett_x * 0.5
    hy = vase.bett_y * 0.5
    hz = vase.bett_z
    ecken = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    linien = []

    def strecke(p, q):
        linien.extend((*p, *q))

    for i in range(4):
        a, b = ecken[i], ecken[(i + 1) % 4]
        strecke((a[0], a[1], 0), (b[0], b[1], 0))
        strecke((a[0], a[1], hz), (b[0], b[1], hz))
        strecke((a[0], a[1], 0), (a[0], a[1], hz))
    return linien
