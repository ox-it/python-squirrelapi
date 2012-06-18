import mock
import unittest2

from squirrelapi import VoicemailUser, SquirrelApiException, VoicemailMessage
from contextlib import contextmanager


class SquirrelUserAPI(unittest2.TestCase):
    def setUp(self):
        pass

    @contextmanager
    def set_response(self, response_file):
        with mock.patch('squirrelapi.SquirrelAPIResource.get_connection') as m:
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
