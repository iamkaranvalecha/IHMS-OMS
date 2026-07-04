# Project #5 workflow

**Board:** [IHMS-OMS Project #5](https://github.com/users/iamkaranvalecha/projects/5/views/1) (public)

Single source of truth for what to work on. Mirrors KB-IHMS Project #4 automation pattern.

## Required agent workflow

1. **Create issue first** — use [Integration task template](../.github/ISSUE_TEMPLATE/integration-task.yml)
2. **Note issue number** — branch MUST be `cursor/{issue-number}-description-bf51`
3. **Link to Project #5** — automatic when `PROJECT_PAT` is configured (see below)
4. **Open PR** — body MUST include `Closes #N`
5. **verify.sh** — paste summary in PR

## Automation

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ensure-labels.yml` | push to `main` (labels.json) | Sync repo labels from `.github/labels.json` |
| `project-sync.yml` | issue opened/labeled, PR opened/merged | Add items to Project #5; set Status/Priority/Size |

### PROJECT_PAT secret (required for board sync)

User-owned Project #5 requires a **classic PAT** stored as repo secret `PROJECT_PAT`:

- Scopes: `project`, `read:project`, `repo`, `read:org`
- Fine-grained PATs cannot access user-owned projects

Until configured, `project-sync.yml` skips gracefully (CI stays green).

### Status columns

`Backlog` → `Ready` → `In progress` → `In review` → `Done`

PR opened → **In review**. PR merged → **Done** (issue + PR).

### Branch → issue linking

Project sync parses `cursor/{issue-number}-*` from branch name to link PR to issue fields.

## Manual fallback

If automation is not yet configured:

```bash
gh project item-add 5 --owner iamkaranvalecha --url https://github.com/iamkaranvalecha/IHMS-OMS/issues/N
gh project item-add 5 --owner iamkaranvalecha --url https://github.com/iamkaranvalecha/IHMS-OMS/pull/N
```

## Current issues (retroactive)

| Issue | Phase | PR |
|-------|-------|-----|
| [#3](https://github.com/iamkaranvalecha/IHMS-OMS/issues/3) | Phase 1 scaffold | #1 (merged) |
| [#4](https://github.com/iamkaranvalecha/IHMS-OMS/issues/4) | Phase 2 gateway | #2 |
