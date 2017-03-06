#!/usr/bin/env python
# ! encoding=utf8

# Author: John Jiang
# Date  : 2016/7/1
from __future__ import unicode_literals, print_function
import json
import os
import re
import sys
import time

import logging
import requests

RECORD_SIZE = 30
RECORD_INTERVAL = 3600

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


class IPGWError(ConnectionError):
    def __init__(self, why):
        self.why = why

    def __str__(self):
        return self.why


class TwoDevicesOnline(IPGWError):
    def __init__(self, why):
        super(TwoDevicesOnline, self).__init__(why)


logger = logging.getLogger(__name__)


def setup_logger():
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())


class IPGW:
    PC_PAGE_URL = 'https://ipgw.neu.edu.cn/srun_portal_pc.php'
    PC_AJAX_URL = 'https://ipgw.neu.edu.cn/include/auth_action.php'
    PHONE_URL = 'https://ipgw.neu.edu.cn/srun_portal_phone.php'
    PC_UA = {'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                            'Chrome/56.0.2924.87 Safari/537.36')}
    PHONE_UA = {'User-Agent': (
        'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) '
        'Version/9.0 Mobile/13B143 Safari/601.1')}
    session = requests.session()

    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password

    @classmethod
    def _request(cls, method, *args, **kwargs):
        while True:
            r = cls.session.request(method, *args, **kwargs)
            # todo
            if 'Portal not response' in r.text:
                logger.error('Portal not response, trying again')
                time.sleep(1)
                continue
            return r

    def login(self):
        """
        登陆IP网关并获取网络使用情况
        """
        data = {
            'action'  : 'login',
            'username': self.username,
            'password': self.password
        }
        alrealy_logged_error = 'E2620: You are already online.(已经在线了)'

        # 不需要cookie，服务器根据请求的IP来获取登录的用户的信息
        text = self._request('POST', self.PC_PAGE_URL, data=data, headers=self.PC_UA).text

        if alrealy_logged_error in text:
            # 尝试以手机端登录
            logger.error('你已经在线了，正在尝试以手机登录')
            text = self._request('POST', self.PC_PAGE_URL, data=data, headers=self.PHONE_UA).text
            if alrealy_logged_error in text:
                raise TwoDevicesOnline('你已有两台设备在线')

        if '网络已连接' not in text:
            match = re.search(r'<input.*?name="url".*?<p>(.*?)</p>', text, re.DOTALL)
            why = match.group(1) if match else 'Unknown Reason'
            logger.error('连接出错 %s', why)
            raise IPGWError(why)

        info = self.get_online_info()
        if not info:
            raise IPGWError('网络出错，请稍候重试')

        return info

    def get_online_info(self):
        r = self._request('POST', self.PC_AJAX_URL, data={'action': 'get_online_info'})
        # 如果未登录，则返回 not_online
        if 'not_online' not in r.text:
            info = r.text.split(',')
            return {
                'user'    : self.username,
                'usedflow': float(info[0]),
                'duration': float(info[1]),
                'time'    : int(time.time()),
                'balance' : float(info[2]),
                'ip'      : info[5]
            }

    def logout_all(self):
        """
        注销此帐号的所有登录
        """
        data = {
            'action'  : 'logout',
            'username': self.username,
            'password': self.password,
        }

        r = self._request('POST', self.PC_AJAX_URL, data)
        r.encoding = 'utf-8'
        return '网络已断开' in r.text

    def logout_current(self, user_ip=None):
        # 网页登录之后的注销按钮，只退出当前IP
        # 特殊用法：使用user_ip使任意IP下线
        data = {
            'action' : 'auto_logout',
            'user_ip': user_ip
        }
        r = self._request('POST', self.PC_PAGE_URL, data)
        r.encoding = 'utf-8'
        if '网络已断开' not in r.text:
            match = re.search(r'<td height="40" style="font-weight:bold;color:orange;">(.*?)</td>', r.text, re.DOTALL)
            if match:
                raise IPGWError(match.group(1).strip())
        return True

    @classmethod
    def is_online(cls):
        r = cls._request('POST', cls.PC_AJAX_URL, data={'action': 'get_online_info'})
        return 'not_online' not in r.text


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
    print(msg.format(width=width, pad='', **info), end='')


def usage():
    msg = []
    msg.append('usage: ipgw [-h] [-o LOGOUT] [-f FORCE_LOGIN] [student_id] [password]')
    msg.append('\nA script to login/logout your school IP gateway(ipgw.neu.edu.cn)')
    msg.append('\noptional arguments:')
    msg.append('  -h, --help      show this help message')
    msg.append('  -o, --logout    logout from IP gateway')
    msg.append('  -f, --force     force login(logout first and then login again)')
    msg.append('  -t, --test      test is online')
    msg.append('  -y, --yes       answer yes to all question')
    msg.append(
            '  student_id      your student id to login, explicitly pass or read from IPGW_ID environment variable')
    msg.append('  password        your password, explicitly pass or read from IPGW_PW environment variable')
    msg.append('\nWritten by johnj.(https://github.com/j178)')
    print('\n'.join(msg))
    sys.exit()


def run():
    is_logout = False
    force_login = False
    answer_yes = False

    if '-h' in sys.argv or '--help' in sys.argv:
        usage()

    if '-t' in sys.argv or '--test' in sys.argv:
        if IPGW.is_online():
            cprint('你已经连接好啦!', color='green')
            return True
        else:
            cprint('你当前没有连接到网络!', color='red')
            return False

    if '-o' in sys.argv or '--logout' in sys.argv:
        args = [x for x in sys.argv[1:] if (x != '-o' and x != '--logout')]
        is_logout = True
    else:
        args = sys.argv[1:]

    if '-f' in args or '--force' in args:
        args = [x for x in args if (x != '-f' and x != '--force')]
        force_login = True
    if '-y' in args or '--yes' in args:
        args = [x for x in args if (x != '-f' and x != '--yes')]
        answer_yes = True

    if len(args) >= 2:
        args = args[:2]
    else:
        try:
            args = os.environ['IPGW_ID'], os.environ['IPGW_PW']
        except KeyError:
            usage()

    ipgw = IPGW(*args)
    if is_logout:
        try:
            ipgw.logout_current()
            cprint('网络已断开', color='green')
            return True
        except IPGWError as e:
            cprint(e, color='red')
            return False

    if force_login:
        ipgw.logout_all()
        cprint('网络已断开，正在重新登录...', color='green')

    # 没有提供选项参数, 则默认为连接网络
    while True:
        try:
            info = ipgw.login()
            track(info)
            display(info)
            return True
        except requests.ConnectionError as e:
            cprint(e, color='red')
            return False
        except TwoDevicesOnline as e:
            cprint(e, color='red')
            cprint('是否注销全部连接并重新登录(y/n)?', color='magenta', end=' ')
            if answer_yes or input().lower().strip() != 'n':
                ipgw.logout_all()
                continue
            return False
        except IPGWError as e:
            cprint(e, color='red')
            cprint('是否重试(y/n)?', color='magenta', end=' ')
            if answer_yes or input().lower().strip() != 'n':
                continue
            else:
                break


def main():
    try:
        return run()
    except KeyboardInterrupt:
        cprint('\nStopped.', 'green')
        return 1


if __name__ == '__main__':
    sys.exit(main())
