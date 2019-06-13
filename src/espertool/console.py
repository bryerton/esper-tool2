import cmd
import time
import datetime
import re
import json
from espertool import esper


class InteractiveMode(cmd.Cmd):
    """Interactive Mode"""

    def __init__(self, udp):
        super().__init__()
        self.connection = udp

        # Get Endpoint Info
        ep = self.connection.read_endpoint_info(0)
        self.ep = ep
        self.intro = "Welcome to " + ep['deviceName'] + " Module " + str(ep['deviceId'])
        self.current_gid = 1
        self.path = "/"
        self.prompt = ep['deviceName'] + "@" + self.connection.peer_name[0] + ":" + self.path + "$ "
        self.endpoint = ep
        self.group = [None]  # First group is None, so gid match up to array indexes
        self.var = [None]  # First var is None, so vid match up to array indexes
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
            if(group is not None):
                self.tree[group['pid']]['groups'][group['key']] = group['gid']

        for var in self.var:
            if(var is not None):
                self.tree[var['gid']]['vars'][var['key']] = var['vid']

    def emptyline(self):
        """Overrides default of passing in previous command on empty line"""
        pass

    def do_endpoint(self, line):
        print(self.ep)

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
        try:
            if(path[0] == '/'):
                gid = 1
            else:
                gid = self.current_gid

            args = re.split(" ", path)

            for key in re.split("/", args[0]):
                # Attempt to find key in current path
                if key in self.tree[gid]['groups']:
                    gid = self.tree[gid]['groups'][key]
                elif key == '..':
                    gid = self.group[gid]['pid']
        except Exception as e:
            gid = 0

        return gid

    def get_vid_from_path(self, path):
        vid = 0
        try:
            if(path[0] == '/'):
                gid = 1
            else:
                gid = self.current_gid

            args = re.split(" ", path)

            for key in re.split("/", args[0]):
                # Attempt to find key in current path
                if key in self.tree[gid]['groups']:
                    gid = self.tree[gid]['groups'][key]
                elif key == '..':
                    gid = self.group[gid]['pid']

                if key in self.tree[gid]['vars']:
                    vid = self.tree[gid]['vars'][key]
        except Exception as e:
            pass

        return vid

    def get_path_from_gid(self, gid):
        path = ""
        while(gid != 1):
            path = self.group[gid]['key'] + "/" + path
            gid = self.group[gid]['pid']

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
        gid = self.get_gid_from_path(line[2:].strip())

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
        """Purpose: List groups and variables\nUsage: ls <path>\n"""
        result_var = []
        result_group = []
        gid = 0
        vid = 0
        if(len(line.strip()) != 0):
            gid = self.get_gid_from_path(line.strip())
            vid = self.get_vid_from_path(line.strip())

        if(gid == 0):
            gid = self.current_gid

        if(vid != 0):
            var = self.var[vid]
            result_var.append([var['key'], var['vid']])
        else:
            for (key, value) in self.tree[gid]['groups'].items():
                result_group.append([key + "/", value])

            for (key, value) in self.tree[gid]['vars'].items():
                result_var.append([key, value])

        if(len(result_group) > 0) or (len(result_var) > 0):
            print('{:<5} {:<32} {:<16} {:<16}'.format("id", "key", "last written", "write count"))
            print('{:<5} {:<32} {:<16} {:<16}'.format("--", "---", "------------", "-----------"))

        if(len(result_group) > 0):
            for item in result_group:
                group = self.group[item[1]]
                print('{:<5} {:<32} {:<16} {:<16}'.format(str(group['gid']), group['key'] + "/", str(group['ts']), str(group['wc'])))

        # Pretty print results
        if(len(result_var) > 0):
            for item in result_var:
                var = self.var[item[1]]
                print('{:<5} {:<32} {:<16} {:<16}'.format(str(var['vid']), var['key'], str(var['ts']), str(var['wc'])))

        print("")

    def complete_read(self, content, line, begidx, endidx):
        result = []
        # Work out 'bottom' level path GID
        gid = self.get_gid_from_path(line[4:].strip())

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

    def do_read(self, line):
        """Purpose: Read Data"""
        result_var = []

        if(len(line.strip()) != 0):
            gid = self.get_gid_from_path(line.strip())
            vid = self.get_vid_from_path(line.strip())

            if(vid != 0):
                var = self.var[vid]
                result_var.append([var['key'], vid])

            else:
                if(gid == 0):
                    gid = self.current_gid

                for (key, value) in self.tree[gid]['vars'].items():
                    result_var.append([key, value])
        else:
            gid = self.current_gid
            for (key, value) in self.tree[gid]['vars'].items():
                result_var.append([key, value])

        if(len(result_var) > 0):
            print('{:<5} {:<32} {:<16}'.format("id", "key", "data"))
            print('{:<5} {:<32} {:<16}'.format("--", "---", "----"))

        for item in result_var:
            var = self.var[item[1]]
            try:
                resp = self.connection.read_var(var['vid'], 0, var['numElements'])
                print('{:<5} {:<32} {:<16}'.format(str(var['vid']), var['key'], str(resp[0]['data'])))
            except self.connection.EsperUDPTimeout:
                print("Timeout reading variable")

    def complete_info(self, content, line, begidx, endidx):
        result = []
        # Work out 'bottom' level path GID
        gid = self.get_gid_from_path(line[4:].strip())

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

    def do_info(self, line):
        """Purpose: List groups and variables\nUsage: ls <path>\n"""
        result_var = []
        result_group = []
        gid = 0
        vid = 0
        if(len(line.strip()) != 0):
            gid = self.get_gid_from_path(line.strip())
            vid = self.get_vid_from_path(line.strip())

        if(vid != 0):
            var = self.var[vid]
            result_var.append([var['key'], var['vid']])
        else:
            if(gid == 0):
                gid = self.current_gid
                for (key, value) in self.tree[gid]['groups'].items():
                    result_group.append([key + "/", value])

                for (key, value) in self.tree[gid]['vars'].items():
                    result_var.append([key, value])
            else:
                key = self.group[gid]['key']
                value = gid
                result_group.append([key + "/", value])

        if(len(result_group) > 0):
            print('{:<5} {:<32} {:<8} {:<8} {:<8} {:<8} {:<8} {:<16} {:<16}'.format("id", "key", "type", "vars", "groups", "option", "status", "last written", "write count"))
            print('{:<5} {:<32} {:<8} {:<8} {:<8} {:<8} {:<8} {:<16} {:<16}'.format("--", "---", "----", "----", "------", "------", "------", "------------", "-----------"))
            for item in result_group:
                group = self.group[item[1]]
                id = group['gid']
                key = group['key'] + "/"
                ts = group['ts']
                wc = group['wc']
                opt = ""
                type_str = "group"
                num_elem = group['numVars']
                max_req = group['numGroups']

                # Hidden
                if(group['option'] & 0x4):
                    opt += "H"
                else:
                    opt += "-"

                stat = ""
                # Temporarily Locked?
                if(group['status'] & 0x1):
                    stat += "T"
                else:
                    stat += "-"

                print('{:<5} {:<32} {:<8} {:<8} {:<8} {:<8} {:<8} {:<16} {:<16}'.format(str(id), key, type_str, str(num_elem), str(max_req), opt, stat, str(ts), str(wc)))
            print("")

        # Pretty print results
        if(len(result_var) > 0):
            print('{:<5} {:<32} {:<8} {:<8} {:<8} {:<8} {:<8} {:<16} {:<16}'.format("id", "key", "type", "elements", "request", "option", "status", "last written", "write count"))
            print('{:<5} {:<32} {:<8} {:<8} {:<8} {:<8} {:<8} {:<16} {:<16}'.format("--", "---", "----", "--------", "-------", "------", "------", "------------", "-----------"))
            for item in result_var:
                var = self.var[item[1]]
                id = var['vid']
                key = var['key']
                ts = var['ts']
                wc = var['wc']
                opt = ""

                type_str = esper.EsperGetTypeString(var['type'])
                num_elem = var['numElements']
                max_req = var['maxElementsPerRequest']

                # Read
                if(var['option'] & 0x1):
                    opt += "R"
                else:
                    opt += "-"

                # Write
                if(var['option'] & 0x2):
                    opt += "W"
                else:
                    opt += "-"

                # Hidden
                if(var['option'] & 0x4):
                    opt += "H"
                else:
                    opt += "-"

                # Storable
                if(var['option'] & 0x8):
                    opt += "S"
                else:
                    opt += "-"

                # Lockable
                if(var['option'] & 0x10):
                    opt += "T"
                else:
                    opt += "-"

                # Window
                if(var['option'] & 0x20):
                    opt += "W"
                else:
                    opt += "-"

                stat = ""
                # Temporarily Locked?
                if(var['status'] & 0x1):
                    stat += "T"
                else:
                    stat += "-"

                # Stored?
                if(var['status'] & 0x2):
                    stat += "S"  # Saved
                else:
                    stat += "U"  # Unsaved

                # Logged?
                if(var['status'] & 0x4):
                    stat += "L"
                else:
                    stat += "-"

                # Validated (checked by validator)
                if(var['status'] & 0x8):
                    stat += "V"
                else:
                    stat += "-"

                print('{:<5} {:<32} {:<8} {:<8} {:<8} {:<8} {:<8} {:<16} {:<16}'.format(str(id), key, type_str, str(num_elem), str(max_req), opt, stat, str(ts), str(wc)))
        print("")

    def complete_write(self, content, line, begidx, endidx):
        result = []
        # Work out 'bottom' level path GID
        gid = self.get_gid_from_path(line[5:].strip())

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

    def do_write(self, line):
        """Purpose: Write Data"""

        if(len(line.strip()) != 0):
            vid = self.get_vid_from_path(line.strip())

            if(vid != 0):
                args = re.split(" ", line.strip())
                # This removes all the blank arguments (ie: double spaces)
                args = [elem for elem in args[1:] if elem]
                num_args = len(args)

                try:
                    if(num_args < 1):
                        print("Missing Data")
                    elif(num_args < 2):
                        var_offset = 0
                        var_data = json.loads(args[0])
                    elif(num_args < 4):
                        var_offset = args[0]
                        var_data = json.loads(args[1])
                except json.decoder.JSONDecodeError:
                    print('Malformed JSON Data')
                    return

                var = self.var[vid]

                # Write data to variable
                try:
                    resp = self.connection.write_var(var['vid'], var_offset, len(var_data), var_data, var['type'])
                except self.connection.EsperUDPTimeout:
                    print("Timeout reading variable")

                # Readback variable written to
                print('{:<5} {:<32} {:<16}'.format("id", "key", "data"))
                print('{:<5} {:<32} {:<16}'.format("--", "---", "----"))
                try:
                    resp = self.connection.read_var(var['vid'], 0, var['numElements'])
                    print('{:<5} {:<32} {:<16}'.format(str(var['vid']), var['key'], str(resp[0]['data'])))
                except self.connection.EsperUDPTimeout:
                    print("Timeout reading variable")

    def do_exit(self, line):
        """Purpose: Quit esper-tool\nUsage: exit\n"""
        return True

    def do_quit(self, line):
        """Purpose: Quit esper-tool\nUsage: quit\n"""
        return True
