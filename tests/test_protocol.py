from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest

from backend.bridge import JsonOut


class ProtocolTests(unittest.TestCase):
    def test_json_protocol_uses_original_stream_during_algorithm_stdout_redirect(self) -> None:
        protocol = io.StringIO()
        redirected = io.StringIO()
        original = sys.stdout
        try:
            sys.stdout = protocol
            out = JsonOut()
            with contextlib.redirect_stdout(redirected):
                out.send({"kind": "event", "event": "log", "data": {"text": "hello"}})
        finally:
            sys.stdout = original

        self.assertEqual(redirected.getvalue(), "")
        message = json.loads(protocol.getvalue())
        self.assertEqual(message["event"], "log")
        self.assertEqual(message["data"]["text"], "hello")


if __name__ == "__main__":
    unittest.main()
