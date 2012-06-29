from setuptools import setup, find_packages

install_requires = open('requirements.txt').readlines()

tests_requires = ["unittest2", "mock"]

setup(name='squirrelapi',
        description='Python wrapper for C3 Squirrel Voicemail HTTP API',
        author='Mobile Oxford',
        author_email='oucs-mobileox@maillist.ox.ac.uk',
        url='https://github.com/oucs/telecoms-self-service',
        version='0.1',
        py_modules=['squirrelapi'],
        setup_requires=["setuptools"],
        install_requires=install_requires,
        tests_require=tests_requires,
        test_suite = "tests",
        )
