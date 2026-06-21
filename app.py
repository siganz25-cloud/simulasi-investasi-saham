import pandas as pd
import numpy as np
import yfinance as yf

from datetime import date, datetime
from math import pi

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import (
    Div,
    MultiSelect,
    DatePicker,
    ColumnDataSource,
    LinearColorMapper,
    ColorBar,
    BasicTicker,
    LabelSet,
    Spinner,
    RadioButtonGroup,
    HoverTool,
)
from bokeh.plotting import figure
from bokeh.transform import transform, cumsum, dodge
from bokeh.palettes import RdBu, Category20


# =========================================
# JUDUL
# =========================================

# Placeholder kosong (dark mode dihapus)
global_style = Div(text="")

title = Div(
    text="""
    <h1>📈 Simulasi Investasi Saham Indonesia</h1>
    <p>
    Dashboard ini dirancang untuk membantu investor menganalisis performa saham LQ45
    berdasarkan data historis dari Yahoo Finance. Pengguna dapat melakukan visualisasi
    harga saham, membandingkan tingkat risiko dan return, mengevaluasi diversifikasi
    portfolio, serta melakukan simulasi investasi berkala untuk mendukung pengambilan
    keputusan investasi yang lebih optimal.
    </p>
    """,
    width=1000
)


# =========================================
# LIST SAHAM LQ45
# =========================================
lq45_stocks = {
    "ACES": "ACES.JK", "ADRO": "ADRO.JK", "AKRA": "AKRA.JK", "AMMN": "AMMN.JK",
    "ANTM": "ANTM.JK", "ASII": "ASII.JK", "BBCA": "BBCA.JK", "BBNI": "BBNI.JK",
    "BBRI": "BBRI.JK", "BBTN": "BBTN.JK", "BMRI": "BMRI.JK", "BRIS": "BRIS.JK",
    "BRPT": "BRPT.JK", "BUKA": "BUKA.JK", "CPIN": "CPIN.JK", "ESSA": "ESSA.JK",
    "EXCL": "EXCL.JK", "GOTO": "GOTO.JK", "HRUM": "HRUM.JK", "ICBP": "ICBP.JK",
    "INCO": "INCO.JK", "INDF": "INDF.JK", "INKP": "INKP.JK", "INTP": "INTP.JK",
    "ITMG": "ITMG.JK", "JPFA": "JPFA.JK", "KLBF": "KLBF.JK", "MAPI": "MAPI.JK",
    "MBMA": "MBMA.JK", "MDKA": "MDKA.JK", "MEDC": "MEDC.JK", "PGAS": "PGAS.JK",
    "PTBA": "PTBA.JK", "SMGR": "SMGR.JK", "SRTG": "SRTG.JK", "TLKM": "TLKM.JK",
    "TOWR": "TOWR.JK", "UNTR": "UNTR.JK", "UNVR": "UNVR.JK",
}


# =========================================
# WARNA & TEMA (LIGHT MODE)
# =========================================
DARK_BG = "#ffffff"
DARK_PANEL = "#f5f7fa"
DARK_TEXT = "#222222"
DARK_BORDER = "#dddddd"

# Palet warna untuk membedakan tiap saham di chart harga & scatter
STOCK_COLORS = Category20[20]


def get_stock_color(index):
    return STOCK_COLORS[index % len(STOCK_COLORS)]


def percent_color(value):
    """Hijau jika >= 0, merah jika < 0."""
    return "#2e7d32" if value >= 0 else "#c62828"


def style_dark_figure(fig):
    """Dark mode dihapus - figure memakai styling default Bokeh (light)."""
    return fig


# =========================================
# WIDGET FILTER
# =========================================
stock_select = MultiSelect(
    title="Pilih Saham",
    value=["BBCA", "BBRI", "TLKM"],
    options=list(lq45_stocks.keys()),
    size=10,
    width=250
)

start_picker = DatePicker(title="Tanggal Mulai", value=date(2023, 1, 1))
end_picker = DatePicker(title="Tanggal Akhir", value=date.today())

filter_title = Div(text="<h2>📊 Filter Data</h2>", styles={"color": DARK_TEXT})


# =========================================
# WIDGET INVESTASI & FREKUENSI
# =========================================
investment_title = Div(text="<h2>💰 Simulasi Investasi Portfolio</h2>", styles={"color": DARK_TEXT})

# Dibuat sekali untuk semua saham di LQ45, agar tidak perlu dibuat ulang
# setiap kali stock_select berubah. Spinner yang tidak terpilih cukup
# disembunyikan/diabaikan dari layout.
investment_inputs = {
    stock: Spinner(title=f"Investasi {stock}", low=0, step=100000, value=1000000, width=180)
    for stock in lq45_stocks
}

investment_layout = row()  # diisi oleh render()

frequency_title = Div(
    text="""
    <h2>💸 Strategi Investasi Berkala</h2>
    <p>
    Fitur ini memungkinkan simulasi strategi investasi berdasarkan
    frekuensi tertentu seperti harian, mingguan, bulanan, atau tahunan.
    Strategi ini umum digunakan dalam metode Dollar Cost Averaging (DCA).
    </p>
    """,
    styles={"color": DARK_TEXT}
)

frequency_selector = RadioButtonGroup(
    labels=["Sekali Investasi", "Harian", "Mingguan", "Bulanan", "Tahunan"],
    active=0
)


# =========================================
# DOWNLOAD DATASET
# =========================================
def load_data(stocks, start, end):
    all_data = []

    for stock in stocks:
        ticker = lq45_stocks[stock]

        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.reset_index(inplace=True)
        df["Stock"] = stock

        all_data.append(df)

    if len(all_data) == 0:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)


# =========================================
# BUILDER FUNCTIONS (dipakai saat awal & saat callback)
# =========================================

def build_price_chart(close_price):
    fig = figure(
        title="📈 Chart Harga Saham",
        x_axis_type="datetime",
        height=500,
        width=650,
        sizing_mode="fixed",
        tools="pan,wheel_zoom,box_zoom,reset,save"
    )

    for i, stock in enumerate(close_price.columns):
        source = ColumnDataSource(data={"Date": close_price.index, "Close": close_price[stock]})
        renderer = fig.line(
            x="Date", y="Close", source=source,
            legend_label=stock, line_width=2,
            color=get_stock_color(i)
        )

        fig.add_tools(HoverTool(
            renderers=[renderer],
            tooltips=[("Saham", stock), ("Tanggal", "@Date{%F}"), ("Harga", "@Close{0,0}")],
            formatters={"@Date": "datetime"},
            mode="mouse"
        ))

    fig.xaxis.axis_label = "Date"
    fig.yaxis.axis_label = "Price"
    fig.legend.click_policy = "hide"

    return style_dark_figure(fig)


def build_heatmap(correlation):
    corr_df = pd.DataFrame(
        [(i, j, correlation.loc[i, j]) for i in correlation.index for j in correlation.columns],
        columns=["Stock1", "Stock2", "Correlation"]
    )

    source_corr = ColumnDataSource(corr_df)

    # Rentang warna disesuaikan dengan nilai korelasi aktual (bukan fixed -1..1)
    # agar perbedaan warna lebih terlihat (lebih sensitif).
    corr_min = corr_df["Correlation"].min()
    corr_max = corr_df["Correlation"].max()

    # Beri sedikit padding agar tidak terlalu ekstrem, tapi tetap lebih sempit dari -1..1
    padding = (corr_max - corr_min) * 0.05 if corr_max != corr_min else 0.05
    low = max(corr_min - padding, -1)
    high = min(corr_max + padding, 1)

    mapper = LinearColorMapper(palette=list(reversed(RdBu[11])), low=low, high=high)

    stocks = list(correlation.columns)

    fig = figure(
        title="📊 Correlation Heatmap",
        x_range=stocks,
        y_range=list(reversed(stocks)),
        toolbar_location=None,
        height=500,
        width=450,
        tools=""
    )

    rect_renderer = fig.rect(
        x="Stock1", y="Stock2", width=1, height=1,
        source=source_corr,
        fill_color=transform("Correlation", mapper),
        line_color=None
    )

    fig.add_tools(HoverTool(
        renderers=[rect_renderer],
        tooltips=[("Pasangan", "@Stock1 - @Stock2"), ("Korelasi", "@Correlation{0.00}")]
    ))

    color_bar = ColorBar(color_mapper=mapper, ticker=BasicTicker(), location=(0, 0))
    color_bar.major_label_text_color = DARK_TEXT
    fig.add_layout(color_bar, "right")

    return style_dark_figure(fig)


def build_risk_table(risk_return_df):
    df = risk_return_df.copy()
    stocks = df["Stock"].tolist()

    source = ColumnDataSource(df)

    fig = figure(
        title="⚖️ Return vs Risk per Saham",
        x_range=stocks,
        height=350,
        width=450,
        sizing_mode="fixed",
        toolbar_location=None,
        tools="hover",
        tooltips=[("Saham", "@Stock"), ("Return", "@Return{0.0000}"), ("Risk", "@Risk{0.0000}")]
    )

    fig.vbar(
        x=dodge("Stock", -0.17, range=fig.x_range), top="Return", width=0.3,
        source=source, color="#42a5f5", legend_label="Return"
    )
    fig.vbar(
        x=dodge("Stock", 0.17, range=fig.x_range), top="Risk", width=0.3,
        source=source, color="#ef5350", legend_label="Risk"
    )

    fig.x_range.range_padding = 0.1
    fig.xgrid.grid_line_color = None
    fig.legend.location = "top_left"
    fig.legend.orientation = "horizontal"
    fig.xaxis.axis_label = "Saham"
    fig.yaxis.axis_label = "Value"

    return style_dark_figure(fig)


def build_scatter(risk_return_df):
    df = risk_return_df.copy()
    df["color"] = [get_stock_color(i) for i in range(len(df))]

    source = ColumnDataSource(df)

    fig = figure(
        title="⚖️ Scatter Plot Risk vs Return",
        height=400,
        width=650,
        sizing_mode="fixed",
        tools="pan,wheel_zoom,box_zoom,reset,save"
    )

    renderer = fig.scatter(x="Risk", y="Return", size=12, source=source, color="color")

    fig.add_tools(HoverTool(
        renderers=[renderer],
        tooltips=[("Saham", "@Stock"), ("Risk", "@Risk{0.0000}"), ("Return", "@Return{0.0000}")]
    ))

    labels = LabelSet(
        x="Risk", y="Return", text="Stock", source=source,
        x_offset=5, y_offset=5, text_color=DARK_TEXT
    )
    fig.add_layout(labels)

    fig.xaxis.axis_label = "Risk (Std Dev)"
    fig.yaxis.axis_label = "Average Return"

    return style_dark_figure(fig)


def build_insight(risk_return_df):
    if not risk_return_df.empty:
        best_stock = risk_return_df.loc[risk_return_df["Return"].idxmax(), "Stock"]
        riskiest_stock = risk_return_df.loc[risk_return_df["Risk"].idxmax(), "Stock"]
        lowest_risk_stock = risk_return_df.loc[risk_return_df["Risk"].idxmin(), "Stock"]
    else:
        best_stock = riskiest_stock = lowest_risk_stock = "-"

    return Div(
        text=f"""
        <div style="background-color:{DARK_PANEL}; color:{DARK_TEXT}; padding:15px; border-radius:8px; margin-top:10px; border:1px solid {DARK_BORDER};">
        <h3>📌 Insight Saham</h3>
        <p>✅ <b>Return tertinggi:</b> {best_stock}</p>
        <p>⚠️ <b>Risiko tertinggi:</b> {riskiest_stock}</p>
        <p>🛡️ <b>Risiko terendah:</b> {lowest_risk_stock}</p>
        </div>
        """
    )


def build_performance_cards(data, stocks):
    perf_list = []

    for stock in stocks:
        stock_data = data[data["Stock"] == stock]

        if stock_data.empty:
            continue

        first_price = stock_data["Close"].iloc[0]
        last_price = stock_data["Close"].iloc[-1]

        change_percent = ((last_price - first_price) / first_price) * 100
        perf_list.append({"Stock": stock, "Change": change_percent})

    if not perf_list:
        fig = figure(height=400, width=650, title="📊 Performa Saham", toolbar_location=None, tools="")
        fig.axis.visible = False
        fig.grid.visible = False
        return style_dark_figure(fig)

    perf_df = pd.DataFrame(perf_list).sort_values("Change", ascending=True)
    perf_df["color"] = [percent_color(v) for v in perf_df["Change"]]

    source = ColumnDataSource(perf_df)

    fig = figure(
        title="📊 Performa Saham: Top Winners & Losers",
        y_range=perf_df["Stock"].tolist(),
        height=max(300, 40 * len(perf_df)),
        width=650,
        sizing_mode="fixed",
        toolbar_location=None,
        tools="hover",
        tooltips=[("Saham", "@Stock"), ("Perubahan", "@Change{0.00}%")]
    )

    fig.hbar(
        y="Stock", right="Change", height=0.6,
        source=source, color="color"
    )

    fig.xaxis.axis_label = "Perubahan (%)"
    fig.yaxis.axis_label = "Saham"
    fig.ygrid.grid_line_color = None
    fig.x_range.start = min(perf_df["Change"].min(), 0) * 1.1 - 1
    fig.x_range.end = max(perf_df["Change"].max(), 0) * 1.1 + 1

    return style_dark_figure(fig)


def build_result_cards(data, stocks, investment_inputs):
    cards = []
    total_current_value = 0
    total_profit_loss = 0

    for stock in stocks:
        stock_data = data[data["Stock"] == stock]

        if stock_data.empty:
            continue

        first_price = stock_data["Close"].iloc[0]
        last_price = stock_data["Close"].iloc[-1]

        investment_amount = investment_inputs[stock].value
        shares = investment_amount / first_price
        current_value = shares * last_price
        profit_loss = current_value - investment_amount

        return_percent = (profit_loss / investment_amount * 100) if investment_amount > 0 else 0
        return_color = percent_color(return_percent)
        pl_color = percent_color(profit_loss)

        total_current_value += current_value
        total_profit_loss += profit_loss

        card = Div(
            text=f"""
            <div style="border:1px solid {DARK_BORDER}; background-color:{DARK_PANEL}; color:{DARK_TEXT}; padding:10px; border-radius:10px; width:220px; margin:5px;">
            <b>{stock}</b><br><br>
            Nilai Saat Ini: <b>Rp {current_value:,.0f}</b><br>
            Return: <b style="color:{return_color};">{return_percent:.2f}%</b><br><br>
            Harga Awal: Rp {first_price:,.0f}<br>
            Harga Akhir: Rp {last_price:,.0f}<br>
            Jumlah Saham: {shares:.2f}<br>
            Profit/Loss: <b style="color:{pl_color};">Rp {profit_loss:,.0f}</b>
            </div>
            """
        )
        cards.append(card)

    return row(*cards), total_current_value, total_profit_loss


def build_pie_chart(stocks, investment_inputs):
    allocation_df = pd.DataFrame({
        "Stock": stocks,
        "Investment": [investment_inputs[s].value for s in stocks]
    })

    allocation_df = allocation_df[allocation_df["Investment"] > 0]

    if allocation_df.empty:
        fig = figure(height=450, width=450, title="🥧 Portfolio Allocation", toolbar_location=None, tools="")
        fig.axis.visible = False
        fig.grid.visible = False
        return style_dark_figure(fig)

    allocation_df["angle"] = (allocation_df["Investment"] / allocation_df["Investment"].sum()) * 2 * pi
    allocation_df["percent"] = (allocation_df["Investment"] / allocation_df["Investment"].sum()) * 100
    allocation_df["color"] = [get_stock_color(i) for i in range(len(allocation_df))]

    source = ColumnDataSource(allocation_df)

    fig = figure(
        height=450, width=450, title="🥧 Portfolio Allocation",
        toolbar_location=None, tools="hover",
        tooltips=[("Saham", "@Stock"), ("Investasi", "Rp @Investment{0,0}"), ("Persentase", "@percent{0.0}%")]
    )

    fig.annular_wedge(
        x=0, y=1, inner_radius=0.4, outer_radius=0.8,
        start_angle=cumsum("angle", include_zero=True),
        end_angle=cumsum("angle"),
        line_color="white",
        fill_color="color",
        legend_field="Stock",
        source=source
    )

    fig.axis.visible = False
    fig.grid.visible = False

    return style_dark_figure(fig)


def build_dca(daily_return, stocks, investment_inputs, frequency_selector):
    weights = np.array([investment_inputs[s].value for s in stocks])

    total_investment = weights.sum()

    if total_investment == 0:
        weights = np.ones(len(weights)) if len(weights) > 0 else weights
    else:
        weights = weights / weights.sum()

    portfolio_return = (daily_return * weights).sum(axis=1)

    investment_series = pd.Series(0.0, index=portfolio_return.index)

    freq = frequency_selector.labels[frequency_selector.active]

    if freq == "Sekali Investasi":
        if len(investment_series) > 0:
            investment_series.iloc[0] = total_investment

    elif freq == "Harian":
        investment_series[:] = total_investment

    elif freq == "Mingguan":
        dates = investment_series.groupby(investment_series.index.to_period("W")).head(1).index
        investment_series.loc[dates] = total_investment

    elif freq == "Bulanan":
        dates = investment_series.groupby(investment_series.index.to_period("M")).head(1).index
        investment_series.loc[dates] = total_investment

    elif freq == "Tahunan":
        dates = investment_series.groupby(investment_series.index.to_period("Y")).head(1).index
        investment_series.loc[dates] = total_investment

    # Simulasi nilai portfolio dari waktu ke waktu
    portfolio_value = []
    current_value = 0

    for i in range(len(portfolio_return)):
        current_value += investment_series.iloc[i]
        current_value *= (1 + portfolio_return.iloc[i])
        portfolio_value.append(current_value)

    portfolio_value = pd.Series(portfolio_value, index=portfolio_return.index)
    total_invested = investment_series.cumsum()

    cumulative_return_percent = (
        (portfolio_value - total_invested) / total_invested.replace(0, np.nan)
    ) * 100

    # Chart
    source = ColumnDataSource(data=dict(
        Date=portfolio_value.index,
        PortfolioValue=portfolio_value.values,
        TotalInvested=total_invested.values
    ))

    fig = figure(
        title=f"📈 Simulasi DCA Portfolio ({freq})",
        x_axis_type="datetime",
        height=550,
        width=1100,
        sizing_mode="fixed",
        tools="pan,wheel_zoom,box_zoom,reset,save"
    )

    r1 = fig.line("Date", "PortfolioValue", source=source, line_width=3, legend_label="Portfolio Value", color="#4caf50")
    r2 = fig.line("Date", "TotalInvested", source=source, line_width=3, legend_label="Total Invested", color="#42a5f5")

    fig.add_tools(HoverTool(
        renderers=[r1, r2],
        tooltips=[("Tanggal", "@Date{%F}"), ("Nilai Portfolio", "Rp @PortfolioValue{0,0}"), ("Total Investasi", "Rp @TotalInvested{0,0}")],
        formatters={"@Date": "datetime"},
        mode="vline"
    ))

    fig.xaxis.axis_label = "Date"
    fig.yaxis.axis_label = "Value (Rp)"
    fig.legend.location = "top_left"
    fig.legend.click_policy = "hide"

    style_dark_figure(fig)

    # Summary
    if len(portfolio_value) > 0:
        final_value = portfolio_value.iloc[-1]
        final_invested = total_invested.iloc[-1]
        final_return = cumulative_return_percent.iloc[-1]
        nominal_return = final_value - final_invested
    else:
        final_value = final_invested = final_return = nominal_return = 0

    return_color = percent_color(nominal_return)

    summary = Div(
        text=f"""
        <div style="border:1px solid {DARK_BORDER}; background-color:{DARK_PANEL}; color:{DARK_TEXT}; padding:15px; border-radius:10px; margin-top:10px;">
        <h3>📊 Hasil Portfolio</h3>
        <p>💰 <b>Total Investasi</b><br>Rp {final_invested:,.0f}</p>
        <p>📈 <b>Nilai Portfolio</b><br>Rp {final_value:,.0f}</p>
        <p>🚀 <b>Return Portfolio</b><br><span style="color:{return_color};">Rp {nominal_return:,.0f}<br>({final_return:.2f}%)</span></p>
        </div>
        """
    )

    return fig, summary


# =========================================
# CONTAINER (placeholder, diisi oleh render())
# =========================================
price_container = column()
heatmap_container = column()
risk_table_container = column()
scatter_container = column()
insight_container = column()
performance_container = column()
result_container = column()
pie_container = column()
dca_container = column(width=1100)
portfolio_summary_container = column()

risk_return_title = Div(
    text="""
    <h2>⚖️ Perbandingan Risk dan Return Saham</h2>
    <p>
    Analisis risk dan return digunakan untuk mengevaluasi hubungan antara tingkat
    keuntungan rata-rata dengan risiko masing-masing saham. Risiko diukur menggunakan
    standar deviasi return harian, sedangkan return dihitung dari rata-rata return
    historis saham.
    </p>
    """,
    styles={"color": DARK_TEXT}
)

performance_title = Div(text="<h2>📊 Performa Saham</h2>", styles={"color": DARK_TEXT})
result_title = Div(text="<h2>📈 Hasil Investasi</h2>", styles={"color": DARK_TEXT})

allocation_title = Div(
    text="""
    <h2>🥧 Alokasi Portfolio</h2>
    <p>Diagram pie menunjukkan proporsi alokasi dana pada masing-masing saham dalam portfolio.</p>
    """,
    styles={"color": DARK_TEXT}
)

cum_desc = Div(
    text="""
    <p>
    Grafik cumulative return menunjukkan perkembangan nilai portfolio dari waktu ke waktu
    berdasarkan strategi investasi yang dipilih. Grafik membandingkan total dana yang
    diinvestasikan dengan nilai aktual portfolio.
    </p>
    """,
    styles={"color": DARK_TEXT}
)

warning_box = Div(
    text="""
    <div style="background-color:#fff3cd; border:1px solid #ffeeba; padding:10px; border-radius:8px;">
    Pilih minimal satu saham.
    </div>
    """
)


# =========================================
# RENDER: dipanggil saat startup & setiap kali filter berubah
# =========================================
def render():
    stocks = stock_select.value

    if not stocks:
        price_container.children = [warning_box]
        heatmap_container.children = []
        risk_table_container.children = []
        scatter_container.children = []
        insight_container.children = []
        performance_container.children = []
        result_container.children = []
        pie_container.children = []
        dca_container.children = []
        investment_layout.children = []
        portfolio_summary_container.children = []
        return

    start_date = datetime.strptime(start_picker.value, "%Y-%m-%d")
    end_date = datetime.strptime(end_picker.value, "%Y-%m-%d")

    data = load_data(stocks, start_date, end_date)

    if data.empty:
        price_container.children = [warning_box]
        return

    close_price = data.pivot(index="Date", columns="Stock", values="Close")
    daily_return = close_price.pct_change().dropna()
    correlation = daily_return.corr()

    avg_return = daily_return.mean()
    risk = daily_return.std()

    risk_return_df = pd.DataFrame({
        "Stock": avg_return.index,
        "Return": avg_return.values,
        "Risk": risk.values
    })

    # Price chart & heatmap
    price_container.children = [build_price_chart(close_price)]
    heatmap_container.children = [build_heatmap(correlation)]

    # Risk/Return table & scatter
    risk_table_container.children = [build_risk_table(risk_return_df)]
    scatter_container.children = [build_scatter(risk_return_df)]

    # Insight
    insight_container.children = [build_insight(risk_return_df)]

    # Performance cards
    performance_container.children = [build_performance_cards(data, stocks)]

    # Investment input spinners (hanya untuk saham terpilih)
    investment_layout.children = [investment_inputs[s] for s in stocks]

    # Hasil investasi
    result_layout, _, _ = build_result_cards(data, stocks, investment_inputs)
    result_container.children = [result_layout]

    # Pie chart alokasi
    pie_container.children = [build_pie_chart(stocks, investment_inputs)]

    # DCA simulation
    dca_fig, dca_summary = build_dca(daily_return, stocks, investment_inputs, frequency_selector)
    dca_container.children = [dca_fig]
    portfolio_summary_container.children = [dca_summary]


# =========================================
# CALLBACK
# =========================================
def on_change(attr, old, new):
    render()


stock_select.on_change("value", on_change)
start_picker.on_change("value", on_change)
end_picker.on_change("value", on_change)
frequency_selector.on_change("active", on_change)

for spinner in investment_inputs.values():
    spinner.on_change("value", on_change)


# =========================================
# KONTEN UTAMA
# =========================================
main_content = column(
    global_style,
    title,

    row(price_container, heatmap_container),

    risk_return_title,
    row(risk_table_container, scatter_container),

    insight_container,

    performance_title,
    performance_container,

    investment_title,
    investment_layout,

    result_title,
    result_container,

    allocation_title,
    pie_container,

    frequency_title,
    frequency_selector,

    dca_container,
    cum_desc,

    width=1100,
)


# =========================================
# LAYOUT
# =========================================
sidebar = column(
    filter_title,
    stock_select,
    start_picker,
    end_picker,
    portfolio_summary_container,
    width=300,
    sizing_mode="fixed"
)

layout = row(sidebar, main_content, sizing_mode="stretch_width")


# =========================================
# INITIAL RENDER
# =========================================
render()

curdoc().add_root(layout)
curdoc().title = "Simulasi Investasi Saham"