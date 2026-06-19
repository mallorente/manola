# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues in `mallorente/manola`. Use the `gh` CLI for issue operations.

## Conventions

- Create an issue: `gh issue create --repo mallorente/manola --title "..." --body-file <file> --label ready-for-agent`.
- Read an issue: `gh issue view <number> --repo mallorente/manola --comments`.
- List issues: `gh issue list --repo mallorente/manola --state open --json number,title,labels`.
- Comment on an issue: `gh issue comment <number> --repo mallorente/manola --body "..."`.
- Apply or remove labels: `gh issue edit <number> --repo mallorente/manola --add-label "..."` or `--remove-label "..."`.
- Close an issue: `gh issue close <number> --repo mallorente/manola --comment "..."`.

## Publishing

When a skill says "publish to the issue tracker", create a GitHub issue in `mallorente/manola`.

When a skill says "fetch the relevant ticket", read the GitHub issue with `gh issue view`.
