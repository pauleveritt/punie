# Sync Agent OS Command

Synchronize Agent OS standards and commands across multiple projects.

## Important Guidelines

This command discovers projects with Agent OS installed and syncs updates from the current (source) project. It mimics the logic from `scripts/project-install.sh` but for updates rather than fresh installs.

**Use case:** You're in `agent-os` source project, created new standards, want to push to projects like `tdom-django`.

**Key behaviors (forked from project-install.sh):**
- Flattens `profiles/{profile}/standards/` → `agent-os/standards/` in target
- Installs commands to `.claude/commands/agent-os/` in target
- Preserves existing descriptions in target's `index.yml`
- Shows what changed (added/modified/unchanged)

## Usage Modes

### Discover Mode (no arguments)
```
/sync-agent-os
```
Scans for all projects with Agent OS installed and presents selection.

### Direct Mode (with argument)
```
/sync-agent-os /Users/pauleveritt/projects/pauleveritt/tdom-django
/sync-agent-os ~/projects/pauleveritt/tdom-django
```
Syncs directly to the specified project, skipping discovery and selection.

### Step 1: Verify Current Project Has Agent OS Source

Check if current project is the Agent OS source:

- `profiles/pauleveritt/standards/index.yml` exists
- `commands/agent-os/` exists

If not, error: "Current project doesn't appear to be the Agent OS source. Run this from the agent-os repository."

### Step 2: Commit Source Changes

Check git status in current project. If there are uncommitted changes in Agent OS files:

**Ask via AskUserQuestion:**

```
The source project has uncommitted changes:
- profiles/pauleveritt/standards/authoring-conventions.md (new)
- commands/agent-os/author-artifact.md (modified)
- profiles/pauleveritt/standards/index.yml (modified)

Commit these changes before syncing?

Options:
1. Yes - commit with auto-generated message [Recommended]
2. Yes - let me write the commit message
3. Skip - sync uncommitted changes anyway
4. Cancel sync
```

If option 1: Generate commit message listing new/modified standards and commands:
```
Update Agent OS: add authoring-conventions standard, update author-artifact command

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

If option 2: Ask for commit message via AskUserQuestion, then commit.

### Step 3: Discover Target Projects

**Check if project path was provided as argument:**

If an argument was provided (e.g., `/sync-agent-os ~/projects/pauleveritt/tdom-django`):

1. **Expand and normalize the path:**
   - Expand `~` to home directory
   - Convert to absolute path

2. **Validate the path:**
   - Check if directory exists
   - Check if `agent-os/standards/index.yml` exists (confirms Agent OS is installed)
   - Check if path is different from current project

3. **If validation fails:**
   - Show error: "Invalid project path: `{path}`. Directory doesn't exist or doesn't have Agent OS installed (missing `agent-os/standards/index.yml`)."
   - Fall back to discovery mode (continue with scanning below)

4. **If validation succeeds:**
   - Set this as the single target project
   - Skip project selection prompt
   - Proceed directly to Step 4 (Choose Sync Scope)

**If no argument provided, scan for projects with Agent OS installed (v2 structure):**

1. List directories in `~/.claude/projects/`
2. For each project directory name:
   - Decode path (e.g., `-Users-pauleveritt-projects-pauleveritt-tdom-django` → `/Users/pauleveritt/projects/pauleveritt/tdom-django`)
   - Check if directory exists
   - Check if `agent-os/standards/index.yml` exists (v2 structure)
   - If yes, add to candidates
3. Exclude current project

**Present via AskUserQuestion:**

```
Found N projects with Agent OS installed:

1. /Users/pauleveritt/projects/pauleveritt/tdom-django
2. /Users/pauleveritt/projects/t-strings/svcs-di

Which projects would you like to sync?

Options:
- All projects
- Select specific projects [multi-select]
- Cancel
```

### Step 4: Choose Sync Scope

**Ask via AskUserQuestion:**

```
What should be synced?

Options:
1. Standards + Commands [Recommended]
2. Standards only
3. Commands only
4. Standards + Commands + CLAUDE.md sections
```

**If option 4 selected**, ask a follow-up:

```
Which sections from this project's CLAUDE.md should be synced to targets?

[Show list of ## sections from source CLAUDE.md]

Options:
- All sections
- Select specific sections [multi-select]
- Skip CLAUDE.md sync
```

### Step 5: Preview Changes for Each Project

For each target project, compare source and target:

**Standards comparison:**
- Read source: `profiles/pauleveritt/standards/**/*.md`
- Read target: `agent-os/standards/**/*.md`
- Compare using content hashing (or simple diff)
- Categorize: Added / Modified / Unchanged

**Commands comparison:**
- Read source: `commands/agent-os/*.md`
- Read target: `.claude/commands/agent-os/*.md`
- Categorize: Added / Modified / Unchanged

**Present via AskUserQuestion:**

```
Preview for /Users/pauleveritt/projects/pauleveritt/tdom-django:

Standards:
  Added:
    - authoring-conventions.md
  Modified:
    - index.yml (will add 1 new entry)
  Unchanged:
    - 7 other standards

Commands:
  Added:
    - author-artifact.md
    - sync-agent-os.md
  Modified:
    - inject-standards.md
  Unchanged:
    - 4 other commands

Proceed with this project?

Options:
1. Yes - sync this project
2. Skip this project
3. Show detailed diff
4. Cancel entire sync
```

### Step 6: Clean Up Target Projects

Before syncing, clean up any legacy Agent OS artifacts from the cline-fork era:

For each target project, check for and remove:
- `agent-os/skills/` directory (if exists from old structure)
- `.claude/skills/` directory (if exists and was managed by Agent OS, not user-created)
- Any references to `@agent-os/skills/` in standards files
- Any references to `@agent-os/skills/` in CLAUDE.md

**Important:** Only remove `.claude/skills/` if it contains files that match Agent OS skill patterns (check for YAML frontmatter with Agent OS references). User-created skills should be preserved.

**Report cleanup:**
```
Cleaning up /Users/pauleveritt/projects/pauleveritt/tdom-django...
  ✅ Removed agent-os/skills/ directory (legacy)
  ✅ Removed 3 Agent OS-managed skills from .claude/skills/
  ✅ Cleaned 2 @agent-os/skills/ references from standards files
  ✅ Cleaned 1 @agent-os/skills/ reference from CLAUDE.md
```

If no cleanup needed, proceed silently.

### Step 7: Execute Sync (Forked from project-install.sh)

For each approved project, perform the sync following project-install.sh logic:

#### 7.1: Sync Standards (if selected)

**Source:** `profiles/pauleveritt/standards/`
**Target:** `{project}/agent-os/standards/`

For each `.md` file in source:
1. Get relative path (e.g., `testing/fakes-over-mocks.md`)
2. Create target directory if needed: `mkdir -p {project}/agent-os/standards/testing`
3. Copy file: `cp source_file target_file`
4. Track: Added or Updated

**Example:**
```bash
# Source: profiles/pauleveritt/standards/authoring-conventions.md
# Target: tdom-django/agent-os/standards/authoring-conventions.md

cp profiles/pauleveritt/standards/authoring-conventions.md \
   /Users/pauleveritt/projects/pauleveritt/tdom-django/agent-os/standards/authoring-conventions.md
```

#### 7.2: Sync Commands (if selected)

**Source:** `commands/agent-os/`
**Target:** `{project}/.claude/commands/agent-os/`

For each `.md` file in source:
1. Create target directory if needed: `mkdir -p {project}/.claude/commands/agent-os`
2. Copy file
3. Track: Added or Updated

**Note:** Commands go to `.claude/` (hidden), not `commands/` (visible).

#### 7.3: Sync CLAUDE.md Sections (if selected)

If user selected CLAUDE.md syncing in Step 4:

**Source:** `CLAUDE.md` (source project)
**Target:** `{project}/CLAUDE.md`

**Logic:**

1. **Read source CLAUDE.md** and parse selected sections
2. **Read target CLAUDE.md** (if exists)
3. **For each selected section:**
   - Check if section exists in target
   - If exists: Ask whether to replace, merge, or skip
   - If not exists: Append to target
4. **Write updated target CLAUDE.md**

**Section handling strategies:**

Ask via AskUserQuestion for each section:
```
Section "## [Section Name]" exists in both source and target.

How should this be handled?
1. Replace — Overwrite target with source version
2. Merge — Append source content to target section
3. Skip — Keep target version unchanged
```

**Example:**
```markdown
Source CLAUDE.md has:
## Standards Management
- Use /inject-standards to load standards
- Run /index-standards after adding new standards

Target CLAUDE.md has:
## Standards Management
- Project-specific note about testing standards

Result (if "Merge" selected):
## Standards Management
- Project-specific note about testing standards
- Use /inject-standards to load standards
- Run /index-standards after adding new standards
```

**Track:** `claude_md_sections_synced`: Count of sections synced

#### 7.4: Track Changes

Keep counts for reporting:
- `standards_added`: Count of new standard files
- `standards_updated`: Count of modified standard files
- `commands_added`: Count of new command files
- `commands_updated`: Count of modified command files
- `claude_md_sections_synced`: Count of CLAUDE.md sections synced (if applicable)

### Step 8: Update Target Index (Forked from project-install.sh create_index)

For each project where standards were synced, rebuild `index.yml` preserving existing descriptions:

**Logic from project-install.sh:**

1. **Read existing index** from `{project}/agent-os/standards/index.yml`
2. **Parse existing descriptions** for each folder/file combination
3. **Scan all .md files** in `{project}/agent-os/standards/`
4. **Generate new index.yml:**
   - For root-level .md files: add under `root:` section
   - For files in subfolders: add under `{folder}:` section
   - **If description exists in old index:** preserve it
   - **If new file (no description):** use `"Needs description - run /index-standards"`
5. **Write new index.yml**

**Example index.yml output:**

```yaml
# Agent OS Standards Index

root:
  agent-verification:
    description: How agents should verify code using Astral skills instead of justfile recipes
  authoring-conventions:
    description: Needs description - run /index-standards

services:
  frozen-dataclass-services:
    description: Immutable services using @dataclass(frozen=True)
  protocol-first-design:
    description: Define interfaces as @runtime_checkable Protocols

testing:
  fakes-over-mocks:
    description: Use simple dataclass fakes, not mock frameworks
```

**Report for this step:**

```
Updating index in /Users/pauleveritt/projects/pauleveritt/tdom-django...
✅ Updated index.yml (8 entries total, 1 new)
```

### Step 9: Report Results

Show summary for all synced projects:

```
✅ Sync complete!

Source project (agent-os):
✅ Committed changes

Synced to 2 projects:

1. /Users/pauleveritt/projects/pauleveritt/tdom-django
   Standards:
     - Added: 1 file (authoring-conventions.md)
     - Updated: 1 file (index.yml)
     - Unchanged: 7 files
   Commands:
     - Added: 2 files (author-artifact.md, sync-agent-os.md)
     - Updated: 1 file (inject-standards.md)
     - Unchanged: 4 files
   CLAUDE.md:
     - Synced: 3 sections (Standards Management, Commands, Verification)

2. /Users/pauleveritt/projects/t-strings/svcs-di
   Standards:
     - Added: 1 file
     - Updated: 1 file
     - Unchanged: 7 files
   Commands:
     - Added: 2 files
     - Updated: 1 file
     - Unchanged: 4 files
   CLAUDE.md:
     - Synced: 3 sections

Next steps:
- Review changes in each target project
- Run tests in target projects to verify compatibility
- Commit changes in target projects when ready
- New standards need descriptions: run /index-standards in each project
```

## Implementation Notes (from project-install.sh)

### Target Structure Detection

All target projects use **Agent OS v2 structure:**
- Standards: `agent-os/standards/`
- Commands: `.claude/commands/agent-os/`
- Index: `agent-os/standards/index.yml`

(There is no v3 structure in practice yet.)

### File Comparison

Compare files by content, not timestamp:
- Read both files
- Compare line-by-line or hash
- If identical: mark "Unchanged"
- If different: mark "Updated"
- If only in source: mark "Added"

### Index Description Preservation

When updating index.yml, parse the existing file to extract descriptions:

```bash
# Pseudo-code from project-install.sh lines 300-327
get_existing_description(folder, filename):
    if old_index exists:
        parse YAML to find: folder: → filename: → description:
        if description exists and not "Needs description":
            return description
    return null
```

### Path Decoding

`~/.claude/projects/` uses encoded directory names:

```
-Users-pauleveritt-projects-pauleveritt-tdom-django
→ /Users/pauleveritt/projects/pauleveritt/tdom-django
```

**Simple approach:** Replace `-` with `/` after the first one, but be careful with project names containing `-`.

**Better approach:** Try common patterns:
- `/Users/pauleveritt/projects/pauleveritt/{name}`
- `/Users/pauleveritt/projects/t-strings/{name}`
- Check if path exists before using

### Safety Checks

- Never auto-commit in target projects (user reviews first)
- Don't sync if source has uncommitted changes (unless user approves)
- Create backups of index.yml before rewriting? (Optional)
- Preserve file permissions when copying

### Legacy Cleanup

The sync command automatically removes legacy Agent OS artifacts from the cline-fork era:
- `agent-os/skills/` directories (Agent OS no longer manages skills)
- References to `@agent-os/skills/` in standards files

Skills are now managed by Claude Code natively in `~/.claude/skills/` (global) or `.claude/skills/` (per-project).

## Related Scripts

- `scripts/project-install.sh` — Fresh install (this command syncs updates)
- `scripts/common-functions.sh` — Shared functions for both
