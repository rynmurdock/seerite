# WIP


# seegit

seegit is a package for converting a git repo into a dataframe of diffs broken down by file (tracing) and then recreating files from the git repo edit-by-edit (rebuilding).

This can enable systematically tracking, visualizing, understanding edits & changes over a set of files.

## Quickstart

You can install the pip package with:

`pip install seegit`

And then run within your repo run:

```
seegit-trace --branch <your branch> --output_path './diffs.parquet' --suffix_of_interest '.tex'
```
to save your git diffs to a parquet file.

and

```
seegit-rebuild --input_path './diffs.parquet'
```

If you'd like to use this for tracking your edits to your work for visualization, understanding, modeling, then we recommended that you use dura (https://github.com/tkellogg/dura/) along with auto-saving in whatever editor you prefer.

The package is written to allow for incorrect or approximately incorrect patches/diffs while raising warnings to facilitate modeling.
