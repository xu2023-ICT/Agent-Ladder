"""Local checkout cache for SWE-bench's frozen repo mirrors.

Shared across steps: step 0 reads file contents out of a checkout to build
oracle prompts; later steps give an agent a real working directory to run
bash/edit/tests in. Clones are cached on disk so repeated runs against the
same repo don't re-clone.
"""

from pathlib import Path

from git import Repo

CACHE_DIR = Path(__file__).resolve().parents[4] / ".cache" / "swebench-repos"


def checkout(repo: str, base_commit: str) -> Path:
    """Ensure `repo` (e.g. "django/django") is cloned and checked out at base_commit.

    Returns the local repo path.
    """
    repo_dir = CACHE_DIR / repo.replace("/", "__")
    if not repo_dir.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        mirror_url = f"https://github.com/swe-bench-repos/{repo.replace('/', '__')}.git"
        Repo.clone_from(mirror_url, repo_dir)

    git_repo = Repo(repo_dir)
    git_repo.git.reset("--hard", base_commit)
    git_repo.git.clean("-fdx")
    return repo_dir
