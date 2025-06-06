#  Copyright 2013 – present by the SalishSeaCast Project contributors
#  and The University of British Columbia
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Jupyter Notebook collection README generator

When you add a new notebook to this directory,
rename a notebook,
or change the description of a notebook in its first Markdown cell,
please generate a updated `README.md` file with:

    python -m make_readme

and commit and push the updated `README.md` to GitHub.
"""
import json
import re
from pathlib import Path

NBVIEWER = "https://nbviewer.org/github"
GITHUB_ORG = "SalishSeaCast"
REPO_NAME = "SalishSeaNowcast"
DEFAULT_BRANCH_NAME = "main"
TITLE_PATTERN = re.compile("#{1,6} ?")


def main():
    cwd_parts = Path.cwd().parts
    repo_path = Path(*cwd_parts[cwd_parts.index(REPO_NAME) + 1 :])
    url = f"{NBVIEWER}/{GITHUB_ORG}/{REPO_NAME}/blob/{DEFAULT_BRANCH_NAME}/{repo_path}"

    readme = """\
The Jupyter Notebooks in this directory document
various aspects of the development and maintenance of the SalishSeaCast
automation system.

In particular:

* The [ERDDAP_datasets.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/ERDDAP_datasets.ipynb)
  notebook describes and partially automates the process of generating
  XML fragments for model results datasets to be included in the ERDDAP
  server system.
* The
  [DevelopingNowcastFigureFunctions.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/DevelopingNowcastFigureFunctions.ipynb)
  notebook describes the recommended process for development of those functions,
  and provides an example of development of one.


The links below are to static renderings of the notebooks via
[nbviewer.org](https://nbviewer.org/).
Descriptions under the links below are from the first cell of the notebooks
(if that cell contains Markdown or raw text).

"""
    for fn in Path(".").glob("*.ipynb"):
        readme += f"* ## [{fn}]({url}/{fn})  \n    \n"
        readme += notebook_description(fn)

    license = f"""
##License

These notebooks and files are copyright 2013 – present
by the SalishSeaCast Project Contributors
and The University of British Columbia.

They are licensed under the Apache License, Version 2.0.
http://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
"""
    with open("README.md", "wt") as f:
        f.writelines(readme)
        f.writelines(license)


def notebook_description(fn):
    description = ""
    with open(fn, "rt") as notebook:
        contents = json.load(notebook)
    try:
        first_cell = contents["worksheets"][0]["cells"][0]
    except KeyError:
        first_cell = contents["cells"][0]
    first_cell_type = first_cell["cell_type"]
    if first_cell_type not in "markdown raw".split():
        return description
    desc_lines = first_cell["source"]
    for line in desc_lines:
        suffix = ""
        if TITLE_PATTERN.match(line):
            line = TITLE_PATTERN.sub("**", line)
            suffix = "**"
        if line.endswith("\n"):
            description += f"    {line[:-1]}{suffix}\n"
        else:
            description += f"    {line}{suffix}"
    description += "\n" * 2
    return description


if __name__ == "__main__":
    main()
