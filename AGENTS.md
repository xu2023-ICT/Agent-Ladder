# Agent Instructions

## GitHub Push

For this repository, do not use GitHub SSH on port 22. The local network closes that connection.

Use GitHub SSH over port 443 with the dedicated GitHub key:

```bash
git config url.ssh://git@ssh.github.com:443/.insteadOf git@github.com:
git config core.sshCommand 'ssh -i ~/.ssh/id_ed25519_github -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new'
git branch --set-upstream-to=origin/main main
```

After the config is present, normal commands should work:

```bash
git push
git pull
git fetch
```

If a one-off push command is needed, use:

```bash
GIT_SSH_COMMAND='ssh -i ~/.ssh/id_ed25519_github -p 443 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new' \
  git push -u ssh://git@ssh.github.com/xu2023-ICT/Agent-Ladder.git main
```
