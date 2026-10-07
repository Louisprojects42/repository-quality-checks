"""Read-only example. Pass the repository you want to inspect."""

import argparse
from pathlib import Path

from repository_quality_checks import check

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("root", type=Path)
args = parser.parse_args()
for problem in check(args.root):
    print(problem)
