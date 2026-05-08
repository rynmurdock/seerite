import os
import subprocess
import logging
import uuid
import shutil

import tqdm
import click
import pandas as pd


def is_new_blank_file(diff_text: str) -> bool:
    """
    Determines if the given git diff only creates a new blank file.
    
    Args:
        diff_text (str): The text of a git diff.
    
    Returns:
        bool: True if the diff only creates a new blank file, False otherwise.
    """
    lines = diff_text.strip().splitlines()
    
    # Check for standard new file indicators
    if not any(line.startswith("new file mode") for line in lines):
        return False
    
    # Make sure the diff doesn't contain any content additions (besides metadata)
    content_lines = [line for line in lines if line.startswith('+') and not line.startswith('+++')]
    
    # A blank file should have no added lines of content
    return len(content_lines) == 0

def read_diffs_from_parquet(csv_path, ):
    diffs = pd.read_parquet(csv_path, ).to_dict()
    return diffs

def rebuild_file_from_diffs(file, diffs, initial_text=""):
    # we avoid the tempfile lib here (& not elsewhere) as this file is 
    #     apt to handle many diffs & it can break if someone were to use parallelism

    # TODO infer a temp directory instead of making it locally
    os.makedirs("./temp/", exist_ok=True)
    some_succeeded = None

    outcome = False
    tempdir = f"./temp/{uuid.uuid4()}"
    os.makedirs(tempdir, exist_ok=True)
    try:
        if initial_text:
            with open(f'{tempdir}/{file}', 'w', encoding='utf-8') as init_file:
                init_file.write(initial_text)

        for i, entry in tqdm.tqdm(enumerate(diffs), disable=True):
            entry = entry.decode('utf-8') if not isinstance(entry, str) else entry
            if not 'new file mode' in entry:
                to_make = [file]
                if '--git' in entry:
                    to_make += entry.split('--git')[1].split(' ')[:2]
                for word in to_make:
                    path = os.path.join(tempdir, word.replace('a/', '').replace('b/', ''))
                    with open(path, 'a') as file:
                        pass
                    assert os.path.exists(path), f'{path} does not exist!'

            # create a new temp_dir for the patch file; we don't want to clog the "repo"
            patch_file_tempdir = f"./temp/{uuid.uuid4()}"
            os.makedirs(patch_file_tempdir, exist_ok=True)
            try:
                assert os.path.exists(patch_file_tempdir)
                patch_file = os.path.join(patch_file_tempdir, f"patch_{i}.diff")
                with open(patch_file, "w", encoding='utf-8') as file:
                    # Write the string to the file
                    file.write(entry)
                
                if not os.path.exists(patch_file) or not os.path.getsize(patch_file):
                    logging.warning('We have an empty or non-existent diff patch file made in rebuild_file_from_diffs!')
                    continue
                try:
                    subprocess.run(
                        [f"git", "apply", "--unsafe-paths", "--no-index", '--unidiff-zero', '-p0',
                        os.path.abspath(patch_file)],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=os.path.abspath(tempdir),
                        text=True,
                        env={**os.environ, 'LC_ALL': 'en_US.UTF-8', 'LANG': 'en_US.UTF-8',
                             'GIT_DIR': os.path.abspath(tempdir), 
                             'GIT_WORK_TREE': os.path.abspath(tempdir)},
                    )
                    some_succeeded = True
                except subprocess.CalledProcessError as e:
                    # TODO add back
                    logging.error(e.stderr)
                    logging.error(e.stdout)
                    logging.error(f"Failed to apply patch {i + 1}.")
            finally:
                shutil.rmtree(patch_file_tempdir, ignore_errors=True)
        if not some_succeeded:
            logging.error(f'No patches succeeded.')
            return False
        # Copy final result to output
        in_folder = [os.path.join(tempdir, j) for j in os.listdir(tempdir)]
        if len(in_folder) == 0:
            logging.warning(f'{tempdir} is blank. {in_folder}')
            return False

        # TODO doesn't need to be a list when we target a single file.
        result_f = reversed([f for f in in_folder if f == file])
        for file in result_f:
            with open(file) as f:
                outcome = f.read()
            if isinstance(outcome, str):
                break
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)
    return outcome



@click.command()
@click.option('--input_path', required=True, help='The name of your diffs file.')
def main(input_path):
    diffs = read_diffs_from_parquet(input_path,)
    if not diffs:
        logging.error(f"No diffs found in {input_path}!")
    else:
        success = rebuild_file_from_diffs(diffs,)
        if success:
            logging.info("File reconstruction complete.")


