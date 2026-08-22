PYTHON ?= python3

.PHONY: test portal roster resolve ingest-all build-resolution phase1

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

portal:
	PYTHONPATH=src $(PYTHON) -m cfb_portal.ingest portal --season $(YEAR)

roster:
	PYTHONPATH=src $(PYTHON) -m cfb_portal.ingest roster --season $(YEAR) $(if $(TEAM),--team "$(TEAM)",)

resolve:
	PYTHONPATH=src $(PYTHON) -m cfb_portal.cli resolve --portal $(PORTAL) --roster $(ROSTER) --output $(OUT)

START ?= 2021
END ?= 2026

ingest-all:
	PYTHONPATH=src $(PYTHON) -m cfb_portal.pipeline ingest --start $(START) --end $(END)

build-resolution:
	PYTHONPATH=src $(PYTHON) -m cfb_portal.pipeline build --start $(START) --end $(END)

phase1: ingest-all build-resolution
