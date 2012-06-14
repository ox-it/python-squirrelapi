import httplib

from urllib import urlencode
from lxml import etree
from datetime import datetime


class SquirrelAPIResource(object):
    def __init__(self, passwd=None, response_type='xml',
            endpoint='voicemail.telecoms.ox.ac.uk'):
        self.passwd = passwd
        self.response_type = response_type
        self.endpoint = endpoint

    def get_connection(self):
        return httplib.HTTPConnection(self.endpoint)


class VoicemailMessage(SquirrelAPIResource):
    MESSAGE_STATUS = {1: 'new', 2: 'urgent', 3: 'saved', 4: 'deleted'}
    MESSAGE_TYPE = {1: 'voice', 2: 'fax'}

    def __init__(self, user, id, status, type, created, sendercli,
            sendermbx, length, mailboxno, **kwargs):
        self.user = user
        self.id = id
        self.status = status
        self.type = type
        self.created = created
        self.sendercli = sendercli
        self.sendermbx = sendermbx,
        self.length = length
        self.mailboxno = mailboxno
        super(VoicemailMessage, self).__init__(**kwargs)

    @classmethod
    def from_element(cls, user, mailboxno, elem):
        """Constructs Messages from etree message Elements"""
        kwargs = {'id': elem.find('id').text,
                'status': int(elem.find('status').text),
                'type': int(elem.find('type').text),
                'created': datetime.strptime(elem.find('created').text,
                    '%Y/%m/%d %I:%M:%S %p'),
                'sendercli': elem.find('sendercli').text,
                'sendermbx': elem.find('sendermbx').text,
                'length': int(elem.find('length').text),
                }
        return cls(user, mailboxno=mailboxno, **kwargs)

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
        return response.read()



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
            return (False, code)
        else:
            self.token = response.xpath('/c3voicemailapi/token')[0].text
            return (True, self.token)

    def get_messages(self, mailboxno=None, msgtype='live', api='uapi'):
        """Generally run without kwargs returns all 'live' messages in a users inbox.
        Live messages include read, unread and saved messages but not deleted.
        These can be accessed by calling with msgtype=deleted or all.

        Some overrides are provided as this method is called by the superuser API also.
        """
        mailboxno = mailboxno or self.mailboxno  # Override for superusers
        if not self.authenticated:
            return False
        conn = self.get_connection()
        params = {'type': self.response_type,
                'func': 'mailboxgetmessages',
                'mailboxno': mailboxno,
                'token': self.token,
                'msgtype': msgtype}
        if self.passwd: params['passwd'] = self.passwd
        conn.request('GET', "/%s.aspx?%s" % (
                    api, urlencode(params)))
        response = etree.parse(conn.getresponse())
        return [VoicemailMessage.from_element(self, mailboxno, e) for e in response.xpath(
            '/c3voicemailapi/messages/message')]

    def delete_message(self, mailboxno, messageid, api='uapi'):
        """
        Delete a message by its ID
        """
        if not self.authenticated:
            return False
        conn = self.get_connection()
        params = {
            'type': self.response_type,
            'func': 'messagedelete',
            'token': self.token,
            'mailboxno': mailboxno,
            'messageid': messageid,
        }
        if self.passwd: params['passwd'] = self.passwd
        conn.request('GET', "/%s.aspx?%s" % (
            api, urlencode(params)))
        response = etree.parse(conn.getresponse())
        return int(response.xpath('/c3voicemailapi/error')[0].find('code').text)

    def forward_message(self, mailboxno, messageid, recipientmailboxno, api='uapi'):
        """
        Forward a message to another mailbox
        """
        if not self.authenticated:
            return False
        conn = self.get_connection()
        params = {
            'type': self.response_type,
            'func': 'messageforward',
            'token': self.token,
            'mailboxno': mailboxno,
            'messageid': messageid,
            'recipientmailboxno': recipientmailboxno
            }
        if self.passwd: params['passwd'] = self.passwd
        conn.request('GET', "/%s.aspx?%s" % (
            api, urlencode(params)))
        response = etree.parse(conn.getresponse())
        return int(response.xpath('/c3voicemailapi/error')[0].find('code').text)

    def save_message(self, mailboxno, messageid, api='uapi'):
        """
        Set the status of a message to "saved"
        """
        if not self.authenticated:
            return False
        conn = self.get_connection()
        params = {
            'type': self.response_type,
            'func': 'messagesave',
            'token': self.token,
            'mailboxno': mailboxno,
            'messageid': messageid,
        }
        if self.passwd: params['passwd'] = self.passwd
        conn.request('GET', "/%s.aspx?%s" % (
            api, urlencode(params)))
        response = etree.parse(conn.getresponse())
        return int(response.xpath('/c3voicemailapi/error')[0].find('code').text)


class VoicemailSuperUser(VoicemailUser):
    def __init__(self, username):
        self.username = username
        super(VoicemailSuperUser, self).__init__(0)

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

if __name__ == '__main__':
    """Test retrieves all messages and downloads as .wav files."""
    su = VoicemailSuperUser('SUPERUSERNAME')
    su.login('SUPERPASSWORD')
    messages = su.get_messages(0)
    for message in messages:
        contents = message.retrieve()
        m = open('%s.wav' % message.id, 'w')
        m.write(contents)
