import os
import subprocess
import logging
import uuid
import shutil

import tqdm
import sys
import curses
import click
import pandas as pd
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


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

def rebuild_file_from_diffs(file: str, 
                            diffs: list, 
                            until: int=None,
                            initial_text: str=""):
    '''
    file: the file of interest to rebuild
    diffs: the patches/diffs to rebuild the file from
    until: the 0-based index to rebuild the file until
    initial text: a text to start from (could be used for getting a single blank diff or modelings)

    returns the contents (str) of the file to rebuild
    '''
    
    # we avoid the tempfile lib here (but not elsewhere) as this file is 
    #     apt to handle many diffs & it can break if someone were to use parallelism
    diffs = diffs[:until+1]

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

            # create a new temp_dir for the patch file; we don't want to clog the "repo"
            patch_file_tempdir = f"./temp/{uuid.uuid4()}"
            os.makedirs(patch_file_tempdir, exist_ok=True)
            try:
                assert os.path.exists(patch_file_tempdir)
                patch_file = os.path.join(patch_file_tempdir, f"patch_{i}.diff")
                with open(patch_file, "w", encoding='utf-8') as ff:
                    # Write the string to the file
                    ff.write(entry)
                
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
        result_f = os.path.join(tempdir, file)
        with open(result_f) as f:
            outcome = f.read()
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)
    return outcome

def filter_diffs_by_file(file: str, 
                         diffs_dict: dict) -> list:
    # we flatten, decode, & filter our diffs
    filtered_diffs = []
    for diff_number, diffs in diffs_dict.items():
        for diff_filepath, diff_patch in diffs.items():
            # our diffs are encoded, not str.
            if diff_filepath == file:
                filtered_diffs.append(diff_patch.decode() 
                                        if diff_patch and not isinstance(diff_patch, str)
                                          else diff_patch)
    logging.debug(f'{file} {filtered_diffs}')
    return filtered_diffs

def select_from_list(items: list, title: str = "Select an item", return_index=False) -> any:
    """
    Display a list of items in a console GUI and let the user select one.
 
    Args:
        items: List of items to display
        title: Title shown at the top of the menu
 
    Returns:
        The selected item, or None if the user pressed 'q' to quit
    """
    result_holder = [None]
 
    def _menu(stdscr):
        curses.curs_set(0)  # Hide cursor
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)   # Selected row
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Title
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Normal row
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Footer
 
        selected = 0
 
        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
 
            # Draw title
            title_text = f" {title} "
            stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            stdscr.addstr(0, 0, title_text[:w])
            stdscr.addstr(1, 0, "─" * min(w, 40))
            stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
 
            # Draw items
            for i, item in enumerate(items):
                row = i + 2
                if row >= h - 1:
                    break  # Don't draw past the screen
 
                label = f"  {str(item)}"
 
                if i == selected:
                    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                    stdscr.addstr(row, 0, label[:w].ljust(min(w - 1, 40)))
                    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                else:
                    stdscr.attron(curses.color_pair(3))
                    stdscr.addstr(row, 0, label[:w])
                    stdscr.attroff(curses.color_pair(3))
 
            # Draw footer
            footer = " ↑↓ Navigate   Enter Select   q Quit "
            stdscr.attron(curses.color_pair(4))
            stdscr.addstr(h - 1, 0, footer[:w])
            stdscr.attroff(curses.color_pair(4))
 
            stdscr.refresh()
 
            key = stdscr.getch()
 
            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(items) - 1:
                selected += 1
            elif key in (ord("\n"), ord("\r")):
                result_holder[0] = selected if return_index else items[selected]
                return
            elif key == ord("q"):
                return

    curses.wrapper(_menu)
    return result_holder[0]

@click.command()
@click.option('--input_path', required=True, help='The name of your diffs parquet file.')
@click.option('--file', required=False, help='The path of the file to rebuild, relative to the git directory.')
@click.option('--until', required=False, help='The 0-based index to rebuild the file until.')
@click.option('--gui', is_flag=True, help='The 0-based index to rebuild the file until.')
def main(file, input_path, until, gui):
    assert gui or (file and until), 'You must have either gui or file & until'
    diffs_df = pd.read_parquet(input_path)
    diffs = diffs_df.to_dict()
    if not gui:
        until = int(until)
        diffs = filter_diffs_by_file(file, diffs)
    if gui:
        print(list(diffs_df.index))
        file = select_from_list(list(diffs_df.index), title="Select your file to reconstruct")
        diffs = filter_diffs_by_file(file, diffs)
        until = select_from_list([f for f in list(diffs_df.loc[file]) if f], 
                                 title='Select your diff to load.', return_index=True)
    if not diffs:
        logging.error(f"No diffs found in {input_path}!")
    else:
        success = rebuild_file_from_diffs(file, diffs, until)
        if success:
            logging.info("File reconstruction complete.")

if __name__ == '__main__':
    main()
