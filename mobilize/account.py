from flask import Blueprint, abort, flash, g, redirect, render_template, url_for

from .auth import login_required
from .extensions import db
from .forms import CredentialsForm, ProfileForm
from .models import User

bp = Blueprint("account", __name__)


@bp.route("/users/<int:user_id>")
@login_required
def profile(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    return render_template("account/profile.html", person=user)


@bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = ProfileForm(obj=g.user)
    if form.validate_on_submit():
        form.populate_obj(g.user)
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("account.profile", user_id=g.user.id))
    return render_template("account/edit_profile.html", form=form)


@bp.route("/credentials", methods=["GET", "POST"])
@login_required
def credentials():
    """Update email and/or password.

    The 2021 version compared and stored the password in plain text. Here the
    current password is checked against its hash and the new one is hashed.
    """
    form = CredentialsForm(email=g.user.email)
    if form.validate_on_submit():
        if not g.user.check_password(form.current_password.data):
            form.current_password.errors.append("Current password is incorrect.")
        else:
            email = form.email.data.strip().lower()
            taken = db.session.execute(
                db.select(User).where(User.email == email, User.id != g.user.id)
            ).scalar()
            if taken:
                form.email.errors.append("That email is already in use.")
            else:
                g.user.email = email
                if form.new_password.data:
                    g.user.set_password(form.new_password.data)
                db.session.commit()
                flash("Login credentials updated.", "success")
                return redirect(url_for("account.credentials"))
    return render_template("account/credentials.html", form=form)
