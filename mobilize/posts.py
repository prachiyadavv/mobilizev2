import os
import uuid

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from sqlalchemy import func, or_
from werkzeug.utils import secure_filename

from .auth import login_required
from .extensions import db
from .forms import ActionForm, CommentForm, PostForm
from .models import Comment, Post, Vote

bp = Blueprint("posts", __name__)

SORTS = {"top": "Most useful", "new": "Newest", "discussed": "Most discussed"}


# --------------------------------------------------------------------------- helpers
def get_post_or_404(post_id):
    post = db.session.get(Post, post_id)
    if post is None:
        abort(404)
    return post


def get_own_post_or_403(post_id):
    post = get_post_or_404(post_id)
    if post.user_id != g.user.id:
        abort(403)
    return post


def save_image(file_storage):
    """Store an uploaded image under a random name and return that name."""
    ext = os.path.splitext(secure_filename(file_storage.filename))[1].lower()
    name = f"{uuid.uuid4().hex}{ext}"
    file_storage.save(os.path.join(current_app.config["UPLOAD_FOLDER"], name))
    return name


def delete_image(name):
    if name:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], name)
        if os.path.exists(path):
            os.remove(path)


def feed_query(author=None):
    """Build the feed query from the search, course and sort parameters."""
    q = request.args.get("q", "").strip()
    course = request.args.get("course", "").strip()
    sort = request.args.get("sort", "top")
    if sort not in SORTS:
        sort = "top"

    votes = (
        db.select(Vote.post_id, func.count(Vote.id).label("n"))
        .group_by(Vote.post_id)
        .subquery()
    )
    comments = (
        db.select(Comment.post_id, func.count(Comment.id).label("n"))
        .group_by(Comment.post_id)
        .subquery()
    )
    stmt = (
        db.select(Post)
        .outerjoin(votes, votes.c.post_id == Post.id)
        .outerjoin(comments, comments.c.post_id == Post.id)
    )
    if author is not None:
        stmt = stmt.where(Post.user_id == author.id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Post.subject.ilike(like), Post.text.ilike(like)))
    if course:
        stmt = stmt.where(Post.course.ilike(course))

    if sort == "top":
        stmt = stmt.order_by(func.coalesce(votes.c.n, 0).desc(), Post.date.desc())
    elif sort == "discussed":
        stmt = stmt.order_by(func.coalesce(comments.c.n, 0).desc(), Post.date.desc())
    else:
        stmt = stmt.order_by(Post.date.desc())

    posts = db.session.execute(stmt).scalars().all()
    return posts, {"q": q, "course": course, "sort": sort}


def course_tags():
    rows = db.session.execute(
        db.select(Post.course).where(Post.course != "").distinct().order_by(Post.course)
    ).scalars()
    return list(rows)


# --------------------------------------------------------------------------- views
@bp.route("/")
def index():
    if g.user:
        return redirect(url_for("posts.feed"))
    top = feed_query()[0][:3]
    return render_template("index.html", top=top)


@bp.route("/feed")
@login_required
def feed():
    posts, params = feed_query()
    return render_template(
        "posts/feed.html",
        posts=posts,
        params=params,
        sorts=SORTS,
        courses=course_tags(),
        title="Question feed",
        endpoint="posts.feed",
    )


@bp.route("/my-posts")
@login_required
def my_posts():
    posts, params = feed_query(author=g.user)
    return render_template(
        "posts/feed.html",
        posts=posts,
        params=params,
        sorts=SORTS,
        courses=course_tags(),
        title="My questions",
        endpoint="posts.my_posts",
    )


@bp.route("/posts/new", methods=["GET", "POST"])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(
            subject=form.subject.data.strip(),
            course=(form.course.data or "").strip().upper(),
            text=form.text.data.strip(),
            author=g.user,
        )
        if form.image.data:
            post.image_file = save_image(form.image.data)
        db.session.add(post)
        db.session.commit()
        flash("Your question is posted.", "success")
        return redirect(url_for("posts.detail", post_id=post.id))
    return render_template("posts/form.html", form=form, post=None)


@bp.route("/posts/<int:post_id>", methods=["GET", "POST"])
@login_required
def detail(post_id):
    post = get_post_or_404(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        db.session.add(Comment(content=form.content.data.strip(), post=post, author=g.user))
        db.session.commit()
        flash("Comment added.", "success")
        return redirect(url_for("posts.detail", post_id=post.id) + "#comments")
    return render_template("posts/detail.html", post=post, form=form, action=ActionForm())


@bp.route("/posts/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = get_own_post_or_403(post_id)
    form = PostForm(obj=post)
    if form.validate_on_submit():
        post.subject = form.subject.data.strip()
        post.course = (form.course.data or "").strip().upper()
        post.text = form.text.data.strip()
        if form.image.data:
            delete_image(post.image_file)
            post.image_file = save_image(form.image.data)
        elif form.remove_image.data:
            delete_image(post.image_file)
            post.image_file = None
        db.session.commit()
        flash("Question updated.", "success")
        return redirect(url_for("posts.detail", post_id=post.id))
    return render_template("posts/form.html", form=form, post=post)


@bp.route("/posts/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = get_own_post_or_403(post_id)
    if not ActionForm().validate_on_submit():
        abort(400)
    delete_image(post.image_file)
    db.session.delete(post)
    db.session.commit()
    flash("Question deleted.", "info")
    return redirect(url_for("posts.feed"))


@bp.route("/posts/<int:post_id>/vote", methods=["POST"])
@login_required
def vote(post_id):
    """Toggle the current user's upvote: vote once, or undo an existing vote."""
    post = get_post_or_404(post_id)
    if not ActionForm().validate_on_submit():
        abort(400)
    existing = db.session.execute(
        db.select(Vote).filter_by(post_id=post.id, user_id=g.user.id)
    ).scalar()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(Vote(post_id=post.id, user_id=g.user.id))
    db.session.commit()
    return redirect(url_for("posts.detail", post_id=post.id))


@bp.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
