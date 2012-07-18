# python-squirrelapi

[![Build Status](https://secure.travis-ci.org/oucs/python-squirrelapi.png?branch=master)](http://travis-ci.org/oucs/python-squirrelapi)

This project wraps the Squirrel HTTP API and provides sensible Python object representations for key resources (users, mailboxes and messages for example).

Example code for authenticating and downloading all your messages as '.wav' files to the working directory.


    user = VoicemailUser(555555)  # Mailboxno
    user.login(123456)  # pin
    messages = user.get_messages()
    for message in messages:
        contents = message.retrieve()
        m = open('%s.wav' % message.id, 'w')
        m.write(contents)

## Tests

You can run tests using:

    python setup.py test

## Revision

This has been developed against the C3 Squirrel documentation "Issue 11". 
