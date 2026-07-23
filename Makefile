.PHONY: help lint test pull status push quick-pr ship pulse

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

pull:  ## Pull latest from origin/main
	git pull origin main

status:  ## Show branch, unpushed commits, staged changes, open PRs
	@echo "=== guacamayo ==="
	@echo "Branch: $$(git branch --show-current)"
	@echo "Unpushed:"
	@git log origin/$$(git branch --show-current)..HEAD --oneline 2>/dev/null || echo "  (no remote tracking)"
	@echo "Staged:"
	@git diff --cached --stat 2>/dev/null || true
	@echo "Modified:"
	@git diff --stat 2>/dev/null || true
	@echo "Open PRs:"
	@gh pr list --state open --json number,title,headBranch --jq '.[] | "#\(.number) \(.title) [\(.headBranch)]"' 2>/dev/null || echo "  (none)"

push:  ## Push current branch to origin
	git push -u origin $$(git branch --show-current)

quick-pr:  ## Create PR from current branch with auto-generated body
	@BRANCH=$$(git branch --show-current); \
	if [ "$$BRANCH" = "main" ]; then echo "Error: can't PR from main"; exit 1; fi; \
	EXISTING=$$(gh pr list --head "$$BRANCH" --json number --jq '.[0].number' 2>/dev/null); \
	if [ -n "$$EXISTING" ]; then echo "PR #$$EXISTING already exists for $$BRANCH"; exit 0; fi; \
	COMMITS=$$(git log origin/main..HEAD --oneline 2>/dev/null); \
	ISSUES=$$(echo "$$COMMITS" | grep -oE '#[0-9]+' | sort -u | tr '\n' ' ' | xargs); \
	if [ -n "$$ISSUES" ]; then \
		CLOSES=$$(echo "$$ISSUES" | tr ' ' '\n' | grep -v '^$$' | sed 's/^/Closes /' | tr '\n' ' '); \
	else \
		CLOSES="(no issue references found in commits)"; \
	fi; \
	BODY=$$(printf "## Summary\n%s\n\n%s\n" "$$COMMITS" "$$CLOSES"); \
	echo "Creating PR for $$BRANCH..."; \
	gh pr create --title "$$BRANCH" --body "$$BODY"

pulse:  ## Refresh dashboard pulse with live cross-repo status (PRs, issues, plans)
	@bash scripts/pulse.sh

ship: lint test pull push quick-pr  ## lint → test → pull → push → PR
