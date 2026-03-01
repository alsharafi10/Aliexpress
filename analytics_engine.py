import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class AnalyticsEngine:
    def __init__(self, db_manager, lang_dict, current_lang_getter, fix_arabic_func):
        self.db = db_manager
        self.lang_dict = lang_dict
        self.get_lang = current_lang_getter
        self.fix_arabic = fix_arabic_func
        
        # Support Arabic fonts
        matplotlib.rcParams['font.family'] = ['Arial', 'Tahoma', 'DejaVu Sans', 'sans-serif']

    def get_df(self):
        df = self.db.get_dataframe()
        if df.empty:
            return None
        
        df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date_dt"])
        
        # Ensure numerical columns
        numeric_cols = ["net_profit", "gross", "profit_margin", "funding", "total_costs_usd", "total_fees_usd"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            else:
                df[col] = 0.0
                
        return df

    def get_trend_data(self):
        df = self.get_df()
        if df is None: return None
        
        df["month"] = df["date_dt"].dt.strftime("%Y-%m")
        monthly = df.groupby("month").agg(
            net_profit_sum=("net_profit", "sum"),
            trade_count=("net_profit", "count"),
            gross_sum=("gross", "sum")
        ).reset_index()
        return monthly

    def plot_trend(self, master_frame):
        monthly = self.get_trend_data()
        if monthly is None or monthly.empty: return None

        plt.rcParams.update({'font.size': 13})
        fig, ax1 = plt.subplots(figsize=(9, 5), facecolor="#1A1A2E")
        ax1.set_facecolor("#1E1E2E")
        ax2 = ax1.twinx()

        lang = self.get_lang()
        L = self.lang_dict.get(lang, {})
        
        lbl_profit = L.get("net_profit", "Net Profit (USD)")
        lbl_trades = L.get("customer_freq", "Trades")
        lbl_title  = L.get("profit_trend", "📈 Monthly Profit Trend")

        xs = range(len(monthly))
        ax1.plot(xs, monthly["net_profit_sum"], marker="o", color="#2ECC71",
                 linewidth=2.8, markersize=9, label=lbl_profit, zorder=3)
        ax1.fill_between(xs, monthly["net_profit_sum"], alpha=0.18, color="#2ECC71")
        ax2.bar(xs, monthly["trade_count"], color="#3498DB",
                alpha=0.40, label=lbl_trades, zorder=1, width=0.55)

        ax1.set_xticks(list(xs))
        ax1.set_xticklabels(monthly["month"], rotation=40, ha="right",
                             fontsize=12, color="#EEEEEE", fontweight="bold")
        
        # Labels
        ax1.set_ylabel(self.fix_arabic(lbl_profit), color="#2ECC71", fontsize=13, fontweight="bold")
        ax2.set_ylabel(self.fix_arabic(lbl_trades), color="#3498DB", fontsize=13, fontweight="bold")
        
        # Colors
        ax1.tick_params(axis='y', colors="#2ECC71", labelsize=11)
        ax1.tick_params(axis='x', colors="#EEEEEE", labelsize=12)
        ax2.tick_params(colors="#3498DB", labelsize=11)
        
        for ax in [ax1, ax2]:
            for spine in ax.spines.values():
                spine.set_color("#444")
        
        ax1.grid(True, alpha=0.20, color="#555", linestyle="--")

        for i, val in enumerate(monthly["net_profit_sum"]):
            ax1.annotate(f"${val:.0f}",
                         xy=(i, val), xytext=(0, 12),
                         textcoords="offset points", ha="center",
                         fontsize=11, color="#FFFFFF", fontweight="bold",
                         bbox=dict(boxstyle="round,pad=0.2", fc="#2ECC71", alpha=0.75, ec="none"))

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        labels_all = [self.fix_arabic(l) for l in labels1 + labels2]
        
        legend_loc = "upper right" if lang == "ar" else "upper left"
        ax1.legend(lines1 + lines2, labels_all, loc=legend_loc,
                   facecolor="#252535", labelcolor="#EEEEEE",
                   fontsize=12, framealpha=0.92, edgecolor="#555")
                   
        fig.suptitle(self.fix_arabic(lbl_title), color="#87CEEB", fontsize=15, fontweight="bold", y=0.98)
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        
        return self._render_canvas(fig, master_frame), monthly

    def _render_canvas(self, fig, master_frame):
        for w in master_frame.winfo_children():
            w.destroy()
        canvas = FigureCanvasTkAgg(fig, master=master_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)
        plt.close(fig)
        return canvas

    def get_pie_data(self):
        df = self.get_df()
        if df is None: return None
        
        total_gross  = df["gross"].sum()
        total_costs  = df["total_costs_usd"].sum()
        total_fees   = df["total_fees_usd"].sum()
        total_profit = df["net_profit"].sum()
        other = max(0, total_gross - total_costs - total_fees - total_profit)
        
        return total_gross, total_costs, total_fees, total_profit, other

    def plot_pie(self, master_frame, labels_dict):
        data = self.get_pie_data()
        if not data: return None
        
        total_gross, total_costs, total_fees, total_profit, other = data
        
        labels  = [labels_dict["costs"], labels_dict["fees"], labels_dict["profit"], labels_dict["other"]]
        sizes   = [total_costs, total_fees, total_profit, other]
        colors  = ["#E74C3C", "#E67E22", "#27AE60", "#7F8C8D"]
        
        filtered = [(l, s, c) for l, s, c in zip(labels, sizes, colors) if s > 0]
        if not filtered: return None
        
        labels2, sizes2, colors2 = zip(*filtered)

        fig, ax = plt.subplots(figsize=(8, 5.5), facecolor="#1A1A2E")
        ax.set_facecolor("#1A1A2E")

        wedges, texts, autotexts = ax.pie(
            sizes2, labels=None, colors=colors2,
            autopct="%1.1f%%", startangle=140,
            pctdistance=0.70, explode=[0.04] * len(sizes2),
            wedgeprops={"linewidth": 2.0, "edgecolor": "#1A1A2E"}
        )
        
        for at in autotexts:
            at.set_color("white")
            at.set_fontsize(13)
            at.set_fontweight("bold")

        centre = plt.Circle((0, 0), 0.48, fc="#1A1A2E")
        ax.add_patch(centre)
        
        ax.text(0, 0.05, self.fix_arabic(labels_dict["total"]), ha="center", va="center", fontsize=11, color="#AAAAAA")
        ax.text(0, -0.18, "${:,.0f}".format(total_gross), ha="center", va="center", fontsize=14, color="#87CEEB", fontweight="bold")

        legend_labels = [
            self.fix_arabic(f"{l}  ${s:,.2f}  ({s/total_gross*100:.1f}%)") if total_gross else self.fix_arabic(f"{l}  ${s:,.2f}")
            for l, s in zip(labels2, sizes2)
        ]
        
        ax.legend(wedges, legend_labels, loc="center left", bbox_to_anchor=(1.02, 0.5),
                  fontsize=12, labelcolor="#EEEEEE", facecolor="#252535", edgecolor="#555555", framealpha=0.92)

        fig.suptitle(self.fix_arabic(labels_dict["title"]), color="#87CEEB", fontsize=15, fontweight="bold", y=0.98)
        fig.tight_layout(rect=[0, 0, 0.82, 0.96])
        
        return self._render_canvas(fig, master_frame), labels2, sizes2, total_gross

    def get_period_data(self, period_type):
        df = self.get_df()
        if df is None: return None
        
        if period_type == "monthly":
            df["period"] = df["date_dt"].dt.strftime("%Y-%m")
        elif period_type == "quarterly":
            df["period"] = df["date_dt"].dt.year.astype(str) + "-Q" + df["date_dt"].dt.quarter.astype(str)
        else:
            df["period"] = df["date_dt"].dt.year.astype(str)
            
        summary = df.groupby("period").agg(
            order_count=("gross", "count"),
            gross_sum=("gross", "sum"),
            profit_sum=("net_profit", "sum"),
            margin_mean=("profit_margin", "mean")
        ).reset_index()
        return summary.round(2)

    def plot_period(self, master_frame, summary, title, ylabel):
        fig, ax = plt.subplots(figsize=(9, 4.5), facecolor="#1A1A2E")
        ax.set_facecolor("#1E1E2E")
        
        bar_colors = ["#27AE60" if v >= 0 else "#E74C3C" for v in summary["profit_sum"]]
        bars = ax.bar(summary["period"], summary["profit_sum"],
                      color=bar_colors, edgecolor="#1A1A2E", linewidth=0.8, width=0.6)
                      
        ax.set_xticks(range(len(summary["period"])))
        ax.set_xticklabels(summary["period"], rotation=40, ha="right",
                           fontsize=12, color="#EEEEEE", fontweight="bold")
                           
        ax.set_ylabel(self.fix_arabic(ylabel), color="#EEEEEE", fontsize=13, fontweight="bold")
        ax.tick_params(axis="y", colors="#CCCCCC", labelsize=11)
        ax.tick_params(axis="x", colors="#EEEEEE", labelsize=12)
        
        for spine in ax.spines.values():
            spine.set_color("#444")
        ax.grid(True, axis="y", alpha=0.18, color="#666", linestyle="--")
        
        max_val = summary["profit_sum"].max() if not summary.empty else 1
        for bar, val in zip(bars, summary["profit_sum"]):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max_val * 0.025,
                    "${:.0f}".format(val),
                    ha="center", va="bottom", fontsize=12, color="#FFFFFF", fontweight="bold")
                    
        fig.suptitle(self.fix_arabic("📊 " + title), color="#87CEEB", fontsize=15, fontweight="bold", y=0.99)
        fig.tight_layout(rect=[0, 0, 1, 0.97])
        
        return self._render_canvas(fig, master_frame)

    def get_customer_data(self):
        df = self.get_df()
        if df is None or "buyer" not in df.columns: return None
        
        cust = df.groupby("buyer").agg(
            trade_count=("gross", "count"),
            total_profit=("net_profit", "sum"),
            avg_profit=("net_profit", "mean"),
            total_gross=("gross", "sum")
        ).reset_index()
        
        profit_sum = cust["total_profit"].sum()
        cust["contribution"] = (cust["total_profit"] / profit_sum * 100 if profit_sum else 0).round(2)
        return cust.sort_values("total_profit", ascending=False).head(15)

    def plot_customer(self, master_frame, cust, title, xlabel):
        fig, ax = plt.subplots(figsize=(9, max(4.0, len(cust) * 0.52)), facecolor="#1A1A2E")
        ax.set_facecolor("#1E1E2E")
        
        import numpy as np
        bar_colors = plt.cm.Blues_r(np.linspace(0.15, 0.75, len(cust)))
        bars = ax.barh(cust["buyer"], cust["total_profit"], color=bar_colors, edgecolor="#1A1A2E", height=0.65)

        ax.set_xlabel(self.fix_arabic(xlabel), color="#EEEEEE", fontsize=13, fontweight="bold")
        ax.tick_params(axis="y", colors="#EEEEEE", labelsize=12)
        ax.tick_params(axis="x", colors="#CCCCCC", labelsize=11)
        
        for spine in ax.spines.values(): spine.set_color("#444")
        ax.grid(True, axis="x", alpha=0.18, color="#666", linestyle="--")

        max_val = cust["total_profit"].max() if not cust.empty else 1
        for bar, val in zip(bars, cust["total_profit"]):
            ax.text(val + max_val * 0.015, bar.get_y() + bar.get_height() / 2, f"${val:.2f}", 
                    va="center", ha="left", fontsize=11, color="#FFFFFF", fontweight="bold")
                    
        if len(bars) > 0:
            ax.text(bars[0].get_width() / 2, bars[0].get_y() + bars[0].get_height() / 2, "🏆", 
                    va="center", ha="center", fontsize=13)

        fig.suptitle(self.fix_arabic(title), color="#87CEEB", fontsize=15, fontweight="bold", y=0.99)
        fig.tight_layout(rect=[0, 0, 1, 0.97])
        
        return self._render_canvas(fig, master_frame)

    def get_product_data(self):
        df = self.get_df()
        if df is None or "product_id" not in df.columns: return None
        
        prod = df.groupby("product_id").agg(
            order_count=("gross", "count"),
            total_profit=("net_profit", "sum"),
            avg_margin=("profit_margin", "mean"),
            total_gross=("gross", "sum")
        ).reset_index()
        
        prod["avg_margin"] = prod["avg_margin"].round(2)
        prod["total_profit"] = prod["total_profit"].round(2)
        return prod.sort_values("avg_margin", ascending=False)

    def plot_product(self, master_frame, prod, title, xlabel, warn_lbl, good_lbl):
        fig, ax = plt.subplots(figsize=(9, max(4.0, len(prod) * 0.56)), facecolor="#1A1A2E")
        ax.set_facecolor("#1E1E2E")

        bar_colors = ["#27AE60" if v >= 15 else "#E67E22" if v >= 10 else "#E74C3C" for v in prod["avg_margin"]]
        bars = ax.barh(prod["product_id"], prod["avg_margin"], color=bar_colors, edgecolor="#1A1A2E", height=0.65)

        ax.axvline(x=10, color="#FF4444", linewidth=2.5, linestyle="--", alpha=0.95, label=self.fix_arabic(warn_lbl), zorder=5)
        ax.axvline(x=15, color="#2ECC71", linewidth=2.0, linestyle=":", alpha=0.85, label=self.fix_arabic(good_lbl), zorder=5)

        ax.set_xlabel(self.fix_arabic(xlabel), color="#EEEEEE", fontsize=13, fontweight="bold")
        ax.tick_params(axis="both", colors="#EEEEEE", labelsize=12)
        for spine in ax.spines.values(): spine.set_color("#444")
        ax.grid(True, axis="x", alpha=0.18, color="#666", linestyle="--")

        for bar, val in zip(bars, prod["avg_margin"]):
            ax.text(val + 0.4, bar.get_y() + bar.get_height() / 2, f"{val:.1f}%", 
                    va="center", ha="left", fontsize=12, color="#FFFFFF", fontweight="bold")

        ax.legend(loc="lower right", fontsize=12, labelcolor="#EEEEEE", facecolor="#252535", edgecolor="#555555", framealpha=0.92)
        ax.invert_yaxis()
        
        fig.suptitle(self.fix_arabic(title), color="#87CEEB", fontsize=15, fontweight="bold", y=0.99)
        fig.tight_layout(rect=[0, 0, 1, 0.97])
        
        return self._render_canvas(fig, master_frame)
