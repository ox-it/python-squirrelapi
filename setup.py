from setuptools import setup, find_packages

install_requires = open('requirements.txt').readlines()

tests_requires = ["unittest2", "mock"]

setup(name='squirrelapi',
        description='Python wrapper for C3 Squirrel Voicemail HTTP API',
        author='Mobile Oxford',
        author_email='mobileoxford@oucs.ox.ac.uk',
        url='https://github.com/ox-it/python-squirrelapi',
        version='0.6',
        py_modules=['squirrel_api', 'squirrel_api.exceptions'],
        setup_requires=["setuptools"],
        install_requires=install_requires,
        tests_require=tests_requires,
        classifiers=[
            'Development Status :: 4 - Beta',
            'License :: OSI Approved :: Apache Software License',
            'Intended Audience :: Developers',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Topic :: Communications :: Telephony',
            'Topic :: Communications :: Internet Phone',
            ],
        test_suite = "tests",
        )
