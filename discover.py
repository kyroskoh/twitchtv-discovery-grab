'''Given username, find other usernames and videos'''
import requests
import re
import gzip
import json
import sys
import time
from urllib import urlencode


API_BASE = 'https://api.twitch.tv/kraken'
FOLLOWS_URL = API_BASE + '/channels/{0}/follows'
FOLLOWING_URL = API_BASE + '/users/{0}/follows/channels'
VIDEOS_URL = API_BASE + '/channels/{0}/videos'
VIEWS_LOWER_LIMIT = 100
default_headers = {'User-Agent': 'ArchiveTeam'}


def main():
    username = sys.argv[1]
    output_filename = sys.argv[2]

    users, videos = fetch(username)

    gzip_file = gzip.open(output_filename, 'w')

    for user in users:
        gzip_file.write('user:{0}\n'.format(user))
    for video in videos:
        gzip_file.write('flv:{0}\n'.format(video))

    gzip_file.close()


def twitch_iter(url, params, key, func, cond=lambda x: True):
    data = set()
    retries = 0

    url = url + '?' + urlencode(params)
    while True:
        print('Get', url)
        response = requests.get(url, headers=default_headers)
        print(response.status_code)

        if response.status_code == 200:
            doc = response.json()
            if doc[key]:
                data.update(func(x) for x in doc[key] if cond(x))
                url = doc['_links']['next']
                time.sleep(0.5)  # play nice
                continue
        else:
            retries += 1
            if retries >= 3:
                raise Exception('URL {0} failed {1} times'
                                .format(url, retries))
            continue

        return data


def fetch(username):
    users = set()
    videos = set()

    # user discovery: who follows this user
    users.update(twitch_iter(FOLLOWS_URL.format(username),
                             {'limit': '100'}, 'follows',
                             lambda x: x['user']['name']))
    # user discovery: who does this user follow
    users.update(twitch_iter(FOLLOWING_URL.format(username),
                             {'limit': '100'}, 'follows',
                             lambda x: x['channel']['name']))
    # video discovery: highlights
    videos.update(twitch_iter(VIDEOS_URL.format(username),
                              {'limit': '100'},
                              'videos', lambda x: x['_id'],
                              lambda x: x['views'] >= VIEWS_LOWER_LIMIT))
    # video discovery: past broadcasts
    videos.update(twitch_iter(VIDEOS_URL.format(username),
                              {'limit': '100', 'broadcasts': 'true'},
                              'videos', lambda x: x['_id'],
                              lambda x: x['views'] >= VIEWS_LOWER_LIMIT))

    return (users, videos)


if __name__ == '__main__':
    main()
