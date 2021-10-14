# import asyncio
# from discord import Embed
# import aiohttp
# from os import getenv
#
#
# YT_API_KEY = getenv('YTapi')
#
# query = 'asdf'
#
# f'https://youtube.googleapis.com/youtube/v3/search?part=snippet&q={query}&key={YT_API_KEY}'
# data = response.json()
#
# next_page = data.get('nextPageToken', None)
# prev_page = data.get('prevPageToken', None)
#
# for item in data['items']:
#     etag = item['etag']
#
#     item_type = item['id']['kind']
#
#     item_id = item['id'].values()[1]
#
#     snippet = item['snippet']
#
#     published = snippet['publishedAt']
#     channel_id = snippet['channelId']
#     title = snippet['title']
#     description = snippet['description']
#     thumbnail = snippet['thumbnails'].values()[-1]['url']
#     channel_title = snippet['channelTitle']
#     live_status = snippet['liveBroadcastContent']
#
#     channel_url = f'https://www.youtube.com/channel/{channel_id}'
#
#     video_url = f'https://www.youtube.com/watch?v={item_id}'
#     playlist_url = f'https://www.youtube.com/playlist?v=&list={item_id}'
