"""Tests written from the team's 2021 user stories and acceptance criteria."""

import io

from conftest import GOOD_PASSWORD, create_post, login, logout, register

from mobilize.extensions import db
from mobilize.models import Post, User, Vote


# ---------------------------------------------------------------- register / sign in
def test_register_logs_user_in_and_hashes_password(client):
    resp = register(client)
    assert b"Welcome to Mobilize, Ana!" in resp.data
    user = db.session.execute(db.select(User)).scalar_one()
    assert user.password_hash != GOOD_PASSWORD
    assert user.check_password(GOOD_PASSWORD)


def test_register_rejects_weak_password(client):
    resp = register(client, password="password")
    assert b"special character" in resp.data
    assert db.session.execute(db.select(User)).first() is None


def test_register_rejects_duplicate_email(client):
    register(client)
    logout(client)
    resp = register(client, email="ANA@example.edu")
    assert b"already exists" in resp.data


def test_login_and_logout(client):
    register(client)
    logout(client)
    assert b"Incorrect email or password" in login(client, password="Wrong#999").data
    resp = login(client)
    assert b"Question feed" in resp.data
    resp = logout(client)
    assert b"logged out" in resp.data


def test_feed_requires_login(client):
    resp = client.get("/feed")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# ---------------------------------------------------------------- posts
def test_create_and_view_post(client):
    register(client)
    resp = create_post(client)
    assert b"Your question is posted." in resp.data
    assert b"Is the final cumulative?" in resp.data
    assert b"Ana Lee" in resp.data  # author shown on the single-post page


def test_create_post_with_image(client, app):
    register(client)
    png = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    resp = create_post(client, image=(png, "diagram.png"))
    post = db.session.execute(db.select(Post)).scalar_one()
    assert post.image_file and post.image_file.endswith(".png")
    assert post.image_file != "diagram.png"  # stored under a random name
    assert client.get(f"/uploads/{post.image_file}").status_code == 200
    assert b"Image attached" in resp.data


def test_create_post_rejects_non_image(client):
    register(client)
    resp = create_post(client, image=(io.BytesIO(b"x"), "script.exe"))
    assert b"Images only." in resp.data


def test_edit_post(client):
    register(client)
    create_post(client)
    resp = client.post("/posts/1/edit", data={"subject": "Updated subject", "text": "New text"},
                       content_type="multipart/form-data", follow_redirects=True)
    assert b"Question updated." in resp.data
    assert b"Updated subject" in resp.data


def test_delete_post_removes_comments_and_votes(client):
    register(client)
    create_post(client)
    client.post("/posts/1", data={"content": "An answer"})
    client.post("/posts/1/vote")
    resp = client.post("/posts/1/delete", follow_redirects=True)
    assert b"Question deleted." in resp.data
    assert db.session.execute(db.select(Post)).first() is None
    assert db.session.execute(db.select(Vote)).first() is None


def test_only_author_can_edit_or_delete(client):
    register(client)
    create_post(client)
    logout(client)
    register(client, email="ben@example.edu", first="Ben")
    assert client.get("/posts/1/edit").status_code == 403
    assert client.post("/posts/1/delete").status_code == 403


def test_my_posts_only_shows_mine(client):
    register(client)
    create_post(client, subject="Ana's question")
    logout(client)
    register(client, email="ben@example.edu", first="Ben")
    create_post(client, subject="Ben's question")
    resp = client.get("/my-posts")
    assert b"Ben&#39;s question" in resp.data
    assert b"Ana&#39;s question" not in resp.data
    assert b"Ana&#39;s question" in client.get("/feed").data


# ---------------------------------------------------------------- comments
def test_comment_on_post(client):
    register(client)
    create_post(client)
    resp = client.post("/posts/1", data={"content": "It is cumulative."}, follow_redirects=True)
    assert b"Comment added." in resp.data
    assert b"It is cumulative." in resp.data
    assert b"1 answer" in resp.data


# ---------------------------------------------------------------- rating
def test_upvote_once_then_undo(client):
    register(client)
    create_post(client)
    post = db.session.get(Post, 1)

    client.post("/posts/1/vote")
    db.session.refresh(post)
    assert post.rating == 1

    client.post("/posts/1/vote")  # second click undoes, never double counts
    db.session.refresh(post)
    assert post.rating == 0


def test_votes_from_different_users_add_up(client):
    register(client)
    create_post(client)
    client.post("/posts/1/vote")
    logout(client)
    register(client, email="ben@example.edu", first="Ben")
    client.post("/posts/1/vote")
    assert db.session.get(Post, 1).rating == 2


# ---------------------------------------------------------------- feed: search, filter, sort
def test_feed_sorts_by_most_useful_and_filters(client):
    register(client)
    create_post(client, subject="Low interest", course="MATH 2164")
    create_post(client, subject="Popular question", course="ITSC 3155")
    client.post("/posts/2/vote")

    html = client.get("/feed?sort=top").data.decode()
    assert html.index("Popular question") < html.index("Low interest")

    html = client.get("/feed?sort=new").data.decode()
    assert html.index("Popular question") < html.index("Low interest")  # newest first

    html = client.get("/feed?course=MATH 2164").data.decode()
    assert "Low interest" in html and "Popular question" not in html

    html = client.get("/feed?q=popular").data.decode()
    assert "Popular question" in html and "Low interest" not in html


# ---------------------------------------------------------------- profile & credentials
def test_update_profile(client):
    register(client)
    resp = client.post("/profile/edit", data={
        "quote": "Ask early.", "courses": "ITSC 3155", "hobbies": "Chess", "color": "teal",
    }, follow_redirects=True)
    assert b"Profile updated." in resp.data
    assert b"Ask early." in resp.data


def test_profile_color_rejects_css_injection(client):
    register(client)
    resp = client.post("/profile/edit", data={"color": "red; background:url(x)"})
    assert b"Use a color name or a hex code." in resp.data


def test_update_credentials_requires_current_password(client):
    register(client)
    resp = client.post("/credentials", data={
        "email": "new@example.edu", "current_password": "Wrong#999", "new_password": "",
    })
    assert b"Current password is incorrect." in resp.data


def test_update_email_and_password_stays_hashed(client):
    register(client)
    resp = client.post("/credentials", data={
        "email": "new@example.edu", "current_password": GOOD_PASSWORD,
        "new_password": "Changed#456",
    }, follow_redirects=True)
    assert b"Login credentials updated." in resp.data
    user = db.session.execute(db.select(User)).scalar_one()
    assert user.email == "new@example.edu"
    assert user.password_hash != "Changed#456"
    logout(client)
    assert b"Question feed" in login(client, "new@example.edu", "Changed#456").data


def test_seed_command(app):
    result = app.test_cli_runner().invoke(args=["seed"])
    assert "Seeded demo data" in result.output
    assert db.session.execute(db.select(db.func.count(Post.id))).scalar() == 6
