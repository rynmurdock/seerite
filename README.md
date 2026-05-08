# seegit

seegit is a package for tracing -- converting a git repo into a dataframe of diffs broken down by file -- and then rebuilding -- recreating files from the git repo edit-by-edit.

This can enable systematically tracking, visualizing, understanding edits & changes over a set of files.

## Quickstart

You can install the pip package by running:

`python3 -m pip install seegit`

or similar if you use uv/conda/etc.

And then within your repo run:

```
seegit-trace --branch <your branch> --output_path './diffs.parquet' --suffix_of_interest '.tex'
```
to save your git diffs to a parquet file.

and

```
seegit-rebuild --input_path './diffs.parquet'
```

If you'd like to seegit this for tracking your edits to your work for visualization, understanding, modeling, then we recommended that you use dura (https://github.com/tkellogg/dura/) along with auto-saving in whatever editor you prefer.

seegit is written in such a way as to allow for incorrect or approximately incorrect patches/diffs while raising warnings to facilitate modeling.


