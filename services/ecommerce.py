def search_products(keywords: list):
    """
    Mock function to simulate searching e-commerce platforms (JD, Taobao, Douyin).
    Returns a list of mock product dictionaries based on keywords.
    """
    # Simply generate mock products based on the first keyword
    main_kw = keywords[0] if keywords else "推荐单品"
    
    products = [
        {
            "id": "jd_1001",
            "platform": "JD",
            "name": f"京东精选 - {main_kw}",
            "price": "￥299.00",
            "image": "https://img14.360buyimg.com/n0/jfs/t1/137699/33/19322/100067/5fa0d317E0db41487/cd3ee7c0419356ce.jpg", # Placeholder JD img
            "link": "https://www.jd.com"
        },
        {
            "id": "tb_2002",
            "platform": "Taobao",
            "name": f"淘宝热卖 - 优质{main_kw}",
            "price": "￥159.00",
            "image": "https://gw.alicdn.com/tfs/TB1J5jgSFXXXXapXXXXXXXXXXXX-350-350.jpg", # Placeholder TB img
            "link": "https://www.taobao.com"
        },
        {
            "id": "dy_3003",
            "platform": "Douyin",
            "name": f"抖音爆款 - 达人同款{main_kw}",
            "price": "￥99.00",
            "image": "https://p3.pstatp.com/origin/x-image/e11942bd957f4951b1f9afba905e94b2.jpeg", # Placeholder DY img
            "link": "https://www.douyin.com"
        }
    ]
    
    return products

def generate_recommendation_plan(styling_info: dict):
    """
    Generate a full recommendation album consisting of multiple plans.
    """
    keywords = styling_info.get("keywords", [])
    
    # Generate 3 variant plans based on the keywords
    album = []
    for i in range(1, 4):
        plan = {
            "plan_id": f"plan_{i}",
            "plan_name": f"方案 {chr(64+i)} ({styling_info.get('description', '推荐计划')})",
            "items": search_products(keywords), # Mock same products for now
        }
        album.append(plan)
        
    return album
