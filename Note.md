- 网关登录地址 https://ipgw.neu.edu.cn

- 移动设备
    - 访问
        1. 跳转至 /index_1.html?url=
        2. 继续跳转至 /srun_portal_phone.php?url=&ac_id=1
    
    - 登录
        POST 到 自身(https://ipgw.neu.edu.cn/srun_portal_phone.php?ac_id=1) => action=login, username, password, [ac_id=1, user_ip, nas_ip, user_mac]
        登录成功后不跳转，显示'注销'按钮
        登录失败在返回页面中显示错误消息，不跳转
        点击'注销'按钮之后: POST到自身(https://ipgw.neu.edu.cn/srun_portal_phone.php?ac_id=1) => action=auto_logout, info, user_ip=xxxx
    
    - 注销
        在首页注销 POST 到自身(https://ipgw.neu.edu.cn/srun_portal_phone.php?ac_id=1) => action=logout, 其他参数同上
    
- 桌面设备
    - 访问
        1. 跳转至 /index_1.html?url=
        2. 继续跳转至 /srun_portal_pc.php?url=&ac_id=1

    - 连接网络
        POST 到自身 => action=login，ac_id=1，user_ip，nas_ip，user_mac，url，username=xxxx，password=xxxx，save_me=0
        登录成功跳转到自身，显示'注销'按钮
        之后使用AJAX POST 到 https://ipgw.neu.edu.cn/include/auth_action.php?k=?? => action=get_online_info,key=??
        
        点击'注销'按钮:
            POST 到 https://ipgw.neu.edu.cn/srun_portal_pc.php?url=&ac_id=1 => action=auto_logout,info,user_ip=xxxx

    - 断开连接
        AJAX POST https://ipgw.neu.edu.cn/include/auth_action.php => action=logout,username=xxxx,password=xxxx,ajax=1, 以alert显示结果

    - 断开全部连接
        与'断开连接'完全相同，没有区别

- 查询上网费用

1. 电脑先连接，之后手机再以不同IP连接，则两台设备同时在线
    在手机端点击登录之后的页面中的'注销'(auto_logou)，仅手机端IP下线，返回登录页面点击'注销'(logout),则电脑IP也下线
2. 手机连接，电脑端点连接之后出现的'注销'(auto_logout)，手机不下线。点击返回电脑登录页面中的'断开连接',则手机下线

3. 从已登录的电脑上(IP不同，UA不同）(手机端已登录) POST https://ipgw.neu.edu.cn/srun_portal_phone.php?ac_id=1 with action=auto_logout,user_ip=手机端IP，成功让此IP下线。
    不使用user_ip参数，仍然让登录同一帐号的手机端下线
    从未登录的电脑上(手机端已登录)执行上面的操作，仍然返回'注销成功'，但是实际并没有效果
    从登录的电脑上(手机端未登录)，执行上面的操作，返回'注销成功'，但是实际被注销的却是电脑端

    从未登录的电脑(手机未登录)，user_ip=219.216.64.143，执行以上操作，返回'注销成功'，此IP掉线
    ===============================================================================
    从已登录的电脑(手机未登录)，user_ip=219.216.64.143，执行以上操作，===================结果有待验证

4. 从已登录的电脑上(手机端未登录) POST https://ipgw.neu.edu.cn/srun_portal_pc.php?url=&ac_id=1，不使用user_ip参数，成功断开电脑端
    从已登录的电脑上(手机端已登录) 执行以上动作，断开电脑端
    从未登录的电脑上(手机端也未登录) 执行上面操作，返回错误：'您似乎未曾连接到网络...'
    从未登录的电脑上(手机端已登录)执行上面操作，返回错误，您似乎未曾连接到网络，手机端未断开
    
5. 从已登录的电脑上(手机端已登录) POST https://ipgw.neu.edu.cn/srun_portal_pc.php user_ip=手机端ip，成功断开手机端
    从已登录的电脑(手机端未登录) 执行上面操作，user_ip=219.216.64.143, 返回'网络已断开', 此IP掉线，本电脑IP没有掉线
    ===================================================================================================
    应用：让任何IP掉线
    从未登录的电脑上(手机端未登录)执行以上操作，user_ip=219.216.64.143 返回'网络已断开', 此IP掉线

6. 电脑登录，手机登录，从电脑端 POST 'https://ipgw.neu.edu.cn/include/auth_action.php'，
        未提供用户名与密码，返回'网络已断开',电脑端下线；提供用户名与错误密码，返回'注销失败：Password is error.',两个帐号均在线；提供正确密码，返回'网络已断开'，两个帐号均下线
    电脑未登录，手机登录，未提供用户名和密码，返回'您似乎未曾连接到网络...'，手机端仍然在线；提供错误密码，返回'注销失败：Password is error.'，手机仍在线；提供正确密码，返回'网络已断开'，手机下线。
    电脑登录，手机未登录，未提供用户名与密码， 返回网络已断开，电脑下线；...
    电脑未登录，手机未登录；未提供用户名与密码，返回你似乎未曾连接到网络；提供正确密码，返回'网络已断开';不提供用户名，返回似乎未曾连接到网络。

7. 电脑登录，手机登录，从电脑端POST https://ipgw.neu.edu.cn/srun_portal_phone.php 不提供帐号和密码，user_ip=电脑IP，电脑下线，手机在线

- 其他测试
1. IP相同，则无论是哪种UA(pc/phone)，均会替换前一次登录
2. IP不同，UA的种类不同，则可以同时在线
3. IP不同，UA的种类相同，则会返回'E2620: You are already online.(已经在线了)'

4. 手机端与电脑端的网页只有展示的方式不一样，具体登录时记录成哪种设备，完全由登录时的UA决定。