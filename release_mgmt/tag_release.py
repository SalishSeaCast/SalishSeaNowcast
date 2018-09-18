# Copyright 2013-2018 The Salish Sea MEOPAR Contributors
# and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""SalishSeaCast release management script that tags NEMO code and model
configuration repos for a production release.
"""
import argparse
import logging
from pathlib import Path

import coloredlogs
import hglib
import verboselogs
import yaml

NAME = "tag_release"
verboselogs.install()
logger = logging.getLogger(NAME)
coloredlogs.install(fmt="%(asctime)s %(hostname)s %(name)s %(levelname)s %(message)s")


def main():
    parsed_args = _command_line_interface()
    repos = _load_repos_list(parsed_args.repos_file)
    for repo in repos:
        _tag_repo(repo, parsed_args.tag)


def _command_line_interface():
    parser = argparse.ArgumentParser(
        description="""
        Tag NEMO code and model configuration repos for a production release.
        """
    )
    parser.prog = f"python -m release_mgmt.{NAME}"
    parser.add_argument(
        "repos_file",
        type=Path,
        help="""
        Path/name of YAML file containing the list of repository paths to tag.
        The list is unique for each user and machine combination.
        """,
    )
    parser.add_argument(
        "tag",
        help="""
        Tag to mark the most recently committed repo changesets with.
        Format: PROD-run-type-hypenated-description
        Examples: PROD-hindcast-201806-v2-2017, PROD-nowcast-green-201702v2
        """,
    )
    return parser.parse_args()


def _load_repos_list(repos_file):
    """
    :param pathlib.Path repos_file:
    :rtype: dict
    """
    with repos_file.open("rt") as f:
        repos_info = yaml.safe_load(f)
    logger.info(f"read list of repos to tag from {repos_file}")
    return (repo for repo in repos_info["repos"])


def _tag_repo(repo, tag):
    logger.info(f"processing repo: {repo}")
    if not Path(repo).exists():
        logger.error(f"repo does not exist: {repo}")
        raise SystemExit(2)
    try:
        with hglib.open(repo) as hg:
            status = hg.status(
                modified=True, added=True, removed=True, deleted=True, copies=True
            )
    except hglib.error.ServerError:
        logger.error(f"unable to find Mercurial repo root in: {repo}")
        raise SystemExit(2)
    if status:
        logger.error(f"uncommitted changes in repo: {repo}")
        raise SystemExit(2)
    with hglib.open(repo) as hg:
        incoming_changes = hg.incoming()
        if incoming_changes:
            logger.warning(
                f"found incoming changes from Bitbucket that you need to "
                f"deal with in repo: {repo}"
            )
            raise SystemExit(2)
        try:
            hg.tag(tag.encode(), message=f"Tag production release {tag}.")
        except hglib.error.CommandError as exc:
            if exc.err.decode().startswith(f"abort: tag '{tag}' already exists"):
                logger.warning(f"tag '{tag}' already exists in repo: {repo}")
                return
            else:
                raise
        logger.success(f"added {tag} to repo: {repo}")
        hg.push()
        logger.success(f"pushed {tag} tag to Bitbucket from repo: {repo}")


if __name__ == "__main__":
    main()  # pragma: no cover
