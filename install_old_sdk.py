#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
在服务器上安装旧版taobao SDK的脚本
"""

import os
import sys
import shutil
import subprocess

def install_old_sdk():
    """安装旧版SDK"""
    print("开始安装旧版taobao SDK...")
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    # taobao SDK的源路径
    taobao_sdk_source = os.path.join(parent_dir, 'taobao-sdk-PYTHON-auto_1479188381469-20250717')
    
    # 目标路径
    taobao_sdk_target = os.path.join(current_dir, 'taobao-sdk-PYTHON-auto_1479188381469-20250717')
    
    print(f"源路径: {taobao_sdk_source}")
    print(f"目标路径: {taobao_sdk_target}")
    
    # 检查源路径是否存在
    if not os.path.exists(taobao_sdk_source):
        print(f"错误: 源路径不存在: {taobao_sdk_source}")
        print("请确保taobao-sdk-PYTHON-auto_1479188381469-20250717文件夹在项目根目录下")
        return False
    
    # 如果目标路径已存在，先删除
    if os.path.exists(taobao_sdk_target):
        print(f"删除已存在的目标路径: {taobao_sdk_target}")
        shutil.rmtree(taobao_sdk_target)
    
    # 复制SDK到目标路径
    try:
        print("复制taobao SDK...")
        shutil.copytree(taobao_sdk_source, taobao_sdk_target)
        print("复制完成")
    except Exception as e:
        print(f"复制失败: {e}")
        return False
    
    # 验证安装
    try:
        sys.path.insert(0, taobao_sdk_target)
        import dingtalk.api
        from dingtalk.api.rest.OapiUserGetRequest import OapiUserGetRequest
        from dingtalk.api.rest.OapiGettokenRequest import OapiGettokenRequest
        print("旧版SDK安装成功！")
        return True
    except ImportError as e:
        print(f"验证失败: {e}")
        return False

def test_old_sdk():
    """测试旧版SDK是否可用"""
    print("测试旧版SDK...")
    
    try:
        # 添加SDK路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sdk_path = os.path.join(current_dir, 'taobao-sdk-PYTHON-auto_1479188381469-20250717')
        
        if not os.path.exists(sdk_path):
            print(f"SDK路径不存在: {sdk_path}")
            return False
        
        sys.path.insert(0, sdk_path)
        
        # 测试导入
        import dingtalk.api
        from dingtalk.api.rest.OapiUserGetRequest import OapiUserGetRequest
        from dingtalk.api.rest.OapiGettokenRequest import OapiGettokenRequest
        
        print("旧版SDK导入成功！")
        
        # 测试创建请求对象
        request = OapiGettokenRequest("https://oapi.dingtalk.com/gettoken")
        print("请求对象创建成功！")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        return False

if __name__ == "__main__":
    print("=== 旧版SDK安装脚本 ===")
    
    # 检查是否已经安装
    if test_old_sdk():
        print("旧版SDK已经可用，无需重新安装")
    else:
        # 安装SDK
        if install_old_sdk():
            print("安装完成，正在测试...")
            if test_old_sdk():
                print("安装和测试都成功！")
            else:
                print("安装成功但测试失败")
        else:
            print("安装失败")
    
    print("=== 脚本结束 ===") 