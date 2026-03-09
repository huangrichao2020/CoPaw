#!/usr/bin/env python3
# 获取真实 Tushare 数据并更新 api_data.json

import sys
import json
sys.path.insert(0, '/Users/tingchi/.copaw')

try:
    import tushare as ts
    from datetime import datetime, timedelta
    import pandas as pd
    
    # Tushare 配置
    TOKEN = "1deb264561d63413c67fea99d8ee634ba4617b16a7114fa2e7251534"
    ts.set_token(TOKEN)
    pro = ts.pro_api()
    
    print("📊 获取 Tushare 数据...")
    
    # 1. 获取最新交易日
    from datetime import datetime
    today = datetime.now().strftime('%Y%m%d')
    five_days_ago = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
    
    trade_cal = pro.trade_cal(exchange='SSE', start_date=five_days_ago, end_date=today, is_open='1')
    if trade_cal.empty:
        print("⚠️ 无交易日数据，使用示例数据")
        # 使用示例数据
        latest_date = '20260306'
    else:
        latest_date = trade_cal['cal_date'].iloc[0]
    
    print(f"✅ 交易日：{latest_date}")
    
    # 2. 获取市场统计
    print("📈 获取市场统计...")
    try:
        daily_info = pro.daily(trade_date=latest_date)
    except Exception as e:
        print(f"⚠️ 获取失败：{e}，使用示例数据")
        daily_info = pd.DataFrame()
    
    if daily_info.empty:
        print("❌ 无日线数据")
        sys.exit(1)
    
    # 计算涨跌家数
    up_count = len(daily_info[daily_info['pct_chg'] > 0])
    down_count = len(daily_info[daily_info['pct_chg'] < 0])
    limit_up = len(daily_info[daily_info['pct_chg'] >= 9.8])
    limit_down = len(daily_info[daily_info['pct_chg'] <= -9.8])
    
    # 总成交额（亿）
    total_amount = daily_info['amount'].sum() / 10000000  # tushare 单位是千元
    
    print(f"  上涨：{up_count} 家 | 下跌：{down_count} 家")
    print(f"  涨停：{limit_up} 家 | 跌停：{limit_down} 家")
    print(f"  成交额：{total_amount:.2f} 亿")
    
    # 3. 获取指数数据
    print("📊 获取指数数据...")
    indices = {
        '000001.SHA': '上证指数',
        '399001.SZ': '深证成指',
        '399006.SZ': '创业板指',
        '000016.SHA': '上证 50',
        '000300.SHA': '沪深 300',
        '000905.SHA': '中证 500',
        '000688.SHA': '科创 50',
        '000012.SHA': '深证成指'
    }
    
    index_data = {}
    for code, name in indices.items():
        try:
            idx = pro.index_daily(ts_code=code, start_date='20260201', end_date=latest_date)
            if not idx.empty:
                data_points = []
                for _, row in idx.iterrows():
                    data_points.append({
                        'trade_date': row['trade_date'],
                        'close': float(row['close']),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'vol': float(row['vol'])
                    })
                index_data[code] = {
                    'name': name,
                    'data': data_points[:15]  # 最近 15 天
                }
        except Exception as e:
            print(f"  ⚠️ {name} 获取失败：{e}")
    
    print(f"  ✅ 获取 {len(index_data)} 个指数")
    
    # 4. 获取涨停股
    print("🏆 获取涨停股...")
    limit_stocks = daily_info[daily_info['pct_chg'] >= 9.8].copy()
    limit_stocks = limit_stocks.sort_values('amount', ascending=False).head(20)
    
    top_stocks = []
    for _, row in limit_stocks.iterrows():
        top_stocks.append({
            'code': row['ts_code'],
            'name': '',  # 需要额外获取
            'close': float(row['close']),
            'amount': float(row['amount']),
            'pct_chg': float(row['pct_chg']),
            'limit_time': '09:30',  # 估算
            'continuous_limit': 1  # 需要额外计算
        })
    
    print(f"  ✅ 获取 {len(top_stocks)} 只涨停股")
    
    # 5. 获取板块数据
    print("🔥 获取板块数据...")
    try:
        # 概念板块
        concept = pro.concept_daily(trade_date=latest_date)
        if not concept.empty:
            concept_stats = concept.groupby('name').agg({
                'pct_chg': 'mean',
                'ts_code': 'count'
            }).reset_index()
            concept_stats = concept_stats.sort_values('pct_chg', ascending=False).head(10)
            
            today_sectors = []
            for _, row in concept_stats.iterrows():
                today_sectors.append({
                    'name': row['name'],
                    'change': round(float(row['pct_chg']), 2),
                    'top1': '',
                    'top2': '',
                    'limit_count': int(row['ts_code'] // 10)
                })
        else:
            today_sectors = []
    except Exception as e:
        print(f"  ⚠️ 板块获取失败：{e}")
        today_sectors = []
    
    # 6. 涨跌分布
    print("📊 计算涨跌分布...")
    dist_data = []
    ranges = [(-20, -10), (-10, -5), (-5, -3), (-3, -1), (-1, 1), (1, 3), (3, 5), (5, 10), (10, 20)]
    for low, high in ranges:
        if low == -20:
            count = len(daily_info[daily_info['pct_chg'] <= high])
        elif high == 20:
            count = len(daily_info[daily_info['pct_chg'] >= low])
        else:
            count = len(daily_info[(daily_info['pct_chg'] > low) & (daily_info['pct_chg'] <= high)])
        dist_data.append({
            'range': f"{low:+.0f}%~{high:+.0f}%",
            'count': count
        })
    
    # 7. 组装数据
    sentiment = round(up_count / (up_count + down_count) * 100, 1) if (up_count + down_count) > 0 else 50
    
    report = {
        "trade_date": latest_date,
        "generate_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "market_stats": {
            "total_amount": round(total_amount / 10000, 2),  # 万亿
            "up": up_count,
            "down": down_count,
            "limit_up": limit_up,
            "limit_down": limit_down,
            "sentiment": sentiment
        },
        "dist_data": dist_data,
        "today_sectors": today_sectors,
        "top_stocks": top_stocks,
        "index_data": index_data
    }
    
    # 8. 写入文件
    output_path = '/Users/tingchi/.copaw/projects/stock_report/api_data.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据已保存到：{output_path}")
    print(f"📄 生成时间：{report['generate_time']}")
    
except Exception as e:
    print(f"❌ 错误：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
