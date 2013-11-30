# -*- coding: utf-8 -*-
import re
from time import sleep
from module.utils import html_unescape
from module.plugins.internal.SimpleHoster import SimpleHoster
from module.common.json_layer import json_loads
from module.plugins.ReCaptcha import ReCaptcha
from module.network.RequestFactory import getURL
from module.utils import parseFileSize
from module.plugins.Plugin import chunks

def getID(url):
    """ returns id from file url"""
    m = re.match(CloudzerNet.__pattern__, url)
    return m.group('ID')

def getAPIData(urls):
    post = {"apikey": CloudzerNet.API_KEY}

    idMap = {}

    for i, url in enumerate(urls):
        id = getID(url)
        post["id_%s" % i] = id
        idMap[id] = url

    for i in xrange(5):
        api = unicode(getURL("http://cloudzer.net/api/filemultiple", get=post), 'iso-8859-1')
        if api != "":
            break
        else:
            sleep(3)

    result = {}

    if api:
        for line in api.splitlines():
            data = line.split(",", 4)
            if data[1] in idMap:
                result[data[1]] = (data[0], data[2], data[4], data[3], idMap[data[1]]) #result[ID] = (on/off, size, name, hashed???, idMap[ID] = url

    return result

def getInfo(urls):
    for chunk in chunks(urls, 80):
        result = []

        api = getAPIData(chunk)

        for data in api.itervalues():
            if data[0] == "online":
                result.append((html_unescape(data[2]), data[1], 2, data[4])) #name, size, on, url

            elif data[0] == "offline":
                result.append((data[4], 0, 1, data[4])) #name = url, size, on, url

        yield result

class CloudzerNet(SimpleHoster):
    __name__ = "CloudzerNet"
    __type__ = "hoster"
    __pattern__ = r"http://(www\.)?(cloudzer\.net/file/|clz\.to/(file/)?)(?P<ID>\w+).*"
    __version__ = "0.03"
    __description__ = """Cloudzer.net hoster plugin"""
    __author_name__ = ("gs", "z00nx", "stickell")
    __author_mail__ = ("I-_-I-_-I@web.de", "z00nx0@gmail.com", "l.stickell@yahoo.it")

    FILE_SIZE_PATTERN = '<span class="size">(?P<S>[^<]+)</span>'
    WAIT_PATTERN = '<meta name="wait" content="(\d+)">'
    FILE_OFFLINE_PATTERN = r'Please check the URL for typing errors, respectively'
    CAPTCHA_KEY = '6Lcqz78SAAAAAPgsTYF3UlGf2QFQCNuPMenuyHF3'
    API_KEY = 'mai1EN4Zieghey1QueGie7fei4eeh5ne'


    def handleFree(self):
        found = re.search(self.WAIT_PATTERN, self.html)
        seconds = int(found.group(1))
        self.logDebug("Found wait", seconds)
        self.setWait(seconds + 1)
        self.wait()
        response = self.load('http://cloudzer.net/io/ticket/slot/%s' % self.file_info['ID'], post=' ', cookies=True)
        self.logDebug("Download slot request response", response)
        response = json_loads(response)
        if response["succ"] is not True:
            self.fail("Unable to get a download slot")

        recaptcha = ReCaptcha(self)
        challenge, response = recaptcha.challenge(self.CAPTCHA_KEY)
        post_data = {"recaptcha_challenge_field": challenge, "recaptcha_response_field": response}
        response = json_loads(self.load('http://cloudzer.net/io/ticket/captcha/%s' % self.file_info['ID'], post=post_data, cookies=True))
        self.logDebug("Captcha check response", response)
        self.logDebug("First check")

        if "err" in response:
            if response["err"] == "captcha":
                self.logDebug("Wrong captcha")
                self.invalidCaptcha()
                self.retry()
            elif "Sie haben die max" in response["err"] or "You have reached the max" in response["err"]:
                self.logDebug("Download limit reached, waiting an hour")
                self.setWait(3600, True)
                self.wait()
        if "type" in response:
            if response["type"] == "download":
                url = response["url"]
                self.logDebug("Download link", url)
                self.download(url, disposition=True)
