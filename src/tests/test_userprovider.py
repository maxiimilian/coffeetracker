import unittest
from modules.userprovider import UserProvider
from modules.coffee import CoffeeUser


class UserProviderTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.u = UserProvider()

    def test_list_usernames(self):
        self.assertListEqual(
            self.u.list_usernames(),
            ["Alice", "Bob"]
        )

    def test_returns_coffeeuser(self):
        for username in self.u.list_usernames():
            self.assertIsInstance(
                self.u.get_CoffeeUser(username), CoffeeUser
            )

    def test_invalid_coffeeuser(self):
        with self.assertRaises(KeyError):
            self.u.get_CoffeeUser("Charlie")

    def test_coffeeuser_splitwise(self):
        alice_no_splitwise = self.u.get_CoffeeUser("Alice")
        bob_splitwise = self.u.get_CoffeeUser("Bob")

        self.assertEqual(alice_no_splitwise.splitwise_id, -1)
        self.assertEqual(bob_splitwise.splitwise_id, 1234)


if __name__ == '__main__':
    unittest.main()
