# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import os
from uuid import uuid4
from tornado import gen
from tornado.options import define, options
from tornado.escape import json_encode, json_decode, url_escape
from tornado.websocket import websocket_connect
from tornado.ioloop import IOLoop
from tornado.httpclient import AsyncHTTPClient

@gen.coroutine
def main():
    kg_host = os.getenv('GATEWAY_HOST', '192.168.99.100:8888')

    client = AsyncHTTPClient()
    kernel_id = options.kernel_id
    
    if not kernel_id:
        print('Creating kernel')
        response = yield client.fetch(
            'http://{}/api/kernels'.format(kg_host),
            method='POST',
            body='{}'
        )
        print('Created kernel')
        kernel = json_decode(response.body)
        kernel_id = kernel['id']
        
    print('Connecting to kernel:', kernel_id)

    ws_url = 'ws://{}/api/kernels/{}/channels'.format(
        kg_host,
        url_escape(kernel_id)
    )
    ws = yield websocket_connect(ws_url)
    print('Connected to kernel', kernel_id)

    # Send an execute request
    msg_id = str(uuid4())
    ws.write_message(json_encode({
        'header': {
            'username': '',
            'version': '5.0',
            'session': '',
            'msg_id': msg_id,
            'msg_type': 'execute_request'
        },
        'parent_header': {},
        'channel': 'shell',
        'content': {
            'code': 'import datetime\nprint(datetime.datetime.utcnow())',
            'silent': False,
            'store_history': False,
            'user_expressions' : {}
        },
        'metadata': {},
        'buffers': {}
    }))

    # Look for stream output for the print in the execute
    while 1:
        msg = yield ws.read_message()
        msg = json_decode(msg)
        msg_type = msg['msg_type']
        print('Received message type:', msg_type)
        parent_msg_id = msg['parent_header']['msg_id']
        if msg_type == 'stream' and parent_msg_id == msg_id:
            print('  Content:', msg['content']['text'])
            break

    ws.close()

if __name__ == '__main__':
    define('kernel_id', default=None, help='Existing kernel ID to connect to')
    options.parse_command_line()
    IOLoop.current().run_sync(main)
