SHELL := /bin/bash

show-help-output:
	@echo -e "------------- pip help -------------\n" 
	@pip help
	@echo

	@for cmd in \
	`pip help \
	 | sed -ne'/Commands:/,/General Options:/s,^\s.*,&,p' \
	 | awk '{print $$1}'`; do \
	echo -e "------------- pip help $$cmd -------------\n"; \
	pip help $$cmd; \
	echo; echo; \
	done
