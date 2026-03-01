from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
                             QScrollArea, QHBoxLayout, QPushButton)
from PyQt6.QtCore import Qt
from ui.i18n import get_text
from utils.style import APP_STYLE

class RecommendationView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()
        
    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setSpacing(10)
        
        # Title
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.layout.addWidget(self.title_label)
        
        # Info Panel
        self.info_layout = QHBoxLayout()
        self.weather_label = QLabel()
        self.body_label = QLabel()
        self.info_layout.addWidget(self.weather_label)
        self.info_layout.addWidget(self.body_label)
        self.layout.addLayout(self.info_layout)
        
        # Scroll Area for Plans
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)
        
        # Back Button
        self.back_btn = QPushButton("← Back")
        self.back_btn.clicked.connect(self.go_back)
        self.layout.addWidget(self.back_btn)
        
        self.setLayout(self.layout)
        self.setStyleSheet(APP_STYLE)
        
    def update_texts(self, lang):
        self.title_label.setText(get_text(lang, 'result_title'))
        self.back_btn.setText("← Back" if lang == 'en' else "← 返回")
        
    def display_results(self, weather_info, cv_results, plans):
        lang = self.main_window.current_lang if self.main_window else 'en'
        
        # Update Info Panel
        w_text = f"{get_text(lang, 'weather_info')} {weather_info['temp']}°C, {weather_info['text']}"
        self.weather_label.setText(w_text)
        
        b_text = f"{get_text(lang, 'body_info')} {cv_results.get('body_type', 'Unknown')}"
        self.body_label.setText(b_text)
        
        # Clear previous plans
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        # Add new plans
        for plan in plans:
            plan_widget = QWidget()
            plan_layout = QVBoxLayout(plan_widget)
            plan_layout.setContentsMargins(10, 10, 10, 10)
            plan_widget.setStyleSheet("background-color: #f9f9f9; border-radius: 8px; border: 1px solid #ddd;")
            
            # Plan Title
            p_title = QLabel(f"<b>{plan['plan_name']}</b>")
            plan_layout.addWidget(p_title)
            
            # Items (Products)
            items_layout = QHBoxLayout()
            for item in plan['items']:
                item_widget = QWidget()
                item_vbox = QVBoxLayout(item_widget)
                
                # Mock image placeholder
                img_lbl = QLabel("[Image]")
                img_lbl.setFixedSize(80, 80)
                img_lbl.setStyleSheet("background-color: #eee; border: 1px solid #ccc;")
                img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                name_lbl = QLabel(item['name'])
                name_lbl.setWordWrap(True)
                price_lbl = QLabel(item['price'])
                price_lbl.setStyleSheet("color: #e53935; font-weight: bold;")
                
                btn = QPushButton(f"{item['platform']} - {get_text(lang, 'buy_link')}")
                btn.setStyleSheet("background-color: #ff9800; color: white;")
                
                item_vbox.addWidget(img_lbl)
                item_vbox.addWidget(name_lbl)
                item_vbox.addWidget(price_lbl)
                item_vbox.addWidget(btn)
                items_layout.addWidget(item_widget)
                
            plan_layout.addLayout(items_layout)
            
            # Mock Virtual Try-On Result
            tryon_lbl = QLabel("[Mock Virtual Try-On Image Here]")
            tryon_lbl.setFixedHeight(150)
            tryon_lbl.setStyleSheet("background-color: #e3f2fd; border: 1px dashed #2196f3; color: #1565c0;")
            tryon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            plan_layout.addWidget(tryon_lbl)
            
            self.scroll_layout.addWidget(plan_widget)
            
    def go_back(self):
        if self.main_window:
            self.main_window.switch_view(0) # 0 is profile index
