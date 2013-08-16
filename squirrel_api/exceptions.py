class SquirrelException(Exception):
    pass


class SquirrelApiException(SquirrelException):
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


class SquirrelConnectionException(SquirrelException):
    pass
