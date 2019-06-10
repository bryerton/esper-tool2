import socket
import time
import struct
import zlib
import ipaddress
import random
from array import array

UDP_VERSION = 0

VAR_TYPE_UNKNOWN = 0
VAR_TYPE_NULL = 1
VAR_TYPE_ASCII = 2
VAR_TYPE_BOOL = 3
VAR_TYPE_UINT8 = 4
VAR_TYPE_UINT16 = 5
VAR_TYPE_UINT32 = 6
VAR_TYPE_UINT64 = 7
VAR_TYPE_INT8 = 8
VAR_TYPE_INT16 = 9
VAR_TYPE_INT32 = 10
VAR_TYPE_INT64 = 11
VAR_TYPE_FLOAT32 = 12
VAR_TYPE_FLOAT64 = 13


def EsperGetTypeSize(type):
    if(type == VAR_TYPE_UNKNOWN):
        return 0
    if(type == VAR_TYPE_NULL):
        return 0
    if(type == VAR_TYPE_ASCII):
        return 1
    if(type == VAR_TYPE_BOOL):
        return 1
    if(type == VAR_TYPE_UINT8):
        return 1
    if(type == VAR_TYPE_UINT16):
        return 2
    if(type == VAR_TYPE_UINT32):
        return 4
    if(type == VAR_TYPE_UINT64):
        return 8
    if(type == VAR_TYPE_INT8):
        return 1
    if(type == VAR_TYPE_INT16):
        return 2
    if(type == VAR_TYPE_INT32):
        return 4
    if(type == VAR_TYPE_INT64):
        return 8
    if(type == VAR_TYPE_FLOAT32):
        return 4
    if(type == VAR_TYPE_FLOAT64):
        return 8

    return 0

def send_discovery(deviceId, deviceName, deviceType, deviceRev, hardwareId, authToken, timeout=3, verbose=False):
    """Send a discovery packet and gather responses"""
    msg = __build_discovery_request(
        deviceId,
        deviceName,
        deviceType,
        deviceRev,
        hardwareId,
        authToken
    )
    if(verbose):
        print("Searching for devices listening on port " + str(27500) + "...")
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    client.sendto(msg.generate_msg(), ('<broadcast>', 27500))
    # Wait for response(s)
    timeout = timeout
    timeout_start = time.time()
    timeout_end = timeout_start + timeout
    response_list = []
    while time.time() < timeout_end:
        time_left = timeout_end - time.time()
        if(time_left <= 0):
            time_left = 0.01
        client.settimeout(time_left)
        try:
            data, server = client.recvfrom(1500)
            # Convert the response into an ESPER response object
            rep = EsperUDP.Response(data)
            if(rep is not None):
                discover_rep = __parse_discovery_response(rep.payload)
                if(discover_rep is not None):
                    response_list.append(discover_rep)
                    if(verbose):
                        print("Found " + discover_rep['name'] + " Rev." + discover_rep['revision'] + " Module " + str(discover_rep['device_id']) + " at " + (str(discover_rep['ipv4']) + ':' + str(discover_rep['port'])))
                else:
                    # TODO: Parse Error object that must have been returned instead
                    pass
        except socket.timeout:
            # This is expected to occur, eventually all devices will have responded
            pass

    client.close()
    return response_list


def __parse_discovery_response(data):
    """Receive Response, and parse it back into a python dict"""
    try:
        response = dict()
        unpacked_data = struct.unpack("<128s64s64s32sIII16xH", data)
        response['hardware_id'] = unpacked_data[0].decode("ascii").rstrip(' \t\r\n\0')
        response['type'] = unpacked_data[1].decode("ascii").rstrip(' \t\r\n\0')
        response['name'] = unpacked_data[2].decode("ascii").rstrip(' \t\r\n\0')
        response['revision'] = unpacked_data[3].decode("ascii").rstrip(' \t\r\n\0')
        response['device_id'] = unpacked_data[4]
        response['uptime'] = unpacked_data[5]
        response['ipv4'] = str(ipaddress.ip_address(unpacked_data[6]))
        # Reserved spot for IPv6 (128 bits)
        response['port'] = unpacked_data[7]
        return response
    except struct.error:
        return None

    return response


def __build_discovery_request(deviceId=None, deviceName="", deviceType="", deviceRev="", hardwareId="", authToken=0):
    """Build a discovery request packet to be sent, that looks for device(s) that match the given filter values"""
    if hardwareId != "":
        use_hardware_id = 0xff
    else:
        use_hardware_id = 0x00

    if deviceType != "":
        use_device_type = 0xff
    else:
        use_device_type = 0x00

    if deviceRev != "":
        use_device_rev = 0xff
    else:
        use_device_rev = 0x00

    if deviceName != "":
        use_device_name = 0xff
    else:
        use_device_name = 0x00

    if deviceId is not None:
        use_device_id = 0xff
        deviceId = int(deviceId)
    else:
        use_device_id = 0x00
        deviceId = int(0)

    request_payload = struct.pack(
        "<BBBBB3xI64sx64sx32sx128sx",
        use_device_id,
        use_device_type,
        use_device_name,
        use_device_rev,
        use_hardware_id,
        deviceId,
        deviceType.encode("ascii"),
        deviceName.encode("ascii"),
        deviceRev.encode("ascii"),
        hardwareId.encode("ascii"))

    return EsperUDP.Request(random.randint(0, 65535), EsperUDP.MSG_TYPE_DISCOVER, 0, request_payload, authToken)


class EsperUDP:
    """ESPER UDP Protocol"""

    ESPER_UDP_VERSION = 0
    ESPER_UDP_DEFAULT_PORT = 27500
    # Message Types
    MSG_TYPE_DISCOVER = 0x0
    MSG_TYPE_PING = 0x1
    MSG_TYPE_VAR_READ = 0x10
    MSG_TYPE_VAR_WRITE = 0x11
    MSG_TYPE_VAR_PATH = 0x12
    MSG_TYPE_VAR_INFO = 0x13
    MSG_TYPE_GROUP_INFO = 0x14
    MSG_TYPE_GROUP_PATH = 0x15
    MSG_TYPE_ENDPOINT_INFO = 0x16
    MSG_TYPE_ERROR = 0xFF

    # Error Codes
    ERR_INTERNAL = -1
    ERR_RUNT_MSG = -2
    ERR_BAD_HEADER_CRC = -3
    ERR_BAD_VERSION = -4
    ERR_BAD_MSG_TYPE = -5
    ERR_BAD_AUTH_TOKEN = -6
    ERR_BAD_PAYLOAD_LEN = -7
    ERR_BAD_PAYLOAD_CRC = -8
    ERR_MISMATCHED_REQ_REP = -9

    # Message Options
    MSG_OPTION_NO_AUTH_TOKEN = 0x1

    class EsperUDPException(Exception):
        pass

    class EsperUDPTimeout(EsperUDPException):
        pass

    class EsperUDPLinkError(EsperUDPException):
        def __init__(self, error_code):
            self.error_string = {
                1: "Ok (No Response)",
                0: "Ok",
                -1: "Internal Error",
                -2: "Out of Range",
                -3: "validation Failed",
                -4: "User Func Validation Failed",
                -5: "Resource Locked",
                -6: "Resource is Read-Only",
                -7: "Resource is Write-Only",
                -8: "Resource Id Not Found",
                -9: "Wrong Var Type",
                -10: "Insufficient Buffer Size",
                -11: "Exceeded Max Elements for Resource",

                -64: "Internal",
                -65: "Runt Message",
                -66: "Bad Header CRC",
                -67: "Bad UDP Version",
                -68: "Bad Message Type",
                -69: "Bad Auth Token",
                -70: "Bad Payload Len",
                -71: "Bad Payload CRC",
                -72: "Mismatched Request/Response",
                -73: "Bad Response Length"
            }

            self.error_code = error_code

        def __str__(self):
            if self.error_code in self.error_string:
                return self.error_string[self.error_code]
            else:
                return "Unknown"

    class Request:

        def __init__(self, msg_id, msg_type, msg_options, payload, auth_token):
            self.msg_id = msg_id
            self.msg_type = msg_type
            if(auth_token is not None):
                self.msg_options = msg_options
            else:
                self.msg_options = msg_options | EsperUDP.MSG_OPTION_NO_AUTH_TOKEN
            self.payload_len = len(payload)
            self.payload = payload
            self.header_crc = 0
            self.payload_crc = 0
            self.auth_token = auth_token

        def __str__(self):
            return "Message Id: " + str(self.msg_id) + "\nMessage Type: " + str(self.msg_type) + "\nPayload Length: " + str(self.payload_len)

        def generate_msg(self):
            # TODO: Determine if we've gone over the MTU size and throw an exception
            # Create Header bytearray
            header = struct.pack(
                "<BBHII",
                UDP_VERSION,
                self.msg_type,
                self.msg_id,
                self.msg_options,
                self.payload_len
            )

            # Calculate Header CRC
            self.header_crc = zlib.crc32(header) & 0xFFFFFFFF

            # Add CRC to Header bytearray
            header = header + struct.pack("<I", self.header_crc)
            if((self.msg_options & EsperUDP.MSG_OPTION_NO_AUTH_TOKEN) == 0):
                header = header + struct.pack("<Q", self.auth_token)

            # Determine if we need to pad
            payload_rem = self.payload_len % 8
            # Pad payload if necessary
            if(payload_rem != 0):
                payload = self.payload + struct.pack(str(8 - payload_rem) + "x")
            else:
                payload = self.payload

            # Calculate Payload CRC
            self.payload_crc = zlib.crc32(payload) & 0xFFFFFFFF

            # Add CRC to Payload
            payload = payload + struct.pack("<I", self.payload_crc)

            # Combine Header and Payload
            msg = header + payload

            return msg

    class Response:
        def __init__(self, data):
            try:
                self.payload = b''
                self.payload_len = 0

                # Unpack Header
                header = struct.unpack_from(
                    "<BBHIII",
                    data,
                    0
                )

                self.udp_version = header[0]
                self.msg_type = header[1]
                self.msg_id = header[2]
                self.payload_len = header[4]
                self.header_crc = header[5]

                self.computed_header_crc = zlib.crc32(data[0:12]) & 0xFFFFFFFF
                if(self.computed_header_crc != self.header_crc):
                    raise EsperUDP.EsperUDPLinkError(EsperUDP.ERR_BAD_HEADER_CRC)

                # Unpack Payload CRC
                payload_crc = struct.unpack_from("<I", data[-4:], 0)
                self.payload_crc = payload_crc[0]

                # Check Payload
                self.computed_payload_crc = zlib.crc32(data[16:-4]) & 0xFFFFFFFF
                if(self.computed_payload_crc != self.payload_crc):
                    raise EsperUDP.EsperUDPLinkError(EsperUDP.ERR_BAD_PAYLOAD_CRC)

                self.payload = data[16:(16) + self.payload_len]

            except struct.error:
                self.msg_id = 0
                self.msg_type = 0
                self.msg_options = 0
                self.header_crc = 0
                self.computed_header_crc = 0
                self.payload_len = 0
                self.payload = b''
                self.payload_crc = 0
                self.computed_payload_crc = 0

        def __repr__(self):
            return { 'msg_id': self.msg_id, 'msg_type': self.msg_type, 'msg_options': self.msg_options, 'payload': self.payload, 'payload_len': self.payload_len }

        def __str__(self):
            return str(self.payload_len)

    def __init__(self, ip, port, timeout=3, auth_token=0):
        self.__client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.__auth_token = auth_token
        self.__connected = False
        self.__msg_id = random.randint(0, 65535)
        self.__server = (ip, port)
        if(timeout is None):
            timeout = 0.01
        self.__client.settimeout(timeout)
        self.__client.connect(self.__server)
        self.peer_name = self.__client.getpeername()

    def set_timeout(self, timeout):
        if(timeout is None):
            timeout = 0.01
        self.__client.settimeout(timeout)

    def connect(self, ):
        """Connect to an ESPER node (verify connection)"""
        pass

    def ping(self, payload):
        request = EsperUDP.Request(
            self.__get_msg_id(),  # Get next message id
            EsperUDP.MSG_TYPE_PING,  # Message Type Ping
            0,  # No Message Options
            payload,  # Empty Payload
            self.__auth_token  # Auth token might be required
        )

        # Send ping
        self.__send_request(request)

        # Get response
        self.__get_response_for_request(request)

        return True


    def get_var_types_available_for_data(self, data):
        """Attempt to determine var_type from dat"""

        # Verify every element in data is the same type
        prev_type = type(data[0])
        for elem in data:
            cur_type = type(elem)
            if(cur_type != prev_type):
                return []
            prev_type = cur_type

        # JSON Null should be converted to None
        if(isinstance(data[0], type(None))):
            return [VAR_TYPE_NULL]

        # Bool is easy
        if(isinstance(data[0], bool)):
            return [VAR_TYPE_BOOL]

        # String isn't hard
        elif(isinstance(data[0], str)):
            return [VAR_TYPE_ASCII]

        # Check float fits inside a 'float' vs 'double' in C
        elif(isinstance(data[0], float)):
            min_val = 0
            max_val = 0
            for elem in data:
                if(elem < min_val):
                    min_val = elem
                if(elem > max_val):
                    max_val = elem

            if((max_val >= 340000000000000000000000000000000000000.0) and (min_val <= -120000000000000000000000000000000000000.0)):
                return [VAR_TYPE_FLOAT64]
            else:
                return [VAR_TYPE_FLOAT32, VAR_TYPE_FLOAT64]

        # Integer, we have to test if any of the numbers are negative
        elif(isinstance(data[0], int)):
            # parse the list and look for a negative number
            is_signed = False
            min_val = 0
            max_val = 0
            for elem in data:
                if(elem < 0):
                    is_signed = True
                if(elem < min_val):
                    min_val = elem
                if(elem > max_val):
                    max_val = elem

            # Determine required integer size and type based on min/max and signage

            # Signed number, can only be represented by float or signed integer
            if(is_signed):
                if(max_val > 2147483647) or (min_val < -2147483648):
                    return [VAR_TYPE_INT64, VAR_TYPE_FLOAT32, VAR_TYPE_FLOAT64]
                if(max_val > 32767) or (min_val < -32768):
                    return [VAR_TYPE_INT32, VAR_TYPE_INT64, VAR_TYPE_FLOAT32, VAR_TYPE_FLOAT64]
                if(max_val > 127) or (min_val < -128):
                    return [VAR_TYPE_INT16, VAR_TYPE_INT32, VAR_TYPE_INT64, VAR_TYPE_FLOAT32, VAR_TYPE_FLOAT64]
                
                return [VAR_TYPE_INT8, VAR_TYPE_INT16, VAR_TYPE_INT32, VAR_TYPE_INT64, VAR_TYPE_FLOAT32, VAR_TYPE_FLOAT64]
            # Unsigned number, only max matters, min = zero
            else:
                if(max_val > 9223372036854775807):
                    return [VAR_TYPE_UINT64, 
                            VAR_TYPE_FLOAT32, VAR_TYPE_FLOAT64]
                if(max_val > 4294967295):
                    return [VAR_TYPE_INT64, 
                            VAR_TYPE_UINT64, 
                            VAR_TYPE_FLOAT32, VAR_TYPE_FLOAT64]
                if(max_val > 2147483647):
                    return [VAR_TYPE_INT64, 
                            VAR_TYPE_UINT32, VAR_TYPE_UINT64, 
                            VAR_TYPE_FLOAT32, VAR_TYPE_FLOAT64]
                if(max_val > 65535):
                    return [VAR_TYPE_INT32, VAR_TYPE_INT64, 
                            VAR_TYPE_UINT32, VAR_TYPE_UINT64, 
                            VAR_TYPE_FLOAT32, VAR_TYPE_FLOAT64]
                if(max_val > 32767):
                    return [VAR_TYPE_INT32, VAR_TYPE_INT64, 
                            VAR_TYPE_UINT16, VAR_TYPE_UINT32, VAR_TYPE_UINT64, 
                            VAR_TYPE_FLOAT32, VAR_TYPE_FLOAT64]
                if(max_val > 255):
                    return [VAR_TYPE_INT16, VAR_TYPE_INT32, VAR_TYPE_INT64, 
                            VAR_TYPE_UINT16, VAR_TYPE_UINT32, VAR_TYPE_UINT64, 
                            VAR_TYPE_FLOAT32, VAR_TYPE_FLOAT64]
                if(max_val > 127):
                    return [VAR_TYPE_INT16, VAR_TYPE_INT32, VAR_TYPE_INT64, 
                            VAR_TYPE_UINT8, VAR_TYPE_UINT16, VAR_TYPE_UINT32, VAR_TYPE_UINT64, 
                            VAR_TYPE_FLOAT32, VAR_TYPE_FLOAT64]

                return [VAR_TYPE_INT8, VAR_TYPE_INT16, VAR_TYPE_INT32, VAR_TYPE_INT64, 
                        VAR_TYPE_UINT8, VAR_TYPE_UINT16, VAR_TYPE_UINT32, VAR_TYPE_UINT64, 
                        VAR_TYPE_FLOAT32, VAR_TYPE_FLOAT64]

        return []


    def write_var(self, vid, offset, num_elements, data, var_type):

        msg_option = 0

        header_payload = struct.pack(
            "<IIIIII",
            1,  # One var to write
            msg_option,  # Relax type matching
            vid,  # Variable Id
            offset,  # Offset of elements to return
            num_elements,  # Number of elements to return
            var_type  # ESPER Variable Type
        )

        # Pack data payload according to decided var_type
        if(var_type == VAR_TYPE_NULL):
            data_payload = b''
        if(var_type == VAR_TYPE_ASCII):
            data_payload = struct.pack("<" + str(num_elements) + "s", data)
        if(var_type == VAR_TYPE_BOOL):
            data_payload = struct.pack("<" + str(num_elements) + "?", *array('B', data))
        if(var_type == VAR_TYPE_UINT8):
            data_payload = struct.pack("<" + str(num_elements) + "B", *array('B', data))
        if(var_type == VAR_TYPE_UINT16):
            data_payload = struct.pack("<" + str(num_elements) + "H", *array('H', data))
        if(var_type == VAR_TYPE_UINT32):
            data_payload = struct.pack("<" + str(num_elements) + "I", *array('I', data))
        if(var_type == VAR_TYPE_UINT64):
            data_payload = struct.pack("<" + str(num_elements) + "Q", *array('Q', data))
        if(var_type == VAR_TYPE_INT8):
            data_payload = struct.pack("<" + str(num_elements) + "b", *array('b', data))
        if(var_type == VAR_TYPE_INT16):
            data_payload = struct.pack("<" + str(num_elements) + "h", *array('h', data))
        if(var_type == VAR_TYPE_INT32):
            data_payload = struct.pack("<" + str(num_elements) + "i", *array('i', data))
        if(var_type == VAR_TYPE_INT64):
            data_payload = struct.pack("<" + str(num_elements) + "q", *array('q', data))
        if(var_type == VAR_TYPE_FLOAT32):
            data_payload = struct.pack("<" + str(num_elements) + "f", *array('f', data))
        if(var_type == VAR_TYPE_FLOAT64):
            data_payload = struct.pack("<" + str(num_elements) + "d", *array('d', data))

        # Determine if we need to pad data payload
        payload_rem = len(data_payload) % 8

        # Pad payload if necessary
        if(payload_rem != 0):
            data_payload = data_payload + struct.pack(str(8 - payload_rem) + "x")

        request = EsperUDP.Request(
            self.__get_msg_id(),
            EsperUDP.MSG_TYPE_VAR_WRITE,
            0,
            header_payload + data_payload,
            self.__auth_token
        )

        self.__send_request(request)

        response = self.__get_response_for_request(request)

        return response

    def read_var(self, vid, offset, num_elements, var_type=0):

        if(var_type == 0):
            msg_option = 0x1
        else:
            msg_option = 0

        payload = struct.pack(
            "<IIIIII",
            1,  # One var requested
            msg_option,  # Ignore var type request (return whatever var is!)
            vid,  # Variable Id
            offset,  # Offset of elements to return
            num_elements,  # Number of elements to return
            var_type  # Type. Set to not care
        )

        request = EsperUDP.Request(
            self.__get_msg_id(),
            EsperUDP.MSG_TYPE_VAR_READ,
            0,
            payload,
            self.__auth_token
        )

        self.__send_request(request)

        response = self.__get_response_for_request(request)

        # Iterate through response
        resp = []
        n = 0
        offset = 0
        while(n == 0):
            section = struct.unpack_from("<IiIHH", response.payload, offset)
            
            vid = section[0]
            err = section[1]
            read_offset = section[2]
            num_elements = section[3]
            var_type = section[4]

            print(len(response.payload))

            data_len = num_elements * EsperGetTypeSize(var_type)
            # TODO: Make this into a read_var class response
            offset = offset + 16
            if(var_type == VAR_TYPE_NULL):
                data = []
            if(var_type == VAR_TYPE_ASCII):
                data = struct.unpack_from("<" + str(num_elements) + "s", response.payload, offset)[0].decode(encoding="ascii").rstrip('\0')
            if(var_type == VAR_TYPE_BOOL):
                data = list(struct.unpack_from("<" + str(num_elements) + "?", response.payload, offset))
            if(var_type == VAR_TYPE_UINT8):
                data = list(struct.unpack_from("<" + str(num_elements) + "B", response.payload, offset))
            if(var_type == VAR_TYPE_UINT16):
                data = list(struct.unpack_from("<" + str(num_elements) + "H", response.payload, offset))
            if(var_type == VAR_TYPE_UINT32):
                data = list(struct.unpack_from("<" + str(num_elements) + "I", response.payload, offset))
            if(var_type == VAR_TYPE_UINT64):
                data = list(struct.unpack_from("<" + str(num_elements) + "Q", response.payload, offset))
            if(var_type == VAR_TYPE_INT8):
                data = list(struct.unpack_from("<" + str(num_elements) + "b", response.payload, offset))
            if(var_type == VAR_TYPE_INT16):
                data = list(struct.unpack_from("<" + str(num_elements) + "h", response.payload, offset))
            if(var_type == VAR_TYPE_INT32):
                data = list(struct.unpack_from("<" + str(num_elements) + "i", response.payload, offset))
            if(var_type == VAR_TYPE_INT64):
                data = list(struct.unpack_from("<" + str(num_elements) + "q", response.payload, offset))
            if(var_type == VAR_TYPE_FLOAT32):
                data = list(struct.unpack_from("<" + str(num_elements) + "f", response.payload, offset))
            if(var_type == VAR_TYPE_FLOAT64):
                data = list(struct.unpack_from("<" + str(num_elements) + "d", response.payload, offset))
            resp.append({
                'id': vid,
                'err': err,
                'offset': read_offset,
                'elements': num_elements,
                'type': var_type,
                'data': data
            })

            offset = offset + data_len
            n = n + 1

        return resp

    def get_var_id(self, path):
        payload = struct.pack(
            "<II" + str(len(path)) + "s",
            len(path.encode()),  # Length of Path
            0,  # No options
            path.encode()
        )

        request = EsperUDP.Request(
            self.__get_msg_id(),
            EsperUDP.MSG_TYPE_VAR_PATH,
            0,
            payload,
            self.__auth_token
        )

        self.__send_request(request)

        response = self.__get_response_for_request(request)

        vid = struct.unpack_from("<I", response.payload, 0)

        return vid[0]

    def get_group_id(self, path):
        payload = struct.pack(
            "<II" + str(len(path)) + "s",
            len(path.encode()),  # Length of Path
            0,  # No options
            path.encode()
        )

        request = EsperUDP.Request(
            self.__get_msg_id(),
            EsperUDP.MSG_TYPE_GROUP_PATH,
            0,
            payload,
            self.__auth_token
        )

        self.__send_request(request)

        response = self.__get_response_for_request(request)

        gid = struct.unpack_from("<I", response.payload, 0)

        return gid[0]

    def read_var_info(self, vid, options):
        payload = struct.pack(
            "<II",
            vid,
            options
        )

        request = EsperUDP.Request(
            self.__get_msg_id(),
            EsperUDP.MSG_TYPE_VAR_INFO,
            0,
            payload,
            self.__auth_token
        )

        self.__send_request(request)

        response = self.__get_response_for_request(request)

        info = struct.unpack_from("<II32sIIIIIBB", response.payload, 0)

        var = {
            'vid': int(info[0]),
            'gid': int(info[1]),
            'key': info[2].decode(encoding="ascii").rstrip('\0'),
            'ts': int(info[3]),
            'wc': int(info[4]),
            'type': int(info[5]),
            'numElements': int(info[6]),
            'maxElementsPerRequest': int(info[7]),
            'option': int(info[8]),
            'status': int(info[9]),
        }

        return var

    def read_group_info(self, gid, options):
        payload = struct.pack(
            "<II",
            gid,
            options
        )

        request = EsperUDP.Request(
            self.__get_msg_id(),
            EsperUDP.MSG_TYPE_GROUP_INFO,
            0,
            payload,
            self.__auth_token
        )

        self.__send_request(request)

        response = self.__get_response_for_request(request)

        info = struct.unpack_from("<II32sIIIIBB", response.payload, 0)

        group = {
            'gid': int(info[0]),
            'pid': int(info[1]),  # Parent Group Id
            'key': info[2].decode(encoding="ascii").rstrip('\0'),
            'numVars': int(info[3]),
            'numGroups': int(info[4]),
            'ts': int(info[5]),
            'wc': int(info[6]),
            'option': int(info[7]),
            'status': int(info[8])
        }

        return group

    def read_endpoint_info(self, options):
        payload = struct.pack(
            "<I",
            options
        )

        request = EsperUDP.Request(
            self.__get_msg_id(),
            EsperUDP.MSG_TYPE_ENDPOINT_INFO,
            0,
            payload,
            self.__auth_token
        )

        self.__send_request(request)

        response = self.__get_response_for_request(request)

        info = struct.unpack_from("<128s64s64s32sIIIiiIIIIIIB", response.payload, 0)

        endpoint = {
            'hardwareId': info[0].decode(encoding="ascii").rstrip('\0'),
            'deviceType': info[1].decode(encoding="ascii").rstrip('\0'),
            'deviceName': info[2].decode(encoding="ascii").rstrip('\0'),
            'deviceRev': info[3].decode(encoding="ascii").rstrip('\0'),
            'uptime': int(info[4]),
            'tickCount': int(info[5]),
            'deviceId': int(info[6]),
            'logLevel': int(info[7]),
            'alarmLevel': int(info[8]),
            'logId': int(info[9]),
            'numModules': int(info[10]),
            'numVars': int(info[11]),
            'numStorableVars': int(info[12]),
            'numGroups': int(info[13]),
            'numAlarms': int(info[14]),
            'api_version': int(info[15])
        }

        return endpoint

    def __verify_response(self, request, response):
        if(request.msg_id != response.msg_id):
            return None

        if(response.msg_type == EsperUDP.MSG_TYPE_ERROR):
            raise EsperUDP.EsperUDPLinkError(struct.unpack("<i", response.payload)[0])

        if(request.msg_type != response.msg_type):
            raise EsperUDP.EsperUDPLinkError(EsperUDP.ERR_BAD_MSG_TYPE)

        return response

    def __send_request(self, request):
        self.__client.send(request.generate_msg(), 0)

    def __get_response_for_request(self, request):
        # Wait for response(s)
        retry = 0
        while(retry < 3):
            try:
                data, server = self.__client.recvfrom(1500)
            except socket.timeout:
                raise EsperUDP.EsperUDPTimeout()
            
            # Check response is not None (mismatched msg id)
            resp = self.__verify_response(request, EsperUDP.Response(data))
            if(resp != None):
                return resp

            # Message was None, aka 'not the message we were waiting for'
            # Try again
            retry = retry + 1

        raise EsperUDP.EsperUDPTimeout()

    def __wait_for_msgs(self, num_msg_expected=1):
        # Wait for response(s)
        timeout_start = time.time()
        timeout_end = timeout_start + self.__timeout
        response_list = []
        keep_waiting = True
        while keep_waiting:
            time_left = timeout_end - time.time()
            if(time_left <= 0):
                time_left = 0.01
            self.__client.settimeout(time_left)
            try:
                data, server = self.__client.recvfrom(1500)
                if(data is not None):
                    response_list.append(data)
            except socket.timeout:
                # This is expected to occur, eventually all devices will have responded
                pass

            if(time.time() >= timeout_end) or (len(response_list) == num_msg_expected):
                keep_waiting = False

        return response_list

    def __get_msg_id(self):
        """Get a new message id"""
        self.__msg_id = self.__msg_id + 1
        return self.__msg_id
