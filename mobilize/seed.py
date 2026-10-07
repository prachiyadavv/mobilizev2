"""Demo data so the app has something to show on first run.

All names and content are fictional.
"""

from datetime import timedelta

from .extensions import db
from .models import Comment, Post, User, Vote, utcnow

USERS = [
    ("Demo", "Student", "demo@example.edu", "Programming, chess", "ITSC 3155, MATH 2164", "teal",
     "The only dumb question is the one you don't ask."),
    ("Maya", "Okafor", "maya@example.edu", "Running, photography", "ITSC 2214, STAT 2122", "", ""),
    ("Leo", "Brandt", "leo@example.edu", "Guitar", "ITSC 3155, ITSC 3146", "", ""),
    ("Priya", "Raman", "priya@example.edu", "Baking, board games", "MATH 2164, ITSC 2181", "", ""),
    ("Sam", "Whitfield", "sam@example.edu", "", "ITSC 3155", "", ""),
]

QUESTIONS = [
    # (author index, course, subject, text, days ago, voter indexes, [(commenter, text)])
    (1, "ITSC 3155", "Is the final exam cumulative?",
     "The syllabus says the final covers \"all course material\" but in lecture it sounded like it "
     "would focus on the second half (testing, design patterns). Does anyone know for sure?",
     6, [0, 2, 3, 4], [
         (2, "I asked during office hours - it's cumulative but weighted toward the second half."),
         (4, "The practice exam on Canvas also has a few UML questions from week 3."),
     ]),
    (3, "MATH 2164", "Best way to study for the eigenvalues quiz?",
     "I can compute eigenvalues fine but I keep messing up the eigenvectors when there are repeated "
     "eigenvalues. Any resources that helped you?",
     4, [0, 1, 4], [
         (0, "3Blue1Brown's linear algebra series made it click for me, especially the change of basis video."),
     ]),
    (4, None, "Where can you print for free on campus?",
     "My printing credit ran out and I need to print a 20-page report. Are there any places that "
     "don't charge?",
     3, [1, 2], [
         (1, "The library gives you a free allowance each semester - check your student account."),
         (3, "The engineering lab used to have free printing for majors, not sure if it still does."),
     ]),
    (2, "ITSC 3155", "How do you split work in the group project without merge conflicts?",
     "Our team of four keeps overwriting each other's templates. How are other teams organizing "
     "their Flask project?",
     2, [0, 1], [
         (0, "We gave each person their own feature branch and one owner per template. Pull requests only."),
     ]),
    (0, "STAT 2122", "Can we use Python instead of R for the homework?",
     "The examples are all in R but I'm much faster in pandas. Has anyone asked the instructor?",
     1, [3], []),
    (3, None, "Any quiet study spots open after midnight during finals?",
     "The library gets packed. Looking for somewhere quiet that stays open late.", 0, [], []),
]


def seed():
    if db.session.execute(db.select(User).limit(1)).scalar():
        return  # already seeded

    users = []
    for first, last, email, hobbies, courses, color, quote in USERS:
        u = User(first_name=first, last_name=last, email=email,
                 hobbies=hobbies, courses=courses, color=color, quote=quote)
        u.set_password("Demo#2021")
        users.append(u)
    db.session.add_all(users)
    db.session.flush()

    now = utcnow()
    for author, course, subject, text, days, voters, comments in QUESTIONS:
        post = Post(subject=subject, course=course or "", text=text,
                    author=users[author], date=now - timedelta(days=days, hours=2))
        db.session.add(post)
        db.session.flush()
        for v in voters:
            db.session.add(Vote(post_id=post.id, user_id=users[v].id))
        for i, (commenter, body) in enumerate(comments):
            db.session.add(Comment(content=body, post=post, author=users[commenter],
                                   date_posted=post.date + timedelta(hours=3 + i)))
    db.session.commit()
