release: build
	twine upload dist/*

pre_release: build
	twine upload --verbose --repository-url https://test.pypi.org/legacy/ dist/*

build: clean
	python setup.py bdist_wheel

clean: test
	rm -vf dist/*
	rm -rvf build/*

test:
	py.test tests

doc:
	mkdocs build

.PHONY: release
