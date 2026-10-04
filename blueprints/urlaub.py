"""
Urlaub Blueprint – Anträge erstellen, anzeigen, stornieren, genehmigen/ablehnen
"""
from datetime import date
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, abort)
from flask_login import login_required, current_user
from extensions import db
from models import (Urlaubsantrag, Mitarbeiter, Abwesenheitsart,
                    AntragStatus, Urlaubskontingent)
from utils import (arbeitstage_berechnen, ueberschneidung_pruefen,
                   resturlaub_berechnen, kontingent_sicherstellen,
                   antrag_status_farbe)
from forms import UrlaubsantragForm, AblehnenForm

urlaub_bp = Blueprint('urlaub', __name__, url_prefix='/urlaub')


@urlaub_bp.route('/neu', methods=['GET', 'POST'])
@login_required
def neu():
    form = UrlaubsantragForm()
    arten = Abwesenheitsart.query.order_by(Abwesenheitsart.name).all()
    form.abwesenheitsart_id.choices = [(a.id, a.name) for a in arten]

    mitarbeiter = current_user.mitarbeiter
    heute = date.today()
    kontingent_sicherstellen(mitarbeiter.id, heute.year)
    urlaub_info = resturlaub_berechnen(mitarbeiter.id, heute.year)

    if form.validate_on_submit():
        datum_von = form.datum_von.data
        datum_bis = form.datum_bis.data

        if datum_bis < datum_von:
            flash('Das Enddatum darf nicht vor dem Startdatum liegen.', 'danger')
            return render_template('urlaub/neu.html', form=form,
                                   urlaub_info=urlaub_info)

        # Arbeitstage berechnen
        tage = arbeitstage_berechnen(datum_von, datum_bis)
        if tage == 0:
            flash('Der gewählte Zeitraum enthält keine Arbeitstage.', 'warning')
            return render_template('urlaub/neu.html', form=form,
                                   urlaub_info=urlaub_info)

        # Überschneidung prüfen
        ueberschneidungen = ueberschneidung_pruefen(mitarbeiter.id,
                                                     datum_von, datum_bis)
        if ueberschneidungen:
            flash('Es existiert bereits ein Antrag für diesen Zeitraum.', 'danger')
            return render_template('urlaub/neu.html', form=form,
                                   urlaub_info=urlaub_info)

        # Resturlaub prüfen (nur wenn als Urlaub zählt)
        art = Abwesenheitsart.query.get(form.abwesenheitsart_id.data)
        if art and art.zaehlt_als_urlaub:
            if tage > urlaub_info['resttage']:
                flash(f'Nicht genug Resturlaub. Verfügbar: '
                      f'{urlaub_info["resttage"]:.1f} Tage, beantragt: '
                      f'{tage:.1f} Tage.', 'danger')
                return render_template('urlaub/neu.html', form=form,
                                       urlaub_info=urlaub_info)

        antrag = Urlaubsantrag(
            mitarbeiter_id=mitarbeiter.id,
            abwesenheitsart_id=form.abwesenheitsart_id.data,
            datum_von=datum_von,
            datum_bis=datum_bis,
            anzahl_tage=tage,
            kommentar=form.kommentar.data,
        )
        db.session.add(antrag)
        db.session.commit()
        flash(f'Urlaubsantrag für {tage:.0f} Arbeitstage erfolgreich eingereicht.', 'success')
        return redirect(url_for('urlaub.meine_antraege'))

    return render_template('urlaub/neu.html', form=form, urlaub_info=urlaub_info)


@urlaub_bp.route('/meine-antraege')
@login_required
def meine_antraege():
    mitarbeiter = current_user.mitarbeiter
    antraege = Urlaubsantrag.query.filter_by(
        mitarbeiter_id=mitarbeiter.id
    ).order_by(Urlaubsantrag.datum_von.desc()).all()
    heute = date.today()
    urlaub_info = resturlaub_berechnen(mitarbeiter.id, heute.year)
    return render_template('urlaub/meine_antraege.html',
                           antraege=antraege, urlaub_info=urlaub_info,
                           antrag_status_farbe=antrag_status_farbe)


@urlaub_bp.route('/<int:antrag_id>')
@login_required
def detail(antrag_id):
    antrag = Urlaubsantrag.query.get_or_404(antrag_id)
    # Nur eigener Antrag oder Manager
    if (antrag.mitarbeiter_id != current_user.mitarbeiter.id
            and not current_user.ist_manager):
        abort(403)
    return render_template('urlaub/detail.html', antrag=antrag,
                           antrag_status_farbe=antrag_status_farbe)


@urlaub_bp.route('/<int:antrag_id>/stornieren', methods=['POST'])
@login_required
def stornieren(antrag_id):
    antrag = Urlaubsantrag.query.get_or_404(antrag_id)
    if antrag.mitarbeiter_id != current_user.mitarbeiter.id:
        abort(403)
    if antrag.status not in (AntragStatus.AUSSTEHEND, AntragStatus.GENEHMIGT):
        flash('Dieser Antrag kann nicht storniert werden.', 'warning')
        return redirect(url_for('urlaub.meine_antraege'))
    antrag.status = AntragStatus.STORNIERT
    db.session.commit()
    flash('Urlaubsantrag wurde storniert.', 'info')
    return redirect(url_for('urlaub.meine_antraege'))


@urlaub_bp.route('/<int:antrag_id>/genehmigen', methods=['POST'])
@login_required
def genehmigen(antrag_id):
    if not current_user.ist_manager:
        abort(403)
    antrag = Urlaubsantrag.query.get_or_404(antrag_id)
    if antrag.status != AntragStatus.AUSSTEHEND:
        flash('Dieser Antrag kann nicht genehmigt werden.', 'warning')
        return redirect(url_for('urlaub.alle_antraege'))
    antrag.status = AntragStatus.GENEHMIGT
    antrag.genehmigt_von_id = current_user.mitarbeiter.id
    db.session.commit()
    flash(f'Antrag von {antrag.mitarbeiter.vollname} wurde genehmigt.', 'success')
    return redirect(request.referrer or url_for('urlaub.alle_antraege'))


@urlaub_bp.route('/<int:antrag_id>/ablehnen', methods=['GET', 'POST'])
@login_required
def ablehnen(antrag_id):
    if not current_user.ist_manager:
        abort(403)
    antrag = Urlaubsantrag.query.get_or_404(antrag_id)
    form = AblehnenForm()
    if form.validate_on_submit():
        antrag.status = AntragStatus.ABGELEHNT
        antrag.genehmigt_von_id = current_user.mitarbeiter.id
        antrag.ablehnungsgrund = form.grund.data
        db.session.commit()
        flash(f'Antrag von {antrag.mitarbeiter.vollname} wurde abgelehnt.', 'warning')
        return redirect(url_for('urlaub.alle_antraege'))
    return render_template('urlaub/ablehnen.html', antrag=antrag, form=form)


@urlaub_bp.route('/alle')
@login_required
def alle_antraege():
    if not current_user.ist_manager:
        abort(403)

    status_filter = request.args.get('status', '')
    mitarbeiter_filter = request.args.get('mitarbeiter_id', type=int)

    query = Urlaubsantrag.query.join(Mitarbeiter)

    if not current_user.ist_admin and current_user.mitarbeiter.abteilung_id:
        query = query.filter(
            Mitarbeiter.abteilung_id == current_user.mitarbeiter.abteilung_id)

    if status_filter:
        query = query.filter(Urlaubsantrag.status == status_filter)
    if mitarbeiter_filter:
        query = query.filter(Urlaubsantrag.mitarbeiter_id == mitarbeiter_filter)

    antraege = query.order_by(Urlaubsantrag.erstellt_am.desc()).all()

    alle_mitarbeiter = Mitarbeiter.query.order_by(
        Mitarbeiter.nachname).all()

    return render_template(
        'urlaub/alle_antraege.html',
        antraege=antraege,
        alle_mitarbeiter=alle_mitarbeiter,
        status_filter=status_filter,
        mitarbeiter_filter=mitarbeiter_filter,
        antrag_status_farbe=antrag_status_farbe,
        AntragStatus=AntragStatus,
    )
