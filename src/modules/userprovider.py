from typing import List, Dict
from configparser import ConfigParser
from modules.coffee import CoffeeUser


class UserProvider:
    def __init__(self, config_file='data/users.ini'):
        self._user_config = ConfigParser()
        self._user_config.read(config_file)

    def get_CoffeeUser(self, username) -> CoffeeUser:
        if username not in self.list_usernames():
            raise KeyError("Invalid username!")

        splitwise_id = self._user_config.getint(username, 'splitwise_id', fallback=-1)
        return CoffeeUser(username, splitwise_id=splitwise_id)

    def list_usernames(self) -> List[str]:
        return self._user_config.sections()

    def list_CoffeeUsers(self) -> Dict[str, CoffeeUser]:
        return {
            username: self.get_CoffeeUser(username)
            for username in self.list_usernames()
        }
