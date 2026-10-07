"""Database models.

Follows the team's original ERD (User, Post, Comment) and adds a Vote table so
each user can upvote a post at most once - the feature the 2021 team could not
finish (see README, "What changed in the rebuild").
"""

from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(60), nullable=False)
    last_name = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    registered_on = db.Column(db.DateTime, nullable=False, default=utcnow)

    # Optional profile fields from the original design
    quote = db.Column(db.String(200), default="")
    color = db.Column(db.String(30), default="")
    hobbies = db.Column(db.String(200), default="")
    courses = db.Column(db.String(200), default="")

    posts = db.relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = db.relationship("Comment", back_populates="author", cascade="all, delete-orphan")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(150), nullable=False)
    course = db.Column(db.String(30), default="")  # e.g. "ITSC 3155"; optional tag
    text = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(120))
    date = db.Column(db.DateTime, nullable=False, default=utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    author = db.relationship("User", back_populates="posts")
    comments = db.relationship(
        "Comment",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="Comment.date_posted",
    )
    votes = db.relationship("Vote", back_populates="post", cascade="all, delete-orphan")

    @property
    def rating(self):
        return len(self.votes)

    def voted_by(self, user):
        return user is not None and any(v.user_id == user.id for v in self.votes)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    post = db.relationship("Post", back_populates="comments")
    author = db.relationship("User", back_populates="comments")


class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    post = db.relationship("Post", back_populates="votes")

    __table_args__ = (db.UniqueConstraint("post_id", "user_id", name="one_vote_per_user"),)
