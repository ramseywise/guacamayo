include ~/.claude/Makefile.common

.PHONY: help lint test pulse install review-lint review-test hygiene hygiene-dry

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

lint:  ## Verify skill files referenced in CLAUDE.md exist
	@echo "Checking skill references..."; \
	MISSING=0; \
	for skill in wake grow dream genesis; do \
		if [ ! -f ".claude/skills/$$skill/SKILL.md" ]; then \
			echo "  MISSING: .claude/skills/$$skill/SKILL.md"; MISSING=1; \
		fi; \
	done; \
	[ $$MISSING -eq 0 ] && echo "  OK (all lifecycle skills present)"

test:  ## Verify identity files exist and have required headers
	@echo "Checking identity structure..."; \
	FAIL=0; \
	for f in .sounding/sounding.md .sounding/user.md .sounding/portfolio.md .sounding/growth.md .sounding/notes/handover.md; do \
		if [ ! -f "$$f" ]; then echo "  MISSING: $$f"; FAIL=1; fi; \
	done; \
	[ $$FAIL -eq 0 ] && echo "  OK (all seed files present)"

pulse:  ## Refresh dashboard pulse with live cross-repo status (PRs, issues, plans)
	@bash scripts/pulse.sh

hygiene:  ## Delete merged/stale branches + show uncommitted state across all repos
	@bash scripts/hygiene.sh

hygiene-dry:  ## Preview hygiene without deleting
	@bash scripts/hygiene.sh --dry-run

install:  ## Install review-cli (editable)
	uv tool install -e .

review-lint:  ## Lint review package
	uv run ruff check review/ tests/review/

review-test:  ## Run review package tests
	uv run pytest tests/review/ -v --tb=short
