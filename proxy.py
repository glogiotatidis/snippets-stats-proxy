#!/usr/bin/env python
import asyncio
import urllib
import uuid

import aiohttp
from aiohttp import web

import config

async def send_to_ga(data):
    hittype = 'pageview'
    params = {
        'v': 1,
        'tid': config.GOOGLE_ANALYTICS_ID,
        'dh': config.GOOGLE_ANALYTICS_DOMAIN,
        't': hittype,
        'ds': 'about:home',
        'cid': uuid.uuid4().hex,
        'ul': data.get('locale', ''),
        'geoid': data.get('country', ''),
        'ua': data.get('agent', ''),
        'dt': 'Snippet {}'.format(data.get('snippet_id')),
        'dp': '/show/{}/'.format(data.get('snippet_id')),
    }
    try:
        await aiohttp.get(config.GOOGLE_ANALYTICS_URL, params=params)
        config.statsd.incr('process_request.ga')
    except (ConnectionRefusedError, aiohttp.errors.ClientError):
        config.statsd.incr('process_request.ga.exception')


def webserver():
    loop = asyncio.get_event_loop()

    def webhook(request):
        data = {
            'agent': request.headers['USER-AGENT'],
        }
        data.update(urllib.parse.parse_qsl(request.query_string))
        if config.GOOGLE_ANALYTICS_URL and config.GOOGLE_ANALYTICS_ID:
            loop.create_task(send_to_ga(data))
        config.statsd.incr('view.webhook')

        if config.MOZILLA_ANALYTICS_URL:
            return aiohttp.web.HTTPFound(
                '{}?{}'.format(config.MOZILLA_ANALYTICS_URL, request.query_string))

        return aiohttp.web.Response(body=b'OK', content_type='text/plain')

    app = web.Application()
    app.router.add_route('GET', '/foo', webhook)
    return app

application = webserver()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    srv = loop.create_server(application.make_handler(), '0.0.0.0', config.PORT)
    loop.create_task(srv)
    print("Server started at {}...".format(config.PORT))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
