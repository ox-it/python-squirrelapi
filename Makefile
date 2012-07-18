FILE_NAME = squirrelapi.py

test:
	pep8 ${FILE_NAME} --ignore=E128,E501,E124,E701,E126 || exit 1
	pyflakes -x W ${FILE_NAME} || exit 1
	python setup.py test

