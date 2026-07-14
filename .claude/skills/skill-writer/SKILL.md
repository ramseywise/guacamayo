---
name: skill-writer
description: Use when writing, creating, updating, or debugging any SKILL.md file or skill structure. Guide for Claude Code skills — frontmatter, progressive disclosure, activation. Also use proactively when about to create or significantly modify any skill.
---

# Skill Writer

Build well-structured skills that activate reliably and use tokens efficiently.

## Quick Reference

| Decision | Answer |
|----------|--------|
| Where to put it? | `~/.claude/skills/` (personal) or `.claude/skills/` (project) |
| What's required? | `skill-name/SKILL.md` with YAML frontmatter |
| Name format? | kebab-case, max 64 chars, no "claude" or "anthropic" |
| Description limit? | 1024 chars max. 130-200 chars practical sweet spot |
| SKILL.md length? | Under 500 lines. Split to reference files beyond that |
| Restart needed? | No - hot-reload works in CC 2.1+ |

## Instructions

### Phase 1: Define Scope

Establish what the skill does and when it activates.

1. **Identify 2-3 concrete use cases** the skill should handle
2. **Determine invocation model**:

| You want... | Set |
|-------------|-----|
| User AND Claude can invoke (default) | No extra fields needed |
| Only user invokes (side effects: deploy, commit) | `disable-model-invocation: true` |
| Only Claude invokes (background knowledge) | `user-invocable: false` |

3. **Choose location**:
   - Personal (`~/.claude/skills/`) - works across all projects
   - Project (`.claude/skills/`) - shared with team via git
   - Plugin (`skills/` inside plugin dir) - namespaced as `plugin:skill`

4. **Keep it focused**: One skill = one capability. If scope feels broad, split into multiple skills.

### Phase 2: Write the Description

The description is the most critical part. It determines whether the skill ever activates.

**How discovery works**: At startup, Claude loads ONLY name + description for every skill (~100 tokens each). All descriptions share a budget of ~15,000 characters (2% of context window). The description is what Claude uses to decide whether to load the full SKILL.md.

**Formula**: `[What it does] + [When to trigger] + [Specific keywords/file types]`

**Rules**:
- Write in third person ("Use when user asks..." not "Use when you ask...")
- Front-load trigger keywords in the first 50 characters
- List concrete operations, file types, and phrases users would say
- Include edge cases ("even if the extracted content will be used elsewhere")
- All "when to use" info MUST be in description, NOT in body
- Keep single-line in YAML (multi-line breaks discovery - see [gotchas.md](gotchas.md))

**Examples from Anthropic production skills**:

✅ Comprehensive, specific:
```yaml
description: Use this skill whenever the user wants to do anything with PDF files. This includes reading or extracting text/tables from PDFs, combining or merging multiple PDFs into one, splitting PDFs apart, rotating pages, creating new PDFs, filling PDF forms. If the user mentions a .pdf file or asks to produce one, use this skill.
```

✅ Clear with trigger words:
```yaml
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beautifying any web UI).
```

❌ Too vague (won't trigger reliably):
```yaml
description: Helps with documents
```

❌ Missing triggers:
```yaml
description: Creates sophisticated multi-page documentation systems.
```

For large skill collections (40+), keep descriptions under 150 chars. For 60+, under 130 chars.

### Phase 3: Write the Frontmatter

```yaml
---
name: skill-name
description: What it does. Use when [specific triggers].
---
```

That's the minimum. Add optional fields only when needed:

```yaml
---
name: skill-name
description: What it does. Use when [specific triggers].
allowed-tools: Read, Grep, Glob          # Restrict tools (for read-only skills)
disable-model-invocation: true           # Only user can invoke
user-invocable: false                    # Only Claude can invoke
model: sonnet                            # Override model for this skill
argument-hint: [file-path] [options]     # Shown in autocomplete
---
```

For complete frontmatter reference, see [reference.md](reference.md).

### Phase 4: Write the SKILL.md Body

**Default assumption: Claude is already smart.** Challenge every paragraph: "Does Claude really need this? Does this justify its token cost?"

**Less instruction → better output.** Empirically validated: a skill cut from 211 to 94 lines produced *richer* output (14 elements vs 11). Shorter skills leave more context budget for actual reasoning. Don't fill 500 lines because you can - fill only what Claude doesn't already know.

**Use imperative voice**:
- ✅ "Extract text using pdfplumber"
- ❌ "Text should be extracted using..." / "You might want to consider..."

**Recommended section order** (observed across Anthropic's production skills):

```markdown
# Skill Name

## Quick Reference
[Table mapping tasks to approaches - HIGH VALUE, agents treat these as lookup databases]

## Instructions
[Step-by-step workflow with numbered phases]
[Code examples showing actual syntax - code first, explanation second]
[Decision trees for choosing approaches]

## Common Patterns
[Frequently needed operations with concrete examples]

## Critical Rules
[Warnings with ❌ WRONG / ✅ CORRECT format]
[Anti-pattern lists - what NOT to do]

## References
[Links to reference files for advanced/detailed content]
```

**Anti-patterns to avoid in the body**:
- No "When to Use This Skill" section (already in description)
- No meta-commentary ("This skill was created to...", "Version history...")
- No verbose explanations - prefer concise examples
- No asking for permission ("Ask the user if...") - skills assume agency
- No time estimates

### Phase 5: Add Supporting Files (When Needed)

Split content when SKILL.md approaches 500 lines.

```
skill-name/
├── SKILL.md              # Required. Core workflow, <500 lines
├── references/           # Optional. Detailed docs
│   ├── reference.md      # General reference
│   └── domain.md         # Domain-specific details
├── scripts/              # Optional. Executable code
│   └── validate.py       # Run with --help, don't read source
└── assets/               # Optional. Templates, fonts
```

**Progressive disclosure rules**:
- References one level deep from SKILL.md only (no chains)
- Info lives in SKILL.md OR reference files, never both
- Reference files >100 lines: include table of contents
- Reference files >10k words: include grep patterns in SKILL.md
- Scripts: tell Claude to run them, not read them ("black box" pattern)

**Never include**: README.md, INSTALLATION_GUIDE.md, CHANGELOG.md, QUICK_REFERENCE.md. Skills are for AI agents, not humans.

### Phase 6: Validate

Before finalizing:

**Structure**:
- [ ] Folder is kebab-case, matches `name` field
- [ ] SKILL.md exists (exact casing, not SKILL.MD or skill.md)
- [ ] YAML frontmatter has `---` delimiters on lines 1 and 3+
- [ ] No XML angle brackets (`<` `>`) in frontmatter
- [ ] Forward slashes in all paths (even on Windows)

**Description**:
- [ ] Under 1024 characters
- [ ] Single-line in YAML (not multi-line/folded)
- [ ] Includes WHAT it does AND WHEN to trigger
- [ ] Contains specific keywords, file types, or user phrases
- [ ] Written in third person

**Content**:
- [ ] SKILL.md under 500 lines
- [ ] Imperative voice throughout
- [ ] Concrete examples, not abstract explanations
- [ ] No "when to use" section in body
- [ ] Reference files one level deep only

**Testing**:
- [ ] Ask Claude: "When would you use the [skill-name] skill?" - verify it quotes trigger conditions
- [ ] Test with obvious query that should trigger
- [ ] Test with paraphrased query
- [ ] Test with unrelated query (should NOT trigger)
- [ ] Test with blank/fresh Claude (no prior context) for true quality check

### Phase 7: Iterate

Skills are living documents. Watch for:

**Undertriggering** (skill doesn't load when it should):
→ Add more trigger keywords and phrases to description
→ Include file types and specific operations
→ Front-load the most common trigger in first 50 chars

**Overtriggering** (skill loads for unrelated queries):
→ Add negative triggers: "Do NOT use for simple data exploration"
→ Be more specific about scope
→ Narrow the description

**Instructions not followed**:
→ Move critical rules to top of SKILL.md
→ Use CRITICAL: headers and ❌/✅ formatting
→ Add verification commands Claude must run before completing
→ For critical validation, use scripts (code is deterministic; language isn't)

For troubleshooting common failures, see [gotchas.md](gotchas.md).

## Output

When creating a skill:

1. Create directory structure
2. Write SKILL.md with frontmatter + body
3. Add reference files if content exceeds 500 lines
4. Run through validation checklist
5. Suggest 3-5 test queries for the user to try
