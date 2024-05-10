"""Message View tests."""

import os
from unittest import TestCase

from app import app, CURR_USER_KEY
from models import (
    db,
    dbx,
    Message,
    User,
    Follow,
    Like,
    DEFAULT_IMAGE_URL,
    DEFAULT_HEADER_IMAGE_URL
)

# To run the tests, you must provide a "test database", since these tests
# delete & recreate the tables & data. In your shell:
#
# Do this only once:
#   $ createdb warbler_test
#
# To run the tests using that test data:
#   $ DATABASE_URL=postgresql:///warbler_test python3 -m unittest

if not app.config['SQLALCHEMY_DATABASE_URI'].endswith("_test"):
    raise Exception(
        "\n\nMust set DATABASE_URL env var to db ending with _test")

# NOW WE KNOW WE'RE IN THE RIGHT DATABASE, SO WE CAN CONTINUE
os.environ['FLASK_DEBUG'] = '0'

# Don't have WTForms use CSRF at all, since it's a pain to test
app.config['WTF_CSRF_ENABLED'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

app.app_context().push()
db.drop_all()
db.create_all()


class UserBaseViewTestCase(TestCase):
    def setUp(self):
        dbx(db.delete(User))
        db.session.commit()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("userTwo", "u2@email.com", "password", None)
        db.session.flush()

        m1 = Message(text="Sample message text", user_id=u1.id)
        db.session.add_all([m1])
        db.session.commit()

        f1 = Follow(
            user_being_followed_id=u2.id,
            user_following_id=u1.id
        )
        f2 = Follow(
            user_being_followed_id=u1.id,
            user_following_id=u2.id
        )
        db.session.add(f1)
        db.session.add(f2)
        db.session.commit()

        l1 = Like(user_id=u2.id, message_id=m1.id)
        db.session.add(l1)
        db.session.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id
        self.m1_id = m1.id


class UserViewTestCase(UserBaseViewTestCase):
    def test_show_following(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get(f"/users/{self.u1_id}/following")
            html = resp.get_data(as_text=True)

            self.assertIn(f"{self.u2_id}", html)

            resp = c.get(f"/users/{self.u2_id}/following")
            html = resp.get_data(as_text=True)

            self.assertIn(f"{self.u1_id}", html)

    def test_show_followers(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get(f"/users/{self.u1_id}/followers")
            html = resp.get_data(as_text=True)

            u2 = db.session.get(User, self.u2_id)

            self.assertIn(f"{u2.username}", html)

            resp = c.get(f"/users/{self.u2_id}/followers")
            html = resp.get_data(as_text=True)

            u1 = db.session.get(User, self.u1_id)

            self.assertIn(f"{u1.username}", html)

    def test_show_likes(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.get(f"/users/{self.u2_id}/likes")
            html = resp.get_data(as_text=True)

            self.assertIn("Sample message text", html)

    def test_delete_user(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post("/users/delete", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertIn("Account deleted!", html)
            self.assertIn("Join Warbler today.", html)

            u1 = db.session.get(User, self.u1_id)

            self.assertIsNone(u1)

    def test_edit_profile(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post(
                "/users/profile",
                data={
                    "username": "userOne",
                    "email": "u1@email.com",
                    "image_url": "",
                    "header_image_url": "",
                    "bio": "Test bio",
                    "password": "password"
                },
                follow_redirects=True)
            html = resp.get_data(as_text=True)

            u1 = db.session.get(User, self.u1_id)

            # How to check all properties at once?
            self.assertIn("userOne", html)
            self.assertEqual("userOne", u1.username)
            self.assertEqual("u1@email.com", u1.email)
            self.assertEqual(DEFAULT_IMAGE_URL, u1.image_url)
            self.assertEqual(DEFAULT_HEADER_IMAGE_URL, u1.header_image_url)
            self.assertEqual("Test bio", u1.bio)

            resp = c.post(
                "/users/profile",
                data={
                    "username": "userTwo",
                    "email": "u1@email.com",
                    "image_url": "",
                    "header_image_url": "",
                    "bio": "Test bio",
                    "password": "password"
                },
                follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertIn("Username already taken!", html)

            resp = c.post(
                "/users/profile",
                data={
                    "username": "u1",
                    "email": "u1@email",
                    "image_url": "",
                    "header_image_url": "",
                    "bio": "Test bio",
                    "password": "password"
                },
                follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertIn("Invalid email address.", html)

            resp = c.post(
                "/users/profile",
                data={
                    "username": "u1",
                    "email": "u1@email.com",
                    "image_url": "not_a_URL",
                    "header_image_url": "",
                    "bio": "Test bio",
                    "password": "password"
                },
                follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertIn("Invalid URL.", html)

            resp = c.post(
                "/users/profile",
                data={
                    "username": "userOne",
                    "email": "u1@email.com",
                    "image_url": "",
                    "header_image_url": "",
                    "bio": "Test bio",
                    "password": "wrong_password"
                },
                follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertIn("Incorrect password entered!", html)

    def test_no_logged_in_user(self):
        with app.test_client() as c:
            resp = c.get(
                f"/users/{self.u1_id}/following",
                follow_redirects=True
            )
            html = resp.get_data(as_text=True)

            self.assertIn("Access unauthorized.", html)
            self.assertIn("What's Happening?", html)

            resp = c.get(
                f"/users/{self.u1_id}/followers",
                follow_redirects=True
            )
            html = resp.get_data(as_text=True)

            self.assertIn("Access unauthorized.", html)
            self.assertIn("What's Happening?", html)

            resp = c.get(f"/users/{self.u2_id}/likes", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertIn("Access unauthorized.", html)
            self.assertIn("What's Happening?", html)

            resp = c.post("/users/delete", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertIn("Access unauthorized.", html)
            self.assertIn("What's Happening?", html)
