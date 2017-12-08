import asyncio
import json

import discord
from . import webreq
import websockets

class AudioTrack:
    def __init__(self, track, identifier, can_seek, author, duration, stream, title, uri):
        self.track = track
        self.identifier = identifier
        self.can_seek = can_seek
        self.author = author
        self.duration = duration
        self.stream = stream
        self.title = title
        self.uri = uri

class Player:
    def __init__(self, client, guild_id):
        self.client = client
        self.guild_id = guild_id
        self.channel_id = None

        self.is_connected = lambda: self.channel_id is not None
        self.is_playing = lambda: self.current is not None

        self.state = None
        
        self.queue = []
        self.current = None

    async def connect(self, channel_id):
        payload = {
            'op': 'connect',
            'guildId': str(self.guild_id),
            'channelId': str(channel_id)
        }
        await self.client.send(payload)
        self.channel_id = str(channel_id)

    async def add(self, track, play=False):
        await self._build_track(track)

        if play_immediately and not self.is_playing():
            await self.play()

    async def play(self):
        if not self.is_connected() or self.is_playing() or not self.queue:
            return

        track = self.queue.pop(0)

        payload = {
            'op': 'play',
            'guildId': str(self.guild_id),
            'track': track.track
        }
        await self.client.send(payload)
        self.current = track
        
    async def on_track_end(self):
        self.current = None
        await self.play()

    async def _build_track(self, track):
        try:
            a = track.get('track')
            info = track.get('info')
            b = info.get('identifier')
            c = info.get('isSeekable')
            d = info.get('author')
            e = info.get('length')
            f = info.get('isStream')
            g = info.get('title')
            h = info.get('uri')
            t = AudioTrack(a, b, c, d, e, f, g, h)
            self.queue.append(t)
        except KeyError:
            return # Raise invalid track passed


class Client:
    def __init__(self, bot, shard_count, user_id, password='', host='localhost', port=80, loop=asyncio.get_event_loop()):
        self.bot = bot
        self.loop = loop
        self.shard_count = shard_count
        self.user_id = user_id
        self.password = password
        self.host = host
        self.port = port
        self.uri = f'ws://{host}:{port}'

        loop.create_task(self.connect())

        self._dispatchers = {
            'track_end': []
        }
    
    async def connect(self):
        headers = {
            'Authorization': self.password,
            'Num-Shards': self.shard_count,
            'User-Id': self.user_id
        }
        try:
            self.ws = await websockets.connect(self.uri, extra_headers=headers)
            self.loop.create_task(self.listen())
            print("[WS] Ready")
        except Exception as e:
            raise e from None
    
    async def listen(self):
        while True:
            data = await self.ws.recv()
            j = json.loads(data)

            if 'op' in j:
                if j.get('op') == 'validationReq':
                    await self.validate_connect(j)
                elif j.get('op') == 'isConnectedReq':
                    await self.validate_connection(j)
                elif j.get('op') == 'sendWS':
                    await self.bot._connection._get_websocket(330777295952543744).send(j.get('message'))
                elif j.get('op') == 'event':
                    await self.dispatch_event(j.get('type'))
                #elif j.get('op') == 'playerUpdate':                
    
    async def dispatch_event(self, t):
        if t == 'TrackEndEvent':
            for listener in self._dispatchers['track_end']:
                await listener()

    async def send(self, data):
        payload = json.dumps(data)
        await self.ws.send(payload)

    async def validate_connect(self, data):
        payload = {
            'op': 'validationRes',
            'guildId': '330777295952543744',
            'channelId': '376428145252761610',
            'valid': True
        }
        
        await self.send(payload)

    async def validate_connection(self, data):
        payload = {
            'op': 'isConnectedRes',
            'shardId': 0,
            'connected': True
        }
        await self.send(payload)
    
    async def dispatch_voice_update(self, payload):
        await self.send(payload)

    async def create_player(self, guild_id):
        p = Player(client=self, guild_id=str(guild_id))
        self._dispatchers['track_end'].append(p.on_track_end)
        return p

    async def get_tracks(self, query):
        headers = {
            'Authorization': self.password,
            'Accept': 'application/json'
        }
        return await webreq.get(f'http://{self.host}:2333/loadtracks?identifier={query}', jsonify=True, headers=headers)