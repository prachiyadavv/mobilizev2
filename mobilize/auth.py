import functools

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from .extensions import db
from .forms import LoginForm, RegisterForm
from .models import User

bp = Blueprint("auth", __name__)


def login_required(view):
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)

    return wrapped


@bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if db.session.execute(db.select(User).filter_by(email=email)).scalar():
            form.email.errors.append("An account with this email already exists.")
        else:
            user = User(
                first_name=form.first_name.data.strip(),
                last_name=form.last_name.data.strip(),
                email=email,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            session.clear()
            session["user_id"] = user.id
            flash(f"Welcome to Mobilize, {user.first_name}!", "success")
            return redirect(url_for("posts.feed"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = db.session.execute(db.select(User).filter_by(email=email)).scalar()
        if user and user.check_password(form.password.data):
            session.clear()
            session["user_id"] = user.id
            next_url = request.args.get("next", "")
            # Only follow local redirects
            if not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("posts.feed")
            return redirect(next_url)
        flash("Incorrect email or password.", "error")
    return render_template("auth/login.html", form=form)


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("posts.index"))
