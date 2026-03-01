from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QRadioButton, QButtonGroup, 
                             QPushButton, QFileDialog, QFormLayout, 
                             QComboBox, QMessageBox)
from ui.i18n import get_text
from utils.style import APP_STYLE

class ProfileView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.image_path = None
        
        self.init_ui()
        
    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setSpacing(15)
        
        # Title
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.layout.addWidget(self.title_label)
        
        # Form Layout
        self.form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.form_layout.addRow(QLabel("Nickname:"), self.name_input)
        
        # Gender
        self.gender_layout = QHBoxLayout()
        self.male_btn = QRadioButton("Male")
        self.female_btn = QRadioButton("Female")
        self.female_btn.setChecked(True)
        self.gender_group = QButtonGroup()
        self.gender_group.addButton(self.male_btn)
        self.gender_group.addButton(self.female_btn)
        self.gender_layout.addWidget(self.male_btn)
        self.gender_layout.addWidget(self.female_btn)
        self.form_layout.addRow(QLabel("Gender:"), self.gender_layout)
        
        # Basic Stats
        self.height_input = QLineEdit("165")
        self.weight_input = QLineEdit("55")
        self.age_input = QLineEdit("25")
        self.city_input = QLineEdit("Beijing")
        
        self.form_layout.addRow(QLabel("Height:"), self.height_input)
        self.form_layout.addRow(QLabel("Weight:"), self.weight_input)
        self.form_layout.addRow(QLabel("Age:"), self.age_input)
        self.form_layout.addRow(QLabel("City:"), self.city_input)
        
        # Scene Selection
        self.scene_combo = QComboBox()
        self.scene_combo.addItems(["Business", "Casual", "Sport", "Wedding"])
        self.form_layout.addRow(QLabel("Scene:"), self.scene_combo)
        
        self.layout.addLayout(self.form_layout)
        
        # Upload Button
        self.upload_btn = QPushButton("Upload Photo")
        self.upload_btn.clicked.connect(self.upload_photo)
        self.upload_label = QLabel("")
        self.upload_label.setStyleSheet("color: green;")
        
        upload_layout = QHBoxLayout()
        upload_layout.addWidget(self.upload_btn)
        upload_layout.addWidget(self.upload_label)
        self.layout.addLayout(upload_layout)
        
        # Analyze Button
        self.analyze_btn = QPushButton("Analyze & Try-on")
        self.analyze_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        self.analyze_btn.clicked.connect(self.on_analyze)
        self.layout.addWidget(self.analyze_btn)
        
        self.setLayout(self.layout)
        self.setStyleSheet(APP_STYLE)
        
    def update_texts(self, lang):
        self.title_label.setText(get_text(lang, 'profile_title'))
        
        # Update Form Labels
        self.form_layout.labelForField(self.name_input).setText(get_text(lang, 'name'))
        self.form_layout.labelForField(self.gender_layout).setText(get_text(lang, 'gender'))
        self.male_btn.setText(get_text(lang, 'gender_m'))
        self.female_btn.setText(get_text(lang, 'gender_f'))
        
        self.form_layout.labelForField(self.height_input).setText(get_text(lang, 'height'))
        self.form_layout.labelForField(self.weight_input).setText(get_text(lang, 'weight'))
        self.form_layout.labelForField(self.age_input).setText(get_text(lang, 'age'))
        self.form_layout.labelForField(self.city_input).setText(get_text(lang, 'city'))
        
        self.form_layout.labelForField(self.scene_combo).setText(get_text(lang, 'scene'))
        # Note: In a real app we'd update combo box items safely
        
        self.upload_btn.setText(get_text(lang, 'upload_photo'))
        if self.image_path:
            self.upload_label.setText(get_text(lang, 'photo_uploaded'))
            
        self.analyze_btn.setText(get_text(lang, 'analyze_btn'))
        
    def upload_photo(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", 
                                                  "Images (*.png *.jpg *.jpeg)")
        if file_name:
            self.image_path = file_name
            lang = self.main_window.current_lang if self.main_window else 'en'
            self.upload_label.setText(get_text(lang, 'photo_uploaded'))
            
    def on_analyze(self):
        if not self.name_input.text() or not self.image_path:
            lang = self.main_window.current_lang if self.main_window else 'en'
            QMessageBox.warning(self, get_text(lang, 'error'), get_text(lang, 'error_missing_info'))
            return
            
        # Collect data
        data = {
            'name': self.name_input.text(),
            'gender': 'Female' if self.female_btn.isChecked() else 'Male',
            'height': float(self.height_input.text() or 165),
            'weight': float(self.weight_input.text() or 55),
            'age': int(self.age_input.text() or 25),
            'city': self.city_input.text(),
            'scene': self.scene_combo.currentText(),
            'image_path': self.image_path
        }
        
        if self.main_window:
            self.main_window.process_analysis(data)
