"""
Admin Blueprint – Benutzerverwaltung, Mitarbeiter, Abteilungen,
Abwesenheitsarten, Feiertage, Urlaubskontingente
"""
from datetime import date
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, abort)
from flask_login import login_required, current_user
from extensions import db
from models import (Benutzer, Mitarbeiter, Abteilung, Abwesenheitsart,
                    Feiertag, Urlaubskontingent, Rolle)
from forms import (BenutzerForm, MitarbeiterForm, AbteilungForm,
                   AbwesenheitsartForm, FeiertagForm, KontingentForm)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Dekorator: Nur Admins haben Zugriff."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.ist_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def manager_required(f):
    """Dekorator: Manager oder Admin haben Zugriff."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.ist_manager:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ─── Übersicht ────────────────────────────────────────────────────────────────
@admin_bp.route('/')
@login_required
@admin_required
def index():
    stats = {
        'benutzer': Benutzer.query.count(),
        'mitarbeiter': Mitarbeiter.query.count(),
        'abteilungen': Abteilung.query.count(),
        'feiertage': Feiertag.query.count(),
    }
    return render_template('admin/index.html', stats=stats)


# ─── Benutzer ─────────────────────────────────────────────────────────────────
@admin_bp.route('/benutzer')
@login_required
@admin_required
def benutzer_liste():
    benutzer = Benutzer.query.order_by(Benutzer.benutzername).all()
    return render_template('admin/benutzer_liste.html', benutzer=benutzer)


@admin_bp.route('/benutzer/neu', methods=['GET', 'POST'])
@login_required
@admin_required
def benutzer_neu():
    form = BenutzerForm()
    abteilungen = Abteilung.query.order_by(Abteilung.name).all()
    form.abteilung_id.choices = [(0, '— Keine Abteilung —')] + \
                                 [(a.id, a.name) for a in abteilungen]
    if form.validate_on_submit():
        b = Benutzer(
            benutzername=form.benutzername.data,
            email=form.email.data,
            rolle=form.rolle.data,
        )
        b.passwort_setzen(form.passwort.data)
        db.session.add(b)
        db.session.flush()  # ID generieren

        m = Mitarbeiter(
            benutzer_id=b.id,
            vorname=form.vorname.data,
            nachname=form.nachname.data,
            personalnummer=form.personalnummer.data or None,
            eintrittsdatum=form.eintrittsdatum.data,
            telefon=form.telefon.data or None,
            position=form.position.data or None,
            abteilung_id=form.abteilung_id.data or None,
        )
        db.session.add(m)
        db.session.commit()
        flash(f'Benutzer {b.benutzername} wurde erfolgreich angelegt.', 'success')
        return redirect(url_for('admin.benutzer_liste'))
    return render_template('admin/benutzer_form.html', form=form, titel='Neuer Benutzer')


@admin_bp.route('/benutzer/<int:benutzer_id>/bearbeiten', methods=['GET', 'POST'])
@login_required
@admin_required
def benutzer_bearbeiten(benutzer_id):
    b = Benutzer.query.get_or_404(benutzer_id)
    m = b.mitarbeiter
    form = BenutzerForm(obj=b)
    abteilungen = Abteilung.query.order_by(Abteilung.name).all()
    form.abteilung_id.choices = [(0, '— Keine Abteilung —')] + \
                                 [(a.id, a.name) for a in abteilungen]

    if request.method == 'GET':
        form.vorname.data = m.vorname if m else ''
        form.nachname.data = m.nachname if m else ''
        form.personalnummer.data = m.personalnummer if m else ''
        form.eintrittsdatum.data = m.eintrittsdatum if m else None
        form.telefon.data = m.telefon if m else ''
        form.position.data = m.position if m else ''
        form.abteilung_id.data = m.abteilung_id if m else 0

    if form.validate_on_submit():
        b.benutzername = form.benutzername.data
        b.email = form.email.data
        b.rolle = form.rolle.data
        b.aktiv = form.aktiv.data
        if form.passwort.data:
            b.passwort_setzen(form.passwort.data)
        if m:
            m.vorname = form.vorname.data
            m.nachname = form.nachname.data
            m.personalnummer = form.personalnummer.data or None
            m.eintrittsdatum = form.eintrittsdatum.data
            m.telefon = form.telefon.data or None
            m.position = form.position.data or None
            m.abteilung_id = form.abteilung_id.data or None
        db.session.commit()
        flash('Benutzer wurde aktualisiert.', 'success')
        return redirect(url_for('admin.benutzer_liste'))
    return render_template('admin/benutzer_form.html', form=form,
                           titel='Benutzer bearbeiten', benutzer=b)


@admin_bp.route('/benutzer/<int:benutzer_id>/deaktivieren', methods=['POST'])
@login_required
@admin_required
def benutzer_deaktivieren(benutzer_id):
    b = Benutzer.query.get_or_404(benutzer_id)
    if b.id == current_user.id:
        flash('Sie können sich nicht selbst deaktivieren.', 'danger')
    else:
        b.aktiv = not b.aktiv
        db.session.commit()
        status = 'aktiviert' if b.aktiv else 'deaktiviert'
        flash(f'Benutzer wurde {status}.', 'info')
    return redirect(url_for('admin.benutzer_liste'))


# ─── Abteilungen ──────────────────────────────────────────────────────────────
@admin_bp.route('/abteilungen')
@login_required
@admin_required
def abteilung_liste():
    abteilungen = Abteilung.query.order_by(Abteilung.name).all()
    return render_template('admin/abteilung_liste.html', abteilungen=abteilungen)


@admin_bp.route('/abteilungen/neu', methods=['GET', 'POST'])
@login_required
@admin_required
def abteilung_neu():
    form = AbteilungForm()
    if form.validate_on_submit():
        a = Abteilung(name=form.name.data, beschreibung=form.beschreibung.data)
        db.session.add(a)
        db.session.commit()
        flash('Abteilung wurde angelegt.', 'success')
        return redirect(url_for('admin.abteilung_liste'))
    return render_template('admin/simple_form.html', form=form,
                           titel='Neue Abteilung', back_url=url_for('admin.abteilung_liste'))


@admin_bp.route('/abteilungen/<int:abteilung_id>/bearbeiten', methods=['GET', 'POST'])
@login_required
@admin_required
def abteilung_bearbeiten(abteilung_id):
    a = Abteilung.query.get_or_404(abteilung_id)
    form = AbteilungForm(obj=a)
    if form.validate_on_submit():
        a.name = form.name.data
        a.beschreibung = form.beschreibung.data
        db.session.commit()
        flash('Abteilung wurde aktualisiert.', 'success')
        return redirect(url_for('admin.abteilung_liste'))
    return render_template('admin/simple_form.html', form=form,
                           titel='Abteilung bearbeiten', back_url=url_for('admin.abteilung_liste'))


# ─── Abwesenheitsarten ────────────────────────────────────────────────────────
@admin_bp.route('/abwesenheitsarten')
@login_required
@admin_required
def abwesenheitsart_liste():
    arten = Abwesenheitsart.query.order_by(Abwesenheitsart.name).all()
    return render_template('admin/abwesenheitsart_liste.html', arten=arten)


@admin_bp.route('/abwesenheitsarten/neu', methods=['GET', 'POST'])
@login_required
@admin_required
def abwesenheitsart_neu():
    form = AbwesenheitsartForm()
    if form.validate_on_submit():
        art = Abwesenheitsart(
            name=form.name.data,
            farbe=form.farbe.data,
            bezahlt=form.bezahlt.data,
            zaehlt_als_urlaub=form.zaehlt_als_urlaub.data,
        )
        db.session.add(art)
        db.session.commit()
        flash('Abwesenheitsart wurde angelegt.', 'success')
        return redirect(url_for('admin.abwesenheitsart_liste'))
    return render_template('admin/simple_form.html', form=form,
                           titel='Neue Abwesenheitsart',
                           back_url=url_for('admin.abwesenheitsart_liste'))


@admin_bp.route('/abwesenheitsarten/<int:art_id>/bearbeiten', methods=['GET', 'POST'])
@login_required
@admin_required
def abwesenheitsart_bearbeiten(art_id):
    art = Abwesenheitsart.query.get_or_404(art_id)
    form = AbwesenheitsartForm(obj=art)
    if form.validate_on_submit():
        art.name = form.name.data
        art.farbe = form.farbe.data
        art.bezahlt = form.bezahlt.data
        art.zaehlt_als_urlaub = form.zaehlt_als_urlaub.data
        db.session.commit()
        flash('Abwesenheitsart wurde aktualisiert.', 'success')
        return redirect(url_for('admin.abwesenheitsart_liste'))
    return render_template('admin/simple_form.html', form=form,
                           titel='Abwesenheitsart bearbeiten',
                           back_url=url_for('admin.abwesenheitsart_liste'))


# ─── Feiertage ────────────────────────────────────────────────────────────────
@admin_bp.route('/feiertage')
@login_required
@admin_required
def feiertag_liste():
    feiertage = Feiertag.query.order_by(Feiertag.datum.desc()).all()
    return render_template('admin/feiertag_liste.html', feiertage=feiertage)


@admin_bp.route('/feiertage/neu', methods=['GET', 'POST'])
@login_required
@admin_required
def feiertag_neu():
    form = FeiertagForm()
    if form.validate_on_submit():
        f = Feiertag(
            datum=form.datum.data,
            bezeichnung=form.bezeichnung.data,
            bundesland=form.bundesland.data or None,
        )
        db.session.add(f)
        db.session.commit()
        flash('Feiertag wurde angelegt.', 'success')
        return redirect(url_for('admin.feiertag_liste'))
    return render_template('admin/simple_form.html', form=form,
                           titel='Neuer Feiertag', back_url=url_for('admin.feiertag_liste'))


@admin_bp.route('/feiertage/<int:f_id>/loeschen', methods=['POST'])
@login_required
@admin_required
def feiertag_loeschen(f_id):
    f = Feiertag.query.get_or_404(f_id)
    db.session.delete(f)
    db.session.commit()
    flash('Feiertag wurde gelöscht.', 'info')
    return redirect(url_for('admin.feiertag_liste'))


# ─── Urlaubskontingente ───────────────────────────────────────────────────────
@admin_bp.route('/kontingente')
@login_required
@manager_required
def kontingent_liste():
    jahr = request.args.get('jahr', date.today().year, type=int)
    kontingente = Urlaubskontingent.query.filter_by(
        jahr=jahr).join(Mitarbeiter).order_by(Mitarbeiter.nachname).all()
    return render_template('admin/kontingent_liste.html',
                           kontingente=kontingente, jahr=jahr)


@admin_bp.route('/kontingente/<int:k_id>/bearbeiten', methods=['GET', 'POST'])
@login_required
@admin_required
def kontingent_bearbeiten(k_id):
    k = Urlaubskontingent.query.get_or_404(k_id)
    form = KontingentForm(obj=k)
    if form.validate_on_submit():
        k.gesamttage = form.gesamttage.data
        k.uebertrag = form.uebertrag.data
        db.session.commit()
        flash('Kontingent wurde aktualisiert.', 'success')
        return redirect(url_for('admin.kontingent_liste', jahr=k.jahr))
    return render_template('admin/simple_form.html', form=form,
                           titel=f'Kontingent: {k.mitarbeiter.vollname} / {k.jahr}',
                           back_url=url_for('admin.kontingent_liste'))
