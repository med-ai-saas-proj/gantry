import requests


class SsiUtils:
    @staticmethod
    async def get():
        url = "https://iboard-query.ssi.com.vn/stock/exchange/hose?boardId=MAIN"
        payload = {}
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "vi",
            "device-id": "A6B0D309-783F-4EB8-A6AE-3E33424EFE06",
            "origin": "https://iboard.ssi.com.vn",
            "priority": "u=1, i",
            "referer": "https://iboard.ssi.com.vn/",
            "sec-ch-ua": '"Opera";v="120", "Not-A.Brand";v="8", "Chromium";v="135"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
        }
        res = requests.request("GET", url, headers=headers, data=payload)
        if res.status_code>=300:
            raise
        retu
