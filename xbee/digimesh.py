"""
digimesh.py

By Matteo Lucchesi, 2011
Inspired by code written by Amit Synderman, Marco Sangalli and Paul Malmsten
matteo@luccalug.it http://matteo.luccalug.it

This module provides an XBee (Digimesh) API library.

Updated by Thom Nichols http://blog.thomnichols.org
"""
# import struct
from xbee.base import XBeeBase


class DigiMesh(XBeeBase):

    """
    Provides an implementation of the XBee API for Digimesh modules
    with recent firmware.

    Commands may be sent to a device by instansiating this class with
    a serial port object (see PySerial) and then calling the send
    method with the proper information specified by the API. Data may
    be read from a device syncronously by calling wait_read_frame. For
    asynchronous reads, see the definition of XBeeBase.
    """
    # Packets which can be sent to an XBee

    # Format:
    #        {name of command:
    #           [{name:field name, len:field length, default: default value sent}
    #            ...
    #            ]
    #         ...
    #         }
    api_commands = {"at":
                    [{'name': 'id',               'len': 1,     'default': '\x08'},
                     {'name': 'frame_id',         'len': 1,     'default': '\x00'},
                     {'name': 'command',          'len': 2,     'default': None},
                     {'name': 'parameter',        'len': None,  'default': None}],
                    "queued_at":
                    [{'name': 'id',               'len': 1,     'default': '\x09'},
                     {'name': 'frame_id',         'len': 1,     'default': '\x00'},
                     {'name': 'command',          'len': 2,     'default': None},
                     {'name': 'parameter',        'len': None,  'default': None}],
                    # explicit adrresing command frame - to do!
                    "remote_at":
                    [{'name': 'id',               'len': 1,     'default': '\x17'},
                     {'name': 'frame_id',         'len': 1,     'default': '\x00'},
                     {'name': 'dest_addr_long',   'len': 8,     'default': None},
                     {'name': 'reserved',         'len': 2,     'default': '\xFF\xFE'},
                     {'name': 'options',          'len': 1,     'default': '\x02'},
                     {'name': 'command',          'len': 2,     'default': None},
                     {'name': 'parameter',        'len': None,  'default': None}],
                    "tx":
                    [{'name': 'id',               'len': 1,     'default': '\x10'},
                     {'name': 'frame_id',         'len': 1,     'default': '\x00'},
                     {'name': 'dest_addr',        'len': 8,     'default': None},
                     {'name': 'reserved',         'len': 2,     'default': '\xFF\xFE'},
                     {'name': 'broadcast_radius', 'len': 1,     'default': '\x00'},
                     {'name': 'options',          'len': 1,     'default': '\x00'},
                     {'name': 'data',             'len': None,  'default': None}],
                    }

    # Packets which can be received from an XBee

    # Format:
    #        {id byte received from XBee:
    #           {name: name of response
    #            structure:
    #                [ {'name': name of field, 'len':length of field}
    #                  ...
    #                  ]
    #            parse_as_io_samples:name of field to parse as io
    #           }
    #           ...
    #        }
    #
    api_responses = {b"\x88":
                     {'name': 'at_response',
                      'structure':
                      [{'name': 'frame_id',    'len': 1},
                       {'name': 'command',     'len': 2},
                       {'name': 'status',      'len': 1},
                       {'name': 'parameter',   'len': None}],
                       'parsing':[('parameter',
                                       lambda self, original: self._parse_FN_at_response(original))]},
                     b"\x8A":
                     {'name': 'status',
                      'structure':
                      [{'name': 'status',      'len': 1}]},
                     b"\x8B":
                     {'name': 'tx_status',
                      'structure':
                      [{'name': 'frame_id',        'len': 1},
                       {'name': 'reserved',        'len': 2, 'default': '\xFF\xFE'},
                       {'name': 'retries',         'len': 1},
                       {'name': 'deliver_status',  'len': 1},
                       {'name': 'discover_status', 'len': 1}]},
                     b"\x90":
                     {'name': 'rx',
                      'structure':
                      [{'name': 'frame_id',    'len': 1},
                       {'name': 'source_addr', 'len': 7},
                       {'name': 'reserved',    'len': 2},
                       {'name': 'options',     'len': 1},
                       {'name': 'data',        'len': None}]},
                     # b"\x91": to do!
                     #    {'name':'explicit_rx_indicator',
                     #     'structure':
                     #        [{'name':'source_addr', 'len':2},
                     #         {'name':'rssi',        'len':1},
                     #         {'name':'options',     'len':1},
                     #         {'name':'rf_data',     'len':None}]},
                     # b"\x92": data sample rx indicator {}
                     b"\x95":
                     {'name': 'node_id',
                      'structure':
                      [{'name': 'source_addr_long',  'len': 8},
                       {'name': 'network_addr',      'len': 2},
                       {'name': 'options',           'len': 1},
                       {'name': 'source_addr',       'len': 2},
                       {'name': 'network_addr_long', 'len': 8},
                       {'name': 'node_id',           'len': 'null_terminated'},
                       {'name': 'parent',            'len': 2},
                       {'name': 'unknown',           'len': None}]},

                     b"\x97":
                     {'name': 'remote_at_response',
                      'structure':
                      [{'name': 'frame_id',        'len': 1},
                       {'name': 'source_addr',     'len': 8},
                       {'name': 'reserved',        'len': 2},
                       {'name': 'command',         'len': 2},
                       {'name': 'status',          'len': 1},
                       {'name': 'parameter',       'len': None}]},
                       'parsing':[('parameter',
                                       lambda self, original: self._parse_FN_at_response(original))]
                     }
    def _parse_FN_at_response(self, packet_info):
        """
        If the given packet is a successful AT response for an ND
        command, parse the parameter field.
        """
        if packet_info['id'] in ('at_response', 'at_remote_response') and packet_info['command'].lower() == b'fn' and packet_info['status'] == b'\x00':
            result = {}

            result['source_addr'] = packet_info['parameter'][0:2]
            result['source_addr_long'] = packet_info['parameter'][2:10]

            null_terminator_index = 10
            while packet_info['parameter'][null_terminator_index:null_terminator_index+1] != b'\x00':
                null_terminator_index+=1

            result['node_identifier'] = packet_info['parameter'][10:null_terminator_index]
            result['parent_address'] = packet_info['parameter'][null_terminator_index+1:null_terminator_index+3]
            result['device_type'] = packet_info['parameter'][null_terminator_index+3:null_terminator_index+4]
            result['status'] = packet_info['parameter'][null_terminator_index+4:null_terminator_index+5]
            result['profile_id'] = packet_info['parameter'][null_terminator_index+5:null_terminator_index+7]
            result['manufacturer'] = packet_info['parameter'][null_terminator_index+7:null_terminator_index+9]

            if (len(packet_info['parameter']) - null_terminator_index-9) == 4:
                result['device_type_id'] = packet_info['parameter'][null_terminator_index+9:null_terminator_index+13]
                # hack
                null_terminator_index += 4

            elif (len(packet_info['parameter']) - null_terminator_index-9) == 5:
                result['device_type_id'] = packet_info['parameter'][null_terminator_index+9:null_terminator_index+13]
                result['rssi'] = packet_info['parameter'][null_terminator_index+13:null_terminator_index+14]
                # hack
                null_terminator_index += 5

            if null_terminator_index+9 != len(packet_info['parameter']):
                raise ValueError("Improper ND response length: expected {0}, read {1} bytes".format(len(packet_info['parameter']), null_terminator_index+9))
               
            return result


    def __init__(self, *args, **kwargs):
        # Call the super class constructor to save the serial port
        super(DigiMesh, self).__init__(*args, **kwargs)
