def get_styling_rules(gender: str, body_type: str, temperature: float, scene: str):
    """
    Core engine that outputs the styling logic based on parameters.
    Returns keywords for searching ecommerce platforms.
    """
    keywords = []
    style_desc = ""
    
    # Simple rule engine mapping
    if gender.lower() == 'female':
        if scene == "Business":
            if "A-shape" in body_type:
                keywords = ["A字半身裙", "修身西装外套", "高跟鞋"] # A-line skirt, tailored blazer
                style_desc = "突出上半身线条，弱化臀部，展现干练职场风范。"
            else:
                keywords = ["阔腿裤套装", "真丝衬衫", "乐福鞋"]
                style_desc = "利落大气的干练职业套装。"
        elif scene == "Casual":
            if temperature > 25:
                keywords = ["法式碎花连衣裙", "草编凉鞋", "冰丝开衫"]
                style_desc = "清爽透气的夏日法式慵懒风。"
            else:
                keywords = ["直筒牛仔裤", "宽松卫衣", "帆布鞋"]
                style_desc = "舒适休闲的日常穿搭。"
        elif scene == "Sport":
            keywords = ["瑜伽裤", "速干运动背心", "跑鞋"]
            style_desc = "活力满满的运动装备。"
        elif scene == "Wedding":
            keywords = ["优雅晚礼服", "精美配饰", "细跟高跟鞋"]
            style_desc = "端庄优雅的宴会礼服。"
            
    else: # Male
        if scene == "Business":
            keywords = ["修身西服套装", "抗皱衬衫", "牛津鞋"]
            style_desc = "经典的商务正装搭配，展现专业形象。"
        elif scene == "Casual":
            if temperature > 25:
                keywords = ["纯棉短袖T恤", "休闲短裤", "小白鞋"]
                style_desc = "清爽的夏日街头风。"
            else:
                keywords = ["休闲夹克", "直筒牛仔裤", "马丁靴"]
                style_desc = "硬朗休闲的日常穿搭。"
        elif scene == "Sport":
            keywords = ["运动束脚裤", "透气运动T恤", "篮球鞋"]
            style_desc = "舒适排汗的运动风格。"
        elif scene == "Wedding":
            keywords = ["绅士礼服", "领结", "皮鞋"]
            style_desc = "得体庄重的婚礼着装。"
            
    # Default fallback
    if not keywords:
        keywords = ["休闲装", "百搭单品"]
        style_desc = "简约百搭的日常装扮。"
        
    return {"keywords": keywords, "description": style_desc}
