import os
import re
import requests
import random

from nonebot import on_command, CommandSession, MessageSegment, NoneBot
from nonebot.exceptions import CQHttpError

from hoshino import R, Service, Privilege
from hoshino.util import FreqLimiter, DailyNumberLimiter

_max = 5
EXCEED_NOTICE = f'您今天已经冲过{_max}次了，请明早5点后再来！'
_nlmt = DailyNumberLimiter(_max)
_r18lmt = DailyNumberLimiter(1)
_flmt = FreqLimiter(5)

sv = Service('setu', manage_priv=Privilege.SUPERUSER, enable_on_default=True, visible=False)
setu_folder = R.img('setu/').path


def setu_gener():
    while True:
        filelist = os.listdir(setu_folder)
        random.shuffle(filelist)
        for filename in filelist:
            if os.path.isfile(os.path.join(setu_folder, filename)):
                yield R.img('setu/', filename)


setu_gener = setu_gener()


def get_setu():
    return setu_gener.__next__()


@sv.on_rex(re.compile(r'^不够[涩瑟色]|^[涩瑟色]图|来一?[点份张][涩瑟色]图|再来[点份张]|看过了|铜'), normalize=True)
async def random_setu(bot: NoneBot, ctx, match):
    keyword = ""
    flag = False
    print("on random_setu")
    await online_setu(ctx, keyword, flag, bot)


@sv.on_rex(re.compile(r'^来[点份张][^劲爆]+[涩瑟色]图'), normalize=True)
async def keyword_setu(bot: NoneBot, ctx, match):
    keyword = ctx["message"][0]["data"]["text"][2:-2]
    flag = False
    print(keyword)
    print("on keyword_setu")
    await online_setu(ctx, keyword, flag, bot)


@sv.on_rex(re.compile(r'^劲爆[涩瑟色]图|来一?[点份张]劲爆[涩瑟色]图'), normalize=True)
async def r18_random_setu(bot: NoneBot, ctx, match):
    if not _r18lmt.check(ctx['user_id']):
        await bot.send(ctx, '您今天已经冲过够劲的了', at_sender=True)
        return
    keyword = ""
    flag = True
    print("on r18_random_setu")
    if ctx['user_id'] not in bot.config.SUPERUSERS:
        _r18lmt.increase(ctx['user_id'])
    await online_setu(ctx, keyword, flag, bot)


@sv.on_rex(re.compile(r'^来[点份张]劲爆.+[涩瑟色]图'), normalize=True)
async def r18_keyword_setu(bot: NoneBot, ctx, match):
    if not _r18lmt.check(ctx['user_id']):
        await bot.send(ctx, '您今天已经冲过够劲的了', at_sender=True)
        return
    keyword = ctx["message"][0]["data"]["text"][4:-2]
    flag = True
    print(keyword)
    print("on r18_keyword_setu")
    if ctx['user_id'] not in bot.config.SUPERUSERS:
        _r18lmt.increase(ctx['user_id'])
    await online_setu(ctx, keyword, flag, bot)


async def send_a_setu(bot, ctx):
    pic = get_setu()
    try:
        await bot.send(ctx, pic.cqcode)
    except CQHttpError:
        sv.logger.error(f"发送图片{pic.path}失败")
        try:
            await bot.send(ctx, '涩图太涩，发不出去勒...')
        except:
            pass


@sv.on_rex(r'setu充值', normalize=False)
async def kakin(bot: NoneBot, ctx, match):
    if ctx['user_id'] not in bot.config.SUPERUSERS:
        return
    count = 0
    for m in ctx['message']:
        if m.type == 'at' and m.data['qq'] != 'all':
            uid = int(m.data['qq'])
            _nlmt.reset(uid)
            count += 1
    if count:
        await bot.send(ctx, f"已为{count}位用户充值完毕！谢谢惠顾～")


async def online_setu(ctx, keyword, flag, bot):
    """随机叫一份涩图，对每个用户有冷却时间"""
    uid = ctx['user_id']
    if not _nlmt.check(uid):
        await bot.send(ctx, EXCEED_NOTICE, at_sender=True)
        return
    if not _flmt.check(uid):
        await bot.send(ctx, '您冲得太快了，请稍候再冲', at_sender=True)
        return

    url = 'https://api.lolicon.app/setu/'
    params = {
        "apikey": "your_api_key",  # 你的apikey
        "size1200": "True"  # 是否限制大小，小水管之友,阔佬可以改成False
    }
    if flag:
        params["r18"] = "1"
    if keyword != "":
        params["keyword"] = keyword
    resp = requests.get(url=url, params=params)
    status_code = resp.status_code
    if status_code != 200:
        print("error status_code，请联系维护组")
    resp_json = resp.json()
    resp_code = resp_json["code"]
    if resp_code != 0:
        if resp_code == 429:
            print("api总调用额度达到上限，将随机发送本地图库中的图片")
            await bot.send(ctx, "api总调用额度达到上限，将随机发送本地图库中的图片")
            _flmt.start_cd(uid)
            _nlmt.increase(uid)
            await send_a_setu(bot, ctx)
            return
        elif resp_code == 404:
            print(resp_json["msg"] + "，将随机发送本地图库中的图片")
            await bot.send(ctx, resp_json["msg"] + "，将随机发送本地图库中的图片")
            _flmt.start_cd(uid)
            _nlmt.increase(uid)
            await send_a_setu(bot, ctx)
            return
        elif resp_code == 403:
            print(resp_json["msg"] + "，请联系维护组（error code 403）")
            await bot.send(ctx, resp_json["msg"] + "，请联系维护组（error code 403）")
            return
        elif resp_code == 401:
            print(resp_json["msg"] + "，请联系维护组（error code 401）")
            bot.send(ctx, resp_json["msg"] + "，请联系维护组（error code 401）")
            return
        elif resp_code == -1:
            print("api炸了")
            await bot.send(ctx, "api炸了")
            return

    # 没啥问题，发图！
    if ctx['user_id'] not in bot.config.SUPERUSERS:
        _flmt.start_cd(uid)
        _nlmt.increase(uid)

    resp_data = resp_json["data"][0]

    pid = resp_data["pid"]
    title = resp_data["title"]
    author = resp_data["author"]
    img_url = resp_data["url"]

    print(pid, title, author, img_url, resp_data["r18"])

    msg = "pid: " + str(pid) + "\n" \
          + "title: " + title + "\n" \
          + "author: " + author + "\n" \
          + "img_url: " + img_url
    await bot.send(ctx, msg)
    if not flag:
        try:
            await bot.send(ctx, '[CQ:image,timeout=30,file=' + img_url + ']')
        except CQHttpError:
            sv.logger.error(f"发送图片{img_url}失败")
            try:
                await bot.send(ctx, '涩图太涩，发不出去勒...')
            except:
                pass
