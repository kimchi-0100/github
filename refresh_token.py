import os
import requests

GITHUB_TOKEN = os.environ["GH_PAT"]
REPO = os.environ["GITHUB_REPOSITORY"]  # GitHub Actions 會自動提供，格式是 "帳號/repo名稱"

META_APP_ID = os.environ["META_APP_ID"]
META_APP_SECRET = os.environ["META_APP_SECRET"]
CURRENT_TOKEN = os.environ["IG_ACCESS_TOKEN"]

# ========== Step 1：跟 Meta 換一組新的長效 token ==========
def refresh_meta_token():
    url = "https://graph.facebook.com/v21.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": META_APP_ID,
        "client_secret": META_APP_SECRET,
        "fb_exchange_token": CURRENT_TOKEN,
    }
    res = requests.get(url, params=params)
    result = res.json()
    print("換新token結果：", result)
    return result.get("access_token")

# ========== Step 2：用 GitHub API 把新 token 寫回 Secrets ==========
def update_github_secret(new_token):
    # 需要先拿 repo 的公鑰，GitHub Secrets 是加密儲存的
    from nacl import encoding, public
    import base64

    # 取得 repo 公鑰
    key_url = f"https://api.github.com/repos/{REPO}/actions/secrets/public-key"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    key_res = requests.get(key_url, headers=headers).json()
    public_key = key_res["key"]
    key_id = key_res["key_id"]

    # 用公鑰加密新token
    def encrypt(public_key_b64, secret_value):
        pk = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
        sealed_box = public.SealedBox(pk)
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        return base64.b64encode(encrypted).decode("utf-8")

    encrypted_value = encrypt(public_key, new_token)

    # 更新 Secret
    update_url = f"https://api.github.com/repos/{REPO}/actions/secrets/IG_ACCESS_TOKEN"
    payload = {
        "encrypted_value": encrypted_value,
        "key_id": key_id,
    }
    update_res = requests.put(update_url, headers=headers, json=payload)
    print("更新Secret狀態碼：", update_res.status_code)

# ========== 主流程 ==========
def main():
    new_token = refresh_meta_token()
    if not new_token:
        print("換取新token失敗，中止")
        return
    update_github_secret(new_token)
    print("Token 更新完成！")

if __name__ == "__main__":
    main()
