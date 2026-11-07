"""Make the project root importable when pytest is run from anywhere.

Without this, `python -m pytest D:/code/itulibrary` from another directory fails to import `itulib` at all -
verified, not assumed - so the suite is only green when the working directory happens to be the project root.
`asn1core` carries the same file for the same reason, including for the `python -O` run in CI where stripped
assertions are the ones that matter.
"""
