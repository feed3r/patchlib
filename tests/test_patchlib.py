#!/usr/bin/env python
"""
python-patch test suite

There are two kind of tests:
 - file-based tests
 - directory-based tests
 - unit tests

File-based test is patch file, initial file and resulting file
for comparison.

Directory-based test is a self-sufficient directory with:
files to be patched, patch file itself and [result] dir. You can
manually apply patch and compare outcome with [result] directory.
This is what this test runner does.

Unit tests test API and are all inside this runner.


== Code Coverage ==

To refresh code coverage stats, get 'coverage' tool from
http://pypi.python.org/pypi/coverage/ and run this file with:

  coverage run run_tests.py
  coverage html -d coverage

On Windows it may be more convenient instead of `coverage` call
`python -m coverage.__main__`
"""

import os
import sys
import re
import shutil
import unittest
import copy
from os import listdir
from os.path import abspath, dirname, exists, join, isdir, isfile
from tempfile import mkdtemp

import patchlib


class TestPatchlib(unittest.TestCase):
  TESTS_DIR = dirname(abspath(__file__))


# ----------------------------------------------------------------------------
class TestPatchFiles(TestPatchlib):
  """
  unittest hack - test* methods are generated by add_test_methods() function
  below dynamically using information about *.patch files from tests directory

  """
  @classmethod
  def setUpClass(cls):
    cls.add_test_methods()

  def _assert_files_equal(self, file1, file2):
      f1 = f2 = None
      try:
        f1 = open(file1, "rb")
        f2 = open(file2, "rb")
        for line in f1:
          self.assertEqual(line, f2.readline())

      finally:
        if f2:
          f2.close()
        if f1:
          f1.close()
  
  def _assert_dirs_equal(self, dir1, dir2, ignore=[]):
      """
      compare dir2 with reference dir1, ignoring entries
      from supplied list

      """
      # recursive
      if type(ignore) == str:
        ignore = [ignore]
      e2list = [en for en in listdir(dir2) if en not in ignore]
      for e1 in listdir(dir1):
        if e1 in ignore:
          continue
        e1path = join(dir1, e1)
        e2path = join(dir2, e1)
        self.assert_(exists(e1path))
        self.assert_(exists(e2path), "%s does not exist" % e2path)
        self.assert_(isdir(e1path) == isdir(e2path))
        if not isdir(e1path):
          self._assert_files_equal(e1path, e2path)
        else:
          self._assert_dirs_equal(e1path, e2path, ignore=ignore)
        e2list.remove(e1)
      for e2 in e2list:
        self.fail("extra file or directory: %s" % e2)

  
  def _run_test(self, testname):
      """
      boilerplate for running *.patch file tests
      """

      # 1. create temp test directory
      # 2. copy files
      # 3. execute file-based patch 
      # 4. compare results
      # 5. cleanup on success

      tmpdir = mkdtemp(prefix="%s."%testname)

      basepath = join(self.TESTS_DIR, testname)
      basetmp = join(tmpdir, testname)

      patch_file = basetmp + ".patch"
      
      file_based = isfile(basepath + ".from")
      from_tgt = basetmp + ".from"

      if file_based:
        shutil.copy(basepath + ".from", tmpdir)
        shutil.copy(basepath + ".patch", tmpdir)
      else:
        # directory-based
        for e in listdir(basepath):
          epath = join(basepath, e)
          if not isdir(epath):
            shutil.copy(epath, join(tmpdir, e))
          else:
            shutil.copytree(epath, join(tmpdir, e))


      # 3.
      # test utility as a whole
      patch_tool = join(dirname(self.TESTS_DIR), "patchlib.py")
      save_cwd = os.getcwdu()
      os.chdir(tmpdir)
      if verbose:
        cmd = '%s %s "%s"' % (sys.executable, patch_tool, patch_file)
        print "\n"+cmd
      else:
        cmd = '%s %s -q "%s"' % (sys.executable, patch_tool, patch_file)
      ret = os.system(cmd)
      assert ret == 0, "Error %d running test %s" % (ret, testname)
      os.chdir(save_cwd)


      # 4.
      # compare results
      if file_based:
        self._assert_files_equal(basepath + ".to", from_tgt)
      else:
        # recursive comparison
        self._assert_dirs_equal(join(basepath, "[result]"),
                                tmpdir,
                                ignore=["%s.patch" % testname, ".svn", "[result]"])


      shutil.rmtree(tmpdir)
      return 0

  @classmethod
  def add_test_methods(cls):
    """	
    hack to generate test* methods in target class - one
    for each *.patch file in tests directory
    """

    # list testcases - every test starts with number
    # and add them as test* methods
    testptn = re.compile(r"^(?P<name>\d{2,}[^\.]+).*$")

    testset = [testptn.match(e).group('name') for e in listdir(self.TESTS_DIR) if testptn.match(e)]
    testset = sorted(set(testset))

    for filename in testset:
        methname = filename.replace(" ", "_")
    def create_closure():
        name = filename
        return lambda self: self._run_test(name)
    setattr(cls, "test%s" % methname, create_closure())


# ----------------------------------------------------------------------------

class TestCheckPatched(TestPatchlib):
    def setUp(self):
        self.save_cwd = os.getcwdu()
        os.chdir(self.TESTS_DIR)

    def tearDown(self):
        os.chdir(self.save_cwd)

    def test_patched_multipatch(self):
        pto = patchlib.fromfile("01uni_multi/01uni_multi.patch")
        os.chdir(join(self.TESTS_DIR, "01uni_multi", "[result]"))
        self.assert_(pto.can_patch("updatedlg.cpp"))

    def test_can_patch_single_source(self):
        pto2 = patchlib.fromfile("02uni_newline.patch")
        self.assert_(pto2.can_patch("02uni_newline.from"))

    def test_can_patch_fails_on_target_file(self):
        pto3 = patchlib.fromfile("03trail_fname.patch")
        self.assertEqual(None, pto3.can_patch("03trail_fname.to"))
        self.assertEqual(None, pto3.can_patch("not_in_source.also"))
   
    def test_multiline_false_on_other_file(self):
        pto = patchlib.fromfile("01uni_multi/01uni_multi.patch")
        os.chdir(join(self.TESTS_DIR, "01uni_multi"))
        self.assertFalse(pto.can_patch("updatedlg.cpp"))

    def test_single_false_on_other_file(self):
        pto3 = patchlib.fromfile("03trail_fname.patch")
        self.assertFalse(pto3.can_patch("03trail_fname.from"))

    def test_can_patch_checks_source_filename_even_if_target_can_be_patched(self):
        pto2 = patchlib.fromfile("04can_patch.patch")
        self.assertFalse(pto2.can_patch("04can_patch.to"))

# ----------------------------------------------------------------------------

class TestPatchParse(TestPatchlib):
    def _testfile(self, name):
        return join(self.TESTS_DIR, 'data', name)

    def test_fromstring(self):
        try:
          f = open(join(self.TESTS_DIR, "01uni_multi/01uni_multi.patch"), "rb")
          readstr = f.read()
        finally:
          f.close()
        pst = patchlib.fromstring(readstr)
        self.assertEqual(len(pst), 5)

    def test_fromfile(self):
        pst = patchlib.fromfile(join(self.TESTS_DIR, "01uni_multi/01uni_multi.patch"))
        self.assertNotEqual(pst, False)
        self.assertEqual(len(pst), 5)
        ps2 = patchlib.fromfile(self._testfile("failing/not-a-patch.log"))
        self.assertFalse(ps2)

    def test_no_header_for_plain_diff_with_single_file(self):
        pto = patchlib.fromfile(join(self.TESTS_DIR, "03trail_fname.patch"))
        self.assertEqual(pto.items[0].header, [])

    def test_header_for_second_file_in_svn_diff(self):
        pto = patchlib.fromfile(join(self.TESTS_DIR, "01uni_multi/01uni_multi.patch"))
        self.assertEqual(pto.items[1].header[0], 'Index: updatedlg.h\r\n')
        self.assert_(pto.items[1].header[1].startswith('====='))

    def test_hunk_desc(self):
        pto = patchlib.fromfile(self._testfile('git-changed-file.diff'))
        self.assertEqual(pto.items[0].hunks[0].desc, 'class JSONPluginMgr(object):')

    def test_autofixed_absolute_path(self):
        pto = patchlib.fromfile(join(self.TESTS_DIR, "data/autofix/absolute-path.diff"))
        self.assertEqual(pto.errors, 0)
        self.assertEqual(pto.warnings, 2)
        self.assertEqual(pto.items[0].source, "winnt/tests/run_tests.py")

    def test_autofixed_parent_path(self):
        # [ ] exception vs return codes for error recovery
        #  [x] separate return code when patch lib compensated the error
        #      (implemented as warning count)
        pto = patchlib.fromfile(join(self.TESTS_DIR, "data/autofix/parent-path.diff"))
        self.assertEqual(pto.errors, 0)
        self.assertEqual(pto.warnings, 2)
        self.assertEqual(pto.items[0].source, "patch.py")

    def test_autofixed_stripped_trailing_whitespace(self):
        pto = patchlib.fromfile(join(self.TESTS_DIR, "data/autofix/stripped-trailing-whitespace.diff"))
        self.assertEqual(pto.errors, 0)
        self.assertEqual(pto.warnings, 4)

    def test_fail_missing_hunk_line(self):
        fp = open(join(self.TESTS_DIR, "data/failing/missing-hunk-line.diff"))
        pto = patchlib.PatchSet()
        self.assertNotEqual(pto.parse(fp), True)
        fp.close()

    def test_fail_context_format(self):
        fp = open(join(self.TESTS_DIR, "data/failing/context-format.diff"))
        res = patchlib.PatchSet().parse(fp)
        self.assertFalse(res)
        fp.close()

    def test_fail_not_a_patch(self):
        fp = open(join(self.TESTS_DIR, "data/failing/not-a-patch.log"))
        res = patchlib.PatchSet().parse(fp)
        self.assertFalse(res)
        fp.close()

    def test_diffstat(self):
        output = """\
 updatedlg.cpp | 20 ++++++++++++++++++--
 updatedlg.h   |  1 +
 manifest.xml  | 15 ++++++++-------
 conf.cpp      | 23 +++++++++++++++++------
 conf.h        |  7 ++++---
 5 files changed, 48 insertions(+), 18 deletions(-), +1203 bytes"""
        pto = patchlib.fromfile(join(self.TESTS_DIR, "01uni_multi/01uni_multi.patch"))
        self.assertEqual(pto.diffstat(), output, "Output doesn't match")

class TestPatchSetDetect(TestPatchlib):
    def test_svn_detected(self):
        pto = patchlib.fromfile(join(self.TESTS_DIR, "01uni_multi/01uni_multi.patch"))
        self.assertEqual(pto.type, patchlib.SVN)

    def test_hg_detected(self):
        pto = patchlib.fromfile(join(self.TESTS_DIR, "data/hg-added-file.diff"))
        self.assertEqual(pto.type, patchlib.HG)

    def test_hg_exported(self):
        pto = patchlib.fromfile(join(self.TESTS_DIR, "data/hg-exported.diff"))
        self.assertEqual(pto.type, patchlib.HG)

    def test_git_changed_detected(self):
        pto = patchlib.fromfile(join(self.TESTS_DIR, "data/git-changed-file.diff"))
        self.assertEqual(pto.type, patchlib.GIT)

class TestPatchApply(TestPatchlib):
    def setUp(self):
        self.save_cwd = os.getcwdu()
        self.tmpdir = mkdtemp(prefix=self.__class__.__name__)
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.save_cwd)
        shutil.rmtree(self.tmpdir)

    def tmpcopy(self, filenames):
        """copy file(s) from test_dir to self.tmpdir"""
        for f in filenames:
          shutil.copy(join(self.TESTS_DIR, f), self.tmpdir)

    def test_apply_returns_false_on_failure(self):
        self.tmpcopy(['data/failing/non-empty-patch-for-empty-file.diff',
                      'data/failing/upload.py'])
        pto = patchlib.fromfile('non-empty-patch-for-empty-file.diff')
        self.assertFalse(pto.apply())

    def test_apply_returns_true_on_success(self):
        self.tmpcopy(['03trail_fname.patch',
                      '03trail_fname.from'])
        pto = patchlib.fromfile('03trail_fname.patch')
        self.assert_(pto.apply())

    def test_revert(self):
        self.tmpcopy(['03trail_fname.patch',
                      '03trail_fname.from'])
        pto = patchlib.fromfile('03trail_fname.patch')
        self.assert_(pto.apply())
        self.assertNotEqual(open(self.tmpdir + '/03trail_fname.from').read(),
                            open(self.TESTS_DIR + '/03trail_fname.from').read())
        self.assert_(pto.revert())
        self.assertEqual(open(self.tmpdir + '/03trail_fname.from').read(),
                         open(self.TESTS_DIR + '/03trail_fname.from').read())

    def test_apply_root(self):
        treeroot = join(self.tmpdir, 'rootparent')
        shutil.copytree(join(self.TESTS_DIR, '06nested'), treeroot)
        pto = patchlib.fromfile(join(self.TESTS_DIR, '06nested/06nested.patch'))
        self.assert_(pto.apply(root=treeroot))

    def test_apply_strip(self):
        treeroot = join(self.tmpdir, 'rootparent')
        shutil.copytree(join(self.TESTS_DIR, '06nested'), treeroot)
        pto = patchlib.fromfile(join(self.TESTS_DIR, '06nested/06nested.patch'))
        for p in pto:
          p.source = 'nasty/prefix/' + p.source
          p.target = 'nasty/prefix/' + p.target
        self.assert_(pto.apply(strip=2, root=treeroot))

class TestHelpers(TestPatchlib):
    # unittest setting
    longMessage = True

    absolute = ['/', 'c:\\', 'c:/', '\\', '/path', 'c:\\path']
    relative = ['path', 'path:\\', 'path:/', 'path\\', 'path/', 'path\\path']

    def test_xisabs(self):
        for path in self.absolute:
            self.assertTrue(patchlib.xisabs(path), 'Target path: ' + repr(path))
        for path in self.relative:
            self.assertFalse(patchlib.xisabs(path), 'Target path: ' + repr(path))

    def test_xnormpath(self):
        path = "../something/..\\..\\file.to.patch"
        self.assertEqual(patchlib.xnormpath(path), '../../file.to.patch')

    def test_xstrip(self):
        for path in self.absolute[:4]:
            self.assertEqual(patchlib.xstrip(path), '')
        for path in self.absolute[4:6]:
            self.assertEqual(patchlib.xstrip(path), 'path')
        # test relative paths are not affected
        for path in self.relative:
            self.assertEqual(patchlib.xstrip(path), path)

    def test_pathstrip(self):
        self.assertEqual(patchlib.pathstrip('path/to/test/name.diff', 2), 'test/name.diff')
        self.assertEqual(patchlib.pathstrip('path/name.diff', 1), 'name.diff')
        self.assertEqual(patchlib.pathstrip('path/name.diff', 0), 'path/name.diff')

# ----------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()