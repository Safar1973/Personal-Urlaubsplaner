"""
Datenbank-Initialisierung und Beispieldaten für den Personal-Urlaubsplaner.
Führen Sie dieses Skript einmalig aus: python init_db.py
"""
from datetime import date, timedelta
from app import create_app
from extensions import db
from models import (Benutzer, Mitarbeiter, Abteilung, Abwesenheitsart,
                    Feiertag, Urlaubskontingent)


def init_db():
    app = create_app()
    with app.app_context():
        print("Erstelle Datenbanktabellen...")
        db.create_all()

        # Prüfen ob Daten bereits vorhanden
        if Benutzer.query.first():
            print("Datenbank enthält bereits Daten. Abbruch.")
            return

        print("Lege Stammdaten an...")

        # ── Abteilungen ──────────────────────────────────────────────────────
        abt_it = Abteilung(name='IT & Entwicklung',
                           beschreibung='Software-Entwicklung und IT-Infrastruktur')
        abt_hr = Abteilung(name='Personal & HR',
                           beschreibung='Personalverwaltung und Recruiting')
        abt_vt = Abteilung(name='Vertrieb',
                           beschreibung='Vertrieb und Kundenbetreuung')
        db.session.add_all([abt_it, abt_hr, abt_vt])
        db.session.flush()

        # ── Abwesenheitsarten ────────────────────────────────────────────────
        arten = [
            Abwesenheitsart(name='Jahresurlaub',        farbe='#4A90D9',
                            bezahlt=True, zaehlt_als_urlaub=True),
            Abwesenheitsart(name='Krankheit',            farbe='#E74C3C',
                            bezahlt=True,  zaehlt_als_urlaub=False),
            Abwesenheitsart(name='Sonderurlaub',         farbe='#9B59B6',
                            bezahlt=True,  zaehlt_als_urlaub=False),
            Abwesenheitsart(name='Unbezahlter Urlaub',   farbe='#95A5A6',
                            bezahlt=False, zaehlt_als_urlaub=True),
            Abwesenheitsart(name='Homeoffice',           farbe='#2ECC71',
                            bezahlt=True,  zaehlt_als_urlaub=False),
        ]
        db.session.add_all(arten)
        db.session.flush()

        # ── Feiertage 2025 & 2026 (bundesweit) ───────────────────────────────
        feiertage_daten = [
            # 2025
            (date(2025, 1, 1),  'Neujahr'),
            (date(2025, 4, 18), 'Karfreitag'),
            (date(2025, 4, 21), 'Ostermontag'),
            (date(2025, 5, 1),  'Tag der Arbeit'),
            (date(2025, 5, 29), 'Christi Himmelfahrt'),
            (date(2025, 6, 9),  'Pfingstmontag'),
            (date(2025, 10, 3), 'Tag der Deutschen Einheit'),
            (date(2025, 12, 25),'1. Weihnachtstag'),
            (date(2025, 12, 26),'2. Weihnachtstag'),
            # 2026
            (date(2026, 1, 1),  'Neujahr'),
            (date(2026, 4, 3),  'Karfreitag'),
            (date(2026, 4, 6),  'Ostermontag'),
            (date(2026, 5, 1),  'Tag der Arbeit'),
            (date(2026, 5, 14), 'Christi Himmelfahrt'),
            (date(2026, 5, 25), 'Pfingstmontag'),
            (date(2026, 10, 3), 'Tag der Deutschen Einheit'),
            (date(2026, 12, 25),'1. Weihnachtstag'),
            (date(2026, 12, 26),'2. Weihnachtstag'),
        ]
        for datum, bezeichnung in feiertage_daten:
            db.session.add(Feiertag(datum=datum, bezeichnung=bezeichnung))
        db.session.flush()

        # ── Benutzer & Mitarbeiter ────────────────────────────────────────────
        def benutzer_anlegen(benutzername, email, passwort, rolle,
                             vorname, nachname, abteilung, personalnr,
                             position, eintritt):
            b = Benutzer(benutzername=benutzername, email=email, rolle=rolle)
            b.passwort_setzen(passwort)
            db.session.add(b)
            db.session.flush()
            m = Mitarbeiter(
                benutzer_id=b.id,
                vorname=vorname,
                nachname=nachname,
                personalnummer=personalnr,
                eintrittsdatum=eintritt,
                position=position,
                abteilung_id=abteilung.id if abteilung else None,
            )
            db.session.add(m)
            db.session.flush()
            return b, m

        # Admin
        b_admin, m_admin = benutzer_anlegen(
            'admin', 'admin@firma.de', 'admin123', 'admin',
            'Max', 'Mustermann', abt_it, 'P001',
            'System-Administrator', date(2020, 1, 1))

        # Manager
        b_mgr, m_mgr = benutzer_anlegen(
            'mueller', 'mueller@firma.de', 'manager123', 'manager',
            'Anna', 'Müller', abt_hr, 'P002',
            'HR-Leiterin', date(2019, 3, 15))

        # Mitarbeiter 1
        b_m1, m_m1 = benutzer_anlegen(
            'schmidt', 'schmidt@firma.de', 'pass123', 'mitarbeiter',
            'Lukas', 'Schmidt', abt_it, 'P003',
            'Backend-Entwickler', date(2021, 6, 1))

        # Mitarbeiter 2
        b_m2, m_m2 = benutzer_anlegen(
            'wagner', 'wagner@firma.de', 'pass123', 'mitarbeiter',
            'Sara', 'Wagner', abt_vt, 'P004',
            'Account-Managerin', date(2022, 9, 1))

        db.session.flush()

        # ── Urlaubskontingente für 2025 & 2026 ───────────────────────────────
        jahr = date.today().year
        for m in [m_admin, m_mgr, m_m1, m_m2]:
            for j in [2025, 2026]:
                db.session.add(Urlaubskontingent(
                    mitarbeiter_id=m.id,
                    jahr=j,
                    gesamttage=30.0,
                    uebertrag=2.0 if j == jahr else 0.0,
                ))

        db.session.commit()
        print("\n✅ Datenbank erfolgreich initialisiert!")
        print("\nDemo-Zugangsdaten:")
        print("  Administrator: admin / admin123")
        print("  Manager:       mueller / manager123")
        print("  Mitarbeiter:   schmidt / pass123")
        print("  Mitarbeiter:   wagner / pass123")
        print("\nAnwendung starten: python app.py")
        print("Browser:           http://localhost:5000")


if __name__ == '__main__':
    init_db()
