import cmd
import time
import datetime
import re


class InteractiveMode(cmd.Cmd):
    """Interactive Mode"""

    def __init__(self, udp):
        super().__init__()
        self.connection = udp

        # Get Endpoint Info
        ep = self.connection.read_endpoint_info(0)
        self.intro = "Welcome to " + ep['deviceName'] + " Module " + str(ep['deviceId'])
        self.current_gid = 1
        self.path = "/"
        self.prompt = ep['deviceName'] + "@" + self.connection.peer_name[0] + ":" + self.path + "$ "
        self.endpoint = ep
        self.group = []
        self.var = []
        self.tree = []
        self.tree.append({'groups': dict(), 'vars': dict()})

        # Build Group Info
        print("Building Group List")
        for n in range(self.endpoint['numGroups']):
            group = self.connection.read_group_info(n + 1, 0)
            self.group.append(group)
            self.tree.append({'groups': dict(), 'vars': dict()})

        # Build Var Info
        print("Building Variable List")
        for n in range(self.endpoint['numVars']):
            var = self.connection.read_var_info(n + 1, 0)
            self.var.append(var)

        for group in self.group:
            self.tree[group['pid']]['groups'][group['key']] = group['gid']

        for var in self.var:
            self.tree[var['gid']]['vars'][var['key']] = var['vid']

        for group in self.group:
            print(group)

    def emptyline(self):
        """Overrides default of passing in previous command on empty line"""
        pass

    def do_timeout(self, line):
        """Purpose: Adjust request timeout length\nUsage: timeout <seconds>\nExample: timeout 0.5\n"""
        line_args = str.split(line, ' ')
        if(line_args[0] != ''):
            self.timeout = float(line_args[0])
        print("Timeout period is " + str(self.timeout))

    def print_esper_error(self, err_json):
        print("Error %d: %s (%d)" % (
            err_json['error']['status'], err_json['error']['meaning'], err_json['error']['code']))

    def do_uptime(self, line):
        """Purpose: Get uptime of current ESPER service\nUsage: uptime\n"""
        ep = self.connection.read_endpoint_info(0)

        # Make a nice uptime string
        s = datetime.timedelta(seconds=(ep['uptime'])).total_seconds()
        (days, remainder) = divmod(s, (3600 * 24))
        (hours, remainder) = divmod(s, 3600)
        (minutes, seconds) = divmod(remainder, 60)
        if(int(days) > 0):
            str_uptime = '{:03}d {:02}h {:02}m {:02}s'.format(int(days), int(hours), int(minutes), int(seconds))
        else:
            str_uptime = '{:02}h {:02}m {:02}s'.format(int(hours), int(minutes), int(seconds))

        # Get start time
        str_starttime = datetime.datetime.fromtimestamp((time.time() - ep['uptime'])).strftime('%Y-%m-%d %H:%M:%S')
        print("Uptime is " + str_uptime + ". Started " + str_starttime)

    def get_gid_from_path(self, path):
        if(path[0] == '/'):
            gid = 1
        else:
            gid = self.current_gid

        for key in re.split("/", path):
            # Attempt to find key in current path            
            if key in self.tree[gid]['groups']:
                gid = self.tree[gid]['groups'][key]
            elif key == '..':
                gid = self.group[gid - 1]['pid']

        return gid

    def get_path_from_gid(self, gid):
        path = ""
        while(gid != 1):
            path = self.group[gid - 1]['key'] + "/" + path
            gid = self.group[gid - 1]['pid']

        return "/" + path

    def complete_cd(self, content, line, begidx, endidx):
        result = []
        # Work out 'bottom' level path GID
        gid = self.get_gid_from_path(line[3:].strip())
        if(gid == 0):
            gid = self.current_gid

        for key, value in self.tree[gid]['groups'].items():
            if key.startswith(content):
                result.append(key + "/")

        if(len(result) == 0):
            for key, value in self.tree[gid]['groups'].items():
                result.append(key + "/")

        return result

    def do_cd(self, line):
        """Purpose: Sets current module\nUsage: cd <path>\n"""
        gid = self.get_gid_from_path(line.strip())
        if(gid != 0):
            self.path = self.get_path_from_gid(gid)
            self.current_gid = gid
            self.prompt = self.endpoint['deviceName'] + "@" + self.connection.peer_name[0] + ":" + self.path + "$ "

    def complete_ls(self, content, line, begidx, endidx):
        result = []
        # Work out 'bottom' level path GID
        gid = self.get_gid_from_path(line[3:].strip())
        if(gid == 0):
            gid = self.current_gid

        for key, value in self.tree[gid]['groups'].items():
            if key.startswith(content):
                result.append(key + "/")

        for key, value in self.tree[gid]['vars'].items():
            if key.startswith(content):
                result.append(key)

        if(len(result) == 0):
            for key, value in self.tree[gid]['groups'].items():
                result.append(key + "/")

            for key, value in self.tree[gid]['vars'].items():
                result.append(key)

        return result

    def do_ls(self, line):
        result = []
        """Purpose: Read module variable(s)\nUsage: ls <path>\n"""
        if(len(line.strip()) == 0):
            for key, value in self.tree[self.current_gid]['groups'].items():
                result.append(key + "/")

            for key, value in self.tree[self.current_gid]['vars'].items():
                result.append(key)

            # Pretty print results
            for item in result:
                print(item)

            print("")

        else:
            print("")

    def do_exit(self, line):
        """Purpose: Quit esper-tool\nUsage: exit\n"""
        return True

    def do_quit(self, line):
        """Purpose: Quit esper-tool\nUsage: quit\n"""
        return True
