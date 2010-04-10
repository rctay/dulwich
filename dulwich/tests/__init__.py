# __init__.py -- The tests for dulwich
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

"""Tests for Dulwich."""

import unittest

"""
XXX: Ideally we should allow other test runners as well,
but unfortunately unittest doesn't have a SkipTest/TestSkipped
exception.

Users of this function should NOT assume it raises an exception; instead, use
'return' to break execution.
"""
def skip_test(reason):
    try:
        from nose import SkipTest
        raise SkipTest(reason)
    except ImportError:
        pass

def test_suite():
    names = [
        'client',
        'file',
        'index',
        'lru_cache',
        'objects',
        'object_store',
        'pack',
        'protocol',
        'repository',
        'server',
        'web',
        ]
    module_names = ['dulwich.tests.test_' + name for name in names]
    result = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(module_names)
    result.addTests(suite)
    return result
