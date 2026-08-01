# Release Prompt

Use this prompt when preparing a release for `mvideo`.

## Prompt

```md
Prepare a release for `mvideo`.

Release target: `v<version>`
Release date: `<YYYY-MM-DD>`
GitHub username for changelog attribution: `@<username>`

Do the following in order:

1. Update `CHANGELOG.md`:
   - keep the `## [Unreleased]` section at the top
   - add or update the `## [<version>] - <YYYY-MM-DD>` section
   - ensure each bullet ends with `(@<username>)`
   - keep the entries concise and release-focused

2. Update `pyproject.toml`:
   - set `[project].version` to `<version>`

3. Update `uv.lock` so it reflects the current project version and dependency state:
   - run `uv lock`

4. Verify the release locally:
   - run `uv sync`
   - run `uv run --with pytest python -m pytest`

5. Commit the release changes with a release-style commit message.

6. Create a git tag named `v<version>`.

7. Report:
   - the version prepared
   - the commit hash
   - the tag name
   - any verification results

Do not push the commit or tag. The user will handle pushing separately.
```
