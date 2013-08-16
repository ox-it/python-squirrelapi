import mock
import unittest2

from squirrel_api import VoicemailUser, VoicemailMessage, VoicemailSuperUser
from squirrel_api.exceptions import SquirrelException, SquirrelApiException
from contextlib import contextmanager


class SquirrelUserAPI(unittest2.TestCase):
    def setUp(self):
        pass

    @contextmanager
    def set_response(self, response_file):
        with mock.patch('squirrel_api.api.SquirrelAPIResource.get_connection') as m:
            with open(response_file) as f:
                m().getresponse.return_value = f
                yield

    def test_valid_auth(self):
        with self.set_response('tests/data/login_successful.xml'):
            user = VoicemailUser(12345)
            token = user.login(123456)
            self.assertEqual(token, 'TESTTOKEN')

    def test_invalid_auth(self):
        with self.set_response('tests/data/login_invalid.xml'):
            user = VoicemailUser(12345)
            with self.assertRaises(SquirrelApiException) as e:
                user.login(123456)
            self.assertEqual(e.exception.error_code, 2101)

    def test_unsuccessful_auth(self):
        with self.set_response('tests/data/login_unsuccessful.xml'):
            user = VoicemailUser(12345)
            with self.assertRaises(SquirrelApiException) as e:
                user.login(123456)
            self.assertEqual(e.exception.error_code, 2205)

    def test_list_messages(self):
        user = VoicemailUser(12345)
        user.token = "FAKETOKEN"
        with self.set_response('tests/data/list_messages.xml'):
            messages = user.get_messages()
            for m in messages:
                self.assertIsInstance(m, VoicemailMessage)

    def test_mailbox_exist_true(self):
        su = VoicemailSuperUser(12345)
        su.token = "FAKE"
        with self.set_response('tests/data/mailbox_exist_true.xml'):
            exist = su.mailbox_exist('12121')
            self.assertTrue(exist)

    def test_mailbox_exist_false(self):
        su = VoicemailSuperUser(12345)
        su.token = "FAKE"
        with self.set_response('tests/data/mailbox_exist_false.xml'):
            exist = su.mailbox_exist('12121')
            self.assertFalse(exist)

    def test_mailbox_exist_wrong(self):
        su = VoicemailSuperUser(12345)
        su.token = "FAKE"
        with self.set_response('tests/data/mailbox_exist_wrong.xml'):
            with self.assertRaises(SquirrelException) as e:
                exist = su.mailbox_exist('123123')