# seegit

seegit is a package for "tracing" -- converting a git repo into a dataframe of diffs broken down by file -- and then "rebuilding" -- recreating files from the git repo edit-by-edit to a selected point in their history.

This can enable systematically tracking, visualizing, & understanding edits & changes over a set of files.

## Quickstart

You can install the pip package by running:

```
pip install git+https://github.com/rynmurdock/seerite
```

or similar if you use uv/conda/etc.

And then within your git repo run:

```
seegit-trace --branch <your branch> --output_path './diffs.parquet' --suffix_of_interest '<trace only files that end with this string>'
```

to save your git diffs to a parquet file.

And then

```
seegit-rebuild --input_path './diffs.parquet' --gui
```

to interactively select your file & your diff to rebuild. Use `--help` to see more 
options you can use with these commands.

## Additional Notes

We also have many useful functions you can use outside of these canonical tools. (To be documented; you can explore yourself for now.)

If you'd like to use seegit for tracking edits moment-by-moment to your files for visualization, understanding, modeling, then we recommend you use dura (https://github.com/tkellogg/dura/) along with auto-saving in whatever editor you prefer. dura can commit your auto-saved changes automatically in the background, which seegit can then trace.

Notably, seegit is written in such a way as to allow for incorrect or approximately incorrect patches/diffs while raising warnings -- this is done to facilitate modeling use cases.


