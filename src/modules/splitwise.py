from splitwise import Splitwise
from splitwise.expense import Expense, ExpenseUser
from splitwise.user import User
import configparser

from modules.coffee import CoffeeBill


class SplitwiseWrapper:
    def __init__(self, config_file="data/splitwise.ini"):
        # Get key and secret from config file
        config = configparser.ConfigParser()
        config.read(config_file)

        if "App" not in config:
            raise ValueError("Please provide app key and secret for Splitwise in config file.")

        self._consumer_key = config["App"].get('key')
        self._consumer_secret = config["App"].get('secret')

        if self._consumer_key is None or self._consumer_secret is None:
            raise ValueError("Please provide app key and secret for Splitwise in config file.")

        # Create user section if it does not exist yet
        if "User" not in config:
            config.add_section("User")

        # Save config for later access
        self._config = config
        self._config_file = config_file

        # Init splitwise
        self._s = Splitwise(
            consumer_key=self._consumer_key,
            consumer_secret=self._consumer_secret,
        )
        if self._access_token is not None:
            self._s.setOAuth2AccessToken(self._access_token)

        # Cache for logged in user
        self._user: User = User()

    @property
    def _access_token(self):
        token = self._config['User'].get('token', "")
        token_type = self._config['User'].get('token_type', "")

        if token == "" or token_type == "":
            return None
        else:
            return {
                "access_token": token,
                "token_type": token_type
            }

    def set_access_token(self, token):
        """
        Set O-Auth token and write to file.

        :token: { "access_token": str, "token_type": str }
        """
        self._config['User']['token'] = token['access_token']
        self._config['User']['token_type'] = token['token_type']

        with open(self._config_file, 'w') as f:
            self._config.write(f)

        self._s.setOAuth2AccessToken(token)

    @property
    def s(self):
        return self._s

    @property
    def user(self) -> User:
        if self._user.getId() is None:
            self._user = self.s.getCurrentUser()
        return self._user

    def pay_bill(self, paying_user_id: int, bill: CoffeeBill) -> str:
        """
        Pay a bill by creating an expense for `paying_user` with respect to logged in splitwise user.
        :param paying_user_id:  Splitwise id of paying user
        :param bill:            CoffeeBill to be payed
        :return:                Splitwise transaction id
        """
        # Convert amount to string
        amount_str = f"{bill.sum:.2f}"

        # User which will pay money
        paying_user = ExpenseUser()
        paying_user.setId(paying_user_id)
        paying_user.setOwedShare(amount_str)

        # User which will receive money
        my_user = ExpenseUser()
        my_user.setId(self.user.getId())
        my_user.setPaidShare(amount_str)

        # Create Expense/Transaction
        expense = Expense()
        expense.setCost(amount_str)
        expense.setDescription(f"CoffeeTracker, Rechnung {bill.id}")
        expense.addUser(paying_user)
        expense.addUser(my_user)

        # Execute transaction
        expense_response, errors = self.s.createExpense(expense)

        if errors is not None:
            raise RuntimeError(
                "An error occured while processing the transaction with Splitwise: "
                f"{errors.errors}"
            )

        return f"{expense_response.getId()}"
