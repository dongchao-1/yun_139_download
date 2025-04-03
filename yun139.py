import base64
import hashlib
import json
import random
import time
import urllib.parse
from datetime import datetime
from typing import Dict, List

import requests

class Yun139:
    def __init__(self, config: Dict):
        self.config = config
        self.session = requests.Session()
        self.ref = None  # For refresh token handler
        
    @property
    def is_family(self) -> bool:
        return self.config.get("type") == "family"
    
    def encode_uri_component(self, s: str) -> str:
        encoded = urllib.parse.quote(s, safe="!()*'")
        return encoded.replace("+", "%20")
    
    def cal_sign(self, body: str, ts: str, rand_str: str) -> str:
        body = self.encode_uri_component(body)
        sorted_chars = sorted(body)
        body = "".join(sorted_chars)
        body = base64.b64encode(body.encode()).decode()
        part1 = hashlib.md5(body.encode()).hexdigest()
        part2 = hashlib.md5(f"{ts}:{rand_str}".encode()).hexdigest()
        res = hashlib.md5((part1 + part2).encode()).hexdigest()
        return res.upper()
    
    def refresh_token(self) -> None:
        if self.ref:
            return self.ref.refresh_token()
            
        try:
            auth = base64.b64decode(self.config["authorization"]).decode()
            parts = auth.split(":")
            if len(parts) < 3:
                raise ValueError("Authorization is invalid, parts < 3")
                
            token_parts = parts[2].split("|")
            if len(token_parts) < 4:
                raise ValueError("Authorization is invalid, token parts < 4")
                
            expiration = int(token_parts[3])
            remaining = expiration - int(time.time() * 1000)
            
            if remaining > 1000 * 60 * 60 * 24 * 15:
                # More than 15 days remaining, no need to refresh
                print(f"Token is still valid, no need to refresh, remaining: {remaining / 1000/ 60 / 60 / 24} days")
                return
                
            if remaining < 0:
                raise ValueError("Authorization has expired")
                
            url = "https://aas.caiyun.feixin.10086.cn:443/tellin/authTokenRefresh.do"
            req_body = f"<root><token>{parts[2]}</token><account>{parts[1]}</account><clienttype>656</clienttype></root>"
            
            headers = {"Content-Type": "application/xml"}
            response = self.session.post(url, data=req_body, headers=headers)
            response.raise_for_status()
            
            resp_data = response.text
            # Parse XML response (simplified)
            if "<return>0</return>" not in resp_data:
                desc = resp_data.split("<desc>")[1].split("</desc>")[0]
                raise ValueError(f"Failed to refresh token: {desc}")
                
            # Extract new token
            new_token = resp_data.split("<token>")[1].split("</token>")[0]
            new_auth = f"{parts[0]}:{parts[1]}:{new_token}"
            self.config["authorization"] = base64.b64encode(new_auth.encode()).decode()
            return self.config["authorization"]
        except Exception as e:
            raise ValueError(f"Refresh token failed: {str(e)}")
    
    def request(self, pathname: str, method: str, callback=None, resp_model=None):
        url = f"https://yun.139.com{pathname}"
        rand_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=16))
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        req_data = {}
        if callback:
            req_data = callback()
            
        body = json.dumps(req_data) if req_data else ""
        sign = self.cal_sign(body, ts, rand_str)
        svc_type = "2" if self.is_family else "1"
        
        headers = {
            "Accept": "application/json, text/plain, */*",
            "CMS-DEVICE": "default",
            "Authorization": f"Basic {self.get_authorization()}",
            "mcloud-channel": "1000101",
            "mcloud-client": "10701",
            "mcloud-sign": f"{ts},{rand_str},{sign}",
            "mcloud-version": "7.14.0",
            "Origin": "https://yun.139.com",
            "Referer": "https://yun.139.com/w/",
            "x-DeviceInfo": "||9|7.14.0|chrome|120.0.0.0|||windows 10||zh-CN|||",
            "x-huawei-channelSrc": "10000034",
            "x-inner-ntwk": "2",
            "x-m4c-caller": "PC",
            "x-m4c-src": "10002",
            "x-SvcType": svc_type,
            "Inner-Hcy-Router-Https": "1",
        }
        
        response = self.session.request(method, url, json=req_data, headers=headers)
        response.raise_for_status()
        
        resp_data = response.json()
        if not resp_data.get("success"):
            raise ValueError(resp_data.get("message", "Unknown error"))
            
        if resp_model:
            # Here you would typically map resp_data to your resp_model
            pass
            
        return resp_data
    
    def post(self, pathname: str, data: Dict, resp_model=None):
        def callback():
            return data
        return self.request(pathname, "POST", callback, resp_model)
    
    def new_json(self, data: Dict) -> Dict:
        common = {
            "catalogType": 3,
            "cloudID": self.config["cloudID"],
            "cloudType": 1,
            "commonAccountInfo": {
                "account": self.get_account(),
                "accountType": 1,
            },
        }
        return {**common, **data}
    
    PAGE_SIZE = 100

    def family_get_files(self, catalog_id: str) -> List[Dict]:
        startNumber = 0
        endNumber = self.PAGE_SIZE
        files = []
        
        while True:
            print(f"startNumber: {startNumber}, endNumber: {endNumber}")
            data = self.new_json({
                'isSumnum': 1,
                'contentSuffix': 'bmp|ilbm|png|gif|jpeg|jpg|mng|ppm|AVI|MPEG|MPG|DAT|DIVX|XVID|RM|RMVB|MOV|QT|ASF|WMV|nAVI|vob|3gp|mp4|flv|AVS|MKV|ogm|ts|tp|nsv|swf|heic|HEIC|heif|HEIF|livp',
                'contentSortType': 5,
                'sortDirection': 1,
                'startNumber': startNumber,
                'endNumber': endNumber,
                'catalogID': catalog_id,
            })
            
            resp = self.post("/orchestration/familyCloud-rebuild/photoContent/v1.0/queryContentInfo", data)
            
            for catalog in resp["data"]["getDiskResult"]["contentList"]:
                files.append({
                    "id": catalog["contentID"],
                    "name": catalog["contentName"],
                    "path": catalog["parentCatalogId"],
                    "contentSize": catalog["contentSize"],
                    "digest": catalog["digest"],
                    "createTime": catalog["exif"]["createTime"],
                })
            print(f"files: {files}")

            if endNumber > resp["data"]["getDiskResult"]["nodeCount"]: # 分页需要更多照片去验证
                break
            startNumber += self.PAGE_SIZE
            endNumber += self.PAGE_SIZE
            
        return files
    
    def family_get_link(self, content_id: str, path: str) -> str:
        data = self.new_json({
            "contentID": content_id,
            "path": f'root:/{path}/{content_id}',
        })
        
        resp = self.post("/orchestration/familyCloud-rebuild/content/v1.0/getFileDownLoadURL", data)
        return resp["data"]["downloadURL"]
    
    def get_authorization(self) -> str:
        if self.ref:
            return self.ref.get_authorization()
        return self.config["authorization"]
    
    def get_account(self) -> str:
        if self.ref:
            return self.ref.get_account()
        return self.config["account"]