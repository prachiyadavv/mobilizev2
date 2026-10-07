"""Mobilize: a Q&A discussion board for university students.

Students post questions about a course or about campus life, answer each
other in the comments, and upvote the questions that are most useful, so the
feed surfaces what people actually need to know.
"""

import os

import click
from flask import Flask, g, session

from .extensions import csrf, db


def create_app(test_config=None):
    """Application factory."""
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("MOBILIZE_SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL",
            "sqlite:///" + os.path.join(app.instance_path, "mobilize.db"),
        ),
        UPLOAD_FOLDER=os.path.join(app.instance_path, "uploads"),
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,  # 4 MB image limit
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)

    from . import account, auth, posts
    from .models import User

    app.register_blueprint(auth.bp)
    app.register_blueprint(posts.bp)
    app.register_blueprint(account.bp)

    @app.before_request
    def load_logged_in_user():
        user_id = session.get("user_id")
        g.user = db.session.get(User, user_id) if user_id else None

    @app.cli.command("init-db")
    def init_db_command():
        """Create all database tables."""
        db.create_all()
        click.echo("Initialized the database.")

    @app.cli.command("seed")
    def seed_command():
        """Load demo users, questions and comments."""
        from .seed import seed

        db.create_all()
        seed()
        click.echo("Seeded demo data. Log in as demo@example.edu / Demo#2021")

    with app.app_context():
        db.create_all()

    return app
