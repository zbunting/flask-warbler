"""User model tests."""

import os
from unittest import TestCase

from app import app
from models import db, dbx, User, Follow

from sqlalchemy.exc import IntegrityError

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
app.app_context().push()
db.drop_all()
db.create_all()


class UserModelTestCase(TestCase):
    def setUp(self):
        dbx(db.delete(User))
        db.session.commit()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)

        db.session.commit()
        self.u1_id = u1.id
        self.u2_id = u2.id

    def tearDown(self):
        db.session.rollback()

    def test_user_model(self):
        u1 = db.session.get(User, self.u1_id)

        # User should have no messages & no followers
        self.assertEqual(len(u1.messages), 0)
        self.assertEqual(len(u1.followers), 0)

    def test_authenticate(self):
        u1 = db.session.get(User, self.u1_id)

        self.assertEqual(User.authenticate("u1", "password"), u1)
        self.assertFalse(User.authenticate("u1", "wrong_password"))
        self.assertFalse(User.authenticate("user", "password"))

    def test_is_following(self):
        u1 = db.session.get(User, self.u1_id)
        u2 = db.session.get(User, self.u2_id)

        self.assertFalse(u1.is_following(u2))

        f1 = Follow(
            user_being_followed_id=self.u2_id,
            user_following_id=self.u1_id
        )
        db.session.add(f1)
        db.session.commit()

        self.assertTrue(u1.is_following(u2))

    def test_is_followed_by(self):
        u1 = db.session.get(User, self.u1_id)
        u2 = db.session.get(User, self.u2_id)

        self.assertFalse(u1.is_followed_by(u2))

        f1 = Follow(
            user_being_followed_id=self.u1_id,
            user_following_id=self.u2_id
        )
        db.session.add(f1)
        db.session.commit()

        self.assertTrue(u1.is_followed_by(u2))

    def test_valid_user_signup(self):
        user = User.signup(
            "testuser",
            "test@test.com",
            "tester"
        )
        db.session.commit()

        user_query = db.session.get(User, user.id)
        self.assertEqual(user_query.username, "testuser")
        self.assertEqual(user_query.email, "test@test.com")

    def test_invalid_user_signup(self):
        with self.assertRaises(IntegrityError):
            User.signup(
                "u1",
                "test@test.com",
                "tester"
            )
            db.session.commit()

    def test_user_authentication(self):
        self.assertTrue(User.authenticate("u1", "password"))
        self.assertFalse(User.authenticate("u3", "password"))
        self.assertFalse(User.authenticate("u1", "wrong_password"))
