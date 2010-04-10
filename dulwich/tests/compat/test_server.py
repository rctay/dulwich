# test_server.py -- Compatibilty tests for git server.
# Copyright (C) 2010 Google, Inc.
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

"""Compatibilty tests between Dulwich and the cgit server.

Warning: these tests should be fairly stable, but when writing/debugging new
tests, deadlocks may freeze the test process such that it cannot be Ctrl-C'ed.
On *nix, you can kill the tests with Ctrl-Z, "kill %".
"""

import threading

from dulwich.server import (
    DictBackend,
    TCPGitServer,
    )
from dulwich.tests import (
    skip_test,
    )
from server_utils import (
    ServerTests,
    ShutdownServerMixIn,
    )
from utils import (
    CompatTestCase,
    )


if not getattr(TCPGitServer, 'shutdown', None):
    _TCPGitServer = TCPGitServer

    class TCPGitServer(ShutdownServerMixIn, TCPGitServer):
        """Subclass of TCPGitServer that can be shut down."""

        def __init__(self, *args, **kwargs):
            # BaseServer is old-style so we have to call both __init__s
            ShutdownServerMixIn.__init__(self)
            _TCPGitServer.__init__(self, *args, **kwargs)

        serve = ShutdownServerMixIn.serve_forever


class GitServerTestCase(ServerTests, CompatTestCase):
    """Tests for client/server compatibility."""

    protocol = 'git'

    def setUp(self):
        ServerTests.setUp(self)
        CompatTestCase.setUp(self)

    def tearDown(self):
        ServerTests.tearDown(self)
        CompatTestCase.tearDown(self)

    def _start_server(self, repo):
        backend = DictBackend({'/': repo})
        dul_server = TCPGitServer(backend, 'localhost', 0)
        threading.Thread(target=dul_server.serve).start()
        self._server = dul_server
        _, port = self._server.socket.getsockname()
        return port

    def test_push_to_dulwich(self):
        return skip_test('Skipping push test due to known deadlock bug.')
