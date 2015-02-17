# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'bs4')
sys.path.insert(0, 'pytz')
import urllib2
import urllib
import httplib
import time
import json
import logging
from cgi import escape
import os
import re
from weibo import APIClient, APIError


class WeiboPoster:
    def __init__(self, app_key, app_secret, redirect_uri, username, password):
        self.app_key = app_key
        self.app_secret = app_secret
        self.username = username
        self.password = password
        self.redirect_uri = redirect_uri
        self.client = self.getAuth()

    # get the code to push a Weibo
    # url: the url to be redirect when OAuth
    def get_code(self, url):
        conn = httplib.HTTPSConnection('api.weibo.com')
        params = urllib.urlencode({
            'action': 'submit',
            'withOfficalFlag': '0',
            'ticket': '',
            'isLoginSina': 0,  
            'response_type': 'code',
            'regCallback': '',
            'redirect_uri': self.redirect_uri,
            'client_id': self.app_key,
            'state': '',
            'from': '',
            'userId': self.username,
            'passwd': self.password
        })  
        conn.request('POST','/oauth2/authorize', params, {'Referer': url, 'Content-Type': 'application/x-www-form-urlencoded'})
        res = conn.getresponse()
        for line in res.msg.headers:
            if re.search('Location', line):
                return line.strip().split('=')[1]
        conn.close()

    # get the Authenticate client
    def getAuth(self):
        client = APIClient(app_key=self.app_key, app_secret=self.app_secret, redirect_uri=self.redirect_uri)
        # get the authenticate page url
        url = client.get_authorize_url()
        # retrieve the authenticate code automatically
        code = self.get_code(url)
        # get access token via the code
        r = client.request_access_token(code)
        access_token = r.access_token
        expires_in = r.expires_in
        # set token to the client
        client.set_access_token(access_token, expires_in)
        return client

    # text: the message content to be post
    # picFile: the picture file stream
    def postWeibo(self, text, picFile=""):
        utext = escape(text)
        # utext = unicode(text, "UTF-8")
        if not picFile == "":
            self.client.statuses.upload.post(status=utext, pic=picFile)
        else:
            self.client.statuses.update.post(status=utext)

# test only
if __name__ == '__main__':
    app_key="Your App Key"
    app_secret="Your App Secret"
    redirect_uri="Your Apps Redirect URI"
    username = "Your Weibo Account"
    password = "Your Weibo Password"
    wbPoster = WeiboPoster(app_key, app_secret, redirect_uri, username, password)
    wbPoster.postWeibo(text="text")

