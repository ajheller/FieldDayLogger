PYTHON ?= python3
SOAK_CMD ?= $(PYTHON) -m fdlogger_next.soak

SOAK_DB ?= soak.db
SOAK_LOG ?= soak.jsonl
SMOKE_SOAK_DB ?= /tmp/fdlogger-next-smoke-soak.db
SMOKE_SOAK_LOG ?= /tmp/fdlogger-next-smoke-soak.jsonl

.PHONY: help
help:
	@printf "FieldDayLogger development targets\n"
	@printf "\n"
	@printf "  make test          Run focused prototype tests\n"
	@printf "  make compile       Compile prototype modules\n"
	@printf "  make check         Run tests, compile, and whitespace check\n"
	@printf "  make install-dev   Reinstall editable checkout into pipx fdlogger app\n"
	@printf "  make commands      Check installed console-script entry points\n"
	@printf "  make gui           Run the prototype Qt GUI\n"
	@printf "  make smoke-soak    Run a 100-operation store soak smoke test\n"
	@printf "  make soak-12h      Run a 12-hour MacBook-style soak\n"
	@printf "  make soak-36h      Run a 36-hour laptop soak\n"
	@printf "\n"
	@printf "Variables: PYTHON, SOAK_CMD, SOAK_DB, SOAK_LOG\n"

.PHONY: test
test:
	$(PYTHON) -W error::ResourceWarning -m unittest testing.test_fdlogger_next

.PHONY: compile
compile:
	$(PYTHON) -m compileall fdlogger_next testing/test_fdlogger_next.py

.PHONY: check
check: test compile
	git diff --check

.PHONY: install-dev
install-dev:
	pipx inject fdlogger --editable .

.PHONY: commands
commands:
	fdlogger-next --help
	fdlogger-next-cli --help
	fdlogger-next-soak --help

.PHONY: gui
gui:
	$(PYTHON) -m fdlogger_next.gui FieldDayNext.db --station station-1 --operator AK6IM

.PHONY: smoke-soak
smoke-soak:
	$(SOAK_CMD) $(SMOKE_SOAK_DB) \
		--seconds 3600 \
		--rate 0 \
		--max-operations 100 \
		--check-interval 0 \
		--rebuild-interval 0 \
		--restart-interval 0 \
		--log $(SMOKE_SOAK_LOG) \
		--seed 11 \
		--quiet
	@tail -n 1 $(SMOKE_SOAK_LOG)

.PHONY: soak-12h
soak-12h:
	$(SOAK_CMD) $(SOAK_DB) \
		--hours 12 \
		--rate 120 \
		--check-interval 60 \
		--rebuild-interval 300 \
		--restart-interval 1800 \
		--log $(SOAK_LOG)

.PHONY: soak-36h
soak-36h:
	$(SOAK_CMD) $(SOAK_DB) \
		--hours 36 \
		--rate 30 \
		--check-interval 60 \
		--rebuild-interval 300 \
		--restart-interval 7200 \
		--log $(SOAK_LOG)
