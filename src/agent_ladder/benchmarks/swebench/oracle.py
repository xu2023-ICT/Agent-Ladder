"""Builds an Oracle-mode SWE-bench prompt: gold-patch-touched files + issue text.

Oracle mode means literally handing the model the files the reference patch
touches and asking for a diff in one shot -- no exploration, no tools. This
is the original SWE-bench paper's (2023) baseline methodology.

The prompt template (PATCH_EXAMPLE / _make_code_text / _prompt) is copied
from swebench.inference.make_datasets.create_instance's "style-2" prompt
verbatim, not imported, because that module's import chain pulls in
`transformers` just for an unrelated tokenizer helper we don't use.
"""

import unidiff

from agent_ladder.benchmarks.swebench.repo import checkout

PATCH_EXAMPLE = """--- a/file.py
+++ b/file.py
@@ -1,27 +1,35 @@
 def euclidean(a, b):
-    while b:
-        a, b = b, a % b
-    return a
+    if b == 0:
+        return a
+    return euclidean(b, a % b)"""


def _get_oracle_filenames(patch: str) -> set[str]:
    return {
        patch_file.source_file.split("a/", 1)[-1]
        for patch_file in unidiff.PatchSet(patch)
    }


def _readme_files(repo_dir):
    return [
        p.name
        for p in repo_dir.iterdir()
        if p.is_file() and p.name.lower().startswith("readme")
    ]


def _read_files(repo_dir, relative_paths):
    return {path: (repo_dir / path).read_text() for path in relative_paths}


def _make_code_text(files_dict: dict[str, str]) -> str:
    all_text = ""
    for filename, contents in sorted(files_dict.items()):
        all_text += f"[start of {filename}]\n"
        all_text += "\n".join(f"{i} {line}" for i, line in enumerate(contents.split("\n"), start=1))
        all_text += f"\n[end of {filename}]\n"
    return all_text.strip("\n")


def build_prompt(instance: dict) -> str:
    repo_dir = checkout(instance["repo"], instance["base_commit"])
    file_contents = _read_files(repo_dir, _get_oracle_filenames(instance["patch"]))
    readmes = _read_files(repo_dir, _readme_files(repo_dir))

    return "\n".join(
        [
            "You will be provided with a partial code base and an issue statement explaining a problem to resolve.",
            "<issue>",
            instance["problem_statement"],
            "</issue>",
            "<code>",
            _make_code_text(readmes),
            _make_code_text(file_contents),
            "</code>",
            "I need you to solve this issue by generating a single patch file that I can apply "
            "directly to this repository using git apply. Please respond with a single patch "
            "file in the following format.",
            "<patch>",
            PATCH_EXAMPLE,
            "</patch>",
        ]
    )
