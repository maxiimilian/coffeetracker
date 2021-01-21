from unittest import TestCase
from pathlib import Path
from datetime import datetime, timedelta
from copy import deepcopy
from time import sleep

from modules.coffee import CoffeeBill, CoffeeUser, Coffee, coffees


class CoffeeBillTests(TestCase):
    def setUp(self) -> None:
        # Create temporary bill for all tests
        tmp_path = Path("/tmp/bill_temp.ini")
        if tmp_path.exists():
            tmp_path.unlink()

        self.test_user = CoffeeUser("Test")
        self.tmp_path = tmp_path
        self.bill = CoffeeBill(self.tmp_path, self.test_user)

    def tearDown(self) -> None:
        # Clean up
        self.tmp_path.unlink()

    def test_file_created(self):
        """ Test if file is created after running constructor (does not make use of self.setUp()) """
        path = Path("/tmp/bill_create.ini")
        if path.exists():
            path.unlink()

        b = CoffeeBill(path, CoffeeUser("Test"))
        self.assertTrue(path.exists())

    def test_pay(self):
        # Not payed in the beginning
        self.assertFalse(self.bill.payed)

        # Now pay
        transaction_id = "TestID"
        self.bill.pay(transaction_id)

        # After payment: Have transaction ID, time, and `payed` = True
        self.assertTrue(self.bill.payed)
        self.assertEqual(self.bill.transaction_id, transaction_id)
        self.assertTrue(self.bill.transaction_time - datetime.now() < timedelta(seconds=1))

        # We can't pay bill twice
        with self.assertRaises(RuntimeError):
            self.bill.pay(transaction_id)

        # We can't add coffee once bill is paid
        with self.assertRaises(RuntimeError):
            self.bill.add(coffees[0])

    def test_load_wrong_user(self):
        """ Should raise error if username in file and constructor don't match. """
        with self.assertRaises(KeyError):
            bill_reloaded = CoffeeBill(self.tmp_path, CoffeeUser("Peter"))

    def test_store_head(self):
        # paying sets all attributes of head and stores file
        self.bill.pay("TestID")
        self.assertTrue(self.bill.payed)

        # reload bill
        bill_reloaded = CoffeeBill(self.tmp_path, self.test_user)
        self.assertTrue(bill_reloaded.payed)
        self.assertEqual(bill_reloaded.transaction_id, self.bill.transaction_id)
        self.assertTrue(self.bill.transaction_time - bill_reloaded.transaction_time < timedelta(seconds=1))

    def test_add_coffee(self):
        self.assertEqual(len(self.bill.items), 0)
        coffee = coffees[0]

        # Check that number increased
        self.bill.add(coffee)
        self.bill.add(coffee)
        self.assertEqual(len(self.bill.items), 2)

    def test_items_dict(self):
        # create unique coffee objects
        coffee0 = deepcopy(coffees[0])
        coffee1 = deepcopy(coffees[0])
        coffee2 = deepcopy(coffees[0])
        self.assertNotEqual(coffee0, coffee2)

        # Add coffees to bill
        self.bill.add(coffee0)
        self.bill.add(coffee1)
        self.bill.add(coffee2)

        # Check that ids of dict match unique coffee objects
        self.assertEqual(self.bill.items[0].coffee, coffee0)
        self.assertEqual(self.bill.items[2].coffee, coffee2)
        self.assertNotEqual(self.bill.items[0].coffee, self.bill.items[2].coffee)

    def test_delete_restore_coffee(self):
        # create unique coffee objects
        coffee0 = deepcopy(coffees[0])
        coffee1 = deepcopy(coffees[0])
        self.assertNotEqual(coffee0, coffee1)

        # Add coffees to bill
        self.bill.add(coffee0)
        self.bill.add(coffee1)

        # Both coffees should be active
        self.assertListEqual(
            [self.bill.items[0].deleted, self.bill.items[1].deleted],
            [False, False]
        )

        # Now delete one coffee
        self.bill.delete(1)

        # Only one coffee should be active
        self.assertListEqual(
            [self.bill.items[0].deleted, self.bill.items[1].deleted],
            [False, True]
        )

        # Now delete second coffee but restore first
        self.bill.delete(0)
        self.bill.restore(1)

        # Only one coffee should be active but inverted
        self.assertListEqual(
            [self.bill.items[0].deleted, self.bill.items[1].deleted],
            [True, False]
        )

    def test_delete_restore_payed(self):
        """ Delete and restore on closed bills should raise an error """
        self.bill.add(coffees[0])
        self.bill.add(coffees[0])
        self.bill.delete(0)
        self.bill.pay("closed")
        self.assertTrue(self.bill.payed)

        # Now try to delete something from the list
        with self.assertRaises(RuntimeError):
            self.bill.delete(1)

        # Try to restore deleted item
        with self.assertRaises(RuntimeError):
            self.bill.restore(0)

    def test_sum(self):
        self.assertEqual(self.bill.sum, 0)

        coffee = coffees[0]
        self.bill.add(coffee)
        self.assertEqual(self.bill.sum, coffee.price)

        self.bill.add(coffee)
        self.assertEqual(self.bill.sum, coffee.price * 2)

        # Deleted coffee should not influence sum anymore
        self.bill.delete(0)
        self.assertEqual(self.bill.sum, coffee.price)

        # Restored coffee should bring sum back to normal
        self.bill.restore(0)
        self.assertEqual(self.bill.sum, coffee.price * 2)

    def test_store_items(self):
        """ Test that all attributes of items are stored and reloaded with csv writer/reader """
        # Add four items (two types)
        # We need to sleep in between because test will otherwise fail.
        # That is due to the timestamp based sorting of `items`. If time stamps are too close, order will differ.
        # Should not be a problem in real life because time difference is less then 1 second.
        self.bill.add(coffees[0])
        sleep(1)
        self.bill.add(coffees[0])
        sleep(1)
        self.bill.add(coffees[1])
        sleep(1)
        self.bill.add(coffees[1])

        # Delete two coffees
        self.bill.delete(1)
        self.bill.delete(2)

        # Reload bill into new variable
        bill_reloaded = CoffeeBill(self.tmp_path, self.test_user)
        self.assertNotEqual(bill_reloaded, self.bill)

        for item_orig, item_reloaded in zip(self.bill.items.values(), bill_reloaded.items.values()):
            # Check reconstruction of Coffee
            self.assertEqual(item_orig.coffee.name, item_reloaded.coffee.name)
            self.assertEqual(item_orig.coffee.price, item_reloaded.coffee.price)

            # Check `deleted` flag
            self.assertEqual(item_orig.deleted, item_reloaded.deleted)

            # Check timestamp is close (not exact because we truncate milliseconds)
            self.assertTrue(
                item_orig.timestamp - item_reloaded.timestamp < timedelta(seconds=1)
            )

            # Generic check of array which would be written by csv writer
            self.assertListEqual(
                item_orig.get_row(),
                item_reloaded.get_row()
            )

