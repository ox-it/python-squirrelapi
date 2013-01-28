import httplib
import logging

from urllib import urlencode
from lxml import etree
from datetime import datetime

logger = logging.getLogger(__name__)


class SquirrelAPIResource(object):
    def __init__(self, passwd=None, response_type='xml',
                endpoint='voicemail.example.com'):
        self.passwd = passwd
        self.response_type = response_type
        self.endpoint = endpoint

    def get_connection(self):
        return httplib.HTTPConnection(self.endpoint)


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


class SquirrelApiException(Exception):
    """
    Custom exception for Squirrel API
    """

    ERROR_CODES = {
        0: 'Success',
        2000: 'Password errors',
        2001: 'Type parameter issues',
        2002: 'Func parameter issues',
        2003: 'Extn parameter issues',
        2010: 'Problem generating statistics',
        2100: 'Mailboxno parameter issues',
        2101: 'Pin parameter issues',
        2102: 'Token invalid',
        2103: 'Name parameter issues',
        2104: 'Cos parameter issues',
        2105: 'Messageid parameter issues',
        2106: 'Greetingnumber parameter issues',
        2107: 'Email parameter issues',
        2108: 'Userdata1 parameter issues',
        2109: 'Cli parameter issues',
        2110: 'Pinrequired parameter issues',
        2111: 'Superuser parameter issues',
        2112: 'Superuserpswd parameter issues',
        2113: 'Greeting number parameter issues',
        2114: 'Marksaved parameter issues',
        2115: 'Action parameter issues',
        2116: 'Lock parameter issues',
        2200: 'Mailbox already exists',
        2201: 'Mailbox does not exist',
        2202: 'Invalid COS',
        2203: 'Validation CLI already in use',
        2204: 'Mailbox locked',
        2205: 'Incorrect PIN',
        2206: 'Incorrect PIN, mailbox locked',
        2207: 'Super User login failed',
        2208: 'Security token invalid',
        2209: 'Message ID invalid',
        2210: 'Validation CLI not used',
        2211: 'Weak PIN',
        2212: 'PIN update required',
        2213: 'PIN not changed',
        2999: 'Other general errors',
    }

    def __init__(self, error_code, path):
        self.error_code = error_code
        self.path = path

    def __str__(self):
        return "Squirrel API returned value {0} ('{1}') for path '{2}'."\
            .format(self.error_code,
                self.ERROR_CODES[self.error_code],
                self.path)


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
        if self.passwd: params['passwd'] = self.passwd
        conn.request('GET', "/%s.aspx?%s" % (
                    api, urlencode(params)))
        return self._handle_login_response(conn.getresponse())

    def _handle_login_response(self, login_response):
        response = etree.parse(login_response)
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
        conn.request('GET', path)
        response = etree.parse(conn.getresponse())
        code = int(response.xpath('/c3voicemailapi/error/code')[0].text)
        if code != 0:
            # Error_code = 0 means "Success"
            raise SquirrelApiException(code, path)
        return response

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
        response = self._handle_GET_request(params)
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
        response = self._handle_GET_request(params)
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
        response = self._handle_GET_request(params)
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
        if self.passwd: params['passwd'] = self.passwd
        conn.request('GET', "/%s.aspx?%s" % (
                    api, urlencode(params)))
        return self._handle_login_response(conn.getresponse())

    def get_messages(self, mailboxno, **kwargs):
        """Given a mailboxno will retrieve all the message objects"""
        return super(VoicemailSuperUser, self).get_messages(mailboxno, **kwargs)

    def get_message(self, mailboxno, messageid):
        return VoicemailMessage(self, messageid, mailboxno=mailboxno, endpoint=self.endpoint)

if __name__ == '__main__':
    """Test retrieves all messages and downloads as .wav files."""
    user = VoicemailUser(12345)
    user.login(123456)
    messages = user.get_messages()
    for message in messages:
        contents = message.retrieve()
        m = open('%s.wav' % message.id, 'w')
        m.write(contents.read())
