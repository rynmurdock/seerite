import os
import subprocess
import logging
import tempfile

import tqdm
import click
import pandas as pd
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def run_git_command(args):
    return subprocess.check_output(["git"] + args, text=True, 
                    env={**os.environ, 'LC_ALL': 'en_US.UTF-8', 'LANG': 'en_US.UTF-8'},
    )

def get_commit_list(branch):
    return run_git_command(["rev-list", "--reverse"] + [f'{branch}']).splitlines()

def get_commit_metadata(commit_hash, branch):
    author = run_git_command(["show", "-s", "--format=%an", commit_hash, f'{branch}'])
    date = run_git_command(["show", "-s", "--format=%ad", commit_hash, f'{branch}'])
    return author, date

def get_diff_stats(prev_commit, current_commit):
    stats_output = run_git_command(["diff", "--numstat",
                                    f"{prev_commit}..{current_commit}",])
    files = []
    for line in stats_output.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            additions, deletions, filename = parts
            files.append((filename, additions, deletions))
    return files

def get_diff_from_contents(first_contents, second_contents):
    '''
    this function, unlike get_file_diff, operates on two texts instead of 2 commits and a filename
    '''

    with tempfile.TemporaryDirectory() as tempdir:
        first_temp_file = os.path.join(tempdir, "first_rebuild_target.temp")
        second_temp_file = os.path.join(tempdir, "second_rebuild_target.temp")

        with open(first_temp_file, "w", encoding="utf-8") as f:
            f.write(first_contents)

        with open(second_temp_file, "w", encoding="utf-8") as f:
            f.write(second_contents)

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
    if subrun.stderr: logging.error(subrun.stderr)
    patch_contents = subrun.stdout

    return patch_contents

def get_file_diff(prev_commit, current_commit, filename, branch):
    try:
        patch_contents = run_git_command(["diff", f"{prev_commit}..{current_commit}", '-U0', 
                                '--no-prefix', '--ws-error-highlight=all', '--diff-algorithm=patience',
                                "--", filename, 
                                '--', 
                                '--', f'{branch}'
                                ])
        return patch_contents
    
    except Exception as e:
        logging.warning(e)
        return ""  # In case the file was deleted/renamed and no diff is available



@click.command()
@click.option('--branch', required=True, help='The name of your branch. Hint: You can use `git status` to find the current branch.')
@click.option('--output_path', default="./git_diffs_by_file.parquet", help='The path of your output dataframe parquet file.')
@click.option('--suffix_of_interest', default=None, help='The suffix of filepaths that you would like to collect diffs for; all others non-matching paths will be excluded.')
def main(branch, output_path, suffix_of_interest):
    commits = ['4b825dc642cb6eb9a060e54bf8d69288fbee4904'] + get_commit_list(branch)
    logging.info(f'Commits: {commits}')

    full_files_diffs = {}
    # loop through our commits
    for i in tqdm.tqdm(range(1, len(commits))):
        prev_commit = commits[i - 1]
        current_commit = commits[i]

        # we don't utilize lots of available metadata for now
        # author, date = get_commit_metadata(current_commit, branch)

        # this may under-report diffs
        diff_stats = get_diff_stats(prev_commit, current_commit)

        # go through each file change in this diff
        for file, adds, dels in diff_stats:
            # skip files that don't have a suffix if given; 
            #     e.g. if we just wanted changes to latex source files.
            if suffix_of_interest and not file.endswith(suffix_of_interest):
                logging.info(f"skipping {file} as it doesn't end with {suffix_of_interest}")
                continue
            file_diff = get_file_diff(prev_commit, current_commit, file, branch).encode('utf-8')
            
            # Add this diff to the file's set or start the list if it already exists.
            if full_files_diffs.get(file):
                full_files_diffs[file] = full_files_diffs[file] + [file_diff]
            else:
                full_files_diffs[file] = [file_diff]

    # our files are rows; our diff number is the column.
    df = pd.DataFrame.from_dict(full_files_diffs, orient='index')

    # df = df[df[0].astype(bool)] # could drop rows with "false"y first columns (set of diffs that're probs empty)
    # df = df[df[0].str.len().astype(bool)] # could drop rows with 0-len first columns; we have some odd cases that above line seems to miss.

    df.to_parquet(output_path,)
    logging.info(f'DataFrame{df}')
    logging.info(f"Per-file diffs generated: {output_path}")


