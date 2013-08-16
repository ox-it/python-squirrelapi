import httplib
from httplib import HTTPException, ImproperConnectionState
import logging
import socket

from urllib import urlencode
from lxml import etree
from datetime import datetime
from lxml.etree import XMLSyntaxError

from squirrel_api.exceptions import SquirrelException, SquirrelApiException, SquirrelConnectionException

logger = logging.getLogger(__name__)


class SquirrelAPIResource(object):
    def __init__(self, passwd=None, response_type='xml',
                endpoint='voicemail.example.com', use_ssl=True, timeout=2):
        self.passwd = passwd
        self.response_type = response_type
        self.endpoint = endpoint
        self.use_ssl = use_ssl
        self.timeout = timeout

    def get_connection(self):
        if self.use_ssl:
            return httplib.HTTPSConnection(self.endpoint, timeout=self.timeout)
        else:
            return httplib.HTTPConnection(self.endpoint, timeout=self.timeout)


class VoicemailMessage(SquirrelAPIResource):
    MESSAGE_STATUS = {1: 'new', 2: 'urgent', 3: 'saved', 4: 'deleted'}
    MESSAGE_TYPE = {1: 'voice', 2: 'fax'}

    def __init__(self, user, id, mailboxno=None, status=None, type=None,
            created=None, sendercli=None, sendermbx=None, length=None, **kwargs):
        self.user = user
        self.mailboxno = mailboxno or user.mailboxno
        self.id = id
        self.status = status
        self.type = type
        self.created = created
        self.sendercli = sendercli
        self.sendermbx = sendermbx,
        self.length = length
        super(VoicemailMessage, self).__init__(**kwargs)

    @classmethod
    def from_element(cls, user, mailboxno, elem, endpoint):
        """Constructs Messages from etree message Elements"""
        kwargs = {'id': elem.find('id').text,
                'status': int(elem.find('status').text),
                'type': int(elem.find('type').text),
                'created': datetime.strptime(elem.find('created').text,
                    '%Y/%m/%d %H:%M:%S'),
                'sendercli': elem.find('sendercli').text,
                'sendermbx': elem.find('sendermbx').text,
                'length': int(elem.find('length').text),
                }
        return cls(user, mailboxno=mailboxno, endpoint=endpoint, **kwargs)

    def retrieve(self, api='fapi', file_format='wav'):
        """Uses the file api to download .wav (default)"""
        conn = self.get_connection()
        params = {'type': self.response_type,
                'func': 'messageretrieve',
                'mailboxno': self.mailboxno,
                'messageid': self.id,
                'marksaved': 'false',
                'format': file_format,
                'token': self.user.token,
                }
        if self.passwd: params['passwd'] = self.passwd
        conn.request('GET', "/%s.aspx?%s" % (
                    api, urlencode(params)))
        response = conn.getresponse()
        return response


class VoicemailUser(SquirrelAPIResource):

    def __init__(self, mailboxno, **kwargs):
        self.mailboxno = mailboxno
        self.token = None
        self.inbox = dict()
        super(VoicemailUser, self).__init__(**kwargs)

    @property
    def authenticated(self):
        if self.token:
            return True
        else:
            return False

    def login(self, pin, api='uapi'):
        """Given a user's pin we either get an authentication token or
        error message / code as a result of this call.
        """
        conn = self.get_connection()
        params = {'type': self.response_type,
                  'func': 'mailboxlogin',
                  'mailboxno': self.mailboxno,
                  'pin': pin}
        if self.passwd:
            params['passwd'] = self.passwd
        try:
            conn.request('GET', "/%s.aspx?%s" % (api, urlencode(params)))
            return self._handle_login_response(conn.getresponse())
        except (HTTPException, ImproperConnectionState, socket.timeout, socket.error):
            raise SquirrelConnectionException

    def _handle_login_response(self, login_response):
        response = self._parse_response(login_response)
        code = int(response.xpath('/c3voicemailapi/error/code')[0].text)
        if code != 0:
            raise SquirrelApiException(code, 'login')
        else:
            self.token = response.xpath('/c3voicemailapi/token')[0].text
            return self.token

    def _handle_GET_request(self, params, api='uapi'):
        """
        Handle a request (GET) to the user API.
        Throws an exception depending on error code.
        """
        if self.passwd: params['passwd'] = self.passwd
        conn = self.get_connection()
        path = "/{0}.aspx?{1}".format(api, urlencode(params))
        logger.info("GET {0}".format(path))
        try:
            conn.request('GET', path)
            response = self._parse_response(conn.getresponse())
        except (HTTPException, socket.timeout):
            raise SquirrelConnectionException
        else:
            code = int(response.xpath('/c3voicemailapi/error/code')[0].text)
            if code != 0:
                # Error_code = 0 means "Success"
                raise SquirrelApiException(code, path)
            return response

    def _parse_response(self, response):
        """Parse response, raise an exception if it cannot be parsed
        """
        try:
            return etree.parse(response)
        except XMLSyntaxError:
            logger.error('Unable to parse XML response', exc_info=True)
            raise SquirrelException('Unable to parse XML response')

    def get_messages(self, mailboxno=None, msgtype='live', api='uapi'):
        """Generally run without kwargs returns all 'live' messages in a users inbox.
        Live messages include read, unread and saved messages but not deleted.
        These can be accessed by calling with msgtype=deleted or all.

        Some overrides are provided as this method is called by the superuser API also.
        """
        mailboxno = mailboxno or self.mailboxno  # Override for superusers
        if not self.authenticated:
            return False
        params = {'type': self.response_type,
                'func': 'mailboxgetmessages',
                'mailboxno': mailboxno,
                'token': self.token,
                'msgtype': msgtype}
        response = self._handle_GET_request(params)
        return [VoicemailMessage.from_element(self, mailboxno, e, self.endpoint) for e in response.xpath(
            '/c3voicemailapi/messages/message')]

    def delete_message(self, mailboxno, messageid, api='uapi'):
        """
        Delete a message by its ID
        """
        if not self.authenticated:
            return False
        params = {
            'type': self.response_type,
            'func': 'messagedelete',
            'token': self.token,
            'mailboxno': mailboxno,
            'messageid': messageid,
        }
        self._handle_GET_request(params)
        return True

    def forward_message(self, mailboxno, messageid, recipientmailboxno):
        """
        Forward a message to another mailbox
        """
        if not self.authenticated:
            return False
        params = {
            'type': self.response_type,
            'func': 'messageforward',
            'token': self.token,
            'mailboxno': mailboxno,
            'messageid': messageid,
            'recipientmailboxno': recipientmailboxno}
        self._handle_GET_request(params)
        return True

    def save_message(self, mailboxno, messageid):
        """
        Set the status of a message to "saved",
        or un-delete a message
        """
        if not self.authenticated:
            return False
        params = {
            'type': self.response_type,
            'func': 'messagesave',
            'token': self.token,
            'mailboxno': mailboxno,
            'messageid': messageid,
        }
        self._handle_GET_request(params)
        return True

    def pin_update(self, mailboxno, new_pin):
        """Update the PIN of a given mailbox
        Will raise exception 2204 if mailbox is locked.
        :param mailboxno: directory number
        :param new_pin: PIN to update
        """
        if not self.authenticated:
            return False
        params = {
            'type': self.response_type,
            'func': 'pinupdate',
            'token': self.token,
            'mailboxno': mailboxno,
            'newpin': new_pin,
        }
        self._handle_GET_request(params)
        return True


class VoicemailSuperUser(VoicemailUser):
    def __init__(self, username, *args, **kwargs):
        self.username = username
        super(VoicemailSuperUser, self).__init__(0, *args, **kwargs)

    def login(self, supswd, api='uapi'):
        """Login as superuser is done with a username/password
        rather than mailboxno and pin like usual users.
        """
        conn = self.get_connection()
        params = {'type': self.response_type,
                'func': 'superuserlogin',
                'superuser': self.username,
                'superpswd': supswd}
        if self.passwd:
            params['passwd'] = self.passwd
        try:
            conn.request('GET', "/%s.aspx?%s" % (api, urlencode(params)))
            return self._handle_login_response(conn.getresponse())
        except (HTTPException, ImproperConnectionState, socket.timeout, socket.error):
            raise SquirrelConnectionException

    def get_messages(self, mailboxno, **kwargs):
        """Given a mailboxno will retrieve all the message objects"""
        return super(VoicemailSuperUser, self).get_messages(mailboxno, **kwargs)

    def get_message(self, mailboxno, messageid):
        return VoicemailMessage(self, messageid, mailboxno=mailboxno, endpoint=self.endpoint)

    def lock_unlock_mailbox(self, mailboxno, lock=False):
        """Lock or unlock a given mailbox
        :param mailboxno: directory number
        :param lock: (default to False / unlock), True to lock
        """
        if not self.authenticated:
            return False
        params = {
            'type': self.response_type,
            'func': 'mailboxlockunlock',
            'token': self.token,
            'mailboxno': mailboxno,
        }
        if lock:
            params['lock'] = 1
        else:
            params['lock'] = 0
        self._handle_GET_request(params, api='aapi')    # aapi: Administrative API
        return True

    def mailbox_exist(self, mailboxno):
        """Check if a mailbox exist
        :param mailboxno: directory number
        :return True if mailbox exist else False
        """
        params = {
            'type': self.response_type,
            'func': 'mailboxexist',
            'token': self.token,
            'mailboxno': mailboxno,
        }
        response = self._handle_GET_request(params, api='aapi')
        # we expect mailboxexist to be 1 when the mailbox exist or 0 when it doesn't
        try:
            value = int(response.xpath('/c3voicemailapi/mailboxexist')[0].text)
        except ValueError:
            logger.error('Unexpected value in response', exc_info=True)
            raise SquirrelException
        if value == 0:
            return False
        elif value == 1:
            return True
        else:
            logger.error('Unexpected int value {value} in response'.format(value=value))
            raise SquirrelException


if __name__ == '__main__':
    """Test retrieves all messages and downloads as .wav files."""
    user = VoicemailUser(12345)
    user.login(123456)
    messages = user.get_messages()
    for message in messages:
        contents = message.retrieve()
        m = open('%s.wav' % message.id, 'w')
        m.write(contents.read())
