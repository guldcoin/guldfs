# guldFS Test Plan

### Installation

SSH key gen/import
PGP key gen/import
.gitconfig generate
.gitignore generate
.dotfiles generate and link

### Working Files

##### plaintext

Create
  Wrote to /blocktree
  dirty in git
Write
  Wrote to /blocktree
  dirty in git
Read
  Pulls from gitolite first
  refuses to read .git
Fsync
  add file

##### GPG

Create
  Wrote to /blocktree
  gpg encrypted first then
  gpg dirty in git
  source ignored in git
Write
  Wrote to /blocktree
  gpg encrypted first then
  gpg dirty in git
  source ignored in git
Read
  Pulls from gitolite first
  refuses to read .git
  decrypts at read time, if no plaintext version available
  decrypts before read
Fsync
  add gpg file

##### AES

Create
  Wrote to /blocktree
  generate password and store in pass then
  aes encrypt then
  aes dirty in git
  source ignored in git
Write
  Wrote to /blocktree
  generate password and store in pass then
  aes encrypt then
  aes dirty in git
  source ignored in git
Read
  Pulls from gitolite first
  refuses to read .git
  decrypts at read time, if no plaintext version available
  decrypts before read
Fsync
  add aes file


### dirs

List
  ignores .git
  includes dirty files
  includes .gitignored files
  strips hook-suffixes from .gitignore special files
Fsyncdir
  add files
  commit w message
  push to gitolite (+ mirrors?)
