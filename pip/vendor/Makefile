all: clean vendor

clean:
	@# Delete vendored items
	for i in `find . -maxdepth 1 -type d -print`; do rm -rf $i; done

vendor:
	@# Install vendored libraries
	pip install -t . -r vendor.txt

	@# Cleanup .egg-info directories
	rm -rf *.egg-info
