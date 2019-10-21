#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil
from typing import List, Set, Tuple, Optional, Any
import dataclasses
import enum

# import numba
import tqdm
import subprocess
import re
import sys
import tempfile
import argparse
import csv
import itertools

# git log --name-status --all
# git format-patch -1 --numbered-files --unified=100000 8aad90891ea4ab5762420c7424db7b01ec50c107 -- "bundles/org.eclipse.swt/Eclipse SWT PI/common_j2se/org/eclipse/swt/internal/Library.java"


_commit_line = re.compile(r'^commit ([0-9a-f]{40})$')
_src_line = re.compile(r'^M\t((.+)\.java)$')
_javadoc_start_marker = re.compile(r'^\s*/\*\*\s*$')
_javadoc_end_marker = re.compile(r'^\s*\*/\s*$')
_javadoc_section_marker = re.compile(r'^\s*\*?\s*@(param|return|exception|throw|throws)\s+')

_total_commits: int = 0
_java_files_commits: int = 0

# @numba.jit()
def has_java_javadoc_changed(patch: str, linecontext: int = 3) -> Tuple[bool, bool, bool, str]:
    patchlines = patch.replace('\r', '').split('\n')

    has_javadoc_tag_changed = False
    # has_javadoc_tag_diffplus = False
    # has_javadoc_tag_diffminus = False

    has_javadoc_changed = False
    has_java_changed = False

    interesting_line_indices: List[bool] = [False] * len(patchlines)

    going = False
    in_javadoc = False
    in_javadoc_tag_section = False
    for l, ln in zip(patchlines, itertools.count()):
        if l.startswith('@@'):
            going = True
        elif l.startswith('--'):
            going = False
        elif going and not in_javadoc and _javadoc_start_marker.match(l):
            in_javadoc = True
        elif going and in_javadoc and _javadoc_end_marker.match(l):
            in_javadoc = False
            in_javadoc_tag_section = False
        elif  going and in_javadoc and not in_javadoc_tag_section and _javadoc_section_marker.match(l):
            in_javadoc_tag_section = True
        elif going and l.startswith('+ ') or l.startswith('- '):
            if in_javadoc_tag_section:
                has_javadoc_tag_changed = True
                # has_javadoc_tag_diffplus |= l.startswith('+ ')
                # has_javadoc_tag_diffminus |= l.startswith('- ')
                for zi in range(max(0, ln - linecontext), min(len(patchlines), ln + linecontext) + 1):
                    interesting_line_indices[zi] = True
            elif in_javadoc:
                has_javadoc_changed = True
            else:
                has_java_changed = True

        # if has_java_changed and has_javadoc_changed and has_javadoc_tag_changed:
        #     return True, True, True

        if has_javadoc_tag_changed:
            brief = '\n'.join(
                l for l, n in zip(patchlines, interesting_line_indices) if n
            )
        else:
            brief = ""

    return has_java_changed, has_javadoc_changed, has_javadoc_tag_changed, brief

@enum.unique
class CommitType(enum.Enum):
    UNKNOWN = None
    JAVA_AND_JAVADOC_TAGS_EVERYWHERE = "Arbitrary Java / JavaDoc changes"
    ONLY_JAVADOC_TAGS_IN_SOME_FILES = "Some files have only JavaDoc tag changes"
    ONLY_JAVADOC_TAGS_EVERYWHERE = "Whole commit has only JavaDoc tag changes"

_mixed_commits: int = 0
_only_javadoc_in_some_files_commits: int = 0
_pure_javadoc_commits: int = 0

@dataclasses.dataclass()
class Commit:
    sha1: str
    files: List[Optional[str]] = None
    commit_type: CommitType = CommitType.UNKNOWN
    file_statuses: List[Tuple[bool, bool, bool, str]] = None

    def classify(self, tmpdir):
        global _mixed_commits, _only_javadoc_in_some_files_commits, _pure_javadoc_commits

        file_statuses: List[Tuple[bool, bool, bool]] = []

        for f in self.files:
            patchname = subprocess.check_output([
                'git', 'format-patch', '-1', '--numbered-files', '--unified=100000',
                '-o', tmpdir, self.sha1,
                '--', f
            ]).decode(sys.getdefaultencoding()).strip()
            try:
                with open(patchname, 'r', encoding='utf-8') as pfile:
                    patch = pfile.read()
                    file_statuses.append(has_java_javadoc_changed(patch))
            except Exception:
                print("Skipping bad patch of commit %s in file %s" % (self.sha1, f))
                file_statuses.append((False, False, False, ''))

        pure_javadoc_tag_files_count = sum(
            1 for (j, d, t, s) in file_statuses if t and not j and not d
        )

        # javadoc_tag_files_count = sum(
        #     1 for (j, d, t, s) in file_statuses if t
        # )

        if pure_javadoc_tag_files_count == len(file_statuses):
            self.commit_type = CommitType.ONLY_JAVADOC_TAGS_EVERYWHERE
            _pure_javadoc_commits += 1
        elif pure_javadoc_tag_files_count > 0:
            self.commit_type = CommitType.ONLY_JAVADOC_TAGS_IN_SOME_FILES
            _only_javadoc_in_some_files_commits += 1
        else:
            self.commit_type = CommitType.JAVA_AND_JAVADOC_TAGS_EVERYWHERE
            _mixed_commits += 1

        self.file_statuses = file_statuses


    def get_file_statuses_str(self) -> str:
        res = []
        for f, (j, d, t, s) in zip(self.files, self.file_statuses):
            if len(s):
                res.append("%s:\n%s\n" % (f, s))
        return "\n".join(res)

    def csv_line(self, url_prefix: str) -> List[str]:
        return [
            self.commit_type.value,
            url_prefix + self.sha1,
            self.get_file_statuses_str()
        ]


def get_commits() -> List[Commit]:
    global _total_commits

    log = subprocess.check_output([
        'git', 'log', '--name-status', '--all'
    ]).decode(sys.getdefaultencoding())
    log = log.replace('\r', '')
    loglines = log.split('\n')
    commits = []
    cur_commit = None
    cur_files = []

    def release():
        global _java_files_commits
        if cur_commit and len(cur_files):
            _java_files_commits += 1
            commits.append(Commit(cur_commit, cur_files.copy()))

    print("Analyzing log...")

    for l in tqdm.tqdm(loglines):
        clm = _commit_line.match(l)
        clf = _src_line   .match(l)
        if clm:
            _total_commits += 1
            release()
            cur_commit = clm.group(1)
            cur_files = []
        elif clf:
            cur_files.append(clf.group(1))
    release()
    return commits

def calc_stats(args):
    commits = get_commits()

    print("Analyzing commits...")

    try:
        tmpdir = tempfile.mkdtemp()
        for c in tqdm.tqdm(commits):
            c.classify(tmpdir)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


    print("Writing table with links:")
    with open("__commits.csv", 'w', newline='', encoding='utf-8') as csvf:
        cw = csv.writer(csvf, dialect='excel', delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
        for cm in tqdm.tqdm(commits):
            if cm.commit_type in {CommitType.ONLY_JAVADOC_TAGS_EVERYWHERE, CommitType.ONLY_JAVADOC_TAGS_IN_SOME_FILES}:
                cw.writerow(cm.csv_line(args.commit_prefix))


    print("Report")
    print("======")
    print("Total commits:", _total_commits)
    print("Commits with Java file changes:", _java_files_commits)
    print("Commits having Code and JavaDoc tags changed in all files: ", _mixed_commits)
    print("Commits having files with only JavaDoc tag changes:", _only_javadoc_in_some_files_commits)
    print("Commits exclusively of JavaDoc tag changes:", _pure_javadoc_commits)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-cp', '--commit-prefix', type=str, default="https://github.com/albertogoffi/toradocu/commit/")
    argparser.add_argument('-cl', '--context-lines', type=int, default=3)
    args = argparser.parse_args()
    calc_stats(args)
