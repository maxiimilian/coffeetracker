import unittest
import shutil
from modules.splitwise import SplitwiseWrapper


class SplitwiseWrapperTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.config_file_empty = "data/splitwise_empty.ini"

        # Copy non-auth file for test
        config_non_auth = "data/splitwise_non_auth.ini"
        config_non_auth_tmp = "/tmp/splitwise_non_auth.ini"
        shutil.copy(config_non_auth, config_non_auth_tmp)
        self.config_non_auth = config_non_auth_tmp

    def test_read_empty_config(self):
        with self.assertRaises(ValueError):
            s = SplitwiseWrapper(self.config_file_empty)

    def test_read_non_auth_config(self):
        s = SplitwiseWrapper(self.config_non_auth)
        self.assertEqual(s._consumer_key, 'AAA')
        self.assertEqual(s._consumer_secret, 'BBB')

    def test_save_auth_token(self):
        token = {
            "access_token": "aaa",
            "token_type": "bearer"
        }

        s = SplitwiseWrapper(self.config_non_auth)
        s.set_access_token(token)

        # Read file back and check that saved token is identical to input `token`
        s = SplitwiseWrapper(self.config_non_auth)
        self.assertDictEqual(s._access_token, token)


if __name__ == '__main__':
    unittest.main()
