# an agent that resolves merge conflicts automatically

## Quickstart 
### Prequisites 

nix should be installed to run the agent script

```
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
```

then set your anthropic key and run the agent with `nix run`


```
export ANTHROPIC_API_KEY=
nix run github:r33drichards/merge-conflict#agent
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
ANTHROPIC_API_KEY='' nix run .#agent
```
