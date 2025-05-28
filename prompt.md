
```
$ git status
On branch test-root
You have unmerged paths.
  (fix conflicts and run "git commit")
  (use "git merge --abort" to abort the merge)

Unmerged paths:
  (use "git add <file>..." to mark resolution)
        both modified:   foo

Changes not staged for commit:
  (use "git add <file>...

no changes added to commit (use "git add" and/or "git commit -a")
➜  merge-conflict git:(test-root) ✗      
```

to view the diff of the un merged path, run:

to view the diff of the un merged path, run:

```sh
$ git diff | cat
diff --cc foo
index 5716ca5,7601807..0000000
--- a/foo
+++ b/foo
@@@ -1,1 -1,1 +1,5 @@@
++<<<<<<< HEAD
 +bar
++=======
+ baz
++>>>>>>> test-branch2
... other changes 
```

You will now create a .patch file and update the contents of foo using this patch to solve the merge conflict, and then delete your patch file to tidy up


I want you to do this but for the current directory. use your shell tool to create files, see the status of a git repo, and run commands until you have solved the merge conflict please :) 


