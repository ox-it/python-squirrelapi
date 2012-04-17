# Python API for C3 Squirrel Voicemail

This project wraps the Squirrel HTTP API and provides sensible Python object representations for key resources (users, mailboxes and messages for example).

Example code for authenticating and downloading all your messages as '.wav' files to the working directory.
```python
user = VoicemailUser(555555)  # Mailboxno
user.login(123456)  # pin
messages = user.get_messages()
for message in messages:
    contents = message.retrieve()
    m = open('%s.wav' % message.id, 'w')
    m.write(contents)
```
