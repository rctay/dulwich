# test_repository.py -- tests for repository.py
# Copyright (C) 2007 James Westby <jw+debian@jameswestby.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) any later version of
# the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.


"""Tests for the repository."""

from cStringIO import StringIO
import os
import shutil
import tempfile
import unittest

from dulwich import errors
from dulwich import objects
from dulwich.repo import (
    check_ref_format,
    Repo,
    read_packed_refs,
    read_packed_refs_with_peeled,
    write_packed_refs,
    _split_ref_line,
    )
from dulwich.tests.utils import (
    open_repo,
    tear_down_repo,
    )

missing_sha = 'b91fa4d900e17e99b433218e988c4eb4a3e9a097'


class CreateRepositoryTests(unittest.TestCase):

    def test_create(self):
        tmp_dir = tempfile.mkdtemp()
        try:
            repo = Repo.init_bare(tmp_dir)
            self.assertEquals(tmp_dir, repo._controldir)
        finally:
            shutil.rmtree(tmp_dir)


class RepositoryTests(unittest.TestCase):

    def setUp(self):
        self._repo = None

    def tearDown(self):
        if self._repo is not None:
            tear_down_repo(self._repo)

    def test_simple_props(self):
        r = self._repo = open_repo('a.git')
        self.assertEqual(r.controldir(), r.path)

    def test_ref(self):
        r = self._repo = open_repo('a.git')
        self.assertEqual(r.ref('refs/heads/master'),
                         'a90fa2d900a17e99b433217e988c4eb4a2e9a097')

    def test_setitem(self):
        r = self._repo = open_repo('a.git')
        r["refs/tags/foo"] = 'a90fa2d900a17e99b433217e988c4eb4a2e9a097'
        self.assertEquals('a90fa2d900a17e99b433217e988c4eb4a2e9a097',
                          r["refs/tags/foo"].id)

    def test_get_refs(self):
        r = self._repo = open_repo('a.git')
        self.assertEqual({
            'HEAD': 'a90fa2d900a17e99b433217e988c4eb4a2e9a097',
            'refs/heads/master': 'a90fa2d900a17e99b433217e988c4eb4a2e9a097',
            'refs/tags/mytag': '28237f4dc30d0d462658d6b937b08a0f0b6ef55a',
            'refs/tags/mytag-packed': 'b0931cadc54336e78a1d980420e3268903b57a50',
            }, r.get_refs())

    def test_head(self):
        r = self._repo = open_repo('a.git')
        self.assertEqual(r.head(), 'a90fa2d900a17e99b433217e988c4eb4a2e9a097')

    def test_get_object(self):
        r = self._repo = open_repo('a.git')
        obj = r.get_object(r.head())
        self.assertEqual(obj._type, 'commit')

    def test_get_object_non_existant(self):
        r = self._repo = open_repo('a.git')
        self.assertRaises(KeyError, r.get_object, missing_sha)

    def test_commit(self):
        r = self._repo = open_repo('a.git')
        obj = r.commit(r.head())
        self.assertEqual(obj._type, 'commit')

    def test_commit_not_commit(self):
        r = self._repo = open_repo('a.git')
        self.assertRaises(errors.NotCommitError,
                          r.commit, '4f2e6529203aa6d44b5af6e3292c837ceda003f9')

    def test_tree(self):
        r = self._repo = open_repo('a.git')
        commit = r.commit(r.head())
        tree = r.tree(commit.tree)
        self.assertEqual(tree._type, 'tree')
        self.assertEqual(tree.sha().hexdigest(), commit.tree)

    def test_tree_not_tree(self):
        r = self._repo = open_repo('a.git')
        self.assertRaises(errors.NotTreeError, r.tree, r.head())

    def test_tag(self):
        r = self._repo = open_repo('a.git')
        tag_sha = '28237f4dc30d0d462658d6b937b08a0f0b6ef55a'
        tag = r.tag(tag_sha)
        self.assertEqual(tag._type, 'tag')
        self.assertEqual(tag.sha().hexdigest(), tag_sha)
        obj_type, obj_sha = tag.object
        self.assertEqual(obj_type, objects.Commit)
        self.assertEqual(obj_sha, r.head())

    def test_tag_not_tag(self):
        r = self._repo = open_repo('a.git')
        self.assertRaises(errors.NotTagError, r.tag, r.head())

    def test_get_peeled(self):
        # unpacked ref
        r = self._repo = open_repo('a.git')
        tag_sha = '28237f4dc30d0d462658d6b937b08a0f0b6ef55a'
        self.assertNotEqual(r[tag_sha].sha().hexdigest(), r.head())
        self.assertEqual(r.get_peeled('refs/tags/mytag'), r.head())

        # packed ref with cached peeled value
        packed_tag_sha = 'b0931cadc54336e78a1d980420e3268903b57a50'
        parent_sha = r[r.head()].parents[0]
        self.assertNotEqual(r[packed_tag_sha].sha().hexdigest(), parent_sha)
        self.assertEqual(r.get_peeled('refs/tags/mytag-packed'), parent_sha)

        # TODO: add more corner cases to test repo

    def test_get_peeled_not_tag(self):
        r = self._repo = open_repo('a.git')
        self.assertEqual(r.get_peeled('HEAD'), r.head())

    def test_get_blob(self):
        r = self._repo = open_repo('a.git')
        commit = r.commit(r.head())
        tree = r.tree(commit.tree)
        blob_sha = tree.entries()[0][2]
        blob = r.get_blob(blob_sha)
        self.assertEqual(blob._type, 'blob')
        self.assertEqual(blob.sha().hexdigest(), blob_sha)

    def test_get_blob_notblob(self):
        r = self._repo = open_repo('a.git')
        self.assertRaises(errors.NotBlobError, r.get_blob, r.head())

    def test_linear_history(self):
        r = self._repo = open_repo('a.git')
        history = r.revision_history(r.head())
        shas = [c.sha().hexdigest() for c in history]
        self.assertEqual(shas, [r.head(),
                                '2a72d929692c41d8554c07f6301757ba18a65d91'])

    def test_merge_history(self):
        r = self._repo = open_repo('simple_merge.git')
        history = r.revision_history(r.head())
        shas = [c.sha().hexdigest() for c in history]
        self.assertEqual(shas, ['5dac377bdded4c9aeb8dff595f0faeebcc8498cc',
                                'ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                                '4cffe90e0a41ad3f5190079d7c8f036bde29cbe6',
                                '60dacdc733de308bb77bb76ce0fb0f9b44c9769e',
                                '0d89f20333fbb1d2f3a94da77f4981373d8f4310'])

    def test_revision_history_missing_commit(self):
        r = self._repo = open_repo('simple_merge.git')
        self.assertRaises(errors.MissingCommitError, r.revision_history,
                          missing_sha)

    def test_out_of_order_merge(self):
        """Test that revision history is ordered by date, not parent order."""
        r = self._repo = open_repo('ooo_merge.git')
        history = r.revision_history(r.head())
        shas = [c.sha().hexdigest() for c in history]
        self.assertEqual(shas, ['7601d7f6231db6a57f7bbb79ee52e4d462fd44d1',
                                'f507291b64138b875c28e03469025b1ea20bc614',
                                'fb5b0425c7ce46959bec94d54b9a157645e114f5',
                                'f9e39b120c68182a4ba35349f832d0e4e61f485c'])

    def test_get_tags_empty(self):
        r = self._repo = open_repo('ooo_merge.git')
        self.assertEqual({}, r.refs.as_dict('refs/tags'))

    def test_get_config(self):
        r = self._repo = open_repo('ooo_merge.git')
        self.assertEquals({}, r.get_config())


class CheckRefFormatTests(unittest.TestCase):
    """Tests for the check_ref_format function.

    These are the same tests as in the git test suite.
    """

    def test_valid(self):
        self.assertTrue(check_ref_format('heads/foo'))
        self.assertTrue(check_ref_format('foo/bar/baz'))
        self.assertTrue(check_ref_format('refs///heads/foo'))
        self.assertTrue(check_ref_format('foo./bar'))
        self.assertTrue(check_ref_format('heads/foo@bar'))
        self.assertTrue(check_ref_format('heads/fix.lock.error'))

    def test_invalid(self):
        self.assertFalse(check_ref_format('foo'))
        self.assertFalse(check_ref_format('heads/foo/'))
        self.assertFalse(check_ref_format('./foo'))
        self.assertFalse(check_ref_format('.refs/foo'))
        self.assertFalse(check_ref_format('heads/foo..bar'))
        self.assertFalse(check_ref_format('heads/foo?bar'))
        self.assertFalse(check_ref_format('heads/foo.lock'))
        self.assertFalse(check_ref_format('heads/v@{ation'))
        self.assertFalse(check_ref_format('heads/foo\bar'))


ONES = "1" * 40
TWOS = "2" * 40
THREES = "3" * 40
FOURS = "4" * 40

class PackedRefsFileTests(unittest.TestCase):

    def test_split_ref_line_errors(self):
        self.assertRaises(errors.PackedRefsException, _split_ref_line,
                          'singlefield')
        self.assertRaises(errors.PackedRefsException, _split_ref_line,
                          'badsha name')
        self.assertRaises(errors.PackedRefsException, _split_ref_line,
                          '%s bad/../refname' % ONES)

    def test_read_without_peeled(self):
        f = StringIO('# comment\n%s ref/1\n%s ref/2' % (ONES, TWOS))
        self.assertEqual([(ONES, 'ref/1'), (TWOS, 'ref/2')],
                         list(read_packed_refs(f)))

    def test_read_without_peeled_errors(self):
        f = StringIO('%s ref/1\n^%s' % (ONES, TWOS))
        self.assertRaises(errors.PackedRefsException, list, read_packed_refs(f))

    def test_read_with_peeled(self):
        f = StringIO('%s ref/1\n%s ref/2\n^%s\n%s ref/4' % (
            ONES, TWOS, THREES, FOURS))
        self.assertEqual([
            (ONES, 'ref/1', None),
            (TWOS, 'ref/2', THREES),
            (FOURS, 'ref/4', None),
            ], list(read_packed_refs_with_peeled(f)))

    def test_read_with_peeled_errors(self):
        f = StringIO('^%s\n%s ref/1' % (TWOS, ONES))
        self.assertRaises(errors.PackedRefsException, list, read_packed_refs(f))

        f = StringIO('%s ref/1\n^%s\n^%s' % (ONES, TWOS, THREES))
        self.assertRaises(errors.PackedRefsException, list, read_packed_refs(f))

    def test_write_with_peeled(self):
        f = StringIO()
        write_packed_refs(f, {'ref/1': ONES, 'ref/2': TWOS},
                          {'ref/1': THREES})
        self.assertEqual(
            "# pack-refs with: peeled\n%s ref/1\n^%s\n%s ref/2\n" % (
            ONES, THREES, TWOS), f.getvalue())

    def test_write_without_peeled(self):
        f = StringIO()
        write_packed_refs(f, {'ref/1': ONES, 'ref/2': TWOS})
        self.assertEqual("%s ref/1\n%s ref/2\n" % (ONES, TWOS), f.getvalue())


class RefsContainerTests(unittest.TestCase):

    def setUp(self):
        self._repo = open_repo('refs.git')
        self._refs = self._repo.refs

    def tearDown(self):
        tear_down_repo(self._repo)

    def test_get_packed_refs(self):
        self.assertEqual({
            'refs/heads/packed': '42d06bd4b77fed026b154d16493e5deab78f02ec',
            'refs/tags/refs-0.1': 'df6800012397fb85c56e7418dd4eb9405dee075c',
            }, self._refs.get_packed_refs())

    def test_get_peeled_not_packed(self):
        # not packed
        self.assertEqual(None, self._refs.get_peeled('refs/tags/refs-0.2'))
        self.assertEqual('3ec9c43c84ff242e3ef4a9fc5bc111fd780a76a8',
                         self._refs['refs/tags/refs-0.2'])

        # packed, known not peelable
        self.assertEqual(self._refs['refs/heads/packed'],
                         self._refs.get_peeled('refs/heads/packed'))

        # packed, peeled
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                         self._refs.get_peeled('refs/tags/refs-0.1'))

    def test_keys(self):
        self.assertEqual([
            'HEAD',
            'refs/heads/loop',
            'refs/heads/master',
            'refs/heads/packed',
            'refs/tags/refs-0.1',
            'refs/tags/refs-0.2',
            ], sorted(list(self._refs.keys())))
        self.assertEqual(['loop', 'master', 'packed'],
                         sorted(self._refs.keys('refs/heads')))
        self.assertEqual(['refs-0.1', 'refs-0.2'],
                         sorted(self._refs.keys('refs/tags')))

    def test_as_dict(self):
        # refs/heads/loop does not show up
        self.assertEqual({
            'HEAD': '42d06bd4b77fed026b154d16493e5deab78f02ec',
            'refs/heads/master': '42d06bd4b77fed026b154d16493e5deab78f02ec',
            'refs/heads/packed': '42d06bd4b77fed026b154d16493e5deab78f02ec',
            'refs/tags/refs-0.1': 'df6800012397fb85c56e7418dd4eb9405dee075c',
            'refs/tags/refs-0.2': '3ec9c43c84ff242e3ef4a9fc5bc111fd780a76a8',
            }, self._refs.as_dict())

    def test_setitem(self):
        self._refs['refs/some/ref'] = '42d06bd4b77fed026b154d16493e5deab78f02ec'
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                         self._refs['refs/some/ref'])
        f = open(os.path.join(self._refs.path, 'refs', 'some', 'ref'), 'rb')
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                          f.read()[:40])
        f.close()

    def test_setitem_symbolic(self):
        ones = '1' * 40
        self._refs['HEAD'] = ones
        self.assertEqual(ones, self._refs['HEAD'])

        # ensure HEAD was not modified
        f = open(os.path.join(self._refs.path, 'HEAD'), 'rb')
        self.assertEqual('ref: refs/heads/master', iter(f).next().rstrip('\n'))
        f.close()

        # ensure the symbolic link was written through
        f = open(os.path.join(self._refs.path, 'refs', 'heads', 'master'), 'rb')
        self.assertEqual(ones, f.read()[:40])
        f.close()

    def test_set_if_equals(self):
        nines = '9' * 40
        self.assertFalse(self._refs.set_if_equals('HEAD', 'c0ffee', nines))
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                         self._refs['HEAD'])

        self.assertTrue(self._refs.set_if_equals(
            'HEAD', '42d06bd4b77fed026b154d16493e5deab78f02ec', nines))
        self.assertEqual(nines, self._refs['HEAD'])

        # ensure symref was followed
        self.assertEqual(nines, self._refs['refs/heads/master'])

        self.assertFalse(os.path.exists(
            os.path.join(self._refs.path, 'refs', 'heads', 'master.lock')))
        self.assertFalse(os.path.exists(
            os.path.join(self._refs.path, 'HEAD.lock')))

    def test_add_if_new(self):
        nines = '9' * 40
        self.assertFalse(self._refs.add_if_new('refs/heads/master', nines))
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                         self._refs['refs/heads/master'])

        self.assertTrue(self._refs.add_if_new('refs/some/ref', nines))
        self.assertEqual(nines, self._refs['refs/some/ref'])

        # don't overwrite packed ref
        self.assertFalse(self._refs.add_if_new('refs/tags/refs-0.1', nines))
        self.assertEqual('df6800012397fb85c56e7418dd4eb9405dee075c',
                         self._refs['refs/tags/refs-0.1'])

    def test_check_refname(self):
        try:
            self._refs._check_refname('HEAD')
        except KeyError:
            self.fail()

        try:
            self._refs._check_refname('refs/heads/foo')
        except KeyError:
            self.fail()

        self.assertRaises(KeyError, self._refs._check_refname, 'refs')
        self.assertRaises(KeyError, self._refs._check_refname, 'notrefs/foo')

    def test_follow(self):
        self.assertEquals(
            ('refs/heads/master', '42d06bd4b77fed026b154d16493e5deab78f02ec'),
            self._refs._follow('HEAD'))
        self.assertEquals(
            ('refs/heads/master', '42d06bd4b77fed026b154d16493e5deab78f02ec'),
            self._refs._follow('refs/heads/master'))
        self.assertRaises(KeyError, self._refs._follow, 'notrefs/foo')
        self.assertRaises(KeyError, self._refs._follow, 'refs/heads/loop')

    def test_contains(self):
        self.assertTrue('refs/heads/master' in self._refs)
        self.assertFalse('refs/heads/bar' in self._refs)

    def test_delitem(self):
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                          self._refs['refs/heads/master'])
        del self._refs['refs/heads/master']
        self.assertRaises(KeyError, lambda: self._refs['refs/heads/master'])
        ref_file = os.path.join(self._refs.path, 'refs', 'heads', 'master')
        self.assertFalse(os.path.exists(ref_file))
        self.assertFalse('refs/heads/master' in self._refs.get_packed_refs())

    def test_delitem_symbolic(self):
        self.assertEqual('ref: refs/heads/master',
                          self._refs.read_loose_ref('HEAD'))
        del self._refs['HEAD']
        self.assertRaises(KeyError, lambda: self._refs['HEAD'])
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                         self._refs['refs/heads/master'])
        self.assertFalse(os.path.exists(os.path.join(self._refs.path, 'HEAD')))

    def test_remove_if_equals(self):
        nines = '9' * 40
        self.assertFalse(self._refs.remove_if_equals('HEAD', 'c0ffee'))
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                         self._refs['HEAD'])

        # HEAD is a symref, so shouldn't equal its dereferenced value
        self.assertFalse(self._refs.remove_if_equals(
            'HEAD', '42d06bd4b77fed026b154d16493e5deab78f02ec'))
        self.assertTrue(self._refs.remove_if_equals(
            'refs/heads/master', '42d06bd4b77fed026b154d16493e5deab78f02ec'))
        self.assertRaises(KeyError, lambda: self._refs['refs/heads/master'])

        # HEAD is now a broken symref
        self.assertRaises(KeyError, lambda: self._refs['HEAD'])
        self.assertEqual('ref: refs/heads/master',
                          self._refs.read_loose_ref('HEAD'))

        self.assertFalse(os.path.exists(
            os.path.join(self._refs.path, 'refs', 'heads', 'master.lock')))
        self.assertFalse(os.path.exists(
            os.path.join(self._refs.path, 'HEAD.lock')))

        # test removing ref that is only packed
        self.assertEqual('df6800012397fb85c56e7418dd4eb9405dee075c',
                         self._refs['refs/tags/refs-0.1'])
        self.assertTrue(
            self._refs.remove_if_equals('refs/tags/refs-0.1',
            'df6800012397fb85c56e7418dd4eb9405dee075c'))
        self.assertRaises(KeyError, lambda: self._refs['refs/tags/refs-0.1'])
