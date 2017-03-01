import re
import logging

import requests
from PIL import Image
from io import BytesIO

session = requests.session()
logging.basicConfig(level=logging.DEBUG)

login_url = 'http://ipgw.neu.edu.cn:8800/'
capcha_url = 'http://ipgw.neu.edu.cn:8800/site/captcha'


def login(username, password):
    r = session.get(login_url)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        logging.exception(e)
        return
    csrf = re.search(r'<input type="hidden" name="_csrf".*?value="(.*?)">', r.text).group(1)

    tried_again = False
    while True:
        captcha = get_captcha(tried_again)
        tried_again = True
        data = {
            '_csrf'                : csrf,
            'LoginForm[username]:' : username,
            'LoginForm[password]'  : password,
            'LoginForm[verifyCode]': captcha
        }

        r = session.post(login_url, data=data)
        # 登录成功
        if '/home/base/index' in r.url:
            logging.info('登录成功')
            return r.text

        logging.error('登录失败')


def get_captcha(refresh=False):
    param = {'refresh': '1'} if refresh else {}
    r = session.get(capcha_url, params=param)
    if r.status_code == 200:
        logging.debug('获取验证码成功')
        img = Image.open(BytesIO(r.content))
        img.show()
        return input('请输入验证码>').strip()
    logging.error('获取验证码失败')


if __name__ == '__main__':
    import sys

    print(login(sys.argv[1], sys.argv[2]))
