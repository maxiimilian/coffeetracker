from __future__ import annotations
import csv
from configparser import ConfigParser
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict
import warnings


class Coffee:
    """ Hold name and price of coffee """
    def __init__(self, name: str, price: float) -> None:
        self._name: str = name
        self._price: float = price

    def __str__(self):
        return f"{self.name}, {self.price:.2f}"

    def __repr__(self):
        return f"<Coffee {self.__str__()}>"

    @property
    def price(self) -> float:
        return self._price

    @property
    def name(self) -> str:
        return self._name


class CoffeeUser:
    DATA_ROOT = Path("data/coffee/")
    BILL_FILENAME_PATTERN = "{:s}_{:04d}.ini"

    """ Provide coffee bills for user """
    def __init__(self, name: str, splitwise_id: int = -1):
        self._name: str = name
        self._splitwise_id: int = splitwise_id
        self._bills: List[CoffeeBill] = []

        # Check if data root is ok
        if not self.DATA_ROOT.exists():
            raise RuntimeError("CoffeeBill data root {:s} does not exist!".format(str(self.DATA_ROOT)))

        # Load existing bills for user
        b_path_pattern = f"{name}_*.ini"
        for b_path in sorted(self.DATA_ROOT.glob(b_path_pattern)):
            self._bills.append(CoffeeBill(
                path=b_path,
                user=self
            ))

        # Create new bill if no existing bills were found
        if len(self.bills) == 0:
            self._bills.append(self._get_new_bill())

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<CoffeeUser {self.name}>"

    @property
    def name(self) -> str:
        return self._name

    @property
    def splitwise_id(self) -> int:
        return self._splitwise_id

    @property
    def bills(self) -> Dict[str, CoffeeBill]:
        """ Returns all bills of this user """
        return {
            bill.id: bill
            for bill in self._bills
        }

    @property
    def bills_payed(self) -> Dict[str, CoffeeBill]:
        """ Returns only payed bills of this user. Should be one less than `bills` """
        return {
            bill.id: bill
            for bill in self._bills
            if bill.payed
        }

    @property
    def current_bill(self) -> CoffeeBill:
        """ Last bill in `bills` is current (open) bill """
        current_bill = list(self.bills.values())[-1]
        return current_bill

    def pay_bill(self, transaction_id) -> None:
        """ Pays current bill """
        self.current_bill.pay(transaction_id)

        # Create new open bill
        self._bills.append(self._get_new_bill())

    def _get_new_bill(self) -> CoffeeBill:
        # New bill only possible if all previous bills were paid
        for b in self.bills.values():
            if not b.payed:
                raise RuntimeError(
                    "New bill could not be created because there exists an open bill which should be payed first"
                )

        # Generates pathlib object according to filename pattern
        bill_path_fn = lambda i: self.DATA_ROOT / self.BILL_FILENAME_PATTERN.format(self.name, i)

        # Find next free filename
        i = 1
        while bill_path_fn(i).exists():
            i += 1

        # Last iteration is next free filename
        bill_path = bill_path_fn(i)
        return CoffeeBill(bill_path, self)


class CoffeeBill:
    DATE_FORMAT = "%Y-%m-%d_%H-%M-%S"

    """ Bill hold coffees """
    def __init__(self, path: [str, Path], user: CoffeeUser):
        self._path = Path(path)
        self._user: CoffeeUser = user

        self._items: List[CoffeeBillItem] = []
        self._transaction_id: str = ""
        self._transaction_time: datetime = None

        self._load()

    def __str__(self):
        return f"CoffeeBill, {self._user.name}, {self.sum:.2f}, ({'Open' if not self.payed else 'Payed'})"

    def __repr__(self):
        return f"<{self.__str__()}>"

    def _load(self) -> None:
        """ Loads bill from file """
        # create file if it does not exist
        if not self._path.is_file():
            self._path.touch()
            self._save()
            return

        # load raw content
        with self._path.open("r") as f:
            raw_content: str = f.read()

        # split file at [Items] into ini part and csv part
        head_raw, items_raw = raw_content.split("[Items]")

        # Process ini and csv parts of bill individually
        self._load_head(head_raw)
        self._load_items(items_raw)

    def _load_head(self, head_raw) -> None:
        """ Load head of bill which is ini file. """
        head = ConfigParser()
        head.read_string(head_raw)
        self._transaction_id = head["Bill"].get('TransactionID', "")

        transaction_time_str: str = head["Bill"].get('TransactionTime', "")
        if transaction_time_str != "":
            self._transaction_time = datetime.strptime(transaction_time_str, self.DATE_FORMAT)

        # Sanity check username
        user = head["Bill"].get('User')
        if user != self._user.name:
            raise KeyError(
                f"This bill file belongs to {user}. However, you created a CoffeeBill for {self._user.name}."
            )

    def _load_items(self, items_raw) -> None:
        """ Load body of bill which is csv file. """
        csv_reader = csv.reader(items_raw.splitlines(), dialect="unix")
        for row in csv_reader:
            # Skip empty rows
            if row == []:
                continue

            # Deserialize row
            item = CoffeeBillItem.deserialize(row)
            self._items.append(item)

    def _save(self) -> None:
        """ Save current state of bill to file """
        # Save head as ini file.
        head = ConfigParser()
        head.add_section('Bill')
        head['Bill']['User'] = self._user.name
        head['Bill']['TransactionID'] = self._transaction_id
        if self._transaction_time is not None:
            head['Bill']['TransactionTime'] = self._transaction_time.strftime(self.DATE_FORMAT)

        head.add_section('Items')
        with self._path.open('w') as f:
            head.write(f)

            # Save body as csv file.
            csv_writer = csv.writer(f, dialect="unix")
            csv_writer.writerows((
                i.get_row() for i in self._items
            ))

    def add(self, coffee: Coffee) -> None:
        if self.payed:
            raise RuntimeError("Bill was already payed! No new item can be added!")

        self._items.append(
            CoffeeBillItem(datetime.now(), coffee, False)
        )
        self._save()

    def delete(self, item_id: int):
        """ Delete (disable) coffee with given id. """
        self._items[item_id].deleted = True
        self._save()

    def restore(self, item_id: int):
        """ Restore (enable) coffee with given id. """
        self._items[item_id].deleted = False
        self._save()

    def pay(self, transaction_id: str) -> None:
        """ Provide transaction id with which this bill was payed. """
        if self.payed:
            raise RuntimeError("Bill was already payed!")
        self._transaction_id = transaction_id
        self._transaction_time = datetime.now()
        self._save()

    @property
    def items(self) -> Dict[int, CoffeeBillItem]:
        # Insertion order for dicts is retained since Python 3.7! Sorting will be preserved.
        return {
            id: item
            for id, item in sorted(
                enumerate(self._items),
                key=lambda i: i[1].timestamp,
                reverse=True
            )
        }

    @property
    def sum(self) -> float:
        """ Sum of bill. Only include non-deleted items. """
        return sum((
            i.coffee.price
            for i in self._items
            if not i.deleted
        ))

    @property
    def transaction_id(self) -> str:
        return self._transaction_id

    @property
    def transaction_time(self) -> datetime:
        return self._transaction_time

    @property
    def payed(self) -> bool:
        return not self.transaction_id == ""

    @property
    def id(self) -> str:
        return self._path.parts[-1]


class CoffeeBillItem:
    def __init__(self, timestamp: datetime, coffee: Coffee, deleted: bool):
        self.timestamp: datetime = timestamp
        self.coffee: Coffee = coffee
        self.deleted: bool = deleted

    @classmethod
    def deserialize(cls, row: List) -> CoffeeBillItem:
        """
        Takes row (List) from CSV reader and deserializes it back into a CoffeeBillItem.
        """
        if len(row) == 3:
            # Backwards compatibility for bills which did not have `deleted` attribute.
            date_str, coffee_str, price_str = row
            deleted = False
        else:
            date_str, coffee_str, price_str, deleted = row
            deleted = bool(int(deleted))  # convert stored int back to bool

        date_obj: datetime = datetime.strptime(date_str, CoffeeBill.DATE_FORMAT)
        coffee: Coffee = coffees_dict[coffee_str]

        # Sanity check coffee price
        price = float(price_str)
        if price != coffee.price:
            warnings.warn(
                f"{coffee.name} is billed with {price:.2f} in file but set to {coffee.price:.2f}. "
                "Continue by using price from file!"
            )
            coffee = deepcopy(coffee)
            coffee._price = price

        return CoffeeBillItem(date_obj, coffee, deleted)

    def get_row(self) -> List[str]:
        """
        Returns BillItem as List to be written by CSV writer.
        """
        return [
            self.timestamp.strftime(CoffeeBill.DATE_FORMAT),
            self.coffee.name,
            self.coffee.price,
            int(self.deleted),  # encode `deleted` bool as int
        ]


# Define coffees we have
coffees = [
    Coffee("Espresso", .3),
    Coffee("Nespresso", .5)
]

coffees_dict = {
    c.name: c
    for c in coffees
}