__author__ = 'austin'

import unittest
from pprint import pprint

from TESTING.unittests.testApp import create_app, db


class TestUser(db.DynamicDocument):
    is_full_account = db.BooleanField(default=False)
    fields_dict = db.DictField()

    def basic_init(self):
        field_keys = [
            'license',
            'insurance',
            'MC'
        ]
        fields = {}
        for key in field_keys:
            fields[key] = "pending_upload"
        self.update(fields_dict=fields)
        self.save()


class EmbeddedTest(unittest.TestCase):

    def create_app(self):
        return create_app()

    def testCreateUser(self):
        user = TestUser(email="test@test.com").save()
        self.assertNotEquals(user, None)
        self.assertEquals(user.fields_dict, {})
        user.basic_init()
        user.reload()
        self.assertNotEquals(user.fields_dict, {})
    #     Ok so they all updated!
        print(user.fields_dict)
        # Now we check the fields
        is_accepted = True
        for field in user.fields_dict:
            if user.fields_dict[field] != "approved":
                is_accepted = False

        if is_accepted:
            # And send an email
            user.update(is_full_account=True)

        user.reload()
        assert user.is_full_account is False

        pprint(user.to_json())

    def doCleanups(self):
        try:
            (TestUser.objects.get(email="test@test.com")).delete()
        except Exception:
            pass
        return super().doCleanups()

    def tearDown(self):
        print("Closing test!")


if __name__ == '__main__':
    unittest.main()
