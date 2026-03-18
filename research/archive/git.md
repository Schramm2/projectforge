We will be using Github-Flow for version control, instead Gitflow and TBD. Read up about it here: [https://docs.github.com/en/get-started/using-github/github-flow](https://docs.github.com/en/get-started/using-github/github-flow)

We may switch to TBD with Posthog once a product is in production.

I know it can seem intimidating to learn. And version control can remain confusing even after using it for a while. So to summarise the link above, here is the TLDR:

## Github-Flow (Not in current state of workflow)

We would only use such strict and managed version control when we have a functioning live deployed product with consistent users to make sure that the live deployed site isn't touched until it is 100% working and passed all tests.

Overall Flow:

Use short-lived feature branches to develop and test locally. Merge back into the dev branch frequently.

Here are the commands to handle that full lifecycle. Replace with your desired branch name.

* **Structure:**

  * `main`: Always deployable.

  * `dev`: Development/Testing Branch

  * `feature-branch`: Created from dev, merged back to dev

* **Workflow:** Branch -> Commit -> Pull Request -> Review -> Merge -> Deploy.

* **Pros:** Very fast, simple, minimizes merge conflicts.

* **Cons:** Hard to manage "release candidates" or older versions.

##### Branch Protection Rules (Crucial)

You must prevent chaos by enforcing rules on the `main` branch.

* **Require Pull Request Reviews:** No one can push directly to `main`. At least 1 other person must approve the code.

* **Require Status Checks to Pass:** Code cannot be merged unless automated tests (CI) pass.

* **Require Linear History (Optional):** Prevents messy merge commits, keeping the history clean.

##### Naming Conventions (Semantic)

To keep things easy for "many people," use standard naming:

* **Branches:** `type/description`

  * `feat/user-login`

  * `fix/header-alignment`

  * `docs/update-readme`

* **Commits (Conventional Commits):**

  * `feat: add new login button`

  * `fix: resolve crash on startup`

##### The Pull Request (PR) Template

Don't just open a blank PR. Standardize the description so reviewers know what to look for.

* **Summary:** What does this change?

* **Type of Change:** (Bug fix, New feature, Breaking change?)

* **Testing:** How was this tested?

* **Screenshots:** (If UI related).

### 1. Create and switch to the new feature branch

```
# Ensure you have the latest dev branch
git switch dev && git pull

# Create and switch to the new branch
git switch -c <branch-name>

# Push the new branch to the remote (publish it)
git push -u origin <branch-name>
```

### 2. Merge back into the target branch (dev)

```
# Switch to the target branch
git switch dev

# Ensure the target branch is up to date
git pull origin dev

# Merge your feature branch in
git merge <branch-name>

# Push the updated target branch to the remote
git push origin dev
```

### 3. Delete the feature branch after merging

```
# Delete the local branch
git branch -d <branch-name>

# Delete the remote branch
git push origin --delete <branch-name>
```

When you merge a branch, the commits from that branch become part of the history of the branch you merged _into_ (in this case, `dev`). Deleting the branch name is just deleting a "label"; the actual commit objects usually remain safe in the history.

## Advanced: Parallel Development with Git Worktrees

Switching branches constantly can be disruptive, especially if you have to wait for a Pull Request review on one feature while starting another. **Git Worktrees** allow you to check out a new branch in a separate folder so you can work on `feat/user-login` and `fix/header-alignment` at the same time.

### 1. Create a Worktree for a New Feature

Instead of switching your current folder away from your work, create a "side-folder" based on the `dev` branch.

Bash

```
# Syntax: git worktree add <path-to-new-folder> -b <new-branch-name> <base-branch>

# Example: Create a folder named "feat-search" containing a new branch "feat/search" based on "dev"
git worktree add ../feat-search -b feat/search dev
```

### 2. Work in the New Environment

Open the new folder in a separate VS Code window.

Bash

```
code ../feat-search
```

> **Python Venv Note:** Because a worktree is a fresh directory, it will not contain your `.venv` folder (since that is usually ignored by Git). You will likely need to create a new venv or point your VS Code interpreter to your existing one.

### 3. Push and PR

Work normally inside this new window. The Git history is shared, so your commits are safe.

Bash

```
git add .
git commit -m "feat: add search bar logic"
git push -u origin feat/search
```

_Follow the standard PR template described above when opening your Pull Request._

### 4. Cleanup

Once your PR is merged into `dev` and the feature is complete:

1. Close the VS Code window for that folder.

2. Run the removal command from your **main** terminal:

Bash

```
# Deletes the folder and unlinks the worktree
git worktree remove ../feat-search
```
