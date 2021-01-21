import unittest
import os
from modules.coffee import CoffeeBill, coffees, CoffeeUser
from pathlib import Path


class CoffeeUserTest(unittest.TestCase):
    def test_create_initial_bill(self):
        u = CoffeeUser("Bill")

    def test_close_bill(self):
        pass
