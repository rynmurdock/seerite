import os
import logging
import tempfile
import subprocess

from seegit import git_trace, git_rebuild


def test_temp_dir_use():
    with tempfile.TemporaryDirectory() as tempdir:
        first_temp_file = os.path.join(tempdir, "first_rebuild_target.tex")
        with open(first_temp_file, "w", encoding="utf-8") as f:
            f.write("whatever!")

        with tempfile.TemporaryDirectory() as scnd_tempdir:
            second_temp_file = os.path.join(scnd_tempdir, "second_rebuild_target.tex")
            with open(second_temp_file, "w", encoding="utf-8") as f:
                f.write("and ever, amen")

            subrun = subprocess.run(
                [
                    "git", "diff", "--no-index",
                    "-U0",
                    "--no-prefix",
                    "--ws-error-highlight=all",
                    "--diff-algorithm=patience",
                    first_temp_file,
                    second_temp_file,
                ],
                env={**os.environ, 'LC_ALL': 'en_US.UTF-8', 'LANG': 'en_US.UTF-8'},
                cwd=tempdir,
                text=True,
                capture_output=True,
            )
            logging.info(subrun.stdout)
            logging.info(subrun.stderr)
            assert not subrun.stderr, subrun.stderr



def test_diff_reconstruction():
    test_parquet_path = '__test_git_diffs_by_file.parquet'
    with open('draft_test.tex', 'r') as f:
        current_draft_test = f.read()

    branch = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    ).decode("utf-8").strip()


    git_trace.BRANCH = branch
    git_trace.main(branch, test_parquet_path, None)
    diffs = git_rebuild.read_diffs_from_parquet(test_parquet_path)
    diffs = [list(v.values())[0] for v in diffs.values()]

    logging.info(diffs)
    outcome = git_rebuild.rebuild_file_from_diffs(branch, diffs)
    logging.info(outcome)

    assert current_draft_test == outcome, f'We failed to reconstruct 1:1. current_draft_test={current_draft_test} reconstruction={outcome}'

    logging.info('Successful reconstruction!')
    logging.info(outcome)

if __name__ == "__main__":
    test_diff_reconstruction()
    test_temp_dir_use()
