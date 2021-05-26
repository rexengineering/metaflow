TARGETS=rexflowctl rexflowlib

all:
	python ../tools/metasetup.py
	for subdir in $(TARGETS); do ( \
		pushd $$subdir; \
		python -m build; \
	); done

clean:
	for subdir in $(TARGETS); do ( \
		pushd $$subdir; \
		rm -f setup.py; \
	    rm -rf flow*; \
		rm -rf build dist *.egg-info; \
	); done

upload: all
	for subdir in $(TARGETS); do ( \
		pushd $${subdir}/dist; \
		anaconda upload $${subdir}-*.tar.gz -u rexchange --private --all; \
	); done

.PHONY: all clean upload
