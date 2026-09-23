"""生成医药电商样例数据 SQL（药品 40 条 + 销售记录约 240 条）

输出: db_setup/02_seed.sql
日期范围: 2026-06-01 ~ 2026-09-15（覆盖 4 个月，含当月，便于做月度/趋势分析）
"""
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(20260916)

OUT = Path(__file__).resolve().parent / "02_seed.sql"

# (药品名称, 分类, 规格, 生产厂家, 单价)
DRUGS = [
    ("对乙酰氨基酚片", "非处方药", "500mg*20片", "华中药业股份有限公司", 12.50),
    ("布洛芬缓释胶囊", "非处方药", "300mg*20粒", "中美天津史克制药有限公司", 24.80),
    ("阿莫西林胶囊", "处方药", "250mg*24粒", "珠海联邦制药股份有限公司", 18.60),
    ("奥美拉唑肠溶胶囊", "非处方药", "20mg*14粒", "阿斯利康制药有限公司", 32.00),
    ("头孢克肟分散片", "处方药", "100mg*12片", "广州白云山制药股份有限公司", 28.90),
    ("阿奇霉素分散片", "处方药", "250mg*6片", "辉瑞制药有限公司", 45.00),
    ("氯雷他定片", "非处方药", "10mg*12片", "上海先灵葆雅制药有限公司", 16.80),
    ("盐酸西替利嗪片", "非处方药", "10mg*20片", "鲁南贝特制药有限公司", 19.90),
    ("复方感冒灵颗粒", "非处方药", "10g*10袋", "广州白云山和记黄埔中药有限公司", 15.50),
    ("连花清瘟胶囊", "非处方药", "0.35g*24粒", "石家庄以岭药业股份有限公司", 26.00),
    ("板蓝根颗粒", "非处方药", "10g*20袋", "广州白云山制药股份有限公司", 13.20),
    ("藿香正气水", "非处方药", "10ml*10支", "太极集团重庆涪陵制药厂", 11.80),
    ("蒙脱石散", "非处方药", "3g*10袋", "博福-益普生（天津）制药有限公司", 22.50),
    ("健胃消食片", "非处方药", "0.8g*32片", "江中药业股份有限公司", 9.90),
    ("复方阿胶浆", "非处方药", "20ml*12支", "东阿阿胶股份有限公司", 168.00),
    ("维生素C片", "保健品", "100mg*100片", "哈药集团制药总厂", 8.80),
    ("钙尔奇碳酸钙D3片", "保健品", "600mg*60片", "惠氏制药有限公司", 58.00),
    ("汤臣倍健蛋白粉", "保健品", "400g/罐", "汤臣倍健股份有限公司", 199.00),
    ("鱼油软胶囊", "保健品", "1000mg*100粒", "汤臣倍健股份有限公司", 128.00),
    ("善存复合维生素片", "保健品", "60片", "惠氏制药有限公司", 89.00),
    ("电子血压计", "医疗器械", "上臂式", "欧姆龙（大连）有限公司", 329.00),
    ("血糖仪", "医疗器械", "含50试纸", "三诺生物传感股份有限公司", 259.00),
    ("医用外科口罩", "医疗器械", "50只/盒", "稳健医疗用品股份有限公司", 29.90),
    ("创可贴", "医疗器械", "100片/盒", "云南白药集团股份有限公司", 15.00),
    ("红外额温枪", "医疗器械", "非接触式", "鱼跃医疗设备股份有限公司", 129.00),
    ("硝苯地平控释片", "处方药", "30mg*7片", "拜耳医药保健有限公司", 38.50),
    ("缬沙坦胶囊", "处方药", "80mg*7粒", "北京诺华制药有限公司", 42.00),
    ("二甲双胍肠溶片", "处方药", "0.25g*48片", "中美上海施贵宝制药有限公司", 21.50),
    ("阿卡波糖片", "处方药", "50mg*30片", "拜耳医药保健有限公司", 56.00),
    ("阿托伐他汀钙片", "处方药", "20mg*7片", "辉瑞制药有限公司", 48.00),
    ("瑞舒伐他汀钙片", "处方药", "10mg*7片", "阿斯利康制药有限公司", 52.00),
    ("盐碘酮片", "处方药", "200mg*10片", "赛诺菲（杭州）制药有限公司", 35.00),
    ("左氧氟沙星片", "处方药", "0.5g*5片", "第一三共制药（北京）有限公司", 39.90),
    ("头孢呋辛酯片", "处方药", "0.25g*12片", "葛兰素史克（中国）投资有限公司", 62.00),
    ("孟鲁司特钠咀嚼片", "处方药", "5mg*5片", "杭州默沙东制药有限公司", 44.50),
    ("布地奈德福莫特罗粉吸入剂", "处方药", "160/4.5ug*60吸", "阿斯利康制药有限公司", 268.00),
    ("胰岛素注射液", "处方药", "300U/支", "诺和诺德（中国）制药有限公司", 68.00),
    ("云南白药气雾剂", "非处方药", "85g", "云南白药集团股份有限公司", 32.50),
    ("马应龙麝香痔疮膏", "非处方药", "10g", "马应龙药业集团股份有限公司", 18.90),
    ("珍珠明目滴眼液", "非处方药", "8ml", "杭州天目山药业股份有限公司", 12.00),
]

CHANNELS = ["自营商城", "第三方平台", "线下药店"]
# 渠道权重：自营商城最多
CHANNEL_WEIGHTS = [0.45, 0.30, 0.25]

START = date(2026, 6, 1)
END = date(2026, 9, 15)


def sql_escape(text: str) -> str:
    return text.replace("'", "''")


def main() -> None:
    lines = [
        "-- 自动生成：医药电商样例数据（勿手工编辑，改 gen_seed.py 后重新生成）",
        "USE pharma_mall;",
        "",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "TRUNCATE TABLE sales_records;",
        "TRUNCATE TABLE drugs;",
        "SET FOREIGN_KEY_CHECKS = 1;",
        "",
        "-- 药品信息",
        "INSERT INTO drugs (drug_name, category, specification, manufacturer, unit_price, stock) VALUES",
    ]
    drug_rows = []
    for name, cat, spec, mfr, price in DRUGS:
        stock = random.randint(80, 1500)
        drug_rows.append(
            f"('{sql_escape(name)}', '{cat}', '{sql_escape(spec)}', '{sql_escape(mfr)}', {price}, {stock})"
        )
    lines.append(",\n".join(drug_rows) + ";")
    lines.append("")

    # 销售记录：约 240 条，按日期分布，越近期销量略高（体现增长趋势）
    records = []
    span_days = (END - START).days + 1
    for _ in range(240):
        drug_id = random.randint(1, len(DRUGS))
        # 近期权重更高
        r = random.random() ** 0.75
        day_offset = int(r * (span_days - 1))
        sale_date = START + timedelta(days=day_offset)
        qty = random.randint(1, 30)
        price = DRUGS[drug_id - 1][4]
        # 大额渠道略有折扣
        channel = random.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0]
        discount = 0.95 if channel == "第三方平台" else 1.0
        amount = round(qty * price * discount, 2)
        records.append(
            f"({drug_id}, {qty}, {amount}, '{sale_date.isoformat()}', '{channel}')"
        )

    lines.append("-- 销售记录")
    lines.append("INSERT INTO sales_records (drug_id, quantity, total_amount, sale_date, channel) VALUES")
    lines.append(",\n".join(records) + ";")
    lines.append("")
    lines.append("-- 校验")
    lines.append("SELECT COUNT(*) AS drug_count FROM drugs;")
    lines.append("SELECT COUNT(*) AS sales_count FROM sales_records;")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE {OUT} drugs={len(DRUGS)} records={len(records)}")


if __name__ == "__main__":
    main()
