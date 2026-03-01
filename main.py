import os
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt

# Ensure the app can find the local modules when run from the main directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_db, get_db
from models.user import UserProfile
from ui.profile_view import ProfileView
from ui.recommendation_view import RecommendationView
from ui.i18n import get_text
from utils.style import APP_STYLE

from services.weather import get_realtime_weather
from services.analyzer import analyze_body_type
from services.stylist import get_styling_rules
from services.ecommerce import generate_recommendation_plan
from services.virtual_tryon import generate_virtual_tryon

class AIFashionArchitectApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_lang = 'zh'
        
        # Initialize Database
        init_db()
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("AI Fashion Architect")
        self.setMinimumSize(500, 700)
        self.setStyleSheet(APP_STYLE)
        
        # Main Widget and Layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Header (Language Toggle)
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lang_btn = QPushButton("English")
        self.lang_btn.setFixedWidth(80)
        self.lang_btn.clicked.connect(self.toggle_language)
        header_layout.addWidget(self.lang_btn)
        main_layout.addLayout(header_layout)
        
        # Stacked Widget for Views
        self.stacked_widget = QStackedWidget()
        
        self.profile_view = ProfileView(self)
        self.recommendation_view = RecommendationView(self)
        
        self.stacked_widget.addWidget(self.profile_view)        # Index 0
        self.stacked_widget.addWidget(self.recommendation_view) # Index 1
        
        main_layout.addWidget(self.stacked_widget)
        
        self.setCentralWidget(main_widget)
        
        # Initialize translations
        self.update_all_texts()

    def toggle_language(self):
        self.current_lang = 'en' if self.current_lang == 'zh' else 'zh'
        self.lang_btn.setText("English" if self.current_lang == 'zh' else "中文")
        self.update_all_texts()
        
    def update_all_texts(self):
        self.setWindowTitle(get_text(self.current_lang, 'app_title'))
        self.profile_view.update_texts(self.current_lang)
        self.recommendation_view.update_texts(self.current_lang)

    def switch_view(self, index: int):
        self.stacked_widget.setCurrentIndex(index)
        
    def process_analysis(self, user_data: dict):
        print(f"Starting analysis for: {user_data['name']}")
        
        # 1. Save to DB
        db = next(get_db())
        new_user = UserProfile(
            name=user_data['name'],
            gender=user_data['gender'],
            height=user_data['height'],
            weight=user_data['weight'],
            age=user_data['age'],
            city=user_data['city'],
            body_type="Pending"
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # 2. Get Weather
        weather = get_realtime_weather(user_data['city'])
        print(f"Weather info retrieved: {weather}")
        
        # 3. CV Analysis (Body Type)
        body_type = analyze_body_type(user_data['image_path'])
        print(f"Analyzed Body Type: {body_type}")
        
        # Update DB with body type
        new_user.body_type = body_type
        db.commit()
        db.close()
        
        cv_results = {"body_type": body_type}
        
        # 4. Styling Logic
        style_info = get_styling_rules(
            gender=user_data['gender'],
            body_type=body_type,
            temperature=weather['temp'],
            scene=user_data['scene']
        )
        print(f"Styling rules keys: {style_info}")
        
        # 5. E-commerce Integration
        plans = generate_recommendation_plan(style_info)
        
        # 6. Virtual Try-On (Mock) for all plans
        for plan in plans:
            tryon_res = generate_virtual_tryon(user_data['image_path'], plan)
            plan['tryon_image'] = tryon_res
            
        print("Analysis complete. Displaying results.")
        
        # Transition to Recommendation View
        self.recommendation_view.display_results(weather, cv_results, plans)
        self.switch_view(1)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Enable High DPI scaling
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        
    window = AIFashionArchitectApp()
    window.show()
    sys.exit(app.exec())
