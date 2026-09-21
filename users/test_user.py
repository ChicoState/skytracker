import unittest
from pathlib import Path

from users import user


class UserStorageTests(unittest.TestCase):
    def test_add_user_persists_and_loads_a_user(self):
        original_users_file = getattr(user, "USERS_FILE", None)

        test_users_file = Path(__file__).with_name(".test-users.json")
        try:
            user.USERS_FILE = test_users_file
            new_user = user.User(
                first_name="Jane",
                last_initial="D",
                user_id="jdoe01",
                email="jane@example.com",
                zip_code="98101",
                birthday="2000-05-12",
            )

            user.add_user(new_user)

            self.assertEqual(user.load_users(), [new_user])
        finally:
            if test_users_file.exists():
                test_users_file.unlink()
            if original_users_file is not None:
                user.USERS_FILE = original_users_file


if __name__ == "__main__":
    unittest.main()
