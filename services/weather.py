import requests

def get_realtime_weather(city_name: str, api_key: str = "MOCK_KEY"):
    """
    Mock function to get realtime weather for a given city in China.
    In production, this would call QWeather API:
    https://devapi.qweather.com/v7/weather/now?location={city_id}&key={api_key}
    """
    # Simply mocking weather based on city keywords or random for now
    mock_data = {
        "Beijing": {"temp": 15.0, "text": "Sunny", "suggestion": "春秋穿搭，建议单衣加薄外套。 (Spring/Autumn wear, light jacket recommended.)"},
        "Shanghai": {"temp": 22.0, "text": "Cloudy", "suggestion": "初夏穿搭，建议短袖、透气材质。 (Early summer wear, short sleeves recommended.)"},
        "Guangzhou": {"temp": 30.0, "text": "Rainy", "suggestion": "盛夏穿搭，注意防晒和防雨，建议短袖短裤。 (Summer wear, short sleeves and shorts, bring an umbrella.)"},
        "Harbin": {"temp": -5.0, "text": "Snowy", "suggestion": "严冬穿搭，建议厚羽绒服，注意保暖。 (Winter wear, heavy down jacket recommended.)"}
    }
    
    # Fallback to a default spring weather if city not in mock data
    weather = mock_data.get(city_name, {"temp": 18.0, "text": "Clear", "suggestion": "舒适温度，建议长袖衬衫加休闲裤。 (Comfortable temperature, long-sleeved shirt and casual pants.)"})
    
    return weather
