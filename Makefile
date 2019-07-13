clean:
	rm -vf dist/*

build: clean
	python setup.py bdist_wheel

pre_release: build
	twine upload --verbose --repository-url https://test.pypi.org/legacy/ dist/*

release: build
	twine upload dist/*

.PHONY: release
