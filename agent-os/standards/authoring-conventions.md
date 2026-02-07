# Authoring Conventions

Rules for writing Agent OS standards and commands.

## Why

Consistent structure makes artifacts discoverable, maintainable, and effective.

## Standards Format

- No YAML frontmatter
- 15-40 lines maximum
- Structure: # Title, code example, ## Why, ## Rules
- One concept per standard
- Must have `index.yml` entry with description

## Commands Format

- Structured sections: # Title, ## Important Guidelines, ### Step N
- Always use AskUserQuestion for interaction
- Follow step-by-step workflow patterns
- Include clear detection logic and error handling

## Overlap Rules

- Check existing standards before creating new ones
- Prefer extending existing standards over creating new ones
- Standards are the source of truth for coding conventions
- Commands coordinate workflows and integrate standards
