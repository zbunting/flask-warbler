import os
from dotenv import load_dotenv

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, CSRFForm, EditProfile
from models import db, dbx, User, Message
from werkzeug.exceptions import Unauthorized

load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SQLALCHEMY_RECORD_QUERIES'] = True
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
toolbar = DebugToolbarExtension(app)

db.init_app(app)


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = db.session.get(User, session[CURR_USER_KEY])

    else:
        g.user = None


@app.before_request
def add_csrf_form_to_g():
    """Add a CSRF form to g."""

    g.csrf_form = CSRFForm()


@app.before_request
def add_request_url_to_g():
    """Add the url the request came from to g."""

    g.request_url = request.url


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Log out user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    if g.user:
        flash('Cannot sign up while logged in')
        return redirect(f"/users/{g.user.id}")

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            db.session.rollback()
            flash("Username already taken", 'danger')
            return render_template('users/signup.jinja', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.jinja', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login and redirect to homepage on success."""

    if g.user:
        flash('Already logged in!')
        return redirect(f"/users/{g.user.id}")

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(
            form.username.data,
            form.password.data,
        )

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.jinja', form=form)


@app.post('/logout')
def logout():
    """Handle logout of user and redirect to homepage."""

    form = g.csrf_form

    if form.validate_on_submit():
        do_logout()
        flash('Logged out!')
        return redirect('/login')

    raise Unauthorized()


##############################################################################
# General user routes:

@app.get('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    search = request.args.get('q')

    if not search:
        q = db.select(User).order_by(User.id.desc())

    else:
        q = db.select(User).filter(User.username.like(f"%{search}%"))

    users = dbx(q).scalars().all()

    return render_template('users/index.jinja', users=users)


@app.get('/users/<int:user_id>')
def show_user(user_id):
    """Show user profile."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = db.get_or_404(User, user_id)

    return render_template('users/show.jinja', user=user)


@app.get('/users/<int:user_id>/likes')
def show_liked_messages(user_id):
    """
    Show all user's liked messages
    Only `user_id` can see their likes
    """

    if (not g.user or g.user.id != user_id):
        flash("Access unauthorized.", "danger")
        return redirect("/")

    return render_template('/users/likes.jinja', user=g.user)


@app.get('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = db.get_or_404(User, user_id)
    return render_template('users/following.jinja', user=user)


@app.get('/users/<int:user_id>/followers')
def show_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = db.get_or_404(User, user_id)
    return render_template('users/followers.jinja', user=user)


@app.post('/users/follow/<int:follow_id>')
def start_following(follow_id):
    """Add a follow for the currently-logged-in user.

    Redirect to following page for the current for the current user.
    """

    if not g.user or not g.csrf_form.validate_on_submit():
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = db.get_or_404(User, follow_id)

    g.user.follow(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.post('/users/stop-following/<int:follow_id>')
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user.

    Redirect to following page for the current for the current user.
    """

    if not g.user or not g.csrf_form.validate_on_submit():
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = db.get_or_404(User, follow_id)

    g.user.unfollow(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def edit_profile():
    """Update profile for current user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = EditProfile(obj=g.user)

    if form.validate_on_submit():

        if User.authenticate(g.user.username, form.password.data):

            try:
                g.user.update_user(
                    form.username.data,
                    form.email.data,
                    form.image_url.data or None,
                    form.header_image_url.data or None,
                    form.bio.data
                )
                db.session.commit()

            except IntegrityError:
                db.session.rollback()
                flash('Username already taken!')
                return render_template("/users/edit.jinja", form=form)

            return redirect(f"/users/{g.user.id}")

        flash('Incorrect password entered!')

    return render_template("/users/edit.jinja", form=form, user_id=g.user.id)


@app.post('/users/delete')
def delete_user():
    """Delete user.

    Redirect to signup page.
    """

    if not g.user or not g.csrf_form.validate_on_submit():
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    flash("Account deleted!")

    return redirect("/signup")


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def add_message():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/create.jinja', form=form)


@app.get('/messages/<int:message_id>')
def show_message(message_id):
    """Show a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = db.get_or_404(Message, message_id)
    return render_template('messages/show.jinja', message=msg)


@app.post('/messages/<int:message_id>/like')
def like_unlike_message(message_id):
    """Like/unlike message with `message_id` for the logged in user"""

    if (not g.user or not g.csrf_form.validate_on_submit()):
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = db.get_or_404(Message, message_id)

    if msg.user_id == g.user.id:
        flash("Cannot like your own message!")
        return redirect("/")

    g.user.like_unlike_msg(msg)

    db.session.commit()

    # NOTE request.referrer relies on the app knowing your broswer history
    # unsupported in some cases
    return redirect(f"{request.form['request_url']}")


@app.post('/messages/<int:message_id>/delete')
def delete_message(message_id):
    """Delete a message.

    Check that this message was written by the current user.
    Redirect to user page on success.
    """

    if not g.user or not g.csrf_form.validate_on_submit():
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = db.get_or_404(Message, message_id)

    if msg.user_id != g.user.id:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# Homepage and error pages


@app.get('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of self & followed_users
    """

    if g.user:
        followed_users = [followed.id for followed in g.user.following]
        q = (
            db.select(Message)
            .where(
                (Message.user_id == g.user.id) |
                (Message.user_id.in_(followed_users))
            )
            .order_by(Message.timestamp.desc())
            .limit(100)
        )

        messages = dbx(q).scalars().all()

        return render_template('home.jinja', messages=messages)

    else:
        return render_template('home-anon.jinja')


@app.after_request
def add_header(response):
    """Add non-caching headers on every request."""

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    response.cache_control.no_store = True

    return response
