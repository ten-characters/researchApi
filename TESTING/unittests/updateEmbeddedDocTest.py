__author__ = 'austin'

import unittest

from TESTING.unittests.testApp import create_app, db


class TestTruck(db.EmbeddedDocument):
    name = db.StringField()
    model = db.StringField()


class TestEmbed(db.EmbeddedDocument):
    trucks = db.ListField(db.EmbeddedDocumentField(TestTruck))


class TestUser(db.DynamicDocument):
    email = db.StringField(required=True)
    embedded = db.EmbeddedDocumentField(TestEmbed, default=None)


class EmbeddedTest(unittest.TestCase):

    def create_app(self):
        return create_app()

    def testCreateUser(self):
        user = TestUser(email="test@test.com").save()
        self.assertNotEquals(user, None)
        self.assertEquals(user.embedded, None)

        embed = TestEmbed()
        user.update(embedded=embed)
        user.reload()
        print(embed.to_json())
        self.assertNotEquals(user.embedded, None)

        truck = TestTruck(name="Shelby", model="Ford")
        user.update(push__embedded__trucks=truck)
        user.reload()
        self.assertEquals(len(user.embedded.trucks), 1)

        truck = TestTruck(name="Joey", model="Ford")
        user.update(push__embedded__trucks=truck)
        user.reload()
        self.assertEquals(len(user.embedded.trucks), 2)

    #     Now let's try to individual update
    #     First find the truck we want to update
        truck = None
        for t in user.embedded.trucks:
            if t.name == "Shelby":
                truck = t
        self.assertNotEquals(truck, None)

    #     Now let's remove that doc, update it, and repush
        user.update(pull__embedded__trucks=truck)
        user.reload()
        self.assertEquals(len(user.embedded.trucks), 1)
        # Update it
        truck.model = "Volvo"
        user.update(push__embedded__trucks=truck)
        user.reload()
        self.assertEquals(len(user.embedded.trucks), 2)

        truck = None
        for t in user.embedded.trucks:
            if t.model == "Volvo":
                truck = t
        self.assertNotEquals(truck, None)

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

