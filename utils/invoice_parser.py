import base64
import json
import requests
import mimetypes

# Configure using environment variable or prompt user for key
def parse_invoice_image(image_path, api_key):
    # Required rule prompt
    prompt = """
1. 只识别固定版式的 AliExpress 商家后台订单详情截图（格式与示例完全一致）。
2. 只提取以下字段，禁止输出任何额外文字。
3. 输出必须为 JSON 格式，字段名称必须完全一致。
4. 不得输出解释，不得输出单位文字，不得输出多余字段。

----------------------------------------
【需要识别字段】

1. order_id
   - 从截图顶部提取订单号。

2. buyer_name
   - 提取买家名称（即使部分被 * 遮挡，也按截图显示内容输出）。

3. product_total_cny
   - 提取“产品总金额”人民币金额（订单金额直接自动汇率美金按照买家付当天的汇率）。

4. order_total_cny
   - 提取“订单金额”人民币金额（资金详情中的订单金额）。
   - 注意：不要提取其他币中，不要提取买家实付币中金额， 要按照订单金额人民币但是要自动汇率美金。

5. commission_rate_percent
   - 从截图中提取“佣金”人民币金额。
   - 计算公式：
     佣金率 % = 佣金金额 ÷ 订单总金额 × 100
   - 保留两位小数。

6. transaction_service_rate_percent
   - 提取“交易服务费”人民币金额。
   - 计算公式：
     交易服务费率 % = 交易服务费 ÷ 订单总金额 × 100
   - 保留两位小数。

7. incubation_service_rate_percent
   - 提取“基础孵化服务费”人民币金额。
   - 计算公式：
     基础孵化服务费率 % = 基础孵化服务费 ÷ 订单总金额 × 100
   - 保留两位小数。

8. order_total_usd
   - 使用 order_total_cny 金额
   - 使用支付时间（付款时间字段）
   - 按支付当天的历史汇率（CNY→USD）进行换算
   - 汇率必须通过系统接入的实时汇率API获取
   - 计算公式：
       USD = order_total_cny ÷ 当天CNY兑USD汇率
   - 保留两位小数

----------------------------------------
【严格规则】

- 禁止识别以下字段：
  商品成本
  实际运费
  包装费
  税费
  其他成本
  预付资金比例
  台币金额
  预计可得

- 若某字段缺失，返回 null
- 所有金额必须为数字类型
- 所有百分比必须为数字类型（不要带 % 符号）
- 不允许输出字符串格式百分比

----------------------------------------
【输出格式示例】

{
  "order_id": "1119289386952659",
  "buyer_name": "T***",
  "product_total_cny": 4813.20,
  "order_total_cny": 6272.95,
  "order_total_usd": 872.45,
  "commission_rate_percent": 8.18,
  "transaction_service_rate_percent": 2.50,
  "incubation_service_rate_percent": 1.53
}

仅输出 JSON。
不要输出解释文字。
不要添加任何额外内容。
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

        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.post(url, headers=headers, json=payload, timeout=60, verify=False)
        if response.status_code != 200:
            err_msg = response.text
            try:
                err_json = response.json()
                if "error" in err_json:
                    err_msg = err_json["error"].get("message", response.text)
            except:
                pass
            raise Exception(f"Gemini API 错误 ({response.status_code}): {err_msg}")
            
        res_json = response.json()
        
        candidates = res_json.get("candidates", [])
        if not candidates:
            raise Exception(f"模型未返回结果。可能是被安全拦截或图片不合规。\n返回数据: {res_json}")
            
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

