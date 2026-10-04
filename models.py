from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, login_manager


# ─── Benutzerrolle Enum ───────────────────────────────────────────────────────
class Rolle:
    ADMIN = 'admin'
    MANAGER = 'manager'
    MITARBEITER = 'mitarbeiter'

    CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Abteilungsleiter'),
        ('mitarbeiter', 'Mitarbeiter'),
    ]


# ─── Antragsstatus Enum ────────────────────────────────────────────────────────
class AntragStatus:
    AUSSTEHEND = 'ausstehend'
    GENEHMIGT = 'genehmigt'
    ABGELEHNT = 'abgelehnt'
    STORNIERT = 'storniert'

    CHOICES = [
        ('ausstehend', 'Ausstehend'),
        ('genehmigt', 'Genehmigt'),
        ('abgelehnt', 'Abgelehnt'),
        ('storniert', 'Storniert'),
    ]


# ─── Benutzer ─────────────────────────────────────────────────────────────────
class Benutzer(UserMixin, db.Model):
    __tablename__ = 'benutzer'

    id = db.Column(db.Integer, primary_key=True)
    benutzername = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    passwort_hash = db.Column(db.String(256), nullable=False)
    rolle = db.Column(db.String(20), nullable=False, default=Rolle.MITARBEITER)
    aktiv = db.Column(db.Boolean, default=True)
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)

    # Beziehung zum Mitarbeiter-Profil
    mitarbeiter = db.relationship('Mitarbeiter', back_populates='benutzer',
                                  uselist=False, cascade='all, delete-orphan')

    def passwort_setzen(self, passwort):
        self.passwort_hash = generate_password_hash(passwort)

    def passwort_pruefen(self, passwort):
        return check_password_hash(self.passwort_hash, passwort)

    @property
    def ist_admin(self):
        return self.rolle == Rolle.ADMIN

    @property
    def ist_manager(self):
        return self.rolle in (Rolle.ADMIN, Rolle.MANAGER)

    def __repr__(self):
        return f'<Benutzer {self.benutzername}>'


@login_manager.user_loader
def load_user(user_id):
    return Benutzer.query.get(int(user_id))


# ─── Abteilung ────────────────────────────────────────────────────────────────
class Abteilung(db.Model):
    __tablename__ = 'abteilung'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    beschreibung = db.Column(db.String(255))

    mitarbeiter = db.relationship('Mitarbeiter', back_populates='abteilung')

    def __repr__(self):
        return f'<Abteilung {self.name}>'


# ─── Mitarbeiter ──────────────────────────────────────────────────────────────
class Mitarbeiter(db.Model):
    __tablename__ = 'mitarbeiter'

    id = db.Column(db.Integer, primary_key=True)
    benutzer_id = db.Column(db.Integer, db.ForeignKey('benutzer.id',
                            ondelete='CASCADE'), unique=True, nullable=False)
    abteilung_id = db.Column(db.Integer, db.ForeignKey('abteilung.id'),
                             nullable=True)
    vorname = db.Column(db.String(80), nullable=False)
    nachname = db.Column(db.String(80), nullable=False)
    personalnummer = db.Column(db.String(20), unique=True, nullable=True)
    eintrittsdatum = db.Column(db.Date, nullable=True)
    telefon = db.Column(db.String(30), nullable=True)
    position = db.Column(db.String(100), nullable=True)

    benutzer = db.relationship('Benutzer', back_populates='mitarbeiter')
    abteilung = db.relationship('Abteilung', back_populates='mitarbeiter')
    urlaubsantraege = db.relationship('Urlaubsantrag', back_populates='mitarbeiter',
                                      cascade='all, delete-orphan',
                                      foreign_keys='Urlaubsantrag.mitarbeiter_id')
    urlaubskontingente = db.relationship('Urlaubskontingent',
                                         back_populates='mitarbeiter',
                                         cascade='all, delete-orphan')

    @property
    def vollname(self):
        return f'{self.vorname} {self.nachname}'

    def __repr__(self):
        return f'<Mitarbeiter {self.vollname}>'


# ─── Abwesenheitsart ──────────────────────────────────────────────────────────
class Abwesenheitsart(db.Model):
    __tablename__ = 'abwesenheitsart'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    farbe = db.Column(db.String(7), default='#4A90D9')  # Hex-Farbe für Kalender
    bezahlt = db.Column(db.Boolean, default=True)
    zaehlt_als_urlaub = db.Column(db.Boolean, default=True)

    antraege = db.relationship('Urlaubsantrag', back_populates='abwesenheitsart')

    def __repr__(self):
        return f'<Abwesenheitsart {self.name}>'


# ─── Urlaubsantrag ────────────────────────────────────────────────────────────
class Urlaubsantrag(db.Model):
    __tablename__ = 'urlaubsantrag'

    id = db.Column(db.Integer, primary_key=True)
    mitarbeiter_id = db.Column(db.Integer, db.ForeignKey('mitarbeiter.id',
                               ondelete='CASCADE'), nullable=False)
    abwesenheitsart_id = db.Column(db.Integer,
                                   db.ForeignKey('abwesenheitsart.id'),
                                   nullable=False)
    genehmigt_von_id = db.Column(db.Integer,
                                 db.ForeignKey('mitarbeiter.id'), nullable=True)
    datum_von = db.Column(db.Date, nullable=False)
    datum_bis = db.Column(db.Date, nullable=False)
    anzahl_tage = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False,
                       default=AntragStatus.AUSSTEHEND)
    kommentar = db.Column(db.Text, nullable=True)
    ablehnungsgrund = db.Column(db.Text, nullable=True)
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    aktualisiert_am = db.Column(db.DateTime, default=datetime.utcnow,
                                onupdate=datetime.utcnow)

    mitarbeiter = db.relationship('Mitarbeiter', back_populates='urlaubsantraege',
                                  foreign_keys=[mitarbeiter_id])
    genehmigt_von = db.relationship('Mitarbeiter',
                                    foreign_keys=[genehmigt_von_id])
    abwesenheitsart = db.relationship('Abwesenheitsart',
                                      back_populates='antraege')

    def __repr__(self):
        return f'<Urlaubsantrag {self.id} - {self.status}>'


# ─── Urlaubskontingent ────────────────────────────────────────────────────────
class Urlaubskontingent(db.Model):
    __tablename__ = 'urlaubskontingent'

    id = db.Column(db.Integer, primary_key=True)
    mitarbeiter_id = db.Column(db.Integer, db.ForeignKey('mitarbeiter.id',
                               ondelete='CASCADE'), nullable=False)
    jahr = db.Column(db.Integer, nullable=False)
    gesamttage = db.Column(db.Float, nullable=False, default=30.0)
    genommene_tage = db.Column(db.Float, nullable=False, default=0.0)
    uebertrag = db.Column(db.Float, nullable=False, default=0.0)

    mitarbeiter = db.relationship('Mitarbeiter',
                                  back_populates='urlaubskontingente')

    __table_args__ = (
        db.UniqueConstraint('mitarbeiter_id', 'jahr',
                            name='uq_mitarbeiter_jahr'),
    )

    @property
    def resttage(self):
        return self.gesamttage + self.uebertrag - self.genommene_tage

    def __repr__(self):
        return f'<Urlaubskontingent {self.mitarbeiter_id} / {self.jahr}>'


# ─── Feiertag ─────────────────────────────────────────────────────────────────
class Feiertag(db.Model):
    __tablename__ = 'feiertag'

    id = db.Column(db.Integer, primary_key=True)
    datum = db.Column(db.Date, nullable=False, unique=True)
    bezeichnung = db.Column(db.String(100), nullable=False)
    bundesland = db.Column(db.String(50), nullable=True)  # None = bundesweit

    def __repr__(self):
        return f'<Feiertag {self.bezeichnung} am {self.datum}>'
