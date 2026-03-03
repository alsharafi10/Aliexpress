# -*- coding: utf-8 -*-
import customtkinter as ctk
from tkinter import messagebox, filedialog
import requests
import json
import pandas as pd
from datetime import datetime
import threading
import os
import logging
import hashlib
import random
import string
import sys
import threading
import os

# Ensure utils directory is in path (especially important for PyInstaller)
base_dir = os.path.dirname(__file__)
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
sys.path.append(os.path.join(base_dir, "utils"))

from utils.invoice_parser import parse_invoice_image
from utils import github_sync
from tkinter import filedialog
OCR_AVAILABLE = True

from config_manager import ConfigManager
from db_manager import DatabaseManager
from analytics_engine import AnalyticsEngine


# ================== 【阿拉伯语RTL修复】==================
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_FIX_AVAILABLE = True
except ImportError:
    ARABIC_FIX_AVAILABLE = False

def fix_arabic(text):
    """
    修复阿拉伯语在Matplotlib图表中的两个问题：
      1. 字母不连写  → arabic_reshaper 处理连字
      2. 词序/方向颠倒 → python-bidi get_display 处理BiDi算法
    对中文/英文无副作用，可无条件包裹所有语言标签。
    """
    if not ARABIC_FIX_AVAILABLE or not text or not isinstance(text, str):
        return text
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text
# ================== 【阿拉伯语修复结束】==================

# ================== 【新增】可视化 & 分析库 ==================
try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    # 【阿拉伯语字体配置】支持Arabic连字的字体列表
    matplotlib.rcParams['font.family'] = ['Arial', 'Tahoma', 'DejaVu Sans', 'sans-serif']
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
from collections import defaultdict
import calendar

logging.getLogger("customtkinter").setLevel(logging.ERROR)

USERS_FILE = "users.json"
LOGIN_DATA_FILE = "login_data.json"

# Managers
config_manager = ConfigManager()
db_manager = DatabaseManager()

# -------------------- دوال المساعدة --------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

ADMIN_PASSWORD_HASH = hash_password("EBOKNm^zn3!z5u5f")

def generate_random_password(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
            if "admin" in users and users["admin"]["password"] != ADMIN_PASSWORD_HASH:
                users["admin"]["password"] = ADMIN_PASSWORD_HASH
                save_users(users)
            return users
        except:
            return {"admin": {"password": ADMIN_PASSWORD_HASH, "role": "admin"}}
    return {"admin": {"password": ADMIN_PASSWORD_HASH, "role": "admin"}}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_login_data():
    if os.path.exists(LOGIN_DATA_FILE):
        try:
            with open(LOGIN_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_login_data(data):
    with open(LOGIN_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_live_exchange_rate(base_currency="USD"):
    try:
        response = requests.get(f"https://api.exchangerate-api.com/v4/latest/{base_currency}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data['rates']['CNY'], "exchangerate-api.com", datetime.now().strftime("%Y-%m-%d %H:%M")
    except:
        pass
    return 6.9398, "默认汇率", "2026-02-17"

EXCHANGE_RATE, RATE_SOURCE, RATE_DATE = get_live_exchange_rate(config_manager.get("base_currency", "USD"))

# -------------------- نافذة تسجيل الدخول (متعددة اللغات) --------------------
class LoginWindow(ctk.CTkFrame):
    def __init__(self, master, initial_lang="zh"):
        super().__init__(master)
        self.master.title("登录 - 速卖通财务系统")
        self.master.geometry("500x400")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.users = load_users()
        self.login_data = load_login_data()

        self.languages = {"中文": "zh", "English": "en", "العربية": "ar"}
        self.current_lang = initial_lang

        self.login_lang = {
            "zh": {
                "title": "💰 速卖通财务系统",
                "username": "用户名:",
                "password": "密码:",
                "remember": "记住我",
                "login_btn": "登录",
                "select_language": "选择语言:",
                "error": "用户名或密码错误"
            },
            "en": {
                "title": "💰 AliExpress Finance System",
                "username": "Username:",
                "password": "Password:",
                "remember": "Remember me",
                "login_btn": "Login",
                "select_language": "Language:",
                "error": "Invalid username or password"
            },
            "ar": {
                "title": "💰 النظام المالي لعلي إكسبريس",
                "username": "اسم المستخدم:",
                "password": "كلمة المرور:",
                "remember": "تذكرني",
                "login_btn": "تسجيل الدخول",
                "select_language": "اختر اللغة:",
                "error": "اسم المستخدم أو كلمة المرور غير صحيحة"
            }
        }

        self.create_login_ui()

    def ltr(self, key):
        """LoginWindow翻译方法，阿拉伯语自动修复RTL"""
        text = self.login_lang.get(self.current_lang, {}).get(key, key)
        if self.current_lang == "ar":
            return fix_arabic(text)
        return text

    def create_login_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self, text=self.ltr("title"),
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)

        lang_frame = ctk.CTkFrame(self, fg_color="transparent")
        lang_frame.pack(pady=5)

        ctk.CTkLabel(lang_frame, text=self.ltr("select_language"),
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=5)

        self.lang_combo = ctk.CTkComboBox(lang_frame, values=list(self.languages.keys()),
                                          command=self.change_login_language, width=120)
        for name, code in self.languages.items():
            if code == self.current_lang:
                self.lang_combo.set(name)
                break
        self.lang_combo.pack(side="left", padx=5)

        ctk.CTkLabel(self, text=self.ltr("username"),
                     font=ctk.CTkFont(size=14)).pack(pady=(20,5))
        
        # 将用户名输入框改为下拉框，以便选择之前记住的用户
        saved_users = list(self.login_data.get("saved_users", {}).keys())
        self.entry_username = ctk.CTkComboBox(self, width=250, values=saved_users, command=self.on_username_selected)
        self.entry_username.pack(pady=5)
        # Bind key release to update password if user types a known username manually
        # Disabled because CustomTkinter ComboBox crashes with "Can't find filter element" on KeyRelease bindings
        # self.entry_username.bind("<KeyRelease>", self.on_username_typed)

        ctk.CTkLabel(self, text=self.ltr("password"),
                     font=ctk.CTkFont(size=14)).pack(pady=5)
        
        pw_frame = ctk.CTkFrame(self, fg_color="transparent")
        pw_frame.pack(pady=5)
        
        self.entry_password = ctk.CTkEntry(pw_frame, width=220, show="*")
        self.entry_password.pack(side="left")
        
        self.show_pw = False
        self.btn_toggle_pw = ctk.CTkButton(pw_frame, text="👁️", width=30, command=self.toggle_password_visibility, fg_color="transparent", hover_color="#333333")
        self.btn_toggle_pw.pack(side="left", padx=(5,0))

        self.remember_var = ctk.BooleanVar(value=False)
        self.remember_check = ctk.CTkCheckBox(self, text=self.ltr("remember"),
                                              variable=self.remember_var)
        self.remember_check.pack(pady=5)

        self.btn_login = ctk.CTkButton(self, text=self.ltr("login_btn"),
                                       command=self.login, width=150, height=40)
        self.btn_login.pack(pady=10)

        if "last_username" in self.login_data:
            last_user = self.login_data["last_username"]
            self.entry_username.set(last_user)
            self.on_username_selected(last_user) # Auto-fill password if remembered

        self.master.bind('<Return>', lambda e: self.login())

    def on_username_selected(self, username):
        """当从下拉框选择用户时，自动填充密码和勾选状态"""
        saved_users = self.login_data.get("saved_users", {})
        if username in saved_users:
            self.entry_password.delete(0, 'end')
            self.entry_password.insert(0, saved_users[username].get("password", ""))
            self.remember_var.set(True)
        else:
            self.entry_password.delete(0, 'end')
            self.remember_var.set(False)

    def on_username_typed(self, event):
        """手动输入用户名时，如果匹配到已保存的用户，也自动填充"""
        username = self.entry_username.get().strip()
        self.on_username_selected(username)

    def toggle_password_visibility(self):
        self.show_pw = not self.show_pw
        if self.show_pw:
            self.entry_password.configure(show="")
            # Text crossed-out eye can be tricky on some fonts, let's use a standard unicode variant or text
            self.btn_toggle_pw.configure(text="🔒") 
        else:
            self.entry_password.configure(show="*")
            self.btn_toggle_pw.configure(text="👁️")

    def change_login_language(self, choice):
        self.current_lang = self.languages[choice]
        self.create_login_ui()

    def login(self):
        username = self.entry_username.get().strip()
        password = self.entry_password.get().strip()
        if username in self.users and self.users[username]["password"] == hash_password(password):
            # 获取当前的 saved_users 字典，如果没有则创建一个新的
            saved_users = self.login_data.get("saved_users", {})
            
            if self.remember_var.get():
                # 更新或添加该用户的密码
                saved_users[username] = {"password": password}
            else:
                # 如果取消勾选记住我，则从记录中删除该用户
                if username in saved_users:
                    del saved_users[username]
                    
            # 更新整体的 login_data
            self.login_data["last_username"] = username
            self.login_data["saved_users"] = saved_users
            save_login_data(self.login_data)
            
            self.auth_success = True
            self.username = username
            self.role = self.users[username]["role"]
            self.master.quit()
        else:
            messagebox.showerror(self.ltr("error"),
                                 self.ltr("error"))

# -------------------- نافذة تغيير كلمة المرور --------------------
class ChangePasswordDialog(ctk.CTkToplevel):
    def __init__(self, parent, username, current_password_hash=None, on_save_callback=None):
        super().__init__(parent)
        self.username = username
        self.current_password_hash = current_password_hash
        self.on_save_callback = on_save_callback
        self.parent_lang = parent.current_lang
        self.parent_dict = parent.lang_dict

        self.title(self.tr("change_password_title"))
        self.geometry("400x250")
        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_force()

        ctk.CTkLabel(self, text=f"{self.tr('user')}: {username}",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(frame, text=self.tr("new_password"), font=ctk.CTkFont(size=14)).pack(anchor="w")
        self.new_password_entry = ctk.CTkEntry(frame, width=200, show="")
        self.new_password_entry.pack(pady=5, fill="x")

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5)

        self.random_btn = ctk.CTkButton(btn_frame, text=self.tr("random_password"),
                                        command=self.generate_random, width=150)
        self.random_btn.pack(side="left", padx=5)

        self.save_btn = ctk.CTkButton(self, text=self.tr("save"), command=self.save,
                                      width=100, fg_color="#32CD32")
        self.save_btn.pack(pady=10)

    def tr(self, key):
        if hasattr(self, 'parent_dict') and self.parent_lang in self.parent_dict:
            text = self.parent_dict[self.parent_lang].get(key, key)
            if self.parent_lang == "ar":
                return fix_arabic(text)
            return text
        return key

    def generate_random(self):
        random_pw = generate_random_password()
        self.new_password_entry.delete(0, 'end')
        self.new_password_entry.insert(0, random_pw)

    def save(self):
        new_pw = self.new_password_entry.get().strip()
        if not new_pw:
            messagebox.showerror(self.tr("error"), self.tr("password_empty"))
            return
        if self.on_save_callback:
            self.on_save_callback(self.username, new_pw)
        self.destroy()

# -------------------- التطبيق الرئيسي --------------------
class FinanceSystemApp(ctk.CTkFrame):
    def __init__(self, master, username, role, initial_lang="zh"):
        super().__init__(master)

        self.username = username
        self.role = role
        self.master.geometry("1400x900")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.exchange_rate = EXCHANGE_RATE
        self.rate_source = RATE_SOURCE
        self.rate_date = RATE_DATE
        # Transactions are now loaded via db_manager when needed, not stored in memory
        
        # Base currency from config
        self.base_currency = config_manager.get("base_currency", "USD")

        self.languages = {"中文": "zh", "English": "en", "العربية": "ar"}
        # Use config for language, fallback to initial_lang
        self.current_lang = config_manager.get("language", initial_lang)

        self.lang_dict = {
            "zh": {
                "app_title": "📊 速卖通财务系统 (专业版)",
                "rate_label": "💱 当前汇率: 1 USD = {} CNY  |  来源: {}  |  更新: {}",
                "refresh_btn": "🔄 更新汇率",
                "select_language": "选择语言:",
                "main_tab": "📝 主计算",
                "compare_tab": "📊 方案比较",
                "log_tab": "📋 交易记录",
                "alerts_tab": "🚨 亏损预警",
                "batch_import": "📥 批量导入(Excel)",
                "import_success": "成功导入 {} 条交易数据!",
                "import_error": "导入失败，请检查文件格式。错误: {}",
                "no_alerts": "✅ 暂无低利润(亏损)订单，运营状况良好！",
                "margin_threshold": "预警阈值 (%):",
                "order_info": "📋 订单信息",
                "date": "日期:",
                "buyer": "买家账号:",
                "order_id": "订单号:",
                "product_id": "商品ID:",
                "order_amount": "🛒 订单金额",
                "gross_order": "订单总金额 (USD):",
                "funding_percent": "预付资金比例 (%):",
                "funding_amount": "预付资金金额 (USD):",
                "platform_fees": "📈 平台费用 (CNY)",
                "commission": "佣金率 (%):",
                "service_fee": "交易服务费率 (%):",
                "affiliate_fee": "基础孵化服务费率 (%):",
                "other_costs": "📦 其他成本",
                "cogs": "商品成本 (COGS):",
                "shipping": "实际运费:",
                "packaging": "包装费:",
                "tax": "税费:",
                "calc_btn": "📊 计算利润",
                "save_btn": "💾 保存交易",
                "reset_btn": "🔄 重置",
                "compare_title": "📊 多方案比较",
                "compare_label": "输入多个融资比例 (用逗号分隔，例如: 50,60,65):",
                "compare_btn": "🔍 比较",
                "export_btn": "📥 导出所有交易到 Excel",
                "refresh_log_btn": "🔄 刷新记录",
                "no_transactions": "暂无交易记录",
                "warning_calc_first": "请先计算利润再保存",
                "warning_fill_buyer_order": "请输入买家账号和订单号",
                "success_saved": "交易 {} 已保存",
                "warning_no_data_export": "没有交易记录可导出",
                "success_exported": "已导出到 {}",
                "error_invalid_number": "请输入有效的数字",
                "error_compare": "比较失败: {}",
                "success_rate_updated": "汇率已更新: 1 USD = {:.4f} CNY",
                "warning_low_margin": "⚠️  警告：利润率低于10%！",
                "best_scheme": "🏆 最佳方案: {}  (净利润: {})",
                "profit_margin": "利润率",
                "net_profit": "净利润(USD)",
                "funding_usd": "融资金额(USD)",
                "funding_ratio": "融资比例",
                "total_fees": "费用总计",
                "payout": "预计可得",
                "total_costs": "成本总计",
                "edit": "编辑",
                "delete": "删除",
                "confirm_delete": "确定要删除此交易吗？",
                "admin_panel": "👑 管理员面板",
                "add_user": "添加用户",
                "username": "用户名",
                "password": "密码",
                "role": "角色",
                "user": "用户",
                "admin": "管理员",
                "existing_users": "现有用户",
                "delete_user": "删除用户",
                "filter_user": "用户:",
                "all_users": "所有用户",
                "logout": "🚪 注销",
                "welcome": "欢迎, {}",
                "random_password": "随机密码",
                "change_password": "修改密码",
                "new_password": "新密码",
                "save": "保存",
                "password_empty": "密码不能为空",
                "change_password_title": "修改密码",
                "edit_user": "编辑用户",
                "error": "错误",
                # ===== 【新增】分析报告相关 =====
                "analytics_tab": "📈 深度分析",
                "profit_trend": "📈 利润趋势折线图",
                "cost_pie": "🥧 费用构成饼图",
                "period_report": "📊 月度/季度/年度汇总",
                "customer_analysis": "👥 客户分析",
                "product_analysis": "📦 产品利润率排行",
                "show_trend": "📈 显示利润趋势图",
                "show_pie": "🥧 显示费用饼图",
                "show_period": "📊 生成汇总报表",
                "show_customer": "👥 客户贡献分析",
                "show_product": "📦 产品利润率排行",
                "period_monthly": "月度",
                "period_quarterly": "季度",
                "period_yearly": "年度",
                "export_report_btn": "📥 导出含分析报告的Excel",
                "no_data_analysis": "暂无足够数据进行分析",
                "customer_freq": "交易次数",
                "customer_total": "累计净利润(USD)",
                "customer_avg": "平均净利润(USD)",
                "product_margin": "平均利润率(%)",
                "product_profit": "总净利润(USD)",
                "product_orders": "订单数",
                "period_label": "周期",
                "period_gross": "总订单额(USD)",
                "period_profit": "总净利润(USD)",
                "period_margin": "平均利润率(%)",
                "period_orders": "订单数",
                "analytics_not_available": "请先安装 matplotlib: pip install matplotlib",
                "ocr_btn": "📸 自动识别 AliExpress 订单截图填表",
                "eg_buyer": "例如: buyer123",
                "eg_order_id": "例如: 123456789",
                "eg_product_id": "例如: P001",
                "eg_amount": "例如: 27.07",
                "api_key_btn": "🔑设置API密钥"
            },
            "en": {
                "app_title": "📊 AliExpress Finance System (Pro)",
                "rate_label": "💱 Exchange Rate: 1 USD = {} CNY  |  Source: {}  |  Updated: {}",
                "refresh_btn": "🔄 Refresh Rate",
                "select_language": "Language:",
                "main_tab": "📝 Main",
                "compare_tab": "📊 Compare",
                "log_tab": "📋 Log",
                "order_info": "📋 Order Info",
                "date": "Date:",
                "buyer": "Buyer Account:",
                "order_id": "Order ID:",
                "product_id": "Product ID:",
                "order_amount": "🛒 Order Amount",
                "gross_order": "Gross Order (USD):",
                "funding_percent": "Funding Percent (%):",
                "funding_amount": "Funding Amount (USD):",
                "platform_fees": "📈 Platform Fees (CNY)",
                "commission": "Commission Rate (%):",
                "service_fee": "Service Fee Rate (%):",
                "affiliate_fee": "Affiliate Fee Rate (%):",
                "other_costs": "📦 Other Costs",
                "cogs": "COGS:",
                "shipping": "Shipping:",
                "packaging": "Packaging:",
                "tax": "Tax:",
                "calc_btn": "📊 Calculate Profit",
                "save_btn": "💾 Save Transaction",
                "reset_btn": "🔄 Reset",
                "compare_title": "📊 Compare Scenarios",
                "compare_label": "Enter funding percentages (comma separated, e.g., 50,60,65):",
                "compare_btn": "🔍 Compare",
                "export_btn": "📥 Export All to Excel",
                "refresh_log_btn": "🔄 Refresh Log",
                "no_transactions": "No transactions",
                "warning_calc_first": "Please calculate profit first",
                "warning_fill_buyer_order": "Please enter buyer account and order ID",
                "success_saved": "Transaction {} saved",
                "warning_no_data_export": "No transactions to export",
                "success_exported": "Exported to {}",
                "error_invalid_number": "Please enter valid numbers",
                "error_compare": "Comparison failed: {}",
                "success_rate_updated": "Exchange rate updated: 1 USD = {:.4f} CNY",
                "warning_low_margin": "⚠️  Warning: Profit margin below 10%!",
                "best_scheme": "🏆 Best: {}  (Net Profit: {})",
                "profit_margin": "Margin",
                "net_profit": "Net Profit(USD)",
                "funding_usd": "Funding(USD)",
                "funding_ratio": "Funding %",
                "total_fees": "Total Fees",
                "payout": "Estimated Payout",
                "total_costs": "Total Costs",
                "edit": "Edit",
                "delete": "Delete",
                "confirm_delete": "Are you sure you want to delete this transaction?",
                "admin_panel": "👑 Admin Panel",
                "add_user": "Add User",
                "username": "Username",
                "password": "Password",
                "role": "Role",
                "user": "User",
                "admin": "Admin",
                "existing_users": "Existing Users",
                "delete_user": "Delete User",
                "filter_user": "User:",
                "all_users": "All Users",
                "logout": "🚪 Logout",
                "welcome": "Welcome, {}",
                "random_password": "Random Password",
                "change_password": "Change Password",
                "new_password": "New Password",
                "save": "Save",
                "password_empty": "Password cannot be empty",
                "change_password_title": "Change Password",
                "edit_user": "Edit User",
                "error": "Error",
                # ===== 【新增】Analytics =====
                "analytics_tab": "📈 Analytics",
                "profit_trend": "📈 Profit Trend Chart",
                "cost_pie": "🥧 Cost Breakdown Pie",
                "period_report": "📊 Monthly/Quarterly/Yearly Summary",
                "customer_analysis": "👥 Customer Analysis",
                "product_analysis": "📦 Product Margin Ranking",
                "show_trend": "📈 Show Profit Trend",
                "show_pie": "🥧 Show Cost Pie Chart",
                "show_period": "📊 Generate Period Report",
                "show_customer": "👥 Customer Contribution",
                "show_product": "📦 Product Margin Ranking",
                "period_monthly": "Monthly",
                "period_quarterly": "Quarterly",
                "period_yearly": "Yearly",
                "export_report_btn": "📥 Export Excel with Analysis Report",
                "no_data_analysis": "Not enough data for analysis",
                "customer_freq": "Transactions",
                "customer_total": "Total Net Profit(USD)",
                "customer_avg": "Avg Net Profit(USD)",
                "product_margin": "Avg Margin(%)",
                "product_profit": "Total Profit(USD)",
                "product_orders": "Orders",
                "period_label": "Period",
                "period_gross": "Total Gross(USD)",
                "period_profit": "Total Net Profit(USD)",
                "period_margin": "Avg Margin(%)",
                "period_orders": "Orders",
                "analytics_not_available": "Please install matplotlib: pip install matplotlib",
                "alerts_tab": "🚨 Loss Alerts",
                "ocr_btn": "📸 Auto-Extract AliExpress Order Image",
                "eg_buyer": "e.g., buyer123",
                "eg_order_id": "e.g., 123456789",
                "eg_product_id": "e.g., P001",
                "eg_amount": "e.g., 27.07",
                "api_key_btn": "🔑 Set API Key"
            },
            "ar": {
                "app_title": "📊 النظام المالي لعلي إكسبريس (احترافي)",
                "rate_label": "💱 سعر الصرف: 1 دولار = {} يوان  |  المصدر: {}  |  آخر تحديث: {}",
                "refresh_btn": "🔄 تحديث السعر",
                "select_language": "اختر اللغة:",
                "main_tab": "📝 الرئيسية",
                "compare_tab": "📊 مقارنة",
                "log_tab": "📋 السجل",
                "order_info": "📋 معلومات الطلب",
                "date": "التاريخ:",
                "buyer": "حساب المشتري:",
                "order_id": "رقم الطلب:",
                "product_id": "معرف المنتج:",
                "order_amount": "🛒 قيمة الطلب",
                "gross_order": "إجمالي الطلب (دولار):",
                "funding_percent": "نسبة التمويل المسبق (%):",
                "funding_amount": "قيمة التمويل المسبق (دولار):",
                "platform_fees": "📈 رسوم المنصة (يوان)",
                "commission": "نسبة العمولة (%):",
                "service_fee": "نسبة رسوم الخدمة (%):",
                "affiliate_fee": "نسبة رسوم الترويج (%):",
                "other_costs": "📦 تكاليف أخرى",
                "cogs": "تكلفة البضاعة:",
                "shipping": "الشحن الفعلي:",
                "packaging": "التغليف:",
                "tax": "الضرائب:",
                "calc_btn": "📊 حساب الربح",
                "save_btn": "💾 حفظ العملية",
                "reset_btn": "🔄 إعادة تعيين",
                "compare_title": "📊 مقارنة السيناريوهات",
                "compare_label": "أدخل نسب التمويل المسبق (مفصولة بفواصل، مثال: 50,60,65):",
                "compare_btn": "🔍 مقارنة",
                "export_btn": "📥 تصدير الكل إلى Excel",
                "refresh_log_btn": "🔄 تحديث السجل",
                "no_transactions": "لا توجد عمليات",
                "warning_calc_first": "يرجى حساب الربح أولاً",
                "warning_fill_buyer_order": "يرجى إدخال حساب المشتري ورقم الطلب",
                "success_saved": "تم حفظ العملية {}",
                "warning_no_data_export": "لا توجد عمليات للتصدير",
                "success_exported": "تم التصدير إلى {}",
                "error_invalid_number": "يرجى إدخال أرقام صحيحة",
                "error_compare": "فشلت المقارنة: {}",
                "success_rate_updated": "تم تحديث سعر الصرف: 1 دولار = {:.4f} يوان",
                "warning_low_margin": "⚠️  تحذير: هامش الربح أقل من 10%!",
                "best_scheme": "🏆 أفضل سيناريو: {}  (صافي الربح: {})",
                "profit_margin": "هامش الربح",
                "net_profit": "صافي الربح(دولار)",
                "funding_usd": "التمويل(دولار)",
                "funding_ratio": "نسبة التمويل",
                "total_fees": "إجمالي الرسوم",
                "payout": "المتوقع تحصيله",
                "total_costs": "إجمالي التكاليف",
                "edit": "تعديل",
                "delete": "حذف",
                "confirm_delete": "هل أنت متأكد من حذف هذه العملية؟",
                "admin_panel": "👑 لوحة التحكم",
                "add_user": "إضافة مستخدم",
                "username": "اسم المستخدم",
                "password": "كلمة المرور",
                "role": "الدور",
                "user": "مستخدم",
                "admin": "مدير",
                "existing_users": "المستخدمون الحاليون",
                "delete_user": "حذف المستخدم",
                "filter_user": "المستخدم:",
                "all_users": "جميع المستخدمين",
                "logout": "🚪 تسجيل الخروج",
                "welcome": "مرحباً, {}",
                "random_password": "كلمة مرور عشوائية",
                "change_password": "تغيير كلمة المرور",
                "new_password": "كلمة المرور الجديدة",
                "save": "حفظ",
                "password_empty": "كلمة المرور لا يمكن أن تكون فارغة",
                "change_password_title": "تغيير كلمة المرور",
                "edit_user": "تعديل المستخدم",
                "error": "خطأ",
                # ===== 【新增】التحليل =====
                "analytics_tab": "📈 التحليلات",
                "profit_trend": "📈 مخطط اتجاه الربح",
                "cost_pie": "🥧 دائرة توزيع التكاليف",
                "period_report": "📊 ملخص شهري/ربعي/سنوي",
                "customer_analysis": "👥 تحليل العملاء",
                "product_analysis": "📦 ترتيب هامش المنتجات",
                "show_trend": "📈 عرض مخطط الاتجاه",
                "show_pie": "🥧 عرض الدائرة",
                "show_period": "📊 إنشاء تقرير الفترة",
                "show_customer": "👥 مساهمة العملاء",
                "show_product": "📦 ترتيب هامش المنتجات",
                "period_monthly": "شهري",
                "period_quarterly": "ربعي",
                "period_yearly": "سنوي",
                "export_report_btn": "📥 تصدير Excel مع التحليل",
                "no_data_analysis": "لا توجد بيانات كافية للتحليل",
                "customer_freq": "المعاملات",
                "customer_total": "إجمالي الربح(دولار)",
                "customer_avg": "متوسط الربح(دولار)",
                "product_margin": "متوسط الهامش(%)",
                "product_profit": "إجمالي الربح(دولار)",
                "product_orders": "الطلبات",
                "period_label": "الفترة",
                "period_gross": "إجمالي الطلبات(دولار)",
                "period_profit": "إجمالي الربح(دولار)",
                "period_margin": "متوسط الهامش(%)",
                "period_orders": "الطلبات",
                "analytics_not_available": "يرجى تثبيت matplotlib: pip install matplotlib",
                "alerts_tab": "🚨 تنبيهات الخسائر",
                "ocr_btn": "📸 استخراج تلقائي لبيانات طلب AliExpress",
                "eg_buyer": "مثال: buyer123",
                "eg_order_id": "مثال: 123456789",
                "eg_product_id": "مثال: P001",
                "eg_amount": "مثال: 27.07",
                "api_key_btn": "🔑 تعيين مفتاح API"
            }
        }

        # 设置窗口标题
        app_title = self.lang_dict.get(self.current_lang, {}).get("app_title", "Finance System")
        self.master.title(app_title)

        self.create_ui()
        self.sync_from_github_bg()
        self._last_data_hash = None  # 用于检测数据是否有变化
        self.start_periodic_sync()  # 启动定时同步

    def sync_from_github_bg(self):
        def _sync():
            try:
                token = config_manager.get("github_token", "")
                data = github_sync.download_data(token)
                if data is not None:
                    # 计算远程数据的哈希值
                    import hashlib
                    data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
                    new_hash = hashlib.md5(data_str.encode('utf-8')).hexdigest()
                    
                    # 如果数据没有变化，跳过更新
                    if self._last_data_hash is not None and new_hash == self._last_data_hash:
                        return
                    
                    self._last_data_hash = new_hash
                    
                    # Overwrite local database with remote json
                    with db_manager.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM transactions")
                        conn.commit()
                    for t in data:
                        db_manager.insert_transaction(t)
                    # Refresh UI in the main thread
                    if hasattr(self, 'refresh_transaction_log'):
                        self.after(0, self.refresh_transaction_log)
            except Exception as e:
                print("GitHub sync download error:", e)
        threading.Thread(target=_sync, daemon=True).start()

    def start_periodic_sync(self):
        """启动定时同步，每5分钟自动从 GitHub 检查数据更新"""
        self._sync_interval_ms = 5 * 60 * 1000  # 5分钟 = 300000毫秒
        self._periodic_sync_tick()

    def _periodic_sync_tick(self):
        """定时同步的回调函数"""
        try:
            self.sync_from_github_bg()
        except Exception as e:
            print("Periodic sync error:", e)
        # 安排下一次同步
        try:
            self.after(self._sync_interval_ms, self._periodic_sync_tick)
        except Exception:
            pass  # 窗口已关闭，忽略

    def sync_to_github_bg(self):
        if self.role != "admin":
            return
        def _sync():
            try:
                token = config_manager.get("github_token", "")
                if token:
                    transactions = db_manager.get_all_transactions()
                    github_sync.upload_data(transactions, token)
                    # 上传后更新本地哈希，避免下次轮询时重复刷新
                    import hashlib
                    data_str = json.dumps(transactions, sort_keys=True, ensure_ascii=False)
                    self._last_data_hash = hashlib.md5(data_str.encode('utf-8')).hexdigest()
            except Exception as e:
                print("GitHub sync upload error:", e)
        threading.Thread(target=_sync, daemon=True).start()


    def tr(self, key, default=None):
        """获取翻译文本，阿拉伯语自动修复RTL/连字显示"""
        text = self.lang_dict.get(self.current_lang, {}).get(key, default if default else key)
        if self.current_lang == "ar" and '{}' not in text and '{:' not in text:
            return fix_arabic(text)
        return text

    def trf(self, key, *args):
        """获取翻译文本并format，阿拉伯语在format后再修复RTL"""
        text = self.lang_dict.get(self.current_lang, {}).get(key, key)
        try:
            text = text.format(*args)
        except Exception:
            pass
        if self.current_lang == "ar":
            return fix_arabic(text)
        return text

    def create_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.current_result = None

        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(pady=10, padx=20, fill="x")

        # UI Priority 1: API Key Button (Rightmost element)
        if OCR_AVAILABLE:
            self.api_key_btn = ctk.CTkButton(self.top_frame, text=self.tr("api_key_btn"), width=120, fg_color="#8B008B", hover_color="#4B0082", command=self.set_api_key)
            self.api_key_btn.pack(side="right", padx=5)

        self.github_token_btn = ctk.CTkButton(self.top_frame, text="🔑 GitHub Token", width=120, fg_color="#2EA043", hover_color="#238636", command=self.set_github_token)
        self.github_token_btn.pack(side="right", padx=5)

        # UI Priority 2: User Settings grouping (Next rightmost)
        right_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        right_frame.pack(side="right", padx=10)

        welcome_text = self.trf("welcome", self.username)
        self.welcome_label = ctk.CTkLabel(right_frame, text=welcome_text, font=ctk.CTkFont(size=12), text_color="#FFA07A")
        self.welcome_label.pack(side="left", padx=5)

        self.logout_btn = ctk.CTkButton(right_frame, text=self.tr("logout"),
                                        command=self.logout, width=80, height=30,
                                        fg_color="#8B3A3A", hover_color="#6B2A2A")
        self.logout_btn.pack(side="left", padx=5)

        # Base Currency 
        curr_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        curr_frame.pack(side="left", padx=5)
        self.curr_combo = ctk.CTkComboBox(curr_frame, values=["USD", "EUR", "GBP", "SAR", "AED"],
                                          command=self.change_currency, width=70)
        self.curr_combo.set(self.base_currency)
        self.curr_combo.pack(side="left", padx=5)

        # Theme Toggle
        theme_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        theme_frame.pack(side="left", padx=5)
        self.theme_btn = ctk.CTkButton(theme_frame, text="☀️/🌙", width=40, height=30, command=self.toggle_theme)
        self.theme_btn.pack(side="left", padx=5)
        # Apply initial theme
        self.apply_theme(config_manager.get("theme", "dark"))

        lang_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        lang_frame.pack(side="left", padx=5)

        self.lang_select_label = ctk.CTkLabel(lang_frame, text=self.tr("select_language"),
                                              font=ctk.CTkFont(size=12))
        self.lang_select_label.pack(side="left", padx=5)

        self.lang_combo = ctk.CTkComboBox(lang_frame, values=list(self.languages.keys()),
                                          command=self.change_language, width=100)
        for name, code in self.languages.items():
            if code == self.current_lang:
                self.lang_combo.set(name)
                break
        self.lang_combo.pack(side="left", padx=5)

        # UI Priority 3: Action Buttons (Next rightmost)
        self.refresh_btn = ctk.CTkButton(self.top_frame, text=self.tr("refresh_btn"),
                                         command=self.refresh_exchange_rate, width=120)
        self.refresh_btn.pack(side="right", padx=10)

        self.batch_import_btn = ctk.CTkButton(self.top_frame, text=self.tr("batch_import"),
                                              command=self.batch_import_excel, width=120, fg_color="#20B2AA", hover_color="#008080")
        self.batch_import_btn.pack(side="right", padx=5)

        # UI Priority 4: Rate Label (Leftmost element, acts as filler)
        rate_text = self.trf("rate_label", f"{self.exchange_rate:.4f}", self.rate_source, self.rate_date)
        self.rate_label = ctk.CTkLabel(self.top_frame, text=rate_text, font=ctk.CTkFont(size=14), text_color="#87CEEB")
        self.rate_label.pack(side="left", padx=10)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(pady=10, padx=20, fill="both", expand=True)

        self.tab_main = self.tabview.add(self.tr("main_tab"))
        self.tab_compare = self.tabview.add(self.tr("compare_tab"))
        self.tab_log = self.tabview.add(self.tr("log_tab"))
        self.tab_alerts = self.tabview.add(self.tr("alerts_tab"))
        # ===== 【新增】深度分析页签 =====
        self.tab_analytics = self.tabview.add(self.tr("analytics_tab"))

        if self.role == "admin":
            self.tab_admin = self.tabview.add(self.tr("admin_panel"))
            self.create_admin_tab()

        self.create_main_tab()
        self.create_compare_tab()
        self.create_log_tab()
        self.create_alerts_tab()
        # ===== 【新增】=====
        self.create_analytics_tab()

        self.update_funding_value()
        self.refresh_transaction_log()
        # self.update_alignment()

    def logout(self):
        self.logout_requested = True
        self.master.quit()

    def change_currency(self, choice):
        self.base_currency = choice
        config_manager.set("base_currency", choice)
        self.refresh_exchange_rate()

    def toggle_theme(self):
        current = config_manager.get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        config_manager.set("theme", new_theme)
        self.apply_theme(new_theme)

    def apply_theme(self, theme):
        if theme == "light":
            ctk.set_appearance_mode("light")
        else:
            ctk.set_appearance_mode("dark")

    def change_language(self, choice):
        self.current_lang = self.languages[choice]
        config_manager.set("language", self.current_lang)
        self.create_ui()

    def set_api_key(self):
        dialog = ctk.CTkInputDialog(text="请在此输入您的专属 Gemini API Key:\n如果您没有，请前往 aistudio.google.com/app/apikey 免费申请", title="配置 API 密钥")
        key = dialog.get_input()
        if key is not None:
            if key.strip() == "":
                messagebox.showwarning("提示", "API 密钥不能为空！系统将继续使用内置安全默认密钥。")
            else:
                config_manager.set("gemini_api_key", key.strip())
                messagebox.showinfo("成功", "您的自定义 API 密钥已成功保存并立即生效！\n之后所有的订单截图都将采用您的专属密钥进行识别。")

    def set_github_token(self):
        dialog = ctk.CTkInputDialog(text="请在此输入您的 GitHub Personal Access Token:\n用于同步数据到远程仓库", title="配置 GitHub Token")
        key = dialog.get_input()
        if key is not None:
            config_manager.set("github_token", key.strip())
            messagebox.showinfo("成功", "GitHub Token 已保存！")
            self.sync_from_github_bg()  # 尝试立刻同步

    def update_alignment(self):
        if self.current_lang == "ar":
            self._apply_rtl(self)
        else:
            self._apply_ltr(self)

    def _apply_rtl(self, widget, visited=None):
        if visited is None:
            visited = set()
        
        # Prevent infinite recursion if widgets loop back
        widget_id = id(widget)
        if widget_id in visited:
            return
        visited.add(widget_id)
        
        # Grid compatibility bypass
        if getattr(widget, 'no_rtl', False):
            return
            
        try:
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(anchor="e", justify="right")
            elif isinstance(widget, ctk.CTkTextbox):
                widget.configure(wrap="word")
            for child in widget.winfo_children():
                self._apply_rtl(child, visited)
        except Exception:
            pass

    def _apply_ltr(self, widget):
        try:
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(anchor="w", justify="left")
            for child in widget.winfo_children():
                self._apply_ltr(child)
        except Exception:
            pass

    # ==================== تبويب لوحة التحكم ====================
    def create_admin_tab(self):
        admin = self.tab_admin

        add_frame = ctk.CTkFrame(admin, fg_color="#2A2A2A", corner_radius=15)
        add_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(add_frame, text="👤 " + self.tr("add_user"),
                     font=ctk.CTkFont(size=18, weight="bold"), text_color="#FFA07A").pack(anchor="w", padx=15, pady=5)

        grid = ctk.CTkFrame(add_frame, fg_color="transparent")
        grid.pack(padx=15, pady=10)
        grid.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(grid, text=self.tr("username") + ":",
                     font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.new_username = ctk.CTkEntry(grid, width=200)
        self.new_username.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(grid, text=self.tr("password") + ":",
                     font=ctk.CTkFont(size=14)).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.new_password = ctk.CTkEntry(grid, width=200, show="")
        self.new_password.grid(row=1, column=1, padx=5, pady=5)

        random_btn = ctk.CTkButton(grid, text=self.tr("random_password"),
                                   command=self.generate_random_for_new, width=120)
        random_btn.grid(row=1, column=2, padx=5, pady=5)

        ctk.CTkLabel(grid, text=self.tr("role") + ":",
                     font=ctk.CTkFont(size=14)).grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.new_role = ctk.CTkComboBox(grid, values=["user", "admin"], width=200)
        self.new_role.set("user")
        self.new_role.grid(row=2, column=1, padx=5, pady=5)

        ctk.CTkButton(add_frame, text=self.tr("add_user"),
                      command=self.add_user, fg_color="#32CD32", hover_color="#228B22").pack(pady=10)

        list_frame = ctk.CTkFrame(admin, fg_color="#2A2A2A", corner_radius=15)
        list_frame.pack(pady=10, padx=10, fill="both", expand=True)

        ctk.CTkLabel(list_frame, text="📋 " + self.tr("existing_users"),
                     font=ctk.CTkFont(size=18, weight="bold"), text_color="#FFA07A").pack(anchor="w", padx=15, pady=5)

        self.users_frame = ctk.CTkScrollableFrame(list_frame, fg_color="transparent")
        self.users_frame.pack(padx=15, pady=10, fill="both", expand=True)

        self.refresh_users_list()

    def refresh_users_list(self):
        for widget in self.users_frame.winfo_children():
            widget.destroy()

        users = load_users()
        for uname, data in users.items():
            if uname == "admin":
                continue
            row = ctk.CTkFrame(self.users_frame, fg_color="#333", corner_radius=5)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=f"{uname} ({data['role']})", font=ctk.CTkFont(size=14),
                         width=200, anchor="w").pack(side="left", padx=10)

            edit_btn = ctk.CTkButton(row, text="✏️", width=30, height=30, fg_color="#1E90FF", hover_color="#1874CD",
                                     command=lambda u=uname, pwd=data['password']: self.edit_user(u, pwd))
            edit_btn.pack(side="right", padx=2)

            del_btn = ctk.CTkButton(row, text="❌", width=30, height=30, fg_color="#8B3A3A", hover_color="#6B2A2A",
                                    command=lambda u=uname: self.delete_user(u))
            del_btn.pack(side="right", padx=2)

    def generate_random_for_new(self):
        random_pw = generate_random_password()
        self.new_password.delete(0, 'end')
        self.new_password.insert(0, random_pw)

    def edit_user(self, username, current_password_hash):
        def on_save(uname, new_password):
            users = load_users()
            if uname in users:
                users[uname]["password"] = hash_password(new_password)
                save_users(users)
                messagebox.showinfo(self.tr("success_saved"),
                                   f"تم تغيير كلمة المرور للمستخدم {uname}")
                self.refresh_users_list()
                self.update_filter_combo()
        ChangePasswordDialog(self, username, current_password_hash, on_save)

    def add_user(self):
        username = self.new_username.get().strip()
        password = self.new_password.get().strip()
        role = self.new_role.get()

        if not username or not password:
            messagebox.showerror(self.tr("error"),
                               self.tr("password_empty"))
            return

        users = load_users()
        if username in users:
            messagebox.showerror(self.tr("error"), "用户名已存在")
            return

        users[username] = {"password": hash_password(password), "role": role}
        save_users(users)
        messagebox.showinfo(self.tr("success_saved"), f"用户 {username} 已添加")
        self.new_username.delete(0, 'end')
        self.new_password.delete(0, 'end')
        self.refresh_users_list()
        self.update_filter_combo()

    def delete_user(self, username):
        if messagebox.askyesno(self.tr("delete"),
                               f"{self.tr('confirm_delete')} {username}?"):
            users = load_users()
            if username in users:
                del users[username]
                save_users(users)
                self.refresh_users_list()
                self.update_filter_combo()

    # ==================== تبويب السجل ====================
    def create_log_tab(self):
        log = self.tab_log

        self.top_log_frame = ctk.CTkFrame(log, fg_color="transparent")
        self.top_log_frame.pack(pady=10, padx=10, fill="x")

        self.export_btn = ctk.CTkButton(self.top_log_frame, text=self.tr("export_btn"),
                                        command=self.export_to_excel, height=40, fg_color="#32CD32")
        self.export_btn.pack(side="left", padx=5)

        # ===== 【新增】含分析报告的增强导出按钮 =====
        self.export_report_btn = ctk.CTkButton(self.top_log_frame,
                                               text=self.tr("export_report_btn"),
                                               command=self._analytics_export_enhanced,
                                               height=40, fg_color="#9932CC", hover_color="#7A219E")
        self.export_report_btn.pack(side="left", padx=5)

        self.refresh_log_btn = ctk.CTkButton(self.top_log_frame, text=self.tr("refresh_log_btn"),
                                             command=self.refresh_transaction_log, height=40, fg_color="#1E90FF")
        self.refresh_log_btn.pack(side="left", padx=5)

        if self.role == "admin":
            self.filter_label = ctk.CTkLabel(self.top_log_frame, text=self.tr("filter_user"),
                                             font=ctk.CTkFont(size=12))
            self.filter_label.pack(side="left", padx=(20,5))

            users = load_users()
            all_label = self.tr("all_users")
            user_list = [all_label] + [u for u in users.keys()]
            self.filter_combo = ctk.CTkComboBox(self.top_log_frame, values=user_list,
                                                command=self.on_filter_change, width=120)
            self.filter_combo.set(all_label)
            self.filter_combo.pack(side="left", padx=5)

        self.log_frame = ctk.CTkScrollableFrame(log, fg_color="#2A2A2A", corner_radius=15)
        self.log_frame.pack(pady=10, padx=10, fill="both", expand=True)

    def on_filter_change(self, choice):
        self.refresh_transaction_log()

    def update_filter_combo(self):
        if hasattr(self, 'filter_combo'):
            users = load_users()
            all_label = self.tr("all_users")
            user_list = [all_label] + list(users.keys())
            current = self.filter_combo.get()
            self.filter_combo.configure(values=user_list)
            if current not in user_list:
                self.filter_combo.set(all_label)

    def get_filtered_transactions(self, filter_user=None):
        if self.role == "admin":
            if filter_user is None or filter_user == self.tr("all_users"):
                return db_manager.get_all_transactions()
            else:
                return db_manager.get_all_transactions(filter_user)
        else:
            return db_manager.get_all_transactions(self.username)

    def update_log_display(self):
        for widget in self.log_frame.winfo_children():
            widget.destroy()

        filter_user = None
        if self.role == "admin" and hasattr(self, 'filter_combo'):
            try:
                choice = self.filter_combo.get()
                all_label = self.tr("all_users")
                if choice and choice != all_label:
                    filter_user = choice
            except Exception:
                pass
        display_trans = self.get_filtered_transactions(filter_user)

        if not display_trans:
            ctk.CTkLabel(self.log_frame, text=self.tr("no_transactions"),
                         font=ctk.CTkFont(size=16)).pack(pady=50)
            return

        headers = [
            self.tr("date"),
            self.tr("buyer").replace(":", ""),
            self.tr("order_id").replace(":", ""),
            self.tr("product_id").replace(":", ""),
            self.tr("gross_order").replace(":", ""),
            self.tr("funding_ratio"),
            self.tr("funding_usd"),
            self.tr("net_profit"),
            self.tr("profit_margin")
        ]
        
        # Define consistent column widths explicitly
        col_widths = [100, 110, 140, 110, 120, 80, 110, 110, 80]
        if self.role == "admin":
            headers.append("操作")
            col_widths.append(80)

        # Create a container frame with a border color. 
        # By adding 1px padding (padx/pady) to cells, the background of this frame shows through as borders.
        table_container = ctk.CTkFrame(self.log_frame, fg_color="#555555", corner_radius=0)
        table_container.pack(fill="x", padx=5, pady=5)
        
        # Bypass RTL applying for the grid container to prevent rendering loops
        table_container.no_rtl = True
        
        # Configure grid columns to enforce widths statically
        for i, w in enumerate(col_widths):
            table_container.grid_columnconfigure(i, minsize=w, weight=0)

        # Draw Headers
        for i, col_text in enumerate(headers):
            lbl = ctk.CTkLabel(table_container, text=col_text, width=col_widths[i], height=35,
                               font=ctk.CTkFont(size=12, weight="bold"),
                               fg_color="#3A3A3A", text_color="#FFFFFF", corner_radius=0)
            lbl.grid(row=0, column=i, padx=1, pady=1, sticky="nsew")

        # Draw Data Rows
        for idx, trans in enumerate(reversed(display_trans[-100:])):
            profit = trans.get('net_profit', 0)
            margin = trans.get('profit_margin', 0)
            
            # Use red background for low margins, else normal row color
            cell_bg = "#6B2A2A" if margin < 10 else "#2B2B2B"
            
            values = [
                str(trans.get('date', '')),
                str(trans.get('buyer', '')),
                str(trans.get('order_id', '')),
                str(trans.get('product_id', '')),
                f"{trans.get('gross',0):.2f}",
                f"{trans.get('funding_percent',0):.1f}%",
                f"{trans.get('funding',0):.2f}",
                f"{profit:.2f}",
                f"{margin:.1f}%"
            ]

            row_idx = idx + 1
            for j, val in enumerate(values):
                lbl = ctk.CTkLabel(table_container, text=val, width=col_widths[j], height=30,
                                   font=ctk.CTkFont(size=12),
                                   fg_color=cell_bg, corner_radius=0)
                lbl.grid(row=row_idx, column=j, padx=1, pady=1, sticky="nsew")

            if self.role == "admin":
                # Actions cell
                action_frame = ctk.CTkFrame(table_container, fg_color=cell_bg, corner_radius=0)
                action_frame.grid(row=row_idx, column=len(values), padx=1, pady=1, sticky="nsew")
                
                # Center buttons in the action frame
                action_frame.grid_columnconfigure((0,1), weight=1)
                action_frame.grid_rowconfigure(0, weight=1)

                edit_btn = ctk.CTkButton(action_frame, text="✏️", width=30, height=24, corner_radius=4,
                                        command=lambda t=trans: self.edit_transaction(t))
                edit_btn.grid(row=0, column=0, padx=2, pady=2)

                del_btn = ctk.CTkButton(action_frame, text="❌", width=30, height=24, corner_radius=4,
                                        fg_color="#8B3A3A", hover_color="#6B2A2A",
                                        command=lambda i=idx, lst=display_trans: self.delete_transaction(i, lst))
                del_btn.grid(row=0, column=1, padx=2, pady=2)

    def edit_transaction(self, trans):
        self.load_transaction(trans)
        self.tabview.set(self.tr("main_tab"))

    def delete_transaction(self, index, display_list):
        if messagebox.askyesno(self.tr("delete"),
                               self.tr("confirm_delete")):
            trans_to_delete = display_list[len(display_list)-1-index]
            db_manager.delete_transaction(trans_to_delete)
            self.refresh_transaction_log()
            self.sync_to_github_bg()

    # ==================== التبويب الرئيسي (معدل لاستخدام النسب المئوية) ====================
    def create_main_tab(self):
        main = self.tab_main

        self.info_frame = ctk.CTkFrame(main, fg_color="#2A2A2A", corner_radius=15)
        self.info_frame.pack(pady=10, padx=10, fill="x")

        self.order_info_label = ctk.CTkLabel(self.info_frame, text=self.tr("order_info"),
                                             font=ctk.CTkFont(size=18, weight="bold"), text_color="#FFA07A")
        self.order_info_label.pack(side="left", padx=15, pady=5)
        
        if OCR_AVAILABLE:
            self.import_img_btn_main = ctk.CTkButton(self.info_frame, text=self.tr("ocr_btn"), width=250, height=35, font=ctk.CTkFont(weight="bold", size=14), fg_color="#C71585", hover_color="#8B008B", command=self.import_from_image)
            self.import_img_btn_main.pack(side="right", padx=15, pady=5)

        # Create a new clear frame for info grid because mixing side/grid triggers errors
        self.grid_frame_container = ctk.CTkFrame(main, fg_color="#2A2A2A", corner_radius=15)
        self.grid_frame_container.pack(pady=5, padx=10, fill="x")

        grid_info = ctk.CTkFrame(self.grid_frame_container, fg_color="transparent")
        grid_info.pack(padx=15, pady=10, fill="x")
        grid_info.grid_columnconfigure((0,1,2,3,4,5), weight=1)

        self.date_label = ctk.CTkLabel(grid_info, text=self.tr("date"),
                                       font=ctk.CTkFont(size=14))
        self.date_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.date_entry = ctk.CTkEntry(grid_info, width=100, placeholder_text="YYYY-MM-DD")
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.buyer_label = ctk.CTkLabel(grid_info, text=self.tr("buyer"),
                                        font=ctk.CTkFont(size=14))
        self.buyer_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.buyer_entry = ctk.CTkEntry(grid_info, width=120, placeholder_text=self.tr("eg_buyer"))
        self.buyer_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        self.order_id_label = ctk.CTkLabel(grid_info, text=self.tr("order_id"),
                                           font=ctk.CTkFont(size=14))
        self.order_id_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.order_id_entry = ctk.CTkEntry(grid_info, width=120, placeholder_text=self.tr("eg_order_id"))
        self.order_id_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.product_id_label = ctk.CTkLabel(grid_info, text=self.tr("product_id"),
                                             font=ctk.CTkFont(size=14))
        self.product_id_label.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.product_id_entry = ctk.CTkEntry(grid_info, width=120, placeholder_text=self.tr("eg_product_id"))
        self.product_id_entry.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        main_frame = ctk.CTkScrollableFrame(main, fg_color="#1E1E1E")
        main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # قسم إجمالي الطلب
        self.section1 = ctk.CTkFrame(main_frame, fg_color="#2A2A2A", corner_radius=15)
        self.section1.pack(pady=10, padx=10, fill="x")

        self.order_amount_label = ctk.CTkLabel(self.section1, text=self.tr("order_amount"),
                                               font=ctk.CTkFont(size=16, weight="bold"), text_color="#FFA07A")
        self.order_amount_label.pack(anchor="w", padx=15, pady=5)

        order_frame = ctk.CTkFrame(self.section1, fg_color="transparent")
        order_frame.pack(padx=15, pady=10, fill="x")

        self.gross_order_label = ctk.CTkLabel(order_frame, text=self.tr("gross_order"),
                                              font=ctk.CTkFont(size=14))
        self.gross_order_label.pack(side="left", padx=5)
        self.gross_order_entry = ctk.CTkEntry(order_frame, width=150, placeholder_text=self.tr("eg_amount"))
        self.gross_order_entry.pack(side="left", padx=10)
        self.gross_order_entry.bind("<KeyRelease>", self.update_funding_value)

        self.funding_percent_label = ctk.CTkLabel(order_frame, text=self.tr("funding_percent"),
                                                  font=ctk.CTkFont(size=14))
        self.funding_percent_label.pack(side="left", padx=20)
        self.funding_percent_entry = ctk.CTkEntry(order_frame, width=80, placeholder_text="65")
        self.funding_percent_entry.insert(0, "65")
        self.funding_percent_entry.pack(side="left", padx=5)
        self.funding_percent_entry.bind("<KeyRelease>", self.update_funding_value)

        ctk.CTkLabel(order_frame, text="%", font=ctk.CTkFont(size=14)).pack(side="left")

        funding_val_frame = ctk.CTkFrame(self.section1, fg_color="transparent")
        funding_val_frame.pack(padx=15, pady=5, fill="x")
        self.funding_amount_label = ctk.CTkLabel(funding_val_frame, text=self.tr("funding_amount"),
                                                 font=ctk.CTkFont(size=14))
        self.funding_amount_label.pack(side="left", padx=5)
        self.funding_value_label = ctk.CTkLabel(funding_val_frame, text="0.00", font=ctk.CTkFont(size=16, weight="bold"),
                                                text_color="#98FB98", width=120, fg_color="#2B2B2B", corner_radius=5)
        self.funding_value_label.pack(side="left", padx=10)

        # قسم رسوم المنصة (نسب مئوية)
        self.section2 = ctk.CTkFrame(main_frame, fg_color="#2A2A2A", corner_radius=15)
        self.section2.pack(pady=10, padx=10, fill="x")
        self.platform_fees_label = ctk.CTkLabel(self.section2, text=self.tr("platform_fees"),
                                                font=ctk.CTkFont(size=16, weight="bold"), text_color="#FFA07A")
        self.platform_fees_label.pack(anchor="w", padx=15, pady=5)

        fees_frame = ctk.CTkFrame(self.section2, fg_color="transparent")
        fees_frame.pack(padx=15, pady=10, fill="x")
        fees_frame.grid_columnconfigure(1, weight=1)

        # Commission rate
        self.commission_label = ctk.CTkLabel(fees_frame, text=self.tr("commission"),
                                             font=ctk.CTkFont(size=14))
        self.commission_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.commission_entry = ctk.CTkEntry(fees_frame, width=100)
        self.commission_entry.insert(0, str(config_manager.get_fee("commission_rate", 10.24)))  # 从配置加载
        self.commission_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(fees_frame, text="%", font=ctk.CTkFont(size=14)).grid(row=0, column=2, padx=2, pady=5, sticky="w")

        # Service fee rate
        self.service_fee_label = ctk.CTkLabel(fees_frame, text=self.tr("service_fee"),
                                              font=ctk.CTkFont(size=14))
        self.service_fee_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.service_fee_entry = ctk.CTkEntry(fees_frame, width=100)
        self.service_fee_entry.insert(0, str(config_manager.get_fee("service_fee_rate", 2.5)))
        self.service_fee_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(fees_frame, text="%", font=ctk.CTkFont(size=14)).grid(row=1, column=2, padx=2, pady=5, sticky="w")

        # Affiliate fee rate
        self.affiliate_fee_label = ctk.CTkLabel(fees_frame, text=self.tr("affiliate_fee"),
                                                font=ctk.CTkFont(size=14))
        self.affiliate_fee_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.affiliate_fee_entry = ctk.CTkEntry(fees_frame, width=100)
        self.affiliate_fee_entry.insert(0, str(config_manager.get_fee("affiliate_fee_rate", 1.64)))
        self.affiliate_fee_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(fees_frame, text="%", font=ctk.CTkFont(size=14)).grid(row=2, column=2, padx=2, pady=5, sticky="w")

        # قسم التكاليف الإضافية
        self.section3 = ctk.CTkFrame(main_frame, fg_color="#2A2A2A", corner_radius=15)
        self.section3.pack(pady=10, padx=10, fill="x")
        self.other_costs_label = ctk.CTkLabel(self.section3, text=self.tr("other_costs"),
                                              font=ctk.CTkFont(size=16, weight="bold"), text_color="#FFA07A")
        self.other_costs_label.pack(anchor="w", padx=15, pady=5)

        costs_frame = ctk.CTkFrame(self.section3, fg_color="transparent")
        costs_frame.pack(padx=15, pady=10, fill="x")

        # COGS
        row1 = ctk.CTkFrame(costs_frame, fg_color="transparent")
        row1.pack(fill="x", pady=2)
        self.cogs_label = ctk.CTkLabel(row1, text=self.tr("cogs"),
                                       font=ctk.CTkFont(size=14), width=150)
        self.cogs_label.pack(side="left")
        self.cogs_amount_entry = ctk.CTkEntry(row1, width=120)
        self.cogs_amount_entry.pack(side="left", padx=5)
        self.cogs_currency_combo = ctk.CTkComboBox(row1, values=["USD", "CNY"], width=80)
        self.cogs_currency_combo.set("USD")
        self.cogs_currency_combo.pack(side="left", padx=5)

        # Shipping
        row2 = ctk.CTkFrame(costs_frame, fg_color="transparent")
        row2.pack(fill="x", pady=2)
        self.shipping_label = ctk.CTkLabel(row2, text=self.tr("shipping"),
                                           font=ctk.CTkFont(size=14), width=150)
        self.shipping_label.pack(side="left")
        self.shipping_amount_entry = ctk.CTkEntry(row2, width=120)
        self.shipping_amount_entry.pack(side="left", padx=5)
        self.shipping_currency_combo = ctk.CTkComboBox(row2, values=["USD", "CNY"], width=80)
        self.shipping_currency_combo.set("USD")
        self.shipping_currency_combo.pack(side="left", padx=5)

        # Packaging
        row3 = ctk.CTkFrame(costs_frame, fg_color="transparent")
        row3.pack(fill="x", pady=2)
        self.packaging_label = ctk.CTkLabel(row3, text=self.tr("packaging"),
                                            font=ctk.CTkFont(size=14), width=150)
        self.packaging_label.pack(side="left")
        self.packaging_amount_entry = ctk.CTkEntry(row3, width=120)
        self.packaging_amount_entry.pack(side="left", padx=5)
        self.packaging_currency_combo = ctk.CTkComboBox(row3, values=["USD", "CNY"], width=80)
        self.packaging_currency_combo.set("USD")
        self.packaging_currency_combo.pack(side="left", padx=5)

        # Tax
        row4 = ctk.CTkFrame(costs_frame, fg_color="transparent")
        row4.pack(fill="x", pady=2)
        self.tax_label = ctk.CTkLabel(row4, text=self.tr("tax"),
                                      font=ctk.CTkFont(size=14), width=150)
        self.tax_label.pack(side="left")
        self.tax_amount_entry = ctk.CTkEntry(row4, width=120)
        self.tax_amount_entry.pack(side="left", padx=5)
        self.tax_currency_combo = ctk.CTkComboBox(row4, values=["USD", "CNY"], width=80)
        self.tax_currency_combo.set("USD")
        self.tax_currency_combo.pack(side="left", padx=5)

        # الأزرار
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=20)

        self.calc_btn = ctk.CTkButton(btn_frame, text=self.tr("calc_btn"),
                                      command=self.calculate, width=150, height=40,
                                      fg_color="#32CD32", hover_color="#228B22", font=ctk.CTkFont(size=16))
        self.calc_btn.pack(side="left", padx=10)

        self.save_btn = ctk.CTkButton(btn_frame, text=self.tr("save_btn"),
                                      command=self.save_current_transaction, width=150, height=40,
                                      fg_color="#1E90FF", hover_color="#1874CD", font=ctk.CTkFont(size=16))
        self.save_btn.pack(side="left", padx=10)

        self.reset_btn = ctk.CTkButton(btn_frame, text=self.tr("reset_btn"),
                                       command=self.reset_main, width=100, height=40,
                                       fg_color="#708090", hover_color="#5A5A5A")
        self.reset_btn.pack(side="left", padx=10)

        self.result_frame = ctk.CTkFrame(main_frame, fg_color="#2B2B2B", corner_radius=10)
        self.result_frame.pack(pady=10, padx=10, fill="x")
        self.result_textbox = ctk.CTkTextbox(self.result_frame, height=250, font=ctk.CTkFont(size=13, family="Consolas"), wrap="none")
        self.result_textbox.pack(pady=10, padx=10, fill="both", expand=True)

    def create_compare_tab(self):
        compare = self.tab_compare

        self.compare_frame = ctk.CTkFrame(compare, fg_color="#2A2A2A", corner_radius=15)
        self.compare_frame.pack(pady=20, padx=20, fill="x")

        self.compare_title_label = ctk.CTkLabel(self.compare_frame, text=self.tr("compare_title"),
                                                font=ctk.CTkFont(size=20, weight="bold"), text_color="#FFA07A")
        self.compare_title_label.pack(pady=10)

        self.compare_instruction_label = ctk.CTkLabel(self.compare_frame, text=self.tr("compare_label"),
                                                      font=ctk.CTkFont(size=14))
        self.compare_instruction_label.pack(pady=5)

        self.compare_percents_entry = ctk.CTkEntry(self.compare_frame, width=300, placeholder_text="50,60,65")
        self.compare_percents_entry.pack(pady=5)

        self.compare_btn = ctk.CTkButton(self.compare_frame, text=self.tr("compare_btn"),
                                         command=self.compare_scenarios, height=40, fg_color="#FF8C00")
        self.compare_btn.pack(pady=10)

        self.compare_result_frame = ctk.CTkFrame(compare, fg_color="#2B2B2B", corner_radius=10)
        self.compare_result_frame.pack(pady=10, padx=20, fill="both", expand=True)
        self.compare_textbox = ctk.CTkTextbox(self.compare_result_frame, height=200, font=ctk.CTkFont(size=13, family="Consolas"), wrap="none")
        self.compare_textbox.pack(pady=10, padx=10, fill="both", expand=True)

    # ==================== الدوال الحسابية (معدلة لاستخدام النسب) ====================
    def update_funding_value(self, event=None):
        try:
            gross = float(self.gross_order_entry.get() or 0)
            percent = float(self.funding_percent_entry.get() or 0)
            funding = gross * (percent / 100)
            self.funding_value_label.configure(text=f"{funding:.2f}")
        except:
            self.funding_value_label.configure(text="0.00")

    def calculate(self):
        try:
            gross_order_usd = float(self.gross_order_entry.get() or 0)
            
            # قراءة النسب المئوية للرسوم
            commission_rate = float(self.commission_entry.get() or 0) / 100.0
            service_rate = float(self.service_fee_entry.get() or 0) / 100.0
            affiliate_rate = float(self.affiliate_fee_entry.get() or 0) / 100.0
            
            funding_percent = float(self.funding_percent_entry.get() or 0)
            funding_usd = gross_order_usd * (funding_percent / 100)

            # حساب الرسوم باليوان = إجمالي الطلب بالدولار * النسبة * سعر الصرف
            commission_cny = gross_order_usd * commission_rate * self.exchange_rate
            service_fee_cny = gross_order_usd * service_rate * self.exchange_rate
            affiliate_fee_cny = gross_order_usd * affiliate_rate * self.exchange_rate

            commission_usd = commission_cny / self.exchange_rate  # يعطي نفس gross * rate
            service_fee_usd = service_fee_cny / self.exchange_rate
            affiliate_fee_usd = affiliate_fee_cny / self.exchange_rate
            total_fees_usd = commission_usd + service_fee_usd + affiliate_fee_usd
            payout_usd = gross_order_usd - total_fees_usd

            cogs_amount = float(self.cogs_amount_entry.get() or 0)
            cogs_currency = self.cogs_currency_combo.get()
            cogs_usd = cogs_amount / self.exchange_rate if cogs_currency == "CNY" else cogs_amount

            shipping_amount = float(self.shipping_amount_entry.get() or 0)
            shipping_currency = self.shipping_currency_combo.get()
            shipping_usd = shipping_amount / self.exchange_rate if shipping_currency == "CNY" else shipping_amount

            packaging_amount = float(self.packaging_amount_entry.get() or 0)
            packaging_currency = self.packaging_currency_combo.get()
            packaging_usd = packaging_amount / self.exchange_rate if packaging_currency == "CNY" else packaging_amount

            tax_amount = float(self.tax_amount_entry.get() or 0)
            tax_currency = self.tax_currency_combo.get()
            tax_usd = tax_amount / self.exchange_rate if tax_currency == "CNY" else tax_amount

            total_costs_usd = cogs_usd + shipping_usd + packaging_usd + tax_usd
            net_profit_usd = payout_usd - funding_usd - total_costs_usd
            profit_margin = (net_profit_usd / gross_order_usd * 100) if gross_order_usd != 0 else 0

            if gross_order_usd != 0:
                comm_percent = (commission_usd / gross_order_usd) * 100
                serv_percent = (service_fee_usd / gross_order_usd) * 100
                aff_percent = (affiliate_fee_usd / gross_order_usd) * 100
            else:
                comm_percent = serv_percent = aff_percent = 0

            self.current_result = {
                'gross': gross_order_usd,
                'commission_cny': commission_cny,
                'service_cny': service_fee_cny,
                'affiliate_cny': affiliate_fee_cny,
                'commission_usd': commission_usd,
                'service_usd': service_fee_usd,
                'affiliate_usd': affiliate_fee_usd,
                'total_fees_usd': total_fees_usd,
                'total_fees_cny': commission_cny + service_fee_cny + affiliate_fee_cny,
                'payout': payout_usd,
                'funding_percent': funding_percent,
                'funding': funding_usd,
                'cogs_usd': cogs_usd,
                'shipping_usd': shipping_usd,
                'packaging_usd': packaging_usd,
                'tax_usd': tax_usd,
                'total_costs_usd': total_costs_usd,
                'net_profit': net_profit_usd,
                'profit_margin': profit_margin,
                'comm_percent': comm_percent,
                'serv_percent': serv_percent,
                'aff_percent': aff_percent
            }
            self.display_result()
        except ValueError:
            messagebox.showerror(self.tr("error_invalid_number"),
                                 self.tr("error_invalid_number"))

    def display_result(self):
        res = self.current_result
        profit_margin = res['profit_margin']
        result_text = f"""
{'='*70}
{self.tr('calc_btn').replace('📊', '📋').center(70)}
{'='*70}

💵 {self.tr('gross_order')} {res['gross']:>15.2f} USD

【{self.tr('platform_fees')}】
{self.tr('commission')} {res['commission_usd']:>10.2f} USD ({res['comm_percent']:>5.2f}%)   | {res['commission_cny']:>10.2f} CNY
{self.tr('service_fee')} {res['service_usd']:>10.2f} USD ({res['serv_percent']:>5.2f}%)   | {res['service_cny']:>10.2f} CNY
{self.tr('affiliate_fee')} {res['affiliate_usd']:>10.2f} USD ({res['aff_percent']:>5.2f}%)   | {res['affiliate_cny']:>10.2f} CNY
{'-'*70}
{self.tr('total_fees')} {res['total_fees_usd']:>10.2f} USD                        | {res['total_fees_cny']:>10.2f} CNY

💰 {self.tr('payout')} {res['payout']:>15.2f} USD

【{self.tr('other_costs')}】
{self.tr('funding_amount')} ({res['funding_percent']:.1f}%): {res['funding']:>15.2f} USD
{self.tr('cogs')} {res['cogs_usd']:>15.2f} USD
{self.tr('shipping')} {res['shipping_usd']:>15.2f} USD
{self.tr('packaging')} {res['packaging_usd']:>15.2f} USD
{self.tr('tax')} {res['tax_usd']:>15.2f} USD
{'-'*70}
{self.tr('total_costs')} {res['total_costs_usd']+res['funding']:>15.2f} USD

{'='*70}
✅ {self.tr('net_profit')} {res['net_profit']:>15.2f} USD
📊 {self.tr('profit_margin')} {profit_margin:>15.2f}%
{'='*70}
"""
        if profit_margin < 10:
            result_text += f"\n{self.tr('warning_low_margin')}\n"
        self.result_textbox.delete("0.0", "end")
        self.result_textbox.insert("0.0", result_text)

    def save_current_transaction(self):
        # Auto-calculate before saving to ensure latest user input is captured
        self.calculate()

        if not hasattr(self, 'current_result'):
            messagebox.showwarning(self.tr("warning_calc_first"),
                                   self.tr("warning_calc_first"))
            return
        buyer = self.buyer_entry.get().strip()
        order_id = self.order_id_entry.get().strip()
        product_id = self.product_id_entry.get().strip()
        date = self.date_entry.get().strip() or datetime.now().strftime("%Y-%m-%d")
        if not buyer or not order_id:
            messagebox.showwarning(self.tr("warning_fill_buyer_order"),
                                   self.tr("warning_fill_buyer_order"))
            return
        trans = {
            'username': self.username,
            'date': date,
            'buyer': buyer,
            'order_id': order_id,
            'product_id': product_id,
            **self.current_result
        }
        if hasattr(self, 'current_editing_id') and self.current_editing_id is not None:
            db_manager.update_transaction(trans, self.current_editing_id)
            # DO NOT clear self.current_editing_id here, allow subsequent saves to update the same record
        else:
            db_manager.insert_transaction(trans)
        self.refresh_transaction_log()
        self.sync_to_github_bg()
        messagebox.showinfo(self.tr("success_saved"),
                            self.trf("success_saved", order_id))

    def load_transaction(self, trans):
        self.current_editing_id = trans.get('id')
        self.gross_order_entry.delete(0, 'end')
        self.gross_order_entry.insert(0, str(trans.get('gross', '')))
        # تحميل النسب من القيم المخزنة باليوان؟ نخزن النسب المستخدمة أم لا؟ سنتركها كما هي.
        # لاحظ أن المعاملات القديمة لا تحتوي على النسب. سيتم استخدام القيم الافتراضية.
        # يمكن تحسين ذلك بتخزين النسب مع المعاملة، لكنه خارج النطاق الحالي.
        self.commission_entry.delete(0, 'end')
        self.commission_entry.insert(0, str(config_manager.get_fee("commission_rate", 10.24)))
        self.service_fee_entry.delete(0, 'end')
        self.service_fee_entry.insert(0, str(config_manager.get_fee("service_fee_rate", 2.5)))
        self.affiliate_fee_entry.delete(0, 'end')
        self.affiliate_fee_entry.insert(0, str(config_manager.get_fee("affiliate_fee_rate", 1.64)))
        self.funding_percent_entry.delete(0, 'end')
        self.funding_percent_entry.insert(0, str(trans.get('funding_percent', '')))
        self.buyer_entry.delete(0, 'end')
        self.buyer_entry.insert(0, trans.get('buyer', ''))
        self.order_id_entry.delete(0, 'end')
        self.order_id_entry.insert(0, trans.get('order_id', ''))
        self.product_id_entry.delete(0, 'end')
        self.product_id_entry.insert(0, trans.get('product_id', ''))
        self.date_entry.delete(0, 'end')
        self.date_entry.insert(0, trans.get('date', datetime.now().strftime("%Y-%m-%d")))
        self.tabview.set(self.tr("main_tab"))
        self.calculate()

    def export_to_excel(self):
        trans_list = db_manager.get_all_transactions()
        if not trans_list:
            messagebox.showwarning(self.tr("warning_no_data_export"),
                                   self.tr("warning_no_data_export"))
            return
        df = pd.DataFrame(trans_list)
        cols = ['username', 'date', 'buyer', 'order_id', 'product_id', 'gross', 'funding_percent', 'funding',
                'cogs_usd', 'shipping_usd', 'packaging_usd', 'tax_usd', 'total_costs_usd',
                'commission_cny', 'service_cny', 'affiliate_cny', 'total_fees_cny',
                'commission_usd', 'service_usd', 'affiliate_usd', 'total_fees_usd',
                'payout', 'net_profit', 'profit_margin']
        available_cols = [c for c in cols if c in df.columns]
        df = df[available_cols]
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if file_path:
            df.to_excel(file_path, index=False)
            messagebox.showinfo(self.tr("success_exported"),
                                self.trf("success_exported", file_path))

    def compare_scenarios(self):
        try:
            percents_str = self.compare_percents_entry.get()
            percents = [float(p.strip()) for p in percents_str.split(',') if p.strip()]
            if not percents:
                return
            gross_order_usd = float(self.gross_order_entry.get() or 0)
            
            # استخدام النسب الحالية للرسوم
            commission_rate = float(self.commission_entry.get() or 0) / 100.0
            service_rate = float(self.service_fee_entry.get() or 0) / 100.0
            affiliate_rate = float(self.affiliate_fee_entry.get() or 0) / 100.0
            
            commission_cny = gross_order_usd * commission_rate * self.exchange_rate
            service_fee_cny = gross_order_usd * service_rate * self.exchange_rate
            affiliate_fee_cny = gross_order_usd * affiliate_rate * self.exchange_rate
            
            commission_usd = commission_cny / self.exchange_rate
            service_fee_usd = service_fee_cny / self.exchange_rate
            affiliate_fee_usd = affiliate_fee_cny / self.exchange_rate
            total_fees_usd = commission_usd + service_fee_usd + affiliate_fee_usd
            payout_usd = gross_order_usd - total_fees_usd

            cogs_amount = float(self.cogs_amount_entry.get() or 0)
            cogs_currency = self.cogs_currency_combo.get()
            cogs_usd = cogs_amount / self.exchange_rate if cogs_currency == "CNY" else cogs_amount

            shipping_amount = float(self.shipping_amount_entry.get() or 0)
            shipping_currency = self.shipping_currency_combo.get()
            shipping_usd = shipping_amount / self.exchange_rate if shipping_currency == "CNY" else shipping_amount

            packaging_amount = float(self.packaging_amount_entry.get() or 0)
            packaging_currency = self.packaging_currency_combo.get()
            packaging_usd = packaging_amount / self.exchange_rate if packaging_currency == "CNY" else packaging_amount

            tax_amount = float(self.tax_amount_entry.get() or 0)
            tax_currency = self.tax_currency_combo.get()
            tax_usd = tax_amount / self.exchange_rate if tax_currency == "CNY" else tax_amount

            total_costs_usd = cogs_usd + shipping_usd + packaging_usd + tax_usd

            rows = []
            for p in percents:
                funding = gross_order_usd * (p / 100)
                net_profit = payout_usd - funding - total_costs_usd
                margin = (net_profit / gross_order_usd * 100) if gross_order_usd != 0 else 0
                rows.append([f"{p}%", f"{funding:.2f}", f"{net_profit:.2f}", f"{margin:.2f}%"])
            best_idx = max(range(len(rows)), key=lambda i: float(rows[i][2]))
            table = f"{self.tr('funding_ratio')} | {self.tr('funding_usd')} | {self.tr('net_profit')} | {self.tr('profit_margin')}\n"
            table += "-"*50 + "\n"
            for r in rows:
                table += f"{r[0]:^8} | {r[1]:>12} | {r[2]:>12} | {r[3]:>8}\n"
            table += "-"*50 + "\n"
            table += self.trf("best_scheme", rows[best_idx][0], rows[best_idx][2])
            self.compare_textbox.delete("0.0", "end")
            self.compare_textbox.insert("0.0", table)
        except Exception as e:
            messagebox.showerror(self.tr("error_compare"),
                                 self.trf("error_compare", e))

    def refresh_exchange_rate(self):
        def update():
            # Get updated rate from API
            new_rate, source, date = get_live_exchange_rate(self.base_currency)
            # Pass to main thread safely to update UI
            self.after(0, self._apply_exchange_rate_ui, new_rate, source, date)
            
        threading.Thread(target=update, daemon=True).start()
        
    def _apply_exchange_rate_ui(self, new_rate, source, date):
        self.exchange_rate = new_rate
        self.rate_source = source
        self.rate_date = date
        rate_text = self.trf("rate_label", f"{self.exchange_rate:.4f}", source, date)
        self.rate_label.configure(text=rate_text)
        messagebox.showinfo(self.tr("success_rate_updated"),
                            self.trf("success_rate_updated", self.exchange_rate))

    def refresh_transaction_log(self):
        self.update_log_display()

    def reset_main(self):
        self.current_editing_id = None
        self.gross_order_entry.delete(0, 'end')
        self.commission_entry.delete(0, 'end')
        self.commission_entry.insert(0, str(config_manager.get_fee("commission_rate", 10.24)))
        self.service_fee_entry.delete(0, 'end')
        self.service_fee_entry.insert(0, str(config_manager.get_fee("service_fee_rate", 2.5)))
        self.affiliate_fee_entry.delete(0, 'end')
        self.affiliate_fee_entry.insert(0, str(config_manager.get_fee("affiliate_fee_rate", 1.64)))
        self.cogs_amount_entry.delete(0, 'end')
        self.shipping_amount_entry.delete(0, 'end')
        self.packaging_amount_entry.delete(0, 'end')
        self.tax_amount_entry.delete(0, 'end')
        self.funding_percent_entry.delete(0, 'end')
        self.funding_percent_entry.insert(0, "65")
        self.cogs_currency_combo.set("USD")
        self.shipping_currency_combo.set("USD")
        self.packaging_currency_combo.set("USD")
        self.tax_currency_combo.set("USD")
        self.buyer_entry.delete(0, 'end')
        self.order_id_entry.delete(0, 'end')
        self.product_id_entry.delete(0, 'end')
        self.date_entry.delete(0, 'end')
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.result_textbox.delete("0.0", "end")
        self.update_funding_value()

    # ==================== 【新增】截图智能识别 ====================
    def import_from_image(self):
        file_path = filedialog.askopenfilename(title="选择订单截图", filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if not file_path:
            return
        
        # Load API Key securely
        api_key = config_manager.get("gemini_api_key", "").strip()
        
        if not api_key:
            messagebox.showwarning(self.tr("warning_no_api_key"),
                                   "API Key is missing! Please click '🔑 Set API Key' to configure your Gemini API Key first.")
            return

        self.import_img_btn_main.configure(text="⏳ 识别中...", state="disabled")
        
        def process_image():
            self.result_textbox.delete("0.0", "end")
            self.result_textbox.insert("end", f"{self.tr('ocr_processing')} {os.path.basename(file_path)}...\n")
            self.calc_btn.configure(state="disabled")
            
            try:
                # Use dynamic API Key from configuration instead of hardcoded
                parsed_data = parse_invoice_image(file_path, api_key)
                
                def update_ui(success, result_data, error_msg=""):
                    self.import_img_btn_main.configure(text="📸 自动识别 AliExpress 订单截图填表", state="normal")
                    self.calc_btn.configure(state="normal")
                    
                    if success and result_data:
                        self.result_textbox.insert("end", f"✔️ {self.tr('ocr_success')}\n\n", "success")
                        
                        # Populate UI using the result_data map
                        self.order_id_entry.delete(0, 'end')
                        if result_data.get("order_id"):
                            self.order_id_entry.insert(0, str(result_data["order_id"]))
                            
                        self.buyer_entry.delete(0, 'end')
                        if result_data.get("buyer_name"):
                            self.buyer_entry.insert(0, str(result_data["buyer_name"]))
                            
                        self.gross_order_entry.delete(0, 'end')
                        if result_data.get("order_total_usd"):
                            self.gross_order_entry.insert(0, str(result_data["order_total_usd"]))
                        elif result_data.get("order_total_cny"):
                            usd_val = float(result_data["order_total_cny"]) / self.exchange_rate
                            self.gross_order_entry.insert(0, f"{usd_val:.2f}")
                            
                        self.commission_entry.delete(0, 'end')
                        if result_data.get("commission_rate_percent"):
                            self.commission_entry.insert(0, str(result_data["commission_rate_percent"]))
                            
                        self.service_fee_entry.delete(0, 'end')
                        if result_data.get("transaction_service_rate_percent"):
                            self.service_fee_entry.insert(0, str(result_data["transaction_service_rate_percent"]))
                            
                        self.affiliate_fee_entry.delete(0, 'end')
                        if result_data.get("incubation_service_rate_percent"):
                            self.affiliate_fee_entry.insert(0, str(result_data["incubation_service_rate_percent"]))

                        self.update_funding_value()
                        self.calculate()
                        messagebox.showinfo(self.tr("ocr_success_title"), self.tr("ocr_success"))
                    else:
                        self.result_textbox.insert("end", f"❌ {self.tr('ocr_failed')}\n{error_msg}\n", "error")
                        messagebox.showerror(self.tr("ocr_failed_title"), f"{self.tr('ocr_failed')}\n{error_msg}")

                self.after(0, update_ui, True, parsed_data)
                
            except Exception as e:
                def update_ui_error(error_msg):
                    self.import_img_btn_main.configure(text="📸 自动识别 AliExpress 订单截图填表", state="normal")
                    self.calc_btn.configure(state="normal")
                    self.result_textbox.insert("end", f"❌ {self.tr('ocr_failed')}\n{error_msg}\n", "error")
                    messagebox.showerror(self.tr("ocr_failed_title"), f"{self.tr('ocr_failed')}\n{error_msg}")
                self.after(0, update_ui_error, str(e))

        threading.Thread(target=process_image, daemon=True).start()

    # ==================== 【新增】亏损预警 (Alerts) 标签页 ====================
    def create_alerts_tab(self):
        tab = self.tab_alerts
        
        top_bar = ctk.CTkFrame(tab, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(top_bar, text=self.tr("margin_threshold", "预警阈值 (%):"), font=ctk.CTkFont(size=14)).pack(side="left", padx=5)
        
        self.alert_threshold_var = ctk.StringVar(value="10.0")
        threshold_entry = ctk.CTkEntry(top_bar, textvariable=self.alert_threshold_var, width=80)
        threshold_entry.pack(side="left", padx=5)
        
        refresh_alerts_btn = ctk.CTkButton(top_bar, text=self.tr("refresh_log_btn"), command=self.refresh_alerts, width=100, fg_color="#E74C3C", hover_color="#C0392B")
        refresh_alerts_btn.pack(side="left", padx=10)

        self.alerts_frame = ctk.CTkScrollableFrame(tab, fg_color="#2A2A2A", corner_radius=15)
        self.alerts_frame.pack(pady=10, padx=10, fill="both", expand=True)

    def refresh_alerts(self):
        for widget in self.alerts_frame.winfo_children():
            widget.destroy()
            
        try:
            threshold = float(self.alert_threshold_var.get())
        except:
            threshold = 10.0
            self.alert_threshold_var.set("10.0")
            
        low_profit_tx = db_manager.get_low_profit_transactions(threshold)
        low_profit_tx.sort(key=lambda x: x.get('profit_margin', 0)) # Sort lowest first (worst losses at top)

        if not low_profit_tx:
            ctk.CTkLabel(self.alerts_frame, text=self.tr("no_alerts", "✅ 暂无低利润(亏损)订单，运营状况良好！"), font=ctk.CTkFont(size=16, weight="bold"), text_color="#2ECC71").pack(pady=50)
            return

        headers = [self.tr("date"), self.tr("buyer").replace(":", ""), self.tr("order_id").replace(":", ""), self.tr("product_id").replace(":", ""), self.tr("gross_order").replace(":", ""), self.tr("net_profit"), self.tr("profit_margin")]
        col_widths = [100, 120, 120, 100, 100, 100, 100]

        header_frame = ctk.CTkFrame(self.alerts_frame, fg_color="#3A3A3A", corner_radius=5)
        header_frame.pack(fill="x", pady=2)

        for i, col in enumerate(headers):
            lbl = ctk.CTkLabel(header_frame, text=col, width=col_widths[i], font=ctk.CTkFont(size=13, weight="bold"))
            lbl.pack(side="left", padx=2)

        for idx, trans in enumerate(low_profit_tx):
            profit = trans.get('net_profit', 0)
            margin = trans.get('profit_margin', 0)
            
            # Worse color for worse margin
            if margin < 0:
                row_color = "#8B0000" # Dark Red for losses
            elif margin < 5:
                row_color = "#8B4513" # SaddleBrown
            else:
                row_color = "#B8860B" # DarkGoldenrod
                
            row_frame = ctk.CTkFrame(self.alerts_frame, fg_color=row_color, corner_radius=3)
            row_frame.pack(fill="x", pady=2)

            values = [
                trans.get('date', ''),
                trans.get('buyer', ''),
                trans.get('order_id', ''),
                trans.get('product_id', ''),
                f"${trans.get('gross',0):.2f}",
                f"${profit:.2f}",
                f"{margin:.1f}%"
            ]

            for j, val in enumerate(values):
                lbl = ctk.CTkLabel(row_frame, text=val, width=col_widths[j], anchor="w", font=ctk.CTkFont(size=12, weight="bold"))
                lbl.pack(side="left", padx=2)
                
            edit_btn = ctk.CTkButton(row_frame, text="✏️", width=30, height=20, command=lambda t=trans: self.edit_transaction(t))
            edit_btn.pack(side="right", padx=5)

    # ==================== 【新增】批量导入 (Batch Import) ====================
    def batch_import_excel(self):
        file_path = filedialog.askopenfilename(
            title="选择要导入的批量订单报表",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("CSV Files", "*.csv")]
        )
        if not file_path:
            return
            
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
                
            # Naive column mapping mechanism - will attempt to find matching columns
            # This is a basic implementation. In production, provide a mapping tool for the user.
            col_map = {
                'buyer': ['buyer', '买家', 'buyer_name', 'account'],
                'order_id': ['order_id', 'order id', '订单号', 'order no'],
                'product_id': ['product_id', 'product id', '商品', 'item id'],
                'gross': ['gross', 'gross_order', '订单金额', 'amount', '总计', 'usd', 'total'],
                'date': ['date', 'time', '日期', 'order date']
            }
            
            def find_col(aliases):
                for col in df.columns:
                    if str(col).lower().strip() in [a.lower() for a in aliases]:
                        return col
                return None
                
            mapped_df = pd.DataFrame()
            for key, aliases in col_map.items():
                found_col = find_col(aliases)
                if found_col:
                    mapped_df[key] = df[found_col]
                else:
                    if key == 'date':
                        mapped_df[key] = datetime.now().strftime("%Y-%m-%d")
                    elif key in ['buyer', 'order_id', 'product_id']:
                        mapped_df[key] = f"Imported_{key}"
                    else:
                        mapped_df[key] = 0.0

            success_count = 0
            
            commission_rate = config_manager.get_fee("commission_rate", 10.24) / 100.0
            service_rate = config_manager.get_fee("service_fee_rate", 2.5) / 100.0
            affiliate_rate = config_manager.get_fee("affiliate_fee_rate", 1.64) / 100.0
            default_funding_pt = config_manager.get("funding_percent", 65.0)

            for _, row in mapped_df.iterrows():
                try:
                    # Parse numericals safely
                    gross_val = float(row.get('gross', 0.0))
                    if pd.isna(gross_val): gross_val = 0.0
                    
                    gross_usd = gross_val
                    funding_usd = gross_usd * (default_funding_pt / 100)
                    
                    # Calculate default fees
                    comm_usd = gross_usd * commission_rate
                    serv_usd = gross_usd * service_rate
                    aff_usd = gross_usd * affiliate_rate
                    
                    total_fees_usd = comm_usd + serv_usd + aff_usd
                    payout = gross_usd - total_fees_usd
                    
                    # Assume zero extra costs on import initially
                    net_profit = payout - funding_usd
                    margin = (net_profit / gross_usd * 100) if gross_usd > 0 else 0
                    
                    dt_val = str(row.get('date', datetime.now().strftime("%Y-%m-%d")))
                    if pd.isna(dt_val) or dt_val == 'nan' or dt_val == 'NaT':
                        dt_val = datetime.now().strftime("%Y-%m-%d")

                    trans = {
                        'username': self.username,
                        'date': dt_val[:10],
                        'buyer': str(row.get('buyer', 'Unknown')),
                        'order_id': str(row.get('order_id', 'Unknown')),
                        'product_id': str(row.get('product_id', '')),
                        'gross': gross_usd,
                        'funding_percent': default_funding_pt,
                        'funding': funding_usd,
                        'cogs_usd': 0.0,
                        'shipping_usd': 0.0,
                        'packaging_usd': 0.0,
                        'tax_usd': 0.0,
                        'total_costs_usd': 0.0,
                        'commission_cny': comm_usd * self.exchange_rate, # simplified representation inverse
                        'service_cny': serv_usd * self.exchange_rate,
                        'affiliate_cny': aff_usd * self.exchange_rate,
                        'total_fees_cny': total_fees_usd * self.exchange_rate,
                        'commission_usd': comm_usd,
                        'service_usd': serv_usd,
                        'affiliate_usd': aff_usd,
                        'total_fees_usd': total_fees_usd,
                        'payout': payout,
                        'net_profit': net_profit,
                        'profit_margin': margin,
                        'comm_percent': commission_rate * 100,
                        'serv_percent': service_rate * 100,
                        'aff_percent': affiliate_rate * 100
                    }
                    db_manager.insert_transaction(trans)
                    success_count += 1
                except Exception as ex:
                    print(f"Failed parsing row: {ex}")
                    continue
                    
            messagebox.showinfo(self.tr("success"), self.trf("import_success", success_count))
            self.refresh_transaction_log()
            self.refresh_alerts()
            
        except Exception as e:
            messagebox.showerror(self.tr("error"), self.trf("import_error", str(e)))

    # ==================== 【新增】深度分析标签页 ====================


    # =====================================================================
    # 【新增】create_analytics_tab — 深度分析 Tab
    # 精准插入到 FinancialSystemApp 类，不修改任何原有方法
    # 功能：月度/季度/年度汇总、利润趋势折线图、费用饼图、
    #       客户贡献度统计、产品利润率排行（从高到低）、含分析页签的Excel导出
    # =====================================================================

    def create_analytics_tab(self):
        """【新增功能】深度分析 Tab — UI 构建（支持 RTL 阿拉伯语）"""
        if not hasattr(self, "tab_analytics"):
            return
        tab = self.tab_analytics
        L = self.lang_dict[self.current_lang]
        is_ar = self.current_lang == "ar"
        # RTL时按钮pack方向取反
        btn_side  = "right" if is_ar else "left"
        exp_side  = "left"  if is_ar else "right"

        self.analytics_engine = AnalyticsEngine(db_manager, self.lang_dict, lambda: self.current_lang, fix_arabic)
        
        # ── 顶部按钮行 ────────────────────────────────────────────────────
        top_bar = ctk.CTkFrame(tab, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=(10, 5))

        buttons_cfg = [
            ("show_trend",    "#1E90FF", self._analytics_show_trend),
            ("show_pie",      "#E67E22", self._analytics_show_pie),
            ("show_period",   "#27AE60", self._analytics_show_period),
            ("show_customer", "#8E44AD", self._analytics_show_customer),
            ("show_product",  "#C0392B", self._analytics_show_product),
        ]
        for key, color, cmd in buttons_cfg:
            ctk.CTkButton(
                top_bar, text=L.get(key, key),
                fg_color=color, hover_color=color,
                height=36, command=cmd
            ).pack(side=btn_side, padx=4)

        # 周期选择（月/季/年）
        self._analytics_period_var = ctk.StringVar(value=L.get("period_monthly", "月度"))
        period_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        period_frame.pack(side=btn_side, padx=15)
        lbl_period = {"zh":"周期:","en":"Period:","ar":"الفترة:"}.get(self.current_lang,"Period:")
        ctk.CTkLabel(period_frame, text=lbl_period, font=ctk.CTkFont(size=12)).pack(side=btn_side, padx=4)
        ctk.CTkSegmentedButton(
            period_frame,
            values=[
                L.get("period_monthly", "月度"),
                L.get("period_quarterly", "季度"),
                L.get("period_yearly", "年度"),
            ],
            variable=self._analytics_period_var, width=200
        ).pack(side=btn_side)

        # 导出增强按钮（对面方向）
        export_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        export_frame.pack(side=exp_side, padx=5)

        self._export_btn = ctk.CTkButton(
            export_frame,
            text=L.get("export_report_btn", "📥 导出含分析报告的Excel"),
            fg_color="#2C3E50", hover_color="#1A252F",
            height=36, command=self._analytics_export_enhanced
        )
        self._export_btn.pack(side=exp_side, padx=4)

        # ── 图表区（主）+ 表格区（侧） ────────────────────────────────────
        body = ctk.CTkFrame(tab, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=5)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        # 图表画布框架（RTL时在右列）
        chart_col = 1 if is_ar else 0
        table_col = 0 if is_ar else 1

        self._chart_frame = ctk.CTkFrame(body, fg_color="#1A1A2E", corner_radius=12)
        self._chart_frame.grid(row=0, column=chart_col, sticky="nsew",
                               padx=(5,0) if is_ar else (0,5))
        lbl_placeholder = {"zh":"点击上方按钮\n生成图表或报表","en":"Click a button above\nto generate chart","ar":"انقر فوق زر أعلاه\nلإنشاء الرسم البياني"}.get(self.current_lang,"Click a button above\nto generate chart")
        self._chart_placeholder = ctk.CTkLabel(
            self._chart_frame, text=f"📊\n\n{lbl_placeholder}",
            font=ctk.CTkFont(size=16), text_color="#555"
        )
        self._chart_placeholder.pack(expand=True)

        # 数据表格框架
        lbl_detail = {"zh":"数据明细","en":"Data Detail","ar":"تفاصيل البيانات"}.get(self.current_lang,"Data Detail")
        table_outer = ctk.CTkFrame(body, fg_color="#1A1A2E", corner_radius=12)
        table_outer.grid(row=0, column=table_col, sticky="nsew")
        self._analytics_table_title = ctk.CTkLabel(
            table_outer, text=lbl_detail,
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#87CEEB",
            anchor="e" if is_ar else "w"
        )
        self._analytics_table_title.pack(anchor="e" if is_ar else "w", padx=12, pady=(10, 4))
        self._analytics_table_frame = ctk.CTkScrollableFrame(table_outer, fg_color="transparent")
        self._analytics_table_frame.pack(fill="both", expand=True, padx=6, pady=(0, 8))

    # ── 内部辅助 ─────────────────────────────────────────────────────────

    def _clear_table(self):
        for w in self._analytics_table_frame.winfo_children():
            w.destroy()

    def _check_matplotlib(self):
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showwarning(
                "缺少库",
                self.lang_dict[self.current_lang].get(
                    "analytics_not_available",
                    "请先安装 matplotlib: pip install matplotlib"
                )
            )
            return False
        return True

    def _render_table(self, rows, headers, title="数据明细"):
        """在右侧表格区渲染简单网格表（支持RTL）"""
        self._clear_table()
        self._analytics_table_title.configure(text=title)
        is_ar = self.current_lang == "ar"
        cell_side = "right" if is_ar else "left"
        text_anchor = "e" if is_ar else "w"
        col_w = max(55, 260 // max(len(headers), 1))

        # 表头
        hrow = ctk.CTkFrame(self._analytics_table_frame, fg_color="#2C3E50", corner_radius=4)
        hrow.pack(fill="x", pady=(0, 2))
        header_list = list(reversed(headers)) if is_ar else headers
        for h in header_list:
            ctk.CTkLabel(
                hrow, text=str(h), width=col_w,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#87CEEB", anchor=text_anchor
            ).pack(side=cell_side, padx=2, pady=4)

        # 数据行
        for i, row in enumerate(rows):
            bg = "#252535" if i % 2 == 0 else "#1E1E2E"
            drow = ctk.CTkFrame(self._analytics_table_frame, fg_color=bg, corner_radius=3)
            drow.pack(fill="x", pady=1)
            row_list = list(reversed(row)) if is_ar else row
            for cell in row_list:
                ctk.CTkLabel(
                    drow, text=str(cell), width=col_w,
                    font=ctk.CTkFont(size=10), anchor=text_anchor
                ).pack(side=cell_side, padx=2, pady=3)

    # ── 【新增功能2】利润趋势折线图 ─────────────────────────────────────

    def _analytics_show_trend(self):
        if not self._check_matplotlib():
            return
            
        result = self.analytics_engine.plot_trend(self._chart_frame)
        if not result:
            messagebox.showwarning("无数据", self.lang_dict[self.current_lang].get("no_data_analysis", "暂无数据"))
            return
            
        canvas, monthly = result
        
        lbl_profit = {"zh": "净利润 (USD)", "en": "Net Profit (USD)", "ar": "صافي الربح (USD)"}.get(self.current_lang, "Net Profit (USD)")
        lbl_trades = {"zh": "交易数", "en": "Trades", "ar": "الصفقات"}.get(self.current_lang, "Trades")
        lbl_table_title = {"zh": "月度利润明细", "en": "Monthly Profit Detail", "ar": "تفاصيل الربح الشهري"}.get(self.current_lang, "Monthly Profit Detail")
        lbl_month  = {"zh": "月份", "en": "Month", "ar": "الشهر"}.get(self.current_lang, "Month")
        lbl_orders = {"zh": "订单额", "en": "Gross", "ar": "إجمالي الطلب"}.get(self.current_lang, "Gross")

        rows = [
            (r["month"], f"{r['net_profit_sum']:.2f}", str(r["trade_count"]), f"{r['gross_sum']:.2f}")
            for _, r in monthly.iterrows()
        ]
        self._render_table(rows, [fix_arabic(lbl_month), fix_arabic(lbl_profit), fix_arabic(lbl_trades), fix_arabic(lbl_orders)], fix_arabic(lbl_table_title))

    # ── 【新增功能2】费用构成饼图 ─────────────────────────────────────────

    def _analytics_show_pie(self):
        if not self._check_matplotlib():
            return
            
        L = self.lang_dict[self.current_lang]
        _lbl = {
            "zh": {"costs":"商品成本","fees":"平台费用","profit":"净利润","other":"其他费用","total":"总订单额","title":"🥧 费用构成分析","table_title":"费用构成明细","col_cat":"类别","col_amt":"金额(USD)","col_pct":"占比","no_data":"费用数据全为零，请先录入交易"},
            "en": {"costs":"Product Costs","fees":"Platform Fees","profit":"Net Profit","other":"Other","total":"Total Orders","title":"🥧 Cost Breakdown","table_title":"Cost Breakdown Detail","col_cat":"Category","col_amt":"Amount(USD)","col_pct":"Share","no_data":"All fee data is zero, please add transactions first"},
            "ar": {"costs":"تكلفة البضاعة","fees":"رسوم المنصة","profit":"صافي الربح","other":"أخرى","total":"إجمالي الطلبات","title":"🥧 تحليل تكوين التكاليف","table_title":"تفاصيل التكاليف","col_cat":"الفئة","col_amt":"المبلغ(USD)","col_pct":"النسبة","no_data":"بيانات الرسوم صفر، يرجى إضافة معاملات"},
        }
        lbl = _lbl.get(self.current_lang, _lbl["en"])
        
        result = self.analytics_engine.plot_pie(self._chart_frame, lbl)
        if not result:
            messagebox.showwarning("无数据", self.lang_dict[self.current_lang].get("no_data_analysis", "暂无数据"))
            return
            
        canvas, labels2, sizes2, total_gross = result
        
        rows = [
            (l, "${:,.2f}".format(s), "{:.1f}%".format(s / total_gross * 100) if total_gross else "0%")
            for l, s in zip(labels2, sizes2)
        ]
        self._render_table(rows, [fix_arabic(lbl["col_cat"]), fix_arabic(lbl["col_amt"]), fix_arabic(lbl["col_pct"])], fix_arabic(lbl["table_title"]))

    # ── 【新增功能1】月度/季度/年度利润汇总 ──────────────────────────────

    def _analytics_show_period(self):
        if not self._check_matplotlib():
            return
            
        L = self.lang_dict[self.current_lang]
        period_label = self._analytics_period_var.get()

        _titles = {
            "zh": {"monthly":"月度利润汇总","quarterly":"季度利润汇总","yearly":"年度利润汇总"},
            "en": {"monthly":"Monthly Profit Summary","quarterly":"Quarterly Profit Summary","yearly":"Yearly Profit Summary"},
            "ar": {"monthly":"ملخص الربح الشهري","quarterly":"ملخص الربح الربعي","yearly":"ملخص الربح السنوي"},
        }
        _cols = {
            "zh": {"period":"周期","orders":"订单数","gross":"订单额","profit":"净利润","margin":"利润率","ylabel":"净利润 (USD)"},
            "en": {"period":"Period","orders":"Orders","gross":"Gross","profit":"Net Profit","margin":"Margin","ylabel":"Net Profit (USD)"},
            "ar": {"period":"الفترة","orders":"الطلبات","gross":"إجمالي الطلب","profit":"صافي الربح","margin":"الهامش","ylabel":"صافي الربح (USD)"},
        }
        titles = _titles.get(self.current_lang, _titles["en"])
        cols   = _cols.get(self.current_lang, _cols["en"])

        if period_label == L.get("period_monthly", "月度"):
            period_type = "monthly"
            title = titles["monthly"]
        elif period_label == L.get("period_quarterly", "季度"):
            period_type = "quarterly"
            title = titles["quarterly"]
        else:
            period_type = "yearly"
            title = titles["yearly"]
            
        summary = self.analytics_engine.get_period_data(period_type)
        if summary is None or summary.empty:
            messagebox.showwarning("无数据", self.lang_dict[self.current_lang].get("no_data_analysis", "暂无数据"))
            return

        self.analytics_engine.plot_period(self._chart_frame, summary, title, cols["ylabel"])

        rows = [
            (r["period"], str(r["order_count"]), "${:.2f}".format(r["gross_sum"]),
             "${:.2f}".format(r["profit_sum"]), "{:.1f}%".format(r["margin_mean"]))
            for _, r in summary.iterrows()
        ]
        self._render_table(rows,
                           [fix_arabic(cols["period"]), fix_arabic(cols["orders"]), fix_arabic(cols["gross"]), fix_arabic(cols["profit"]), fix_arabic(cols["margin"])],
                           fix_arabic(title))

    # ── 【新增功能3】客户交易频次与贡献度统计 ────────────────────────────

    def _analytics_show_customer(self):
        if not self._check_matplotlib():
            return
            
        _lbl = {
            "zh": {"title":"👥 客户贡献度分析 (Top 15)","xlabel":"总净利润 (USD)","table_title":"客户贡献度 Top15","col_buyer":"买家账号","col_trades":"交易次","col_profit":"总利润","col_avg":"均利润","col_contrib":"贡献度"},
            "en": {"title":"👥 Customer Contribution (Top 15)","xlabel":"Total Net Profit (USD)","table_title":"Customer Contribution Top15","col_buyer":"Buyer","col_trades":"Trades","col_profit":"Total Profit","col_avg":"Avg Profit","col_contrib":"Share"},
            "ar": {"title":"👥 مساهمة العملاء (أفضل 15)","xlabel":"إجمالي صافي الربح (USD)","table_title":"أفضل 15 عميلاً","col_buyer":"المشتري","col_trades":"الصفقات","col_profit":"إجمالي الربح","col_avg":"متوسط الربح","col_contrib":"النسبة"},
        }
        lbl = _lbl.get(self.current_lang, _lbl["en"])

        cust = self.analytics_engine.get_customer_data()
        if cust is None or cust.empty:
            messagebox.showwarning("无数据", self.lang_dict[self.current_lang].get("no_data_analysis", "暂无数据"))
            return

        self.analytics_engine.plot_customer(self._chart_frame, cust, lbl["title"], lbl["xlabel"])

        rows = [
            (r["buyer"], str(r["trade_count"]),
             "${:.2f}".format(r["total_profit"]),
             "${:.2f}".format(r["avg_profit"]),
             "{:.1f}%".format(r["contribution"]))
            for _, r in cust.iterrows()
        ]
        self._render_table(
            rows,
            [fix_arabic(lbl["col_buyer"]), fix_arabic(lbl["col_trades"]), fix_arabic(lbl["col_profit"]), fix_arabic(lbl["col_avg"]), fix_arabic(lbl["col_contrib"])],
            fix_arabic(lbl["table_title"])
        )

    # ── 【新增功能3】产品利润率排行（从高到低） ──────────────────────────

    def _analytics_show_product(self):
        if not self._check_matplotlib():
            return
            
        _lbl = {
            "zh": {"title":"📦 产品利润率排行 (从高到低)","xlabel":"平均利润率 (%)","warn10":"⚠️ 10% 警戒线","good15":"✅ 15% 优秀线","table_title":"产品利润率排行","col_rank":"排名","col_pid":"产品ID","col_margin":"利润率","col_profit":"总利润","col_orders":"订单数"},
            "en": {"title":"📦 Product Margin Ranking (High→Low)","xlabel":"Avg Margin (%)","warn10":"⚠️ 10% Warning","good15":"✅ 15% Excellent","table_title":"Product Margin Ranking","col_rank":"Rank","col_pid":"Product ID","col_margin":"Margin","col_profit":"Total Profit","col_orders":"Orders"},
            "ar": {"title":"📦 ترتيب هامش المنتجات (من الأعلى)","xlabel":"متوسط الهامش (%)","warn10":"⚠️ تحذير 10%","good15":"✅ ممتاز 15%","table_title":"ترتيب هامش المنتجات","col_rank":"الترتيب","col_pid":"معرف المنتج","col_margin":"الهامش","col_profit":"إجمالي الربح","col_orders":"الطلبات"},
        }
        lbl = _lbl.get(self.current_lang, _lbl["en"])

        prod = self.analytics_engine.get_product_data()
        if prod is None or prod.empty:
            messagebox.showwarning("无数据", self.lang_dict[self.current_lang].get("no_data_analysis", "暂无数据"))
            return

        self.analytics_engine.plot_product(self._chart_frame, prod, lbl["title"], lbl["xlabel"], lbl["warn10"], lbl["good15"])

        rows = [
            (i + 1, r["product_id"], "{:.1f}%".format(r["avg_margin"]),
             "${:.2f}".format(r["total_profit"]), str(r["order_count"]))
            for i, (_, r) in enumerate(prod.iterrows())
        ]
        self._render_table(
            rows,
            [fix_arabic(lbl["col_rank"]), fix_arabic(lbl["col_pid"]), fix_arabic(lbl["col_margin"]), fix_arabic(lbl["col_profit"]), fix_arabic(lbl["col_orders"])],
            fix_arabic(lbl["table_title"])
        )

    # ── 【新增功能4】导出增强：含"分析报告"页签的 Excel ────────────────

    def _analytics_export_enhanced(self):
        """
        【新增】在原有交易明细导出基础上，增加"分析报告"等汇总页签。
        原有 export_to_excel 功能完全不变，此为独立的增强导出入口。
        Excel 页签：交易明细 / 分析报告 / 月度利润汇总 / 季度利润汇总 /
                    年度利润汇总 / 客户贡献度Top10 / 产品利润率排行
        """
        L = self.lang_dict[self.current_lang]
        
        # 使用 db_manager 获取数据，而不是废弃的 self.transactions
        trans_list = db_manager.get_all_transactions()
        
        if not trans_list:
            messagebox.showwarning(
                L.get("warning_no_data_export", "无数据"),
                L.get("warning_no_data_export", "暂无交易数据")
            )
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="财务综合分析报告.xlsx"
        )
        if not file_path:
            return

        # ── 原有交易明细（完整保留，不做任何修改）──
        df_raw = pd.DataFrame(trans_list)
        cols = [
            "username", "date", "buyer", "order_id", "product_id",
            "gross", "funding_percent", "funding",
            "cogs_usd", "shipping_usd", "packaging_usd", "tax_usd",
            "total_costs_usd",
            "commission_cny", "service_cny", "affiliate_cny", "total_fees_cny",
            "commission_usd", "service_usd", "affiliate_usd", "total_fees_usd",
            "payout", "net_profit", "profit_margin"
        ]
        available_cols = [c for c in cols if c in df_raw.columns]
        df_export = df_raw[available_cols].copy()

        # ── 分析数据准备 ──
        df = df_raw.copy()
        df["date_dt"] = pd.to_datetime(df.get("date", pd.NaT), errors="coerce")
        for col in ["net_profit", "gross", "profit_margin",
                    "total_costs_usd", "total_fees_usd"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            else:
                df[col] = 0.0

        # 月度汇总
        df["month"] = df["date_dt"].dt.strftime("%Y-%m")
        monthly = df.groupby("month").agg(
            订单数=("gross", "count"),
            总订单额=("gross", "sum"),
            总净利润=("net_profit", "sum"),
            平均利润率=("profit_margin", "mean")
        ).reset_index().rename(columns={"month": "月份"}).round(2)

        # 季度汇总
        df["quarter"] = (
            df["date_dt"].dt.year.astype(str) + "-Q" +
            df["date_dt"].dt.quarter.astype(str)
        )
        quarterly = df.groupby("quarter").agg(
            订单数=("gross", "count"),
            总订单额=("gross", "sum"),
            总净利润=("net_profit", "sum"),
            平均利润率=("profit_margin", "mean")
        ).reset_index().rename(columns={"quarter": "季度"}).round(2)

        # 年度汇总
        df["year"] = df["date_dt"].dt.year
        yearly = df.groupby("year").agg(
            订单数=("gross", "count"),
            总订单额=("gross", "sum"),
            总净利润=("net_profit", "sum"),
            平均利润率=("profit_margin", "mean")
        ).reset_index().rename(columns={"year": "年份"}).round(2)

        # 客户贡献度 Top10
        if "buyer" in df.columns:
            cust = df.groupby("buyer").agg(
                交易次数=("gross", "count"),
                总净利润=("net_profit", "sum"),
                平均净利润=("net_profit", "mean"),
                总订单额=("gross", "sum")
            ).reset_index()
            profit_sum = cust["总净利润"].sum()
            cust["贡献度(%)"] = (
                cust["总净利润"] / profit_sum * 100
                if profit_sum != 0 else 0
            ).round(2)
            cust = cust.sort_values("总净利润", ascending=False).head(10).round(2)
        else:
            cust = pd.DataFrame({"提示": ["无buyer字段"]})

        # 产品利润率排行（从高到低）
        if "product_id" in df.columns:
            prod = df.groupby("product_id").agg(
                订单数=("gross", "count"),
                总净利润=("net_profit", "sum"),
                平均利润率=("profit_margin", "mean"),
                总订单额=("gross", "sum")
            ).reset_index()
            prod = prod.sort_values("平均利润率", ascending=False).round(2)
            prod.insert(0, "利润率排名", range(1, len(prod) + 1))
        else:
            prod = pd.DataFrame({"提示": ["无product_id字段"]})

        # 分析报告摘要
        total_profit = df["net_profit"].sum()
        total_gross  = df["gross"].sum()
        summary_df = pd.DataFrame({
            "指标": [
                "报告生成时间", "交易总笔数", "总订单额(USD)",
                "总净利润(USD)", "平均利润率(%)",
                "月均净利润(USD)", "客户数", "产品种类数"
            ],
            "数值": [
                pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                len(df),
                round(total_gross, 2),
                round(total_profit, 2),
                round(df["profit_margin"].mean(), 2),
                round(monthly["总净利润"].mean(), 2) if not monthly.empty else 0,
                df["buyer"].nunique() if "buyer" in df.columns else "N/A",
                df["product_id"].nunique() if "product_id" in df.columns else "N/A",
            ]
        })

        # ── 写入 Excel（共7个页签） ──
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df_export.to_excel(writer, sheet_name="交易明细", index=False)
            summary_df.to_excel(writer, sheet_name="分析报告", index=False)
            monthly.to_excel(writer, sheet_name="月度利润汇总", index=False)
            quarterly.to_excel(writer, sheet_name="季度利润汇总", index=False)
            yearly.to_excel(writer, sheet_name="年度利润汇总", index=False)
            cust.to_excel(writer, sheet_name="客户贡献度Top10", index=False)
            prod.to_excel(writer, sheet_name="产品利润率排行", index=False)

            # 自动调整列宽
            for sheet_name in writer.sheets:
                ws = writer.sheets[sheet_name]
                for col in ws.columns:
                    max_len = max(
                        len(str(cell.value)) if cell.value is not None else 0
                        for cell in col
                    )
                    ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 32)

        messagebox.showinfo(
            "导出成功",
            "综合分析报告已导出！\n共7个页签：交易明细 / 分析报告 / "
            "月度汇总 / 季度汇总 / 年度汇总 / 客户贡献度Top10 / 产品利润率排行\n\n" + file_path
        )


# -------------------- بدء التشغيل --------------------
if __name__ == "__main__":
    root = ctk.CTk()
    current_lang = "zh"
    while True:
        login = LoginWindow(root, current_lang)
        login.pack(fill="both", expand=True)
        
        def on_login_close():
            login.auth_success = False
            root.quit()
            
        root.protocol("WM_DELETE_WINDOW", on_login_close)
        root.mainloop()
        
        login.pack_forget()
        auth_success = getattr(login, "auth_success", False)
        username = getattr(login, "username", None)
        role = getattr(login, "role", None)
        current_lang = login.current_lang
        
        login.destroy()
        
        if auth_success:
            app = FinanceSystemApp(root, username, role, current_lang)
            app.pack(fill="both", expand=True)
            
            def on_app_close():
                app.logout_requested = False
                root.quit()
                
            root.protocol("WM_DELETE_WINDOW", on_app_close)
            root.mainloop()
            
            app.pack_forget()
            logout_requested = getattr(app, "logout_requested", False)
            current_lang = app.current_lang
            app.destroy()
            
            if logout_requested:
                continue
            else:
                break
        else:
            break
