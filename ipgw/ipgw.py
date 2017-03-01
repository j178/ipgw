#!/usr/bin/env python3
# Author: John Jiang
# Date  : 2016/7/1

# 开机自动登陆，关机自动退出脚本
# todo 通过「校园统一身份认证SSO」修改任何人的校园网密码
import json
import os
import re
import sys
import time

import requests

RECORD_SIZE = 30
RECORD_INTERVAL = 3600 if not os.environ.get('DEBUG') else 0

PAGE_URL = 'https://ipgw.neu.edu.cn/srun_portal_pc.php'
AJAX_URL = 'https://ipgw.neu.edu.cn/include/auth_action.php'

ATTRIBUTES = {
    'bold'     : 1,
    'dark'     : 2,
    'underline': 4,
    'blink'    : 5,
    'reverse'  : 7,
    'concealed': 8
}

HIGHLIGHTS = {
    'on_grey'   : 40,
    'on_red'    : 41,
    'on_green'  : 42,
    'on_yellow' : 43,
    'on_blue'   : 44,
    'on_magenta': 45,
    'on_cyan'   : 46,
    'on_white'  : 47
}

COLORS = {
    'grey'   : 30,
    'red'    : 31,
    'green'  : 32,
    'yellow' : 33,
    'blue'   : 34,
    'magenta': 35,
    'cyan'   : 36,
    'white'  : 37,
}
RESET = '\033[0m'

s = requests.Session()
# 网管系统使用UA来判断登录的设备，最多允许同时有两个不同的UA登录
# 当有第三个UA尝试登录时，返回'E2620: You are already online.(已经在线了)'
s.headers['User-Agent'] = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/56.0.2924.87 Safari/537.36')


def cprint(text, color=None, on_color=None, attrs=None, **kwargs):
    fmt_str = '\033[%dm%s'
    if color is not None:
        text = fmt_str % (COLORS[color], text)

    if on_color is not None:
        text = fmt_str % (HIGHLIGHTS[on_color], text)

    if attrs is not None:
        for attr in attrs:
            text = fmt_str % (ATTRIBUTES[attr], text)

    text += RESET
    print(text, **kwargs)


def size_fmt(num, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Y', suffix)


def login(username, password):
    """
    登陆IP网关并获取网络使用情况

    :param str username: 学号
    :param str password: 密码
    :returns bool|str 登陆成功返回 True, 否则为错误消息
    """

    def parse(text):
        info = text.split(',')
        return {
            'user'    : username,
            'usedflow': float(info[0]),
            'duration': float(info[1]),
            'time'    : int(time.time()),
            'balance' : float(info[2]),
            'ip'      : info[5]
        }

    data = {
        'action'  : 'login',
        'ac_id'   : 1,
        'username': username,
        'password': password
    }

    # 不需要cookie，服务器根据请求的IP来获取登录的用户的信息
    r = s.post(PAGE_URL, data)

    if '网络已连接' in r.text:
        # 如果未登录，则返回 not_online
        r = s.post(AJAX_URL, data={'action': 'get_online_info'})
        info = parse(r.text)
        track(info)
        display(info)
    else:
        match = re.search(r'<input.*?name="url".*?<p>(.*?)</p>', r.text, re.DOTALL)
        why = match.group(1) if match else 'Unknown Reason'
        raise requests.ConnectionError(why)


def logout_all(username, password=''):
    """
    登出IP网关
    因为一个账号可以在多个IP处登陆，所以一个账号对应多个IP
    '断开连接'的意思是，将当前IP从连接中断开, '断开全部链接'是指将当前账号对应的所有IP都断开。
    在管理页面的'下线'功能也是将IP断开。
    <del>移动页面的'注销'是指'断开所有链接', 即将账号对应的所有链接都断开。</del>
    :param str username:
    :param password: 断开全部链接时需要
    """
    data = {
        'action'  : 'logout',
        'username': username,
        'password': password,
        'ajax'    : '1'
    }

    r = s.post(AJAX_URL, data)
    r.encoding = 'utf-8'
    cprint(r.text, color='cyan')


def logout_current(*args):
    # 网页登录之后的注销按钮，只退出当前IP
    data = {
        'action': 'auto_logout',
        # 'info'   : '',
        # 'user_ip': '118.202.11.141'
    }
    s.post(PAGE_URL, data)


def track(info):
    """记录信息并返回此次与上次的差别"""
    datafile = os.path.join(os.path.expanduser('~'), '.ipgw')
    user = info['user']
    data = {}

    period = 0
    newused = 0
    try:
        with open(datafile, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        with open(datafile, 'w') as f:
            data.setdefault(user, []).append(info)
            json.dump(data, f)
            return

    if user in data:
        last = data[user][-1]
        # 缩小文件体积，只记录最新的十条记录
        if len(data[user]) > RECORD_SIZE:
            data[user] = data[user][-RECORD_SIZE:]
        # 如果间距小于x，则不记录
        if info['time'] - last['time'] < RECORD_INTERVAL:
            return
        period = info['duration'] - last['duration']
        newused = info['usedflow'] - last['usedflow']

        with open(datafile, 'w') as f:
            data.setdefault(user, []).append(info)
            json.dump(data, f)

    info['period'] = period if period >= 0 else 0
    info['newused'] = newused if newused >= 0 else 0


def is_online():
    r = s.post(AJAX_URL, data={'action': 'get_online_info'})
    if 'not_online' in r.text:
        cprint('You are offline', color='red')
        return False

    cprint('You are online', color='green')
    return True


def display(info):
    info['usedflow'] = size_fmt(info['usedflow'])
    info['duration'] = '{:.2f} H'.format(info['duration'] / 3600)
    info['balance'] = '{} Yuan'.format(info['balance'])
    width = len(info['ip'])
    msg = '''\
+-----------+--{pad:-<{width}}-+
| User      |  {user:<{width}} |
| Used Flow |  {usedflow:<{width}} |
| Used Time |  {duration:<{width}} |
| Balance   |  {balance:<{width}} |
| IP        |  {ip:<{width}} |
+-----------+--{pad:-<{width}}-+{record}
'''

    if 'period' in info:
        period = '{:.2f} H'.format(info['period'] / 3600)
        newused = size_fmt(info['newused'])
        info['record'] = '\nIn past {period} used {newused}'.format(period=period, newused=newused)
    else:
        info['record'] = ''
    print(msg.format(**info, width=width, pad=''), end='')


def usage():
    msg = []
    msg.append('usage: ipgw [-h] [-o LOGOUT] [-f FORCE_LOGIN] [student_id] [password]')
    msg.append('\nA script to login/logout your school IP gateway(ipgw.neu.edu.cn)')
    msg.append('\noptional arguments:')
    msg.append('  -h, --help      show this help message')
    msg.append('  -o, --logout    logout from IP gateway')
    msg.append('  -f, --force     force login(logout first and then login again)')
    msg.append('  -t, --test      test is online')
    msg.append('  student_id      your student id to login, explicitly pass or read from IPGW_ID environment variable')
    msg.append('  password        your password, explicitly pass or read from IPGW_PW environment variable')
    msg.append('\nWritten by johnj.(https://github.com/j178)')
    print('\n'.join(msg))
    sys.exit()


def run():
    is_logout = False
    force_login = False

    if '-h' in sys.argv or '--help' in sys.argv:
        usage()

    if '-t' in sys.argv or '--test' in sys.argv:
        is_online()
        return

    if '-o' in sys.argv or '--logout' in sys.argv:
        args = [x for x in sys.argv[1:] if (x != '-o' and x != '--logout')]
        is_logout = True
    else:
        args = sys.argv[1:]

    if '-f' in args or '--force' in args:
        args = [x for x in args if (x != '-f' and x != '--force')]
        force_login = True

    if len(args) >= 2:
        args = args[:2]
    else:
        try:
            args = os.environ['IPGW_ID'], os.environ['IPGW_PW']
        except KeyError:
            usage()

    if is_logout:
        return logout_current(*args)
    if force_login:
        logout_all(*args)
        return login(*args)

    # 没有提供选项参数, 则默认为连接网络
    while True:
        try:
            return login(*args)
        except requests.ConnectionError as e:
            cprint(e, color='red')
            cprint('是否断开全部链接并重新连接(y/n)?', color='magenta', end=' ')
            if input().lower().strip() != 'n':
                logout_all(*args)
            else:
                break


def main():
    try:
        run()
    except KeyboardInterrupt:
        cprint('\nStopped.', 'green')


if __name__ == '__main__':
    main()
