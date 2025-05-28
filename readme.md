# An Agent that Resolves Merge Conflicts Automatically

**Warning!** This agent executes bash commands on your local shell. Its reccomended to run this inside of a vm or docker container, in order to prevent accidental data loss. 

## Quickstart 

### Prequisites 

nix should be installed to run the agent script

```
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
```

## Running the Agent

you should be in the state where you have attempted to rebase and git is telling you that there are conflicts 
```

[robertwendt@nixos:~/repo]$ git status
On branch foo
Your branch is up to date with 'origin/foo'.

nothing to commit, working tree clean

[robertwendt@nixos:~/repo]$ git rebase origin/main 
Auto-merging src/Homepage/Homepage.jsx
CONFLICT (content): Merge conflict in src/Homepage/Homepage.jsx
error: could not apply d62f39d4... add foo
hint: Resolve all conflicts manually, mark them as resolved with
hint: "git add/rm <conflicted_files>", then run "git rebase --continue".
hint: You can instead skip this commit: run "git rebase --skip".
hint: To abort and get back to the state before "git rebase", run "git rebase --abort".
hint: Disable this message with "git config advice.mergeConflict false"
Could not apply d62f39d4... add foo

[robertwendt@nixos:~/repo]$ # now you would run nix run github:r33drichards/merge-conflict
```

then set your anthropic key and run the agent with `nix run`


```
export ANTHROPIC_API_KEY=
nix run github:r33drichards/merge-conflict
```

## local testing


clone the repo

```
git clone git@github.com:/r33drichards/merge-conflict
```

to intentionally create a merge conflict, commit a file with the following contents: foo: foo. Commit. Branch off this commit and change one of the foo's to bar, foo: bar And branch of to another from your first branch and change the same line to foo: baz.

Now merge one back into your starting branch and then the other.



```sh
#! /bin/bash
# delete all existing branches if they exist 
git branch -D test-root
git branch -D test-branch
git branch -D test-branch2


# create the root commit
git switch -c test-root
echo "foo" > foo
git add foo
git commit -m "foo"

git switch -c test-branch
echo "bar" > foo
git add foo
git commit -m "bar"

# create test-branch2 from test-root
git checkout test-root
git switch -c test-branch2
echo "baz" > foo
git add foo
git commit -m "baz"

git switch test-root
git merge test-branch
git merge test-branch2
```

run the agent to solve the merge conflict for you
```
ANTHROPIC_API_KEY='' nix run .
```
