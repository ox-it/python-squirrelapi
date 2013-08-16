DIR_NAME = squirrel_api/*

test:
	@pep8 ${DIR_NAME} --ignore=E128,E501,E124,E701,E126 || exit 1
	@pyflakes ${DIR_NAME} || exit 1
	@python setup.py test

