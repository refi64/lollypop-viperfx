#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


class ImageFetcher:
    """
        Init fetcher
    """
    def __init__(self):
        
        

    """
        Get urls on google image corresponding to search
        @param search words as string
        @return [urls as string]
    """
    def get_urls(self, search):
        try:
            response = urllib.request.urlopen("https://ajax.googleapis.com/"
                                              "ajax/services/search/images"
                                              "?&q=%s&v=1.0&start=0&rsz=8" %
                                              urllib.parse.quote(search))
        except Exception as e:
            print(e)
            return None

        data = response.read()
        decode = json.loads(data.decode("utf-8"))
        urls = []
        if not decode:
            return None
        for item in decode['responseData']['results']:
            urls.append(item['url'])

        return urls
