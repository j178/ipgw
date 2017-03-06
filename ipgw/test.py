# auto_logout意思是只断开当前登录的设备
import requests
import logging

import sys

from _ipgw.ipgw.ipgw import IPGW

logging.basicConfig(level=logging.DEBUG)


def logout_current(device, ip=None):
    url = {
        'phone': 'https://ipgw.neu.edu.cn/srun_portal_phone.php',
        'pc'   : 'https://ipgw.neu.edu.cn/srun_portal_pc.php'
    }[device]

    data = {
        'action' : 'auto_logout',
        'user_ip': ip
    }
    r = requests.post(url, data=data)
    r.encoding = 'utf-8'

    if device == 'phone' and '注销成功！' in r.text:
        logging.info('Log phone out successfully')

    with open('tmp.html', 'w') as f:
        f.write(r.text)


def get_online_info():
    url = 'https://ipgw.neu.edu.cn/include/auth_action.php'
    r = requests.post(url, data={'action': 'get_online_info'})
    if r.text == 'not_online':
        print('You are offline')
    else:
        print(r.text)


def logout_all(device, username=None, password=None):
    url = {
        'phone': 'https://ipgw.neu.edu.cn/srun_portal_phone.php',
        'pc'   : 'https://ipgw.neu.edu.cn/include/auth_action.php'
    }[device]

    data = {
        'action'  : 'logout',
        'username': username,
        'password': password
    }

    if device == 'phone':
        data.update({'user_ip': '219.216.65.201'})

    r = requests.post(url, data=data)
    r.encoding = 'utf-8'
    with open('tmp.html', 'w') as f:
        f.write(r.text)


def test_login():
    ipgw = IPGW(sys.argv[1], sys.argv[2])
    ipgw.login()


if __name__ == '__main__':
    # logout_current('phone', '118.202.12.104')
    # logout_all('phone')
    # get_online_info()
    test_login()
