"""Message View tests."""

import os
from unittest import TestCase

from app import app, CURR_USER_KEY
from models import db, dbx, Message, User, Follow, Like

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

        m1 = Message(text="m1-text", user_id=u1.id)
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

            self.assertIn(f"{self.u2_id}", html)

            resp = c.get(f"/users/{self.u2_id}/followers")
            html = resp.get_data(as_text=True)

            self.assertIn(f"{self.u1_id}", html)

    def test_no_logged_in_user(self):
        with app.test_client() as c:
            resp = c.get(f"/users/{self.u1_id}/followers")
            self.assertEqual(resp.status_code, 302)

            resp = c.get(f"/users/{self.u1_id}/following")
            self.assertEqual(resp.status_code, 302)
