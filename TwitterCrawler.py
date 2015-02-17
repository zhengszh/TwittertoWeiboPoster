# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'bs4')
sys.path.insert(0, 'pytz')
import urllib2
import urllib
import os, sys
import time, datetime
import re
import json
import HTMLParser
import logging
from cgi import escape
from sgmllib import SGMLParser
from bs4 import BeautifulSoup
from pytz.gae import pytz
from google.appengine.api import urlfetch

def convertSinaLink(link):
	html_parser = HTMLParser.HTMLParser()
	url = "http://api.t.sina.com.cn/short_url/shorten.json"
	data = {
		"source" : "Your App Key",
		"url_long" : link
	}
	data = urllib.urlencode(data)
	req = urllib2.Request(url, data)
	response = urllib2.urlopen(req)
	content = response.read()
	content = json.loads(content)
	if len(content) > 0:
		if 'url_short' in content[0]:
			return content[0]['url_short']
	logging.debug("unable to get short link from sina" + str(content))
	return link

class TwitterCrawler:
	"""docstring for TwitterCrawler"""
	def __init__(self, accounts, timeInterval):
		self.accounts = accounts
		self.timeInterval = timeInterval
		# set proxy for test inside GFW
		# proxies = {'http': '127.0.0.1:8087', "https" : "https://127.0.0.1:8087"}
		# proxy_support = urllib2.ProxyHandler(proxies)
		# opener = urllib2.build_opener(proxy_support, urllib2.HTTPHandler)
		# urllib2.install_opener(opener)

	# get the html content of the main page of given user
	def getPageContent(self, username):
		viewHeader = {
			"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
			"Referer": "http://google.com"
		}
		req = urllib2.Request('https://twitter.com/' + username, headers=viewHeader)
		content = urllib2.urlopen(req).read()
		return content

	# deal with tag('#') in the tweet, convert it into the "#xxx#" format in Weibo
	def dealWithTags(self, tweet):
		tagPattern = re.compile(r'<a class="twitter-hashtag pretty-link js-nav".+?><s>#</s><b>(.+?)</b></a>')
		match = tagPattern.search(tweet)
		while not match == None:
			tagHtml = match.group(0)
			tag = "#" + match.group(1) + "#"
			tweet = tweet.replace(tagHtml, tag)
			match = tagPattern.search(tweet)
		return tweet

	# eliminate picture link in the tweet
	def dealWithPics(self, tweet):
		picPagePattern = re.compile(r'<a class="twitter-timeline-link u-hidden".+?>pic.twitter.com/.+?</a>')
		match = picPagePattern.search(tweet)
		if not match == None:
			picHtml = match.group(0)
			tweet = tweet.replace(picHtml, "")
		return tweet

	# convert the html of a link into a simple link string
	def dealWithLinks(self, tweet):
		linkPattern = re.compile(r'<a class="twitter-timeline-link.*?".+?data-expanded-url="(.+?)".+?>.+?<\/a>')
		match = linkPattern.search(tweet)
		while not match == None:
			linkHtml = match.group(0)
			link = match.group(1)
			link = str(convertSinaLink(link))
			tweet = tweet.replace(linkHtml, link)
			match = linkPattern.search(tweet)
		return tweet

	# convert the html of an '@' into a simple '@' string
	def dealWithAt(self, tweet):
		atPattern = re.compile(r'<a class="twitter-atreply pretty-link".+?><s>@</s><b>(.+?)</b></a>')
		match = atPattern.search(tweet)
		while not match == None:
			atHtml = match.group(0)
			atStr = "@" + match.group(1)
			tweet = tweet.replace(atHtml, atStr)
			match = atPattern.search(tweet)
		return tweet

	# filter unrelevant html content
	def tweetContentOperation(self, tweet):
		tweet = self.dealWithPics(self.dealWithTags(self.dealWithAt(self.dealWithLinks(tweet))))
		html_parser = HTMLParser.HTMLParser()
		tweet = html_parser.unescape(tweet)
		tweet = tweet.replace("\n", " ")
		return tweet

	# get all tweets from the html of a given main page
	def getAllTweets(self, content):
		soup = BeautifulSoup(content)
		# get the main body div
		tweetList = soup.findAll('div', attrs={"class":"Grid", "data-component-term":"tweet"})
		returnList = []
		for tweet in tweetList:
			tweet = str(tweet)
			# retrieve main body tweet
			mainPattern = re.compile(r'<p class="ProfileTweet-text js-tweet-text u-dir".+?lang=".+?">([\s\S]+?)<\/p>')
			mainContentMatch = mainPattern.search(tweet)
			tweetContent = mainContentMatch.group(1)

			# retrieve post time
			timePattern = re.compile(r'<a class="ProfileTweet-timestamp js-permalink js-nav js-tooltip"[\n ]+?href="/.+?/status/[0-9]+?".+?title="(.+?)"+?>')
			timeContentMatch = timePattern.search(tweet)
			tweetTime = timeContentMatch.group(1)
			digest = {"content": tweetContent, "time": tweetTime}
			picturePattern = re.compile(r'<img.+?class="TwitterPhoto-mediaSource".+?src="(https://pbs.twimg.com/.+?)"')
			pictureMatch = picturePattern.search(tweet)
			if not pictureMatch == None:
				pictureUrls = picturePattern.findall(tweet)
				for i, pic in enumerate(pictureUrls):
					pictureUrls[i] = pic.replace(":large", "")
				digest['picture'] = pictureUrls[0]

			retweetSign = '<span class="Icon Icon--retweeted Icon--small"></span>'
			if retweetSign in tweet:
				retOriginPattern = re.compile(r'<div.+?data-retweet-id=".+?".+?data-screen-name="(.+?)".+?>')
				retweetOrigin = retOriginPattern.search(tweet).group(1)
				# add explanation of a retweet
				digest['content'] = "From@" + retweetOrigin + ": " + digest['content'] 

			returnList.append(digest)

		# format
		# content: the main text of the tweet
		# time: the post time in GST form
		# (picture: url of the first picture)
		logging.debug("main page size " + str(len(returnList)))
		return list(reversed(returnList))

	# get the latest tweet from a list of tweets
	def filterLatestTweets(self, tweetList):
		# Current time in UTC
		nowUTC = datetime.datetime.now(pytz.timezone('UTC'))
		# Convert to US/Pacific time zone
		nowPacific = nowUTC.astimezone(pytz.timezone('US/Pacific'))
		nowPacific = nowPacific.replace(tzinfo=None)
		latest = []
		for tweet in tweetList:
			postTime = time.strptime(tweet['time'], '%I:%M %p - %d %b %Y')
			postTime = datetime.datetime(*postTime[0:6])
			logging.debug(str(postTime))
			logging.debug(nowPacific)
			# if a recent tweet
			if (nowPacific - postTime).total_seconds() <= self.timeInterval:
				tweet['content'] = self.tweetContentOperation(tweet['content'])
				latest.append(tweet)
		logging.debug("latest number " + str(len(latest)))
		return latest

	def getLatestTweets(self):
		tweets = []
		# for all account, get all tweet in the main page
		for acc in self.accounts:
			accList = self.getAllTweets(self.getPageContent(acc))
			tweets += accList
		# get the recent tweets
		tweets = self.filterLatestTweets(tweets)
		return tweets