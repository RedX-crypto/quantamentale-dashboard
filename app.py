@st.cache_data
def build_pro_chart(df, title_name, chart_type="Candele (Candlestick)", is_log=True):
    df_c = df.copy()
    df_c = df_c.dropna(subset=['Close', 'Open', 'High', 'Low'])
    fig = go.Figure()
    
    if chart_type == "Candele (Candlestick)" and 'Open' in df_c.columns:
        fig.add_trace(go.Candlestick(
            x=df_c['Date'],
            open=df_c['Open'],
            high=df_c['High'],
            low=df_c['Low'],
            close=df_c['Close'],
            name="Prezzo OHLC",
            increasing_line_color='#26a69a', 
            decreasing_line_color='#ef5350',
            increasing_fillcolor='#26a69a',
            decreasing_fillcolor='#ef5350'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df_c['Date'],
            y=df_c['Close'],
            mode='lines',
            name="Valore",
            line=dict(color='#2962FF', width=2)
        ))

    fig.update_layout(
        title=dict(text=f"<b>{title_name}</b> — {'Scala Logaritmica' if is_log else 'Scala Lineare'}", font=dict(size=16)),
        yaxis_title="Prezzo / Valore",
        xaxis_title="Data",
        template="plotly_white",
        height=500,
        margin=dict(l=30, r=30, t=50, b=30),
        xaxis=dict(
            rangeslider=dict(visible=False), 
            showgrid=True, 
            gridcolor='#F0F2F5',
            type='date'
        ),
        yaxis=dict(type="log" if is_log else "linear", showgrid=True, gridcolor='#F0F2F5'),
        showlegend=False
    )
    return fig
