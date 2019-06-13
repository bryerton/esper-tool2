from espertool import cli


def test_parse_url():
    assert(cli.parse_url("192.168.1.1") == (None, "192.168.1.1", cli.esper.udp.EsperUDP.ESPER_UDP_DEFAULT_PORT))
    assert(cli.parse_url("192.168.1.1", 100) == (None, "192.168.1.1", 100))
    assert(cli.parse_url("0xff@192.168.1.1", 100) == (0xff, "192.168.1.1", 100))
    assert(cli.parse_url("0xff@192.168.1.1:101") == (0xff, "192.168.1.1", 101))
