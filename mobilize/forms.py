from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, EmailField, PasswordField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp

# Password rule from the original "enforce a regex" feature: at least one
# letter, one number and one special character. The rebuild raises the minimum
# length from 6 to 8 and drops the original 12-character maximum.
PASSWORD_PATTERN = r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&]).{8,}$"
PASSWORD_MESSAGE = (
    "Use at least 8 characters, including a letter, a number "
    "and a special character (@$!%*#?&)."
)
IMAGE_TYPES = ["jpg", "jpeg", "png", "gif", "webp"]


def password_field(label):
    return PasswordField(
        label,
        validators=[DataRequired(), Regexp(PASSWORD_PATTERN, message=PASSWORD_MESSAGE)],
    )


class RegisterForm(FlaskForm):
    first_name = StringField("First name", validators=[DataRequired(), Length(max=60)])
    last_name = StringField("Last name", validators=[DataRequired(), Length(max=60)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = password_field("Password")
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])


class PostForm(FlaskForm):
    subject = StringField("Subject", validators=[DataRequired(), Length(max=150)])
    course = StringField("Course (optional)", validators=[Optional(), Length(max=30)])
    text = TextAreaField("Question", validators=[DataRequired()])
    image = FileField("Image (optional)", validators=[FileAllowed(IMAGE_TYPES, "Images only.")])
    remove_image = BooleanField("Remove current image")


class CommentForm(FlaskForm):
    content = TextAreaField("Your answer", validators=[DataRequired()])


class ProfileForm(FlaskForm):
    quote = StringField("Favorite quote", validators=[Optional(), Length(max=200)])
    color = StringField(
        "Favorite color",
        validators=[
            Optional(),
            Length(max=30),
            # Used in an inline style, so allow only color names or hex codes
            Regexp(r"^(#[0-9A-Fa-f]{3,8}|[A-Za-z]+)$", message="Use a color name or a hex code."),
        ],
    )
    hobbies = StringField("Hobbies", validators=[Optional(), Length(max=200)])
    courses = StringField("Courses this semester", validators=[Optional(), Length(max=200)])


class CredentialsForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField(
        "New password (leave blank to keep)",
        validators=[Optional(), Regexp(PASSWORD_PATTERN, message=PASSWORD_MESSAGE)],
    )


class ActionForm(FlaskForm):
    """Empty form used to put a CSRF token on button-only POSTs (vote, delete)."""
