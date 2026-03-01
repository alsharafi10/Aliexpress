import base64
import json
import requests
import mimetypes

# Configure using environment variable or prompt user for key
def parse_invoice_image(image_path, api_key):
    # Required rule prompt
    prompt = """
    只识别固定版式的 AliExpress 商家后台订单详情截图。
    只提取以下字段，禁止输出任何额外文字。
    输出必须为 JSON 格式，字段名称必须完全一致。
    不得输出解释，不得输出单位文字，不得输出多余字段。

    【需要识别字段】
    1. order_id: 从截图顶部提取订单号。
    2. buyer_name: 提取买家名称（即使部分被 * 遮挡，也按截图显示内容输出）。
    3. product_total_cny: 提取“产品总金额”人民币金额。
    4. order_total_cny: 提取“订单金额”人民币金额（资金详情中的订单金额）。注意：不要提取买家在截图最下面的买家实付币种。
    5. commission_rate_percent: 提取“佣金”人民币金额，并计算 (佣金金额 / 订单总金额 * 100)，保留两位小数。
    6. transaction_service_rate_percent: 提取“交易服务费”人民币金额，并计算 (交易服务费 / 订单总金额 * 100)，保留两位小数。
    7. incubation_service_rate_percent: 提取“基础孵化服务费”人民币金额，并计算 (基础孵化服务费 / 订单总金额 * 100)，保留两位小数。

    【严格规则】
    - 禁止识别以下字段：商品成本、实际运费、包装费、税费、其他成本、预付资金比例、买家实付的币种金额、预计可得
    - 若某字段缺失，返回 null
    - 所有金额必须为数字类型
    - 所有百分比必须为数字类型（不要带 % 符号）
    - 不要输出解释文字。不要添加任何额外内容。仅输出 JSON。
    """
    
    try:
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/jpeg"

        with open(image_path, "rb") as f:
            image_data = f.read()
        
        encoded_image = base64.b64encode(image_data).decode('utf-8')

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": encoded_image
                        }
                    }
                ]
            }]
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        res_json = response.json()
        
        candidates = res_json.get("candidates", [])
        if not candidates:
            return None
            
        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        # Parse output ensuring JSON
        resp_text = text.strip()
        if resp_text.startswith("```json"):
            resp_text = resp_text[7:]
        if resp_text.endswith("```"):
            resp_text = resp_text[:-3]
            
        return json.loads(resp_text)
    except Exception as e:
        # Need to raise it to catch it in the UI and show the actual error to user
        raise Exception(str(e))

