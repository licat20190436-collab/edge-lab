"""
论文画图脚本 - 边缘微服务网络雪崩实验
使用方法：
  1. 安装依赖：pip install pandas matplotlib numpy
  2. 直接运行：python draw_paper_figures.py
  3. 图片会保存在同一目录下，命名为 fig1.png ~ fig5.png

如果需要修改数据，只改下面 ===数据区=== 里的内容，画图代码不需要动。
"""

import matplotlib
matplotlib.use('Agg')  # 不弹窗，直接保存文件
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ============================================================
# ===                    数据区（只改这里）                 ===
# ============================================================
# 字段说明：(组别, 内存MB, 弱网类型, 并发数, 吞吐量req/s, 平均延迟ms, P99延迟ms, 超时数, 成功数)
# 弱网类型：'none'=无弱网, 'fixed'=固定150ms+5%丢包, 'jitter'=150ms±20ms+5%丢包

RAW_DATA = [
    # --- A组：400MB 基准线（无约束）---
    ('A', 400, 'none',   50,  190.88,  84.5,   82.1,    84,  9391),
    ('A', 400, 'none',   100, 164.08,  207.5,  5175.2,  100, 4837),
    ('A', 400, 'fixed',  100, 212.83,  435.4,  19523.8, 8,   6550),
    ('A', 400, 'fixed',  300, 184.61,  349.5,  1044.1,  539, 8686),

    # --- B组：128MB 无弱网 ---
    ('B', 128, 'none',  100, 259.10, 368.9,  19532.7, 4,   9697),
    ('B', 128, 'none',  120, 238.45, 191.4,  558.2,   115, 9248),
    ('B', 128, 'none',  150, 8.72,   878.4,  11495.9, 298, 137),
    ('B', 128, 'none',  180, 12.08,  8873.7, 19823.8, 167, 335),
    ('B', 128, 'none',  200, 10.17,  235.9,  0,       400, 13),
    ('B', 128, 'none',  300, 183.84, 492.4,  4601.8,  322, 8798),

    # --- C组：128MB 固定弱网 ---
    ('C', 128, 'fixed', 100, 254.85, 173.2,  538.8,   100, 9604),
    ('C', 128, 'fixed', 120, 5.99,   999.0,  19999.0, 240, 0),     # NaN改成999/19999方便画图
    ('C', 128, 'fixed', 150, 7.41,   494.1,  19999.0, 300, 10),
    ('C', 128, 'fixed', 180, 179.34, 391.3,  3370.4,  163, 8657),
    ('C', 128, 'fixed', 200, 28.93,  1157.4, 5911.0,  396, 978),

    # --- D组：256MB 无弱网（使用REPRO平均值替换原始D2/D3/D4）---
    ('D', 256, 'none',  100, 188.00, 216.5,  140.5,   147, 9190),
    ('D', 256, 'none',  150, 187.29, 238.8,  203.7,   246, 9024),  # REPRO平均
    ('D', 256, 'none',  200, 185.50, 411.7,  19418.2, 279, 8891),  # REPRO平均
    ('D', 256, 'none',  300, 194.07, 353.0,  357.5,   572, 9008),  # G1/G2平均（稳定！）

    # --- E组：256MB 固定弱网 ---
    ('E', 256, 'fixed', 100, 258.79, 174.8,  537.6,   100, 9692),
    ('E', 256, 'fixed', 150, 10.20,  257.6,  1105.7,  300, 133),   # 潮汐效应！
    ('E', 256, 'fixed', 200, 171.86, 273.1,  660.1,   363, 8166),
    ('E', 256, 'fixed', 300, 31.65,  2393.8, 19765.1, 500, 1026),

    # --- F组：128MB 带抖动弱网（潮汐同步对照实验）---
    ('F', 128, 'jitter', 120, 268.43, 177.9, 553.3,  120, 9479),
    ('F', 128, 'jitter', 150, 10.14,  4722.8, 11955.1, 229, 177),
]

# ============================================================
# ===                   画图代码（不用改）                  ===
# ============================================================

# 解析数据
groups = {}
for row in RAW_DATA:
    grp, mem, net, conc, tput, avg_lat, p99, timeouts, success = row
    key = (grp, mem, net)
    if key not in groups:
        groups[key] = []
    total = success + timeouts
    success_rate = success / total * 100 if total > 0 else 0
    groups[key].append({
        'conc': conc,
        'tput': tput,
        'avg_lat': avg_lat,
        'p99': p99,
        'timeouts': timeouts,
        'success': success,
        'success_rate': success_rate,
    })

# 排序
for k in groups:
    groups[k].sort(key=lambda x: x['conc'])

def get(key, field):
    """取某组的某字段列表"""
    return [d[field] for d in groups[key]]

# 颜色和线型
STYLES = {
    ('B', 128, 'none'):   dict(color='#1565C0', ls='-',  marker='o', lw=2, ms=7, label='128 MB, No Impairment'),
    ('C', 128, 'fixed'):  dict(color='#C62828', ls='--', marker='s', lw=2, ms=7, label='128 MB, Fixed Delay (150ms+5% loss)'),
    ('D', 256, 'none'):   dict(color='#2E7D32', ls='-',  marker='^', lw=2, ms=7, label='256 MB, No Impairment'),
    ('E', 256, 'fixed'):  dict(color='#E65100', ls='--', marker='D', lw=2, ms=7, label='256 MB, Fixed Delay (150ms+5% loss)'),
}

plt.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 12,
    'axes.labelsize': 11,
    'legend.fontsize': 9,
    'figure.dpi': 150,
})

# ── 图1：成功率 vs 并发 ──────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
for key, style in STYLES.items():
    if key not in groups:
        continue
    x = get(key, 'conc')
    y = get(key, 'success_rate')
    ax.plot(x, y, color=style['color'], ls=style['ls'],
            marker=style['marker'], lw=style['lw'], ms=style['ms'],
            label=style['label'])

# 标注崩溃区域
ax.axvspan(115, 155, alpha=0.08, color='red', label='_nolegend_')
ax.text(130, 8, '128MB\ncollapse\nzone', ha='center', fontsize=8, color='#C62828')

ax.set_xlabel('Concurrent Connections')
ax.set_ylabel('Request Success Rate (%)')
ax.set_title('Figure 1: Success Rate vs. Concurrent Connections\nUnder Different Memory and Network Conditions')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=True)
ax.set_ylim(-5, 108)
ax.set_xlim(85, 315)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('fig1_success_rate.png', bbox_inches='tight')
plt.close()
print("fig1_success_rate.png generated")

# ── 图2：P99延迟 vs 并发 ─────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
for key, style in STYLES.items():
    if key not in groups:
        continue
    x = get(key, 'conc')
    y = [min(v, 20000) / 1000 for v in get(key, 'p99')]  # 转秒，上限20s
    ax.plot(x, y, color=style['color'], ls=style['ls'],
            marker=style['marker'], lw=style['lw'], ms=style['ms'],
            label=style['label'])

ax.axhline(y=20, color='gray', ls=':', lw=1)
ax.text(310, 20.3, '20s\ntimeout', fontsize=8, color='gray', ha='right')
ax.set_xlabel('Concurrent Connections')
ax.set_ylabel('P99 Tail Latency (seconds)')
ax.set_title('Figure 2: P99 Tail Latency vs. Concurrent Connections')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=True)
ax.set_ylim(-0.5, 22)
ax.set_xlim(85, 315)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('fig2_p99_latency.png', bbox_inches='tight')
plt.close()
print("fig2_p99_latency.png generated")

# ── 图3：吞吐量 vs 并发 ──────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
for key, style in STYLES.items():
    if key not in groups:
        continue
    x = get(key, 'conc')
    y = get(key, 'tput')
    ax.plot(x, y, color=style['color'], ls=style['ls'],
            marker=style['marker'], lw=style['lw'], ms=style['ms'],
            label=style['label'])

ax.set_xlabel('Concurrent Connections')
ax.set_ylabel('Throughput (requests/second)')
ax.set_title('Figure 3: Throughput vs. Concurrent Connections')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=True)
ax.set_ylim(-5, 300)
ax.set_xlim(85, 315)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('fig3_throughput.png', bbox_inches='tight')
plt.close()
print("fig3_throughput.png generated")

# ── 图4：潮汐同步效应实证对比 ───────────────────────────────
fig, ax = plt.subplots(figsize=(7, 5))

# C vs F 在120并发下的对比
scenarios = [
    'C2\n128MB+Fixed Delay\n120 concurrent',
    'F1\n128MB+Jittered Delay\n120 concurrent',
    'C3\n128MB+Fixed Delay\n150 concurrent',
    'F2\n128MB+Jittered Delay\n150 concurrent',
]
success_rates = [
    0,    # C2: 0 success
    98.7, # F1: 9479/(9479+120)*100
    3.2,  # C3: 10/(10+300)*100
    43.6, # F2: 177/(177+229)*100
]
colors_bar = ['#C62828', '#1565C0', '#C62828', '#1565C0']
hatches = ['', '', '///', '///']

bars = ax.bar(range(4), success_rates, color=colors_bar,
              hatch=hatches, edgecolor='white', linewidth=1.5, width=0.6)
for bar, val in zip(bars, success_rates):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
            f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

ax.set_xticks(range(4))
ax.set_xticklabels(scenarios, fontsize=9)
ax.set_ylabel('Request Success Rate (%)')
ax.set_title('Figure 4: Tidal Synchronization Effect\nFixed Delay vs. Jittered Delay at Same Concurrency')
ax.set_ylim(0, 115)
ax.grid(True, axis='y', alpha=0.3)

patch1 = mpatches.Patch(color='#C62828', label='Fixed Delay (150ms)')
patch2 = mpatches.Patch(color='#1565C0', label='Jittered Delay (150ms±20ms)')
ax.legend(handles=[patch1, patch2], loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=True)
plt.tight_layout()
plt.savefig('fig4_tidal_sync.png', bbox_inches='tight')
plt.close()
print("fig4_tidal_sync.png generated")

# ── 图5：雪崩临界点汇总 ─────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 4.5))

labels = ['128MB\nNo Impairment', '128MB\nFixed Weak Net', '256MB\nNo Impairment', '256MB\nFixed Weak Net']
thresholds = [120, 100, 300, 150]
colors_b = ['#1565C0', '#C62828', '#2E7D32', '#E65100']
notes = ['~120', '~100\n(tidal sync)', '>300\n(stable)', '~150\n(tidal sync)']

bars = ax.bar(labels, thresholds, color=colors_b, width=0.5, edgecolor='white', linewidth=1.5)
for bar, note in zip(bars, notes):
    ax.text(bar.get_x() + bar.get_width()/2,
            bar.get_height() + 4,
            note, ha='center', va='bottom', fontsize=9, fontweight='bold')

ax.set_ylabel('Avalanche Threshold\n(Concurrent Connections)')
ax.set_title('Figure 5: Avalanche Threshold Comparison\nAcross Memory and Network Configurations')
ax.set_ylim(0, 360)
ax.grid(True, axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('fig5_thresholds.png', bbox_inches='tight')
plt.close()
print("fig5_thresholds.png generated")

print("\nAll done! Check fig1 to fig5 in current directory")
