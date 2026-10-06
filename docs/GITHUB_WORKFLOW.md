# GitHub workflow

Use **one repository**, with feature branches and pull requests. Do not create a new repository for
each feature. The provided Git bundle preserves the real implementation commits, in their original
order; commits identify the AI development assistant rather than impersonating the candidate.

## Restore the repository with its history

Extract the delivery ZIP, then from its parent folder:

```bash
git clone enterprise-ai-assistant/repository.bundle enterprise-ai-assistant-work
cd enterprise-ai-assistant-work
git remote remove origin
git log --oneline
```

The ZIP also contains the source files directly for inspection. Clone the bundle to retain history;
starting with `git init` on the extracted source would discard that history.

## Create a public repository and push

With GitHub CLI installed, authenticate using its browser flow:

```bash
gh auth login
gh repo create enterprise-ai-assistant --public --source=. --remote=origin --push
```

Or create an **empty** public repository in GitHub, without an initial README, then:

```bash
git remote add origin https://github.com/YOUR_USERNAME/enterprise-ai-assistant.git
git push -u origin main
```

Do not paste GitHub tokens or provider credentials into chat, source files or commit messages.
The `.env` file is ignored. The assessment PDF itself is not included in the public source package.

## Further changes

```bash
git switch -c feature/live-provider-verification
# Make and test the changes.
git add app tests docs
git commit -m "test: verify live provider integration"
git push -u origin feature/live-provider-verification
gh pr create --base main --title "Verify live provider integration" --body "Adds provider verification and records results."
```

Review CI, merge the PR on GitHub, then pull main locally. Configure your own `git user.name` and
`git user.email` for commits you author. Enable branch protection and required CI for main.
