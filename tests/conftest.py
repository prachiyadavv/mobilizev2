import pytest

from mobilize import create_app
from mobilize.extensions import db


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test",
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })
    (tmp_path / "uploads").mkdir(exist_ok=True)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


GOOD_PASSWORD = "Secret#123"


def register(client, email="ana@example.edu", password=GOOD_PASSWORD, first="Ana", last="Lee"):
    return client.post("/register", data={
        "first_name": first, "last_name": last, "email": email,
        "password": password, "confirm": password,
    }, follow_redirects=True)


def login(client, email="ana@example.edu", password=GOOD_PASSWORD):
    return client.post("/login", data={"email": email, "password": password},
                       follow_redirects=True)


def logout(client):
    return client.get("/logout", follow_redirects=True)


def create_post(client, subject="Is the final cumulative?", text="Asking for a friend.",
                course="ITSC 3155", **extra):
    data = {"subject": subject, "text": text, "course": course, **extra}
    return client.post("/posts/new", data=data, content_type="multipart/form-data",
                       follow_redirects=True)
