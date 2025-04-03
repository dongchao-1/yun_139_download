#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from yun139 import Yun139
import hashlib
import requests
import os
from datetime import datetime

config_file = '/app_config/config.json'

def load_config():
    with open(config_file, 'r') as file:
        config = json.load(file)
    return config

def save_config(config):
    with open(config_file, 'w') as file:
        json.dump(config, file, indent=4)

def calculate_file_sha256(file_path):
    sha256_hash = hashlib.sha256()
    
    # 以二进制方式打开文件
    with open(file_path, 'rb') as file:
        # 分块读取文件，避免大文件一次性读取造成内存问题
        for byte_block in iter(lambda: file.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()

def download_file(url, file_path, create_time=None):
    response = requests.get(url, stream=True)  # 使用 stream=True 以分块下载
    if response.status_code == 200:
        with open(file_path, 'wb') as file:  # 以二进制模式写入文件
            for chunk in response.iter_content(chunk_size=8192):  # 分块写入
                file.write(chunk)
        print(f"文件已下载到: {file_path}")

        if create_time is not None:
            # 解析 createTime（格式：20250328074827 → YYYYMMDDHHMMSS）
            dt = datetime.strptime(create_time, "%Y%m%d%H%M%S")
            timestamp = dt.timestamp()
            
            # 修改文件的访问和修改时间
            os.utime(file_path, (timestamp, timestamp))
            # print(f"文件时间已设置为: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"下载失败，状态码: {response.status_code}")

def file_exists(file_path):
    return os.path.isfile(file_path)

if __name__ == "__main__":
    print("starting yun139 file download...")
    config = load_config()
    yun139 = Yun139({'type': 'family',
                     'authorization': config['authorization'],
                     'cloudID': config['cloudID'],
                     'catalogID': config['catalogID'],
                     'account': config['account'],})
    new_token = yun139.refresh_token()
    if new_token:
        print("Token refreshed successfully.")
        config['authorization'] = new_token
        save_config(config)

    files = yun139.family_get_files(config['catalogID'])
    for f in files:
        print(f"File: {f}")
        f_name = f"/app_data/{f['name']}"
        if file_exists(f_name):
            print(f"File already exists: {f_name}")
            sha256 = calculate_file_sha256(f_name)
            if sha256 == f['digest']:
                print("File SHA256 matches.")
                continue
            else:
                print(f"File SHA256: {sha256}, expected: {f['digest']}")
                print("File SHA256 does not match, downloading new version.")
        
        print(f"Downloading file: {f_name}")
        url = yun139.family_get_link(f['id'], f['path'])
        print(f"Download URL: {url}")
        download_file(url, f_name, f['createTime'])
        print(f"File downloaded: {f_name}")
    print("All files processed.")
