Stage only some hunks of a file, without `git add -p` (for agents and shells with no interactive input).

## Usage

    grab exec git-hunks list  <file>          # number each hunk of the unstaged diff
    grab exec git-hunks stage <file> 0,2      # stage hunks 0 and 2 (git apply --cached)
    grab exec git-hunks show  <file> 0,2      # print the patch that `stage` would apply

Hunks are numbered from 0 in the order of `git diff -U3 -- <file>`. Renumber
after each `stage`: the remaining diff has changed.
