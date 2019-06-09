import esper_tool2


def test_parse_url():
    assert(esper_tool2.main.parse_url("192.168.1.1") == (None, "192.168.1.1", esper_tool2.esper.udp.EsperUDP.ESPER_UDP_DEFAULT_PORT))
    assert(esper_tool2.main.parse_url("192.168.1.1", 100) == (None, "192.168.1.1", 100))
    assert(esper_tool2.main.parse_url("0xff@192.168.1.1", 100) == (0xff, "192.168.1.1", 100))
    assert(esper_tool2.main.parse_url("0xff@192.168.1.1:101") == (0xff, "192.168.1.1", 101))
