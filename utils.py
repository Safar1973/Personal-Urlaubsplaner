"""
Hilfsfunktionen für Urlaubsberechnungen, Überschneidungsprüfung und Resturlaub.
"""
from datetime import date, timedelta
from models import Urlaubsantrag, Urlaubskontingent, Feiertag, AntragStatus
from extensions import db


def arbeitstage_berechnen(datum_von: date, datum_bis: date) -> float:
    """
    Berechnet die Anzahl der Arbeitstage (Mo–Fr, ohne Feiertage) zwischen
    zwei Daten (inklusive beider Grenztage).
    """
    if datum_von > datum_bis:
        return 0.0

    feiertage = {
        f.datum for f in Feiertag.query.filter(
            Feiertag.datum >= datum_von,
            Feiertag.datum <= datum_bis
        ).all()
    }

    tage = 0.0
    aktuell = datum_von
    while aktuell <= datum_bis:
        # 0=Mo, 4=Fr → Wochentag
        if aktuell.weekday() < 5 and aktuell not in feiertage:
            tage += 1.0
        aktuell += timedelta(days=1)
    return tage


def ueberschneidung_pruefen(mitarbeiter_id: int, datum_von: date,
                             datum_bis: date,
                             ausschluss_id: int = None) -> list:
    """
    Prüft, ob für einen Mitarbeiter im angegebenen Zeitraum bereits
    ein genehmigter oder ausstehender Antrag existiert.
    Gibt eine Liste der kollidierenden Anträge zurück.
    """
    query = Urlaubsantrag.query.filter(
        Urlaubsantrag.mitarbeiter_id == mitarbeiter_id,
        Urlaubsantrag.status.in_([AntragStatus.GENEHMIGT,
                                   AntragStatus.AUSSTEHEND]),
        Urlaubsantrag.datum_von <= datum_bis,
        Urlaubsantrag.datum_bis >= datum_von,
    )
    if ausschluss_id:
        query = query.filter(Urlaubsantrag.id != ausschluss_id)
    return query.all()


def team_ueberschneidung_pruefen(abteilung_id: int, datum_von: date,
                                  datum_bis: date,
                                  ausschluss_mitarbeiter_id: int = None) -> list:
    """
    Prüft, welche Mitarbeiter einer Abteilung im angegebenen Zeitraum
    bereits Urlaub haben (genehmigte Anträge).
    """
    from models import Mitarbeiter
    query = Urlaubsantrag.query.join(Mitarbeiter).filter(
        Mitarbeiter.abteilung_id == abteilung_id,
        Urlaubsantrag.status == AntragStatus.GENEHMIGT,
        Urlaubsantrag.datum_von <= datum_bis,
        Urlaubsantrag.datum_bis >= datum_von,
    )
    if ausschluss_mitarbeiter_id:
        query = query.filter(
            Urlaubsantrag.mitarbeiter_id != ausschluss_mitarbeiter_id)
    return query.all()


def resturlaub_berechnen(mitarbeiter_id: int, jahr: int) -> dict:
    """
    Berechnet das Urlaubskontingent und den Resturlaub für ein Jahr.
    Gibt ein Dict mit gesamttage, genommene_tage, resttage zurück.
    """
    kontingent = Urlaubskontingent.query.filter_by(
        mitarbeiter_id=mitarbeiter_id,
        jahr=jahr
    ).first()

    if not kontingent:
        return {
            'gesamttage': 0,
            'uebertrag': 0,
            'genommene_tage': 0,
            'resttage': 0,
            'kontingent': None,
        }

    # Genommene Tage aus genehmigten Anträgen neu berechnen
    genommene = db.session.query(
        db.func.sum(Urlaubsantrag.anzahl_tage)
    ).join(
        Urlaubsantrag.abwesenheitsart
    ).filter(
        Urlaubsantrag.mitarbeiter_id == mitarbeiter_id,
        Urlaubsantrag.status == AntragStatus.GENEHMIGT,
        db.extract('year', Urlaubsantrag.datum_von) == jahr,
    ).scalar() or 0.0

    kontingent.genommene_tage = genommene
    db.session.commit()

    return {
        'gesamttage': kontingent.gesamttage,
        'uebertrag': kontingent.uebertrag,
        'genommene_tage': kontingent.genommene_tage,
        'resttage': kontingent.resttage,
        'kontingent': kontingent,
    }


def kontingent_sicherstellen(mitarbeiter_id: int, jahr: int,
                              standard_tage: float = 30.0) -> Urlaubskontingent:
    """
    Stellt sicher, dass für den Mitarbeiter und das Jahr ein Kontingent
    existiert. Legt es bei Bedarf an.
    """
    k = Urlaubskontingent.query.filter_by(
        mitarbeiter_id=mitarbeiter_id, jahr=jahr).first()
    if not k:
        k = Urlaubskontingent(
            mitarbeiter_id=mitarbeiter_id,
            jahr=jahr,
            gesamttage=standard_tage,
        )
        db.session.add(k)
        db.session.commit()
    return k


def antrag_status_farbe(status: str) -> str:
    """Gibt die Bootstrap-Farbe für einen Antragsstatus zurück."""
    farben = {
        'ausstehend': 'warning',
        'genehmigt': 'success',
        'abgelehnt': 'danger',
        'storniert': 'secondary',
    }
    return farben.get(status, 'secondary')
