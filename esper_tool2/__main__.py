from pkg_resources import get_distribution, DistributionNotFound
import sys
import argparse
import time
import datetime
import webbrowser
import socket
import esper.udp
import struct

# Version information is gathered using setup_scm
try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass
except:
    __version__ = "0.0.1"
    pass


def set_default_subparser(self, name, args=None):
    """default subparser selection. Call after setup, just before parse_args()
    name: is the name of the subparser to call by default
    args: if set is the argument list handed to parse_args()

    , tested with 2.7, 3.2, 3.3, 3.4
    it works with 2.6 assuming argparse is installed
    """
    subparser_found = False
    for arg in sys.argv[1:]:
        if arg in ['-h', '--help']:  # global help if no subparser
            break
        if arg in ['--version']:  # global help if no subparser
            break
    else:
        for x in self._subparsers._actions:
            if not isinstance(x, argparse._SubParsersAction):
                continue

            for sp_name in x._name_parser_map.keys():
                if sp_name in sys.argv[1:]:
                    subparser_found = True

        if not subparser_found:
            # insert default in first position, this implies no
            # global options without a sub_parsers specified
            if args is None:
                sys.argv.insert(1, name)
            else:
                args.insert(0, name)


def parse_url(url, default_port=esper.udp.EsperUDP.ESPER_UDP_DEFAULT_PORT, default_auth=None):
    """Utility function to parse ESPER url in the format auth_token@IP:PORT"""

    auth_delimit = url.find('@')
    port_delimit = url.find(':')

    if(auth_delimit != -1):
        auth_token = int(url[0:auth_delimit], 0)
        auth_delimit = auth_delimit + 1
    else:
        auth_token = default_auth
        auth_delimit = None

    if(port_delimit != -1):
        port = int(url[port_delimit + 1:])
    else:
        port = default_port
        port_delimit = None

    ip = url[auth_delimit:port_delimit]

    return (auth_token, ip, port)


def cmd_console(args):
    pass


def cmd_web(args):
    pass


def cmd_read(args):
    (auth_token, ip, port) = parse_url(args.url)
    try:
        udp = esper.udp.EsperUDP(ip, port, int(args.timeout), auth_token)
        # If args.vid can't be converted to an integer, try it as a string
        # Note: This involves an extra UDP request to get the VID of the path
        try:
            args.vid = int(args.vid)
        except ValueError:
            # Attempt to get the variable id of the path from the argument
            data = udp.get_var_id(path=args.vid)
            args.vid = data

        data = udp.read_var(vid=int(args.vid), offset=int(args.offset), num_elements=int(args.length))
        print(data)
    except ConnectionRefusedError:
        print("Connectiong Refused " + ip + ":" + str(port))
    except esper.udp.EsperUDP.EsperUDPLinkError as e:
        print("ESPER Link Error Received: " + str(e))
    except socket.timeout:
        print("Timed out pinging " + ip + ":" + str(port))
    except KeyboardInterrupt:
        pass


def cmd_write(args):
    (auth_token, ip, port) = parse_url(args.url)
    try:
        udp = esper.udp.EsperUDP(ip, port, int(args.timeout), auth_token)
        data = udp.write_var(
            vid=int(args.vid),
            offset=int(args.offset),
            num_elements=int(args.length),
            data=args.data
        )
        print(data)
    except ConnectionRefusedError:
        print("Connectiong Refused " + ip + ":" + str(port))
    except esper.udp.EsperUDP.EsperUDPLinkError as e:
        print("ESPER Link Error Received: " + str(e))
    except socket.timeout:
        print("Timed out pinging " + ip + ":" + str(port))
    except KeyboardInterrupt:
        pass


def cmd_ping(args):
    args.count = int(args.count)
    if(args.count > 1024):
        args.count = 1024

    args.size = int(args.size)
    if(args.size > 65535):
        args.size = 65535

    (auth_token, ip, port) = parse_url(args.url)

    udp = esper.udp.EsperUDP(ip, port, int(args.timeout), auth_token)

    print("Pinging " + str(ip) + ":" + str(port) + " (" + udp.peer_name[0] + ") with " + str(args.size) + " byte payload\n")
    rx_count = 0
    tx_count = 0
    start_time = time.time()
    for n in range(0, args.count):
        tx_time = time.time()
        try:
            tx_count = tx_count + 1
            udp.ping(struct.pack("" + str(args.size) + "x"))
            rx_count = rx_count + 1
        except ConnectionRefusedError:
            print("Connectiong Refused " + ip + ":" + str(port))
            break
        except esper.udp.EsperUDP.EsperUDPLinkError as e:
            print("ESPER Link Error Received: " + str(e))
            break
        except socket.timeout:
            print("Timed out pinging " + ip + ":" + str(port))
        except KeyboardInterrupt:
            break

        rx_time = time.time()
        elapsed_time = rx_time - tx_time
        print("Ping received from " + ip + ":" + str(port) + " count=" + str(tx_count) + " time=" + str.format('{0:.3f}', elapsed_time * 1000) + " ms")
    total_elapsed_time = time.time() - start_time
    if(rx_count > 0):
        loss_percent = 100 - (tx_count / rx_count * 100)
    else:
        loss_percent = 100
    print("\n--- " + str(ip) + " ping statistics ---")
    print(str(args.count) + " packets transmitted, " + str(rx_count) + " received, " + str.format('{0:.1f}', loss_percent) + "% packet loss, time " + str.format('{0:.3f}', total_elapsed_time * 1000) + " ms")


def cmd_discover(args):
    # Verbose is not allowed if JSON argument is passed
    if(args.json):
        args.verbose = False
    else:
        args.verbose = True

    # Send out discover packet
    resp = esper.udp.send_discovery(
        args.id,
        args.name,
        args.type,
        args.rev,
        args.hwid,
        args.auth,
        args.timeout,
        args.verbose
    )

    if(args.json):
        print(resp)
    else:
        # Sort list of responses by name
        resp.sort(key=lambda x: x['name'])
        # Pretty print responses
        print("\n--- Discovered %u device(s)" % len(resp) + " ---")
        for device in resp:

            # Make a nice uptime string
            s = datetime.timedelta(seconds=(device['uptime'])).total_seconds()
            (days, remainder) = divmod(s, (3600 * 24))
            (hours, remainder) = divmod(s, 3600)
            (minutes, seconds) = divmod(remainder, 60)
            str_uptime = '{:03}d {:02}h {:02}m {:02}s'.format(int(days), int(hours), int(minutes), int(seconds))

            # Pretty print the found device
            print("%s Rev.%s Module %s\n\tIP: %s \n\tHardware Id: %s\n\tStarted %s (%s)\n" % (
                device['name'],
                device['revision'],
                device['device_id'],
                (str(device['ipv4']) + ':' + str(device['port'])),
                device['hardware_id'],
                datetime.datetime.fromtimestamp((time.time() - device['uptime'])).strftime('%Y-%m-%d %H:%M:%S'),
                str_uptime)
            )


def main():
    prog = 'esper-tool2'

    argparse.ArgumentParser.set_default_subparser = set_default_subparser

    parser = argparse.ArgumentParser(prog=prog)

    # Verbose, because sometimes you want feedback
    parser.add_argument('-v', '--verbose', help="Verbose output", default=False, action='store_true')
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)

    # Sub parser
    subparsers = parser.add_subparsers(title='commands', dest='command', description='Available Commands', help='', metavar='Type ' + prog + ' [command] -h to see additional options')

    # Console Mode
    parser_console = subparsers.add_parser('console', help='<auth@<protocol://ip:port>')
    parser_console.add_argument("-t", "--timeout", default=3, help="Request Timeout in Seconds")
    parser_console.set_defaults(func=cmd_console)

    # Web Mode
    parser_web = subparsers.add_parser('web', help='')
    parser_web.add_argument("url", help="<auth@<protocol://ip:port>")
    parser_web.set_defaults(func=cmd_web)

    # Direct Write Variable Command

    # Direct Read Variable Command
    parser_read = subparsers.add_parser('read', help='')
    parser_read.add_argument("url", help="<auth@protocol://ip:port>")
    parser_read.add_argument("vid", help="id or path")
    parser_read.add_argument("offset", default=0, help="offset")
    parser_read.add_argument("length", default=1, help="length")
    parser_read.add_argument("-t", "--timeout", default=3, help="Request Timeout in Seconds")
    parser_read.set_defaults(func=cmd_read)

    # Direct File Upload (multiple write calls)

    # Direct File Download (multiple read calls)

    # Ping Request (alive)
    parser_ping = subparsers.add_parser('ping', help='<auth@<protocol://ip:port>')
    parser_ping.add_argument("url", help="")
    parser_ping.add_argument("-s", "--size", default=64, help="Number of bytes to send")
    parser_ping.add_argument("-c", "--count", default=1, help="Count")
    parser_ping.add_argument("-t", "--timeout", default=3, help="Request Timeout in Seconds")
    parser_ping.set_defaults(func=cmd_ping)

    # Discovery arguments
    parser_discover = subparsers.add_parser('discover', help='')
    parser_discover.add_argument("-t", "--timeout", default=3, help="Request Timeout in Seconds")
    parser_discover.add_argument("-v", "--verbose", default=False, help="Verbose response for debugging", action='store_true')
    parser_discover.add_argument("-j", "--json", default=False, help="Output JSON object", action='store_true')
    parser_discover.add_argument("-a", "--auth", default=0, help="Auth Token")
    parser_discover.add_argument("--name", default="", help="Device name to search for")
    parser_discover.add_argument("--type", default="", help="Device type to search for")
    parser_discover.add_argument("--rev", default="", help="Device revision to search for")
    parser_discover.add_argument("--id", default=None, help="Device id to search for")
    parser_discover.add_argument("--hwid", default="", help="Hardware id to search for")
    parser_discover.set_defaults(func=cmd_discover)
    # Set default subparser to console, so console will be run if no subcommand is given
    parser.set_default_subparser('console')

    # Put the arguments passed into args
    args = parser.parse_args()

    # Call handler for argument
    args.func(args)
    sys.exit(0)


if __name__ == "__main__":
    main()
