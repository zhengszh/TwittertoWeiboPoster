# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'bs4')
sys.path.insert(0, 'pytz')
import time
import os
import urllib
import urllib2
import logging
from TwitterCrawler import TwitterCrawler
from WeiboPoster import WeiboPoster
from StringIO import StringIO
from google.appengine.api import urlfetch
urlfetch.set_default_fetch_deadline(45)

if __name__ == '__main__':
	namelist = ['techmeme']
	crawler = TwitterCrawler(namelist, (8 * 60))
	latestTweets = crawler.getLatestTweets()
	if not len(latestTweets) == 0:
		logging.debug("get some tweets:")
		app_key="Your App Key"
	    app_secret="Your App Secret"
	    redirect_uri="Your Apps Redirect URI"
	    username = "Your Weibo Account"
	    password = "Your Weibo Password"
		wbPoster = WeiboPoster(app_key, app_secret, redirect_uri, username, password)
		for t in latestTweets:
			for k in t:
				logging.debug(k + " : " + str(t[k]))
			logging.debug("-------------------------------\n")
			if 'picture' in t:
				logging.debug("have picture")
				url = t['picture']
				response = urlfetch.fetch(url, method=urlfetch.GET)
				if response.status_code == 200:
					logging.debug("download picture succeed")
					pic_data = response.content
					wbPoster.postWeibo(t['content'], StringIO(pic_data))
					logging.debug("post picture succeed")
				else:
					logging.debug("download picture failed")
			else:
				wbPoster.postWeibo(t['content'], "")
			logging.debug("post succeed")
			time.sleep(45)
	else:
		logging.debug("no tweet in this minute")