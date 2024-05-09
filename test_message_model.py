"""User model tests."""

import os
from unittest import TestCase

from app import app
from models import db, dbx, User, Message

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

        m1 = Message(
            text="This is a test message",
            user_id=u1.id
        )

        db.session.add(m1)

        db.session.commit()
        self.u1_id = u1.id
        self.u2_id = u2.id
        self.m1_id = m1.id

    def tearDown(self):
        db.session.rollback()

    def test_messages_on_user(self):
        u1 = db.session.get(User, self.u1_id)

        self.assertEqual(len(u1.messages), 1)

    def test_create_message(self):
        u1 = db.session.get(User, self.u1_id)
        self.assertEqual(len(u1.messages), 1)

        m2 = Message(
            text="Second test message",
            user_id=u1.id
        )
        db.session.add(m2)
        db.session.commit()

        self.assertEqual(len(u1.messages), 2)

        msg = db.session.get(Message, m2.id)
        self.assertEqual(msg.text, "Second test message")
