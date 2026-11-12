import os
import tempfile
import unittest
from unittest import mock

from moonraker_obico import janus_config_builder as builder


SERVER_TURN = {
    'server': 'turn.example.com',
    'port': 3478,
    'type': 'tcp',
    'username': '1800000000:printer-3',
    'credential': 'aqQz58G8MRvfAIvzt+aNSAVO9ik=',
}

OBICO_DEFAULT = {
    'server': 'turn.obico.io',
    'port': 80,
    'type': 'tcp',
    'username': 'printer-token',
    'credential': 'printer-token',
}


class JanusTurnSettingsTests(unittest.TestCase):

    def test_server_without_a_relay_gets_obico_relay_with_the_auth_token(self):
        self.assertEqual(builder.janus_turn_settings('printer-token'), OBICO_DEFAULT)
        self.assertEqual(builder.janus_turn_settings('printer-token', {}), OBICO_DEFAULT)

    def test_relay_sent_by_the_server_is_used(self):
        self.assertEqual(builder.janus_turn_settings('printer-token', SERVER_TURN), SERVER_TURN)

    def test_port_and_type_are_optional(self):
        turn = {k: v for k, v in SERVER_TURN.items() if k not in ('port', 'type')}

        settings = builder.janus_turn_settings('printer-token', turn)

        self.assertEqual((settings['port'], settings['type']), (3478, 'udp'))

    def test_unusable_answers_fall_back_to_obico_relay(self):
        unusable = [
            dict(SERVER_TURN, server=''),
            dict(SERVER_TURN, type='sctp'),
            dict(SERVER_TURN, port='not-a-port'),
            dict(SERVER_TURN, port=70000),
            dict(SERVER_TURN, credential='x"\n}\nplugins: {'),   # would break out of the quoted value
            dict(SERVER_TURN, username='back\\slash'),
            {k: v for k, v in SERVER_TURN.items() if k != 'credential'},
            'turn.example.com',
        ]
        for turn in unusable:
            with self.subTest(turn=turn):
                self.assertEqual(builder.janus_turn_settings('printer-token', turn), OBICO_DEFAULT)


class BuildJanusJcfgTests(unittest.TestCase):

    def build(self, turn):
        with tempfile.TemporaryDirectory() as etc_dir, \
                mock.patch.object(builder, 'RUNTIME_JANUS_ETC_DIR', etc_dir), \
                mock.patch.object(builder, 'find_system_janus_paths', return_value=('/usr/bin/janus', '/usr/lib/janus')):
            builder.build_janus_jcfg('printer-token', turn)
            with open(os.path.join(etc_dir, 'janus.jcfg')) as f:
                return f.read()

    def test_nat_section_carries_the_relay_sent_by_the_server(self):
        jcfg = self.build(SERVER_TURN)

        self.assertIn('turn_server = "turn.example.com"', jcfg)
        self.assertIn('turn_port = 3478', jcfg)
        self.assertIn('turn_type = "tcp"', jcfg)
        self.assertIn('turn_user = "1800000000:printer-3"', jcfg)
        self.assertIn('turn_pwd = "aqQz58G8MRvfAIvzt+aNSAVO9ik="', jcfg)
        self.assertNotIn('turn.obico.io', jcfg)

    def test_nat_section_is_unchanged_without_one(self):
        jcfg = self.build(None)

        self.assertIn('turn_server = "turn.obico.io"', jcfg)
        self.assertIn('turn_port = 80', jcfg)
        self.assertIn('turn_user = "printer-token"', jcfg)
        self.assertIn('turn_pwd = "printer-token"', jcfg)


if __name__ == '__main__':
    unittest.main()
