# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Unlicense OR CC0-1.0
import logging

import pexpect
import pytest
from dnsfixture import DnsPythonWrapper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
ipv6_enabled = False


class MdnsConsole:
    def __init__(self, command):
        self.process = pexpect.spawn(command, encoding='utf-8')
        self.process.logfile = open('mdns_interaction.log', 'w')  # Log all interactions
        self.process.expect('mdns> ', timeout=10)

    def send_input(self, input_data):
        logger.info(f'Sending to stdin: {input_data}')
        self.process.sendline(input_data)

    def get_output(self, expected_data):
        logger.info(f'Expecting: {expected_data}')
        self.process.expect(expected_data, timeout=10)
        output = self.process.before.strip()
        logger.info(f'Received from stdout: {output}')
        return output

    def terminate(self):
        self.send_input('exit')
        self.get_output('Exit')
        self.process.wait()
        self.process.close()
        assert self.process.exitstatus == 0


@pytest.fixture(scope='module')
def mdns_console():
    app = MdnsConsole('./build_linux_console/mdns_host.elf')
    yield app
    app.terminate()


@pytest.fixture(scope='module')
def dig_app():
    return DnsPythonWrapper()


def test_mdns_init(mdns_console, dig_app):
    mdns_console.send_input('mdns_init -h hostname')
    mdns_console.get_output('MDNS: Hostname: hostname')
    dig_app.check_record('hostname.local', query_type='A', expected=True)
    if ipv6_enabled:
        dig_app.check_record('hostname.local', query_type='AAAA', expected=True)


def test_add_service(mdns_console, dig_app):
    mdns_console.send_input('mdns_service_add _http _tcp 80 -i test_service')
    mdns_console.get_output('MDNS: Service Instance: test_service')
    dig_app.check_record('_http._tcp.local', query_type='PTR', expected=True)


def test_remove_service(mdns_console, dig_app):
    mdns_console.send_input('mdns_service_remove _http _tcp')
    dig_app.check_record('_http._tcp.local', query_type='PTR', expected=False)


if __name__ == '__main__':
    pytest.main(['-s', 'test_mdns.py'])
