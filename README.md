# Agent-Ladder

## GitHub Push Notes

If `git push -u origin main` fails with:

```text
Connection closed by ... port 22
fatal: Could not read from remote repository.
```

the local network is likely blocking GitHub SSH on port 22. Use GitHub's SSH-over-443 endpoint and explicitly select the GitHub SSH key.

This repository is configured with:

```bash
git config url.ssh://git@ssh.github.com:443/.insteadOf git@github.com:
git config core.sshCommand 'ssh -i ~/.ssh/id_ed25519_github -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new'
git branch --set-upstream-to=origin/main main
```

After that, normal commands should work:

```bash
git push
git pull
git fetch
```

The successful one-off push command was:

```bash
GIT_SSH_COMMAND='ssh -i ~/.ssh/id_ed25519_github -p 443 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new' \
  git push -u ssh://git@ssh.github.com/xu2023-ICT/Agent-Ladder.git main
```
