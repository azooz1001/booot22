import pyppeteer
import asyncio
import json

html = ""


async def screenshotHelper(filename):
    global html
    browser = await pyppeteer.launch({
        "headless": True,
        "handleSIGINT": False,
        "handleSIGTERM": False,
        "handleSIGHUP": False,
    })
    page = await browser.newPage()
    await page.setViewport({
        "width": 1100,
        "height": 780,
        "deviceScaleFactor": 1.0,
    })

    await page.setContent(html)
    await page.waitForSelector(".loaded")
    await page.screenshot({
        "type": "jpeg",
        "quality": 100,
        "clip": {
            "x": 0,
            "y": 0,
            "width": 1100,
            "height": 780
        },
        "path": filename,
    })
    await browser.close()


def screenshot(filename):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(screenshotHelper(filename))
    loop.close()


def init():
    global html
    with open("mock.html", "r", encoding="utf8") as file:
        html = file.read()

    with open("config.json", "r", encoding="utf8") as file:
        data = json.load(file)
        setPrimaryColor(data["primaryColor"])
        setBackgroundColor(data["backgroundColor"])
        setFont(data["font"])


def setPrimaryColor(color):
    replace("primary-color", "--primary-color: %s;" % color)


def setBackgroundColor(color):
    replace("background-color", "--background-color: %s;" % color)


def setFont(font):
    replace("font", "font-family: '%s', sans-serif;" % font)


def setProfileImage(url):
    replace("pfpurl", url)


def setQuote(quote):
    replace("text", quote)


def setAuthor(name):
    replace("displayname", name)


def setHandle(handle):
    replace("handle", handle)


def replace(placeholder, text):
    global html
    placeholder = placeholder.upper()
    html = html.replace("%%%s%%" % placeholder, text)

