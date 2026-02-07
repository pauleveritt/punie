# Author Artifact Command

Interactive command for creating or updating Agent OS standards and Claude Code skills based on existing knowledge.

## Important Guidelines

This command helps you decide **what format** your knowledge should take, then creates it in the right location:
- **Standards** (managed by Agent OS) — Declarative conventions in `profiles/pauleveritt/standards/`
- **Skills** (managed by Claude Code) — Procedural workflows in `~/.claude/skills/` or `.claude/skills/`

The command checks for overlaps in **both** locations to prevent duplication.

**Related Commands:**
- `/discover-standards` — Extract standards from existing code
- `/inject-standards` — Add standards to context explicitly
- `/index-standards` — Update standards index.yml file

**Key Principles:**
- Always check for overlap with both standards AND skills
- Process one artifact at a time
- Use AskUserQuestion for all interactions
- Follow the authoring-conventions standard

### Step 1: Understand Intent

Check if the user provided arguments with their `/author-artifact` command.

**If arguments provided:** Use them as the description of what they want to document.

**If no arguments:** Ask what knowledge they want to document. Example question:
- "What would you like to document? Describe the convention, rule, or workflow you want to capture."

### Step 1.5: Detect Update Intent

If the invocation text includes the word "update" (case-insensitive), assume the user wants to improve an existing artifact.

1. Search existing standards and skills for likely matches:
   - Standards: `profiles/pauleveritt/standards/index.yml`
   - Skills: `~/.claude/skills/*.md` frontmatter
2. Prompt the user to select which artifact to update.
3. If no matches are found, ask the user to name the artifact or provide a path.

If the user does **not** explicitly say "update," still listen for hints that something already exists (e.g., "current," "existing," file paths, or a known artifact name). If detected, ask:

```
It sounds like something already exists. Do you want to update an existing artifact instead of creating a new one?

Options:
1. Yes - update existing
2. No - create new
```

If they choose update, follow the update flow below.

### Step 2: Classify — Standard or Skill?

Analyze the user's description against decision criteria:

**Standard Indicators:**
- Expressing a convention or rule (declarative)
- Needs explicit control over when it's used
- Combinable with other standards
- Cross-cutting concern
- Expressible in 15-40 lines
- Focuses on "what" and "why"

**Skill Indicators:**
- Describing procedural steps (imperative)
- Should auto-invoke based on user request
- Self-contained workflow
- Needs 100+ lines to explain
- Focuses on "how" to execute
- May need bundled resources

**Present recommendation via AskUserQuestion:**

```
Based on your description, I recommend creating a [STANDARD/SKILL] because [brief rationale].

Options:
1. Standard (15-40 lines, explicit injection, rule-based) [mark as recommended if appropriate]
2. Simple Skill (100+ lines, auto-loads, procedural workflow)
3. Complex Skill (needs scripts/references/assets, folder structure)
4. Not sure — ask me clarifying questions
```

**If "Not sure" selected:** Ask 2-3 targeted follow-up questions:
- "Is this primarily a rule/convention or a step-by-step process?"
- "Should this auto-load when users work on related tasks, or be explicitly injected?"
- "Is this a single principle or a multi-step workflow?"

After clarifying questions, present the recommendation again.

### Step 3: Check for Overlap in BOTH Locations

Read existing artifacts to identify overlaps in both standards AND skills:

1. **Read** `profiles/pauleveritt/standards/index.yml` for all standard descriptions
2. **Scan** `~/.claude/skills/*.md` frontmatter for skill descriptions (use Glob + Read)
3. **Check BOTH directions** regardless of classification:
   - If creating a standard, check skills too
   - If creating a skill, check standards too

**Present findings via AskUserQuestion:**

If overlaps found:
```
I found potential overlaps with existing artifacts:

Standards:
- [standard name] — [description]

Skills:
- [skill name] — [description]

How would you like to proceed?
1. Update [existing artifact name] — improve the existing file
2. Consolidate [artifacts] — merge overlapping content
3. Create anyway — overlap is intentional
4. Cancel — existing coverage is sufficient
```

If no overlaps found:
```
No overlaps found with existing standards or skills. Ready to proceed with creating a new [standard/skill].
```

---

## Updating an Existing Artifact

### Step U1: Identify the Artifact

If update intent was detected, confirm the target artifact and locate its file path:
- Standards: `profiles/pauleveritt/standards/{category}/{name}.md`
- Skills: `~/.claude/skills/{name}.md` or `.claude/skills/{name}.md`

If multiple matches exist, ask the user to choose.

### Step U2: Understand Desired Changes

Ask what should be improved or added. Keep questions short and focused:
- "What should be added, removed, or clarified?"
- "Are there new examples or edge cases to include?"
- "Do any rules change?"

### Step U3: Draft the Revision

Read the existing artifact and draft an updated version that preserves its format:
- Standards: stay within 15-40 lines; keep example, ## Why, ## Rules
- Skills: keep YAML frontmatter; preserve sections like ## Anti-Patterns and ## Related Skills

### Step U4: Confirm and Apply

Present the draft and ask:

```
Would you like to:
1. Apply these updates
2. Request edits
3. Cancel
```

If applying:
- Update the file in place
- For standards, update `profiles/pauleveritt/standards/index.yml` if the description should change

---

## Creating a Standard

### Step 4: Determine Location and Naming

- Suggest category folder (existing or new) in `profiles/pauleveritt/standards/{category}/`
- Suggest kebab-case filename
- Example: `profiles/pauleveritt/standards/testing/async-fixtures.md`

**Ask via AskUserQuestion:**

```
Suggested location and name:
[path/to/file]

Options:
1. Use suggested location
2. Specify different location [allow user to provide path]
```

### Step 5: Gather Content — From Code or Description

**Ask via AskUserQuestion:**

```
How would you like to provide the content for this standard?

1. **Point to example code** — I'll analyze specific files/functions [Recommended]
2. **Describe directly** — Answer questions about the convention
```

#### Option 1: Point to Example Code (Extraction Logic from /discover-standards)

**Ask for code location:**
```
Which file(s) or function(s) demonstrate this pattern?

Provide paths like:
- src/api/routes.py
- src/components/Button.tsx
- src/services/*.py (glob pattern)
```

**Then analyze the code:**
1. Read the specified files
2. Look for the specific pattern the user mentioned
3. Extract:
   - Code examples that demonstrate the pattern
   - The underlying principle/rule
   - Why this pattern is used (infer from code context)

**Ask clarifying questions:**
```
I see the pattern in the code. A few questions:

1. What problem does this pattern solve? Why not use [alternative approach]?
2. Are there exceptions where this pattern shouldn't be used?
```

Wait for response, then proceed to draft.

#### Option 2: Describe Directly

Ask domain-specific questions to gather content details:

- "What code example best demonstrates this standard?"
- "What problem does this solve? (for ## Why section)"
- "What are the specific rules? (for ## Rules section)"
- "Are there any exceptions or edge cases?"

**Important:** Ask questions incrementally (2-3 at a time), not all at once.

### Step 6: Draft and Confirm Standard

Before drafting, **read the authoring-conventions standard** for format requirements.

Draft the standard following the format:

```markdown
# Title

[Code example]

## Why

[1-2 sentence rationale]

## Rules

- Rule 1
- Rule 2
- Rule 3
```

**Present draft via normal output, then ask:**

```
Here's the draft standard. Would you like to:
1. Create it as-is
2. Request edits [allow user to specify changes]
3. Cancel
```

### Step 7: Create Standard File and Update Index

1. Create the file at the determined location
2. Update `profiles/pauleveritt/standards/index.yml`
3. Ask user to confirm the description for index.yml via AskUserQuestion:
   ```
   Suggested index.yml entry:

   category:
     standard-name:
       description: [Brief description]

   Options:
   1. Use this description
   2. Provide different description [allow user input]
   ```
4. Add entry to index.yml under appropriate category

**Provide summary:**
```
✅ Created standard at [path]
✅ Updated index.yml

Next steps:
- Use /inject-standards to test the standard
- Use /sync-agent-os to deploy to other projects
```

---

## Creating a Skill

### Step 4: Determine Location and Naming

**Ask via AskUserQuestion:**

```
Where should this skill live?

1. **Global** (~/.claude/skills/) — Available in all projects [Recommended]
2. **Project-local** (.claude/skills/) — Only this project

Which location?
```

Then suggest a kebab-case filename:
```
Suggested name: [skill-name].md

Options:
1. Use this name
2. Specify different name [allow user input]
```

**For Complex Skills with folder structure:**

If the user selected "Complex Skill" in Step 2, ask:
```
This will be a complex skill with bundled resources. Will you need:

1. Scripts (Python/Bash for automation)
2. References (detailed docs loaded as needed)
3. Assets (templates, images, boilerplate files)

Select all that apply (or none for simple folder structure)
```

**Determine final location:**
- Simple skill: `~/.claude/skills/{name}.md` or `.claude/skills/{name}.md`
- Complex skill: `~/.claude/skills/{name}/SKILL.md` or `.claude/skills/{name}/SKILL.md`

### Step 5: Ask Clarifying Questions for Skill

Ask domain-specific questions to gather content details:

- "What are the key steps in this workflow?"
- "What tools or commands are involved?"
- "When should this skill auto-load? (for the description frontmatter)"
- "What are common mistakes or anti-patterns?"
- "Are there related skills or standards users should know about?"

**Important:** Ask questions incrementally (2-3 at a time), not all at once.

### Step 6: Draft and Confirm Skill

Draft the skill following Claude Code's skill format:

**For Simple Skills:**

```markdown
---
description:
  [Comprehensive description including when to use this skill.
  This triggers auto-loading, so be specific about contexts.]
allowed-tools: [optional]
---

# Skill Title

## Overview
[Content]

## Key Steps
[Workflow steps]

## Anti-Patterns
[Common mistakes]

## Related Standards
[References to @agent-os/standards/ if relevant]
```

**For Complex Skills:**

Provide guidance on:
- What to include in SKILL.md (overview, workflow, references to bundled resources)
- What scripts to create in scripts/ directory
- What documentation to include in references/
- What assets to place in assets/

**Present draft via normal output, then ask:**

```
Here's the draft skill. Would you like to:
1. Create it as-is
2. Request edits [allow user to specify changes]
3. Cancel
```

### Step 7: Create Skill File

**For Simple Skills:**
1. Create the .md file at the determined location (`~/.claude/skills/` or `.claude/skills/`)

**For Complex Skills:**
1. Create the folder structure:
   - `{name}/SKILL.md` (main entry point)
   - `{name}/scripts/` (if requested)
   - `{name}/references/` (if requested)
   - `{name}/assets/` (if requested)
2. Create initial SKILL.md with guidance on how to populate the folders

**Provide summary:**
```
✅ Created skill at [path]

This skill is managed by Claude Code (not Agent OS).
It will auto-load based on its description frontmatter.

Next steps:
- Test the skill by working on a relevant task
- Refine the description if it's not auto-loading correctly
- Add related standards references if applicable
```

---

## Design Notes

**Why "author-artifact"**: Neutral term covering both standards (managed by Agent OS) and skills (managed by Claude Code natively). "Author" signals intentional creation vs "discover" which signals extraction from code.

**Overlap check timing**: Before drafting saves time and tokens vs discovering overlap after writing.

**Bidirectional overlap checking**: Essential because:
- A new standard might overlap with an existing skill
- A new skill might overlap with existing standards
- Prevents duplication and maintains consistency

**Code extraction for standards**: Bridges the gap between `/discover-standards` (scan codebase) and `/author-artifact` (I know what I want). When you know the pattern and can point to examples, extraction is more accurate than describing from memory.

**Skills written to Claude Code locations**: Agent OS doesn't manage skills (no syncing, no `profiles/*/skills/`), but `/author-artifact` can still create skill files in Claude Code's native locations for convenience.

**Complements /discover-standards**:
- `/discover-standards` — extracts from code (broad discovery)
- `/author-artifact` with code examples — extracts from specific examples (focused authoring)
- `/author-artifact` with description — creates from knowledge (pure authoring)
