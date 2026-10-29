"""Generate SVG diagrams for the Agent Smith SWE-bench benchmark report."""

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def generate_pareto_svg(output_path: Path) -> None:
    """Generate SVG scatter plot of Latency vs Solve Rate."""
    # Models data: (name, latency_s, solve_rate_pct, category, color)
    models = [
        ("gemini-3.1-flash-lite", 0.88, 100.0, "Optimal", "#10b981", 12, -18),
        ("gemini-3.5-flash-lite", 0.95, 100.0, "Optimal", "#10b981", 12, -5),
        ("openai/gpt-4o-mini", 1.01, 100.0, "Optimal", "#10b981", 12, 10),
        ("mistral-small-24b", 1.16, 80.0, "Compact", "#f59e0b", 12, 5),
        ("openai/gpt-4o", 2.41, 100.0, "Flagship", "#3b82f6", 12, -12),
        ("meta-llama/llama-3.3-70b", 4.38, 100.0, "Open-Weights", "#6366f1", 12, -12),
        ("nemotron-3-ultra (Free)", 4.89, 100.0, "MoE Free", "#8b5cf6", 12, 14),
        ("qwen-2.5-coder-32b", 6.09, 100.0, "Code AST", "#0ea5e9", 12, -12),
    ]

    # Coordinate mapping:
    # X range: 0s to 10s -> map to pixels 90 to 760 (width 670)
    # Y range: 60% to 105% -> map to pixels 360 to 90 (height 270)
    def x_px(val: float) -> float:
        return 90 + (val / 8.0) * 670

    def y_px(val: float) -> float:
        return 360 - ((val - 60) / 45.0) * 270

    svg = []
    svg.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 460" width="100%" height="auto">')
    svg.append('  <defs>')
    svg.append('    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">')
    svg.append('      <stop offset="0%" stop-color="#ffffff"/>')
    svg.append('      <stop offset="100%" stop-color="#f8fafc"/>')
    svg.append('    </linearGradient>')
    svg.append('    <filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">')
    svg.append('      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.08"/>')
    svg.append('    </filter>')
    svg.append('  </defs>')

    # Background card
    svg.append('  <rect width="850" height="460" rx="12" fill="url(#bgGrad)" stroke="#e2e8f0" stroke-width="1"/>')

    # Title & Subtitle
    svg.append('  <text x="30" y="42" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" font-size="18" font-weight="700" fill="#0f172a">Pareto Frontier: Per-Request Latency vs Solve Rate</text>')
    svg.append('  <text x="30" y="65" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" font-size="12" fill="#64748b">Benchmark on 5 SWE-bench tasks (40 runs). Top-left quadrant represents the Pareto Optimal Zone.</text>')

    # Gridlines & Y-axis labels
    y_ticks = [60, 70, 80, 90, 100]
    for y_val in y_ticks:
        yp = y_px(y_val)
        svg.append(f'  <line x1="90" y1="{yp:.1f}" x2="800" y2="{yp:.1f}" stroke="#e2e8f0" stroke-dasharray="4,4"/>')
        svg.append(f'  <text x="75" y="{yp + 4:.1f}" font-family="sans-serif" font-size="11" fill="#64748b" text-anchor="end">{y_val}%</text>')

    # X-axis labels
    x_ticks = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    for x_val in x_ticks:
        xp = x_px(x_val)
        svg.append(f'  <line x1="{xp:.1f}" y1="90" x2="{xp:.1f}" y2="360" stroke="#f1f5f9"/>')
        svg.append(f'  <text x="{xp:.1f}" y="380" font-family="sans-serif" font-size="11" fill="#64748b" text-anchor="middle">{x_val:.1f}s</text>')

    # Axes
    svg.append('  <line x1="90" y1="360" x2="800" y2="360" stroke="#94a3b8" stroke-width="1.5"/>')
    svg.append('  <line x1="90" y1="90" x2="90" y2="360" stroke="#94a3b8" stroke-width="1.5"/>')

    # Axis Titles
    svg.append('  <text x="445" y="405" font-family="sans-serif" font-size="12" font-weight="600" fill="#334155" text-anchor="middle">Average Per-Request Latency (Seconds)</text>')
    svg.append('  <text x="25" y="225" font-family="sans-serif" font-size="12" font-weight="600" fill="#334155" text-anchor="middle" transform="rotate(-90 25 225)">Task Solve Rate</text>')

    # Pareto Optimal Zone Shading (Top Left)
    opt_x_end = x_px(1.5)
    opt_y_start = y_px(100)
    opt_y_end = y_px(60)
    svg.append(f'  <rect x="90" y="{opt_y_start - 20:.1f}" width="{opt_x_end - 90:.1f}" height="{opt_y_end - opt_y_start + 20:.1f}" fill="#dcfce7" fill-opacity="0.4" rx="4"/>')
    svg.append(f'  <text x="{opt_x_end - 10:.1f}" y="{opt_y_start + 20:.1f}" font-family="sans-serif" font-size="11" font-weight="700" fill="#15803d" text-anchor="end">PARETO OPTIMAL ZONE</text>')

    # Plot Pareto curve line
    p_pts = [(0.88, 100.0), (0.95, 100.0), (1.01, 100.0), (2.41, 100.0), (4.38, 100.0), (4.89, 100.0), (6.09, 100.0)]
    pts_str = " ".join(f"{x_px(x):.1f},{y_px(y):.1f}" for x, y in p_pts)
    svg.append(f'  <polyline points="{pts_str}" fill="none" stroke="#10b981" stroke-width="2.5" stroke-dasharray="3,3"/>')

    # Plot Models
    for name, lat, rate, cat, color, dx, dy in models:
        cx = x_px(lat)
        cy = y_px(rate)
        # Point shadow & circle
        svg.append(f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="{color}" stroke="#ffffff" stroke-width="2" filter="url(#shadow)"/>')
        # Label
        svg.append(f'  <text x="{cx + dx:.1f}" y="{cy + dy:.1f}" font-family="sans-serif" font-size="11" font-weight="600" fill="#1e293b">{name} ({lat}s)</text>')

    # Legend
    svg.append('  <g transform="translate(180, 425)">')
    svg.append('    <circle cx="0" cy="5" r="5" fill="#10b981"/>')
    svg.append('    <text x="10" y="9" font-family="sans-serif" font-size="11" fill="#475569">Pareto Optimal (Flash/Mini)</text>')
    svg.append('    <circle cx="170" cy="5" r="5" fill="#3b82f6"/>')
    svg.append('    <text x="180" y="9" font-family="sans-serif" font-size="11" fill="#475569">Flagship &amp; Open-Weights</text>')
    svg.append('    <circle cx="340" cy="5" r="5" fill="#8b5cf6"/>')
    svg.append('    <text x="350" y="9" font-family="sans-serif" font-size="11" fill="#475569">Frontier MoE (Free Tier)</text>')
    svg.append('    <circle cx="500" cy="5" r="5" fill="#f59e0b"/>')
    svg.append('    <text x="510" y="9" font-family="sans-serif" font-size="11" fill="#475569">Compact Architecture</text>')
    svg.append('  </g>')

    svg.append('</svg>')
    output_path.write_text("\n".join(svg), encoding="utf-8")
    print(f"✅ Generated {output_path.name}")


def generate_performance_bars_svg(output_path: Path) -> None:
    """Generate SVG horizontal bar comparison for all 8 models."""
    models = [
        ("gemini-3.1-flash-lite", "Gemini", 100.0, 8.08, "$0.0022", "#10b981"),
        ("gemini-3.5-flash-lite", "Gemini", 100.0, 11.58, "$0.0021", "#10b981"),
        ("openai/gpt-4o-mini", "OpenRouter", 100.0, 1.01, "$0.0032", "#10b981"),
        ("openai/gpt-4o", "OpenRouter", 100.0, 2.41, "$0.0520", "#3b82f6"),
        ("meta-llama/llama-3.3-70b", "OpenRouter", 100.0, 4.38, "$0.0051", "#3b82f6"),
        ("nvidia/nemotron-3-ultra", "NVIDIA NIM", 100.0, 4.89, "$0.0000", "#8b5cf6"),
        ("qwen/qwen-2.5-coder-32b", "OpenRouter", 100.0, 6.09, "$0.0028", "#3b82f6"),
        ("mistral-small-24b", "OpenRouter", 80.0, 1.16, "$0.0041", "#f59e0b"),
    ]

    svg = []
    svg.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 450" width="100%" height="auto">')
    svg.append('  <rect width="850" height="450" rx="12" fill="#ffffff" stroke="#e2e8f0" stroke-width="1"/>')
    svg.append('  <text x="30" y="38" font-family="sans-serif" font-size="18" font-weight="700" fill="#0f172a">Model Solve Rate &amp; Latency Spectrum</text>')
    svg.append('  <text x="30" y="58" font-family="sans-serif" font-size="12" fill="#64748b">Comparison across all 8 evaluated LLMs on 5 verified SWE-bench tasks (40 runs)</text>')

    # Table Header
    svg.append('  <rect x="30" y="75" width="790" height="30" fill="#f8fafc" rx="6"/>')
    svg.append('  <text x="45" y="95" font-family="sans-serif" font-size="11" font-weight="700" fill="#475569">MODEL IDENTIFIER</text>')
    svg.append('  <text x="280" y="95" font-family="sans-serif" font-size="11" font-weight="700" fill="#475569">PROVIDER</text>')
    svg.append('  <text x="410" y="95" font-family="sans-serif" font-size="11" font-weight="700" fill="#475569">SOLVE RATE (BAR)</text>')
    svg.append('  <text x="620" y="95" font-family="sans-serif" font-size="11" font-weight="700" fill="#475569">AVG LATENCY</text>')
    svg.append('  <text x="740" y="95" font-family="sans-serif" font-size="11" font-weight="700" fill="#475569">AVG COST</text>')

    y_pos = 125
    for name, provider, rate, lat, cost, color in models:
        # Row zebra
        svg.append(f'  <line x1="30" y1="{y_pos + 18}" x2="820" y2="{y_pos + 18}" stroke="#f1f5f9"/>')
        # Model Name
        svg.append(f'  <text x="45" y="{y_pos}" font-family="monospace" font-size="11" font-weight="600" fill="#1e293b">{name}</text>')
        # Provider
        svg.append(f'  <text x="280" y="{y_pos}" font-family="sans-serif" font-size="11" fill="#64748b">{provider}</text>')
        # Solve Rate Bar
        bar_w = (rate / 100.0) * 140
        svg.append(f'  <rect x="410" y="{y_pos - 11}" width="140" height="14" rx="4" fill="#f1f5f9"/>')
        svg.append(f'  <rect x="410" y="{y_pos - 11}" width="{bar_w:.1f}" height="14" rx="4" fill="{color}"/>')
        svg.append(f'  <text x="560" y="{y_pos}" font-family="sans-serif" font-size="11" font-weight="600" fill="#334155">{rate:.0f}%</text>')
        # Latency
        svg.append(f'  <text x="620" y="{y_pos}" font-family="sans-serif" font-size="11" fill="#0284c7" font-weight="600">{lat:.2f}s</text>')
        # Cost
        svg.append(f'  <text x="740" y="{y_pos}" font-family="sans-serif" font-size="11" fill="#16a34a" font-weight="600">{cost}</text>')
        y_pos += 38

    svg.append('</svg>')
    output_path.write_text("\n".join(svg), encoding="utf-8")
    print(f"✅ Generated {output_path.name}")


def generate_intermediary_metrics_svg(output_path: Path) -> None:
    """Generate SVG flowchart of the 3 Intermediary Metrics."""
    svg = []
    svg.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 360" width="100%" height="auto">')
    svg.append('  <rect width="850" height="360" rx="12" fill="#ffffff" stroke="#e2e8f0" stroke-width="1"/>')
    svg.append('  <text x="30" y="38" font-family="sans-serif" font-size="18" font-weight="700" fill="#0f172a">Intermediary Behavioral Metrics Architecture (Section V.7)</text>')
    svg.append('  <text x="30" y="58" font-family="sans-serif" font-size="12" fill="#64748b">Measurement of agent reasoning lifecycle across Exploration, Convergence, and Submission Discipline</text>')

    # 3 Cards for the 3 metrics
    # Card 1: Metric 1
    svg.append('  <rect x="30" y="85" width="240" height="235" rx="8" fill="#eff6ff" stroke="#bfdbfe" stroke-width="1.5"/>')
    svg.append('  <circle cx="60" cy="115" r="16" fill="#3b82f6"/>')
    svg.append('  <text x="60" y="120" font-family="sans-serif" font-size="12" font-weight="700" fill="#ffffff" text-anchor="middle">1</text>')
    svg.append('  <text x="85" y="115" font-family="sans-serif" font-size="13" font-weight="700" fill="#1e3a8a">Exploration Efficiency</text>')
    svg.append('  <text x="85" y="130" font-family="sans-serif" font-size="10" font-weight="600" fill="#2563eb">METRIC 1</text>')
    svg.append('  <line x1="45" y1="145" x2="255" y2="145" stroke="#bfdbfe"/>')
    svg.append('  <text x="45" y="168" font-family="sans-serif" font-size="11" fill="#1e293b" font-weight="600">First Target Touch Step</text>')
    svg.append('  <text x="45" y="190" font-family="sans-serif" font-size="10" fill="#475569">Step where the agent first</text>')
    svg.append('  <text x="45" y="206" font-family="sans-serif" font-size="10" fill="#475569">locates and opens the file</text>')
    svg.append('  <text x="45" y="222" font-family="sans-serif" font-size="10" fill="#475569">modified in the final patch.</text>')
    svg.append('  <rect x="45" y="250" width="210" height="50" rx="6" fill="#ffffff" stroke="#93c5fd"/>')
    svg.append('  <text x="55" y="270" font-family="sans-serif" font-size="10" font-weight="700" fill="#1d4ed8">Empirical Result:</text>')
    svg.append('  <text x="55" y="288" font-family="sans-serif" font-size="11" font-weight="700" fill="#15803d">🎯 Step 1 to 2 across all models</text>')

    # Arrow 1 -> 2
    svg.append('  <path d="M 275 200 L 295 200" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)"/>')

    # Card 2: Metric 2
    svg.append('  <rect x="305" y="85" width="240" height="235" rx="8" fill="#f0fdf4" stroke="#bbf7d0" stroke-width="1.5"/>')
    svg.append('  <circle cx="335" cy="115" r="16" fill="#10b981"/>')
    svg.append('  <text x="335" y="120" font-family="sans-serif" font-size="12" font-weight="700" fill="#ffffff" text-anchor="middle">2</text>')
    svg.append('  <text x="360" y="115" font-family="sans-serif" font-size="13" font-weight="700" fill="#065f46">Test Convergence Step</text>')
    svg.append('  <text x="360" y="130" font-family="sans-serif" font-size="10" font-weight="600" fill="#059669">METRIC 2</text>')
    svg.append('  <line x1="320" y1="145" x2="530" y2="145" stroke="#bbf7d0"/>')
    svg.append('  <text x="320" y="168" font-family="sans-serif" font-size="11" fill="#1e293b" font-weight="600">Regression Pass Step</text>')
    svg.append('  <text x="320" y="190" font-family="sans-serif" font-size="10" fill="#475569">Iteration where unit tests</text>')
    svg.append('  <text x="320" y="206" font-family="sans-serif" font-size="10" fill="#475569">first pass completely green</text>')
    svg.append('  <text x="320" y="222" font-family="sans-serif" font-size="10" fill="#475569">inside the Docker sandbox.</text>')
    svg.append('  <rect x="320" y="250" width="210" height="50" rx="6" fill="#ffffff" stroke="#86efac"/>')
    svg.append('  <text x="330" y="270" font-family="sans-serif" font-size="10" font-weight="700" fill="#047857">Empirical Result:</text>')
    svg.append('  <text x="330" y="288" font-family="sans-serif" font-size="11" font-weight="700" fill="#15803d">🧪 Step 4 to 5 on successful runs</text>')

    # Arrow 2 -> 3
    svg.append('  <path d="M 550 200 L 570 200" stroke="#94a3b8" stroke-width="2"/>')

    # Card 3: Metric 3
    svg.append('  <rect x="580" y="85" width="240" height="235" rx="8" fill="#faf5ff" stroke="#e9d5ff" stroke-width="1.5"/>')
    svg.append('  <circle cx="610" cy="115" r="16" fill="#8b5cf6"/>')
    svg.append('  <text x="610" y="120" font-family="sans-serif" font-size="12" font-weight="700" fill="#ffffff" text-anchor="middle">3</text>')
    svg.append('  <text x="635" y="115" font-family="sans-serif" font-size="13" font-weight="700" fill="#581c87">Submission Discipline</text>')
    svg.append('  <text x="635" y="130" font-family="sans-serif" font-size="10" font-weight="600" fill="#7c3aed">METRIC 3</text>')
    svg.append('  <line x1="595" y1="145" x2="805" y2="145" stroke="#e9d5ff"/>')
    svg.append('  <text x="595" y="168" font-family="sans-serif" font-size="11" fill="#1e293b" font-weight="600">Verification-to-Exit Lag</text>')
    svg.append('  <text x="595" y="190" font-family="sans-serif" font-size="10" fill="#475569">Iterations elapsed between</text>')
    svg.append('  <text x="595" y="206" font-family="sans-serif" font-size="10" fill="#475569">first passing test and final</text>')
    svg.append('  <text x="595" y="222" font-family="sans-serif" font-size="10" fill="#475569">answer call (0 is optimal).</text>')
    svg.append('  <rect x="595" y="250" width="210" height="50" rx="6" fill="#ffffff" stroke="#d8b4fe"/>')
    svg.append('  <text x="605" y="270" font-family="sans-serif" font-size="10" font-weight="700" fill="#6d28d9">Empirical Result:</text>')
    svg.append('  <text x="605" y="288" font-family="sans-serif" font-size="11" font-weight="700" fill="#15803d">🏁 0 to 1 step lag (Zero drift)</text>')

    svg.append('</svg>')
    output_path.write_text("\n".join(svg), encoding="utf-8")
    print(f"✅ Generated {output_path.name}")


def generate_token_curve_svg(output_path: Path) -> None:
    """Generate SVG line chart showing Token Accumulation Curve: Windowed vs Unbounded."""
    svg = []
    svg.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 480" width="100%" height="auto">')
    svg.append('  <defs>')
    svg.append('    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">')
    svg.append('      <stop offset="0%" stop-color="#ffffff"/>')
    svg.append('      <stop offset="100%" stop-color="#f8fafc"/>')
    svg.append('    </linearGradient>')
    svg.append('    <linearGradient id="redZone" x1="0%" y1="0%" x2="0%" y2="100%">')
    svg.append('      <stop offset="0%" stop-color="#fee2e2" stop-opacity="0.6"/>')
    svg.append('      <stop offset="100%" stop-color="#fee2e2" stop-opacity="0.1"/>')
    svg.append('    </linearGradient>')
    svg.append('  </defs>')

    # Background card
    svg.append('  <rect width="850" height="480" rx="12" fill="url(#bgGrad)" stroke="#e2e8f0" stroke-width="1"/>')

    # Title & Subtitle
    svg.append('  <text x="30" y="40" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" font-size="18" font-weight="700" fill="#0f172a">Courbe d\'Accumulation des Tokens : Avec vs Sans Fenêtrage (Ablation 1)</text>')
    svg.append('  <text x="30" y="62" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" font-size="12" fill="#64748b">Évolution du nombre de tokens consommés par l\'agent SWE-bench au fil des itérations (Plafond autorisé : 300 000 tokens)</text>')

    # Coordinate mapping:
    # X range: Step 1 to 8 -> map to px 95 to 770
    # Y range: 0 to 450,000 -> map to px 380 to 90
    def x_px(step: float) -> float:
        return 95 + ((step - 1) / 7.0) * 675

    def y_px(tokens: float) -> float:
        return 380 - (tokens / 450000.0) * 290

    # Shaded Danger Zone (> 300,000)
    limit_y = y_px(300000)
    svg.append(f'  <rect x="95" y="90" width="675" height="{limit_y - 90:.1f}" fill="url(#redZone)" rx="4"/>')
    svg.append(f'  <text x="760" y="112" font-family="sans-serif" font-size="11" font-weight="700" fill="#b91c1c" text-anchor="end">ZONE INTERDITE / DISQUALIFICATION (&gt; 300k)</text>')

    # Gridlines Y
    for t_val in [50000, 100000, 150000, 200000, 250000, 300000, 350000, 400000]:
        yp = y_px(t_val)
        is_limit = (t_val == 300000)
        stroke_color = "#ef4444" if is_limit else "#e2e8f0"
        stroke_w = "2" if is_limit else "1"
        dash = "6,4" if is_limit else "4,4"
        svg.append(f'  <line x1="95" y1="{yp:.1f}" x2="770" y2="{yp:.1f}" stroke="{stroke_color}" stroke-width="{stroke_w}" stroke-dasharray="{dash}"/>')
        label_color = "#b91c1c" if is_limit else "#64748b"
        font_weight = "700" if is_limit else "400"
        svg.append(f'  <text x="85" y="{yp + 4:.1f}" font-family="sans-serif" font-size="11" font-weight="{font_weight}" fill="{label_color}" text-anchor="end">{t_val // 1000}k</text>')

    # 300k limit tag on chart
    svg.append(f'  <rect x="105" y="{limit_y - 24:.1f}" width="220" height="20" rx="4" fill="#fee2e2" stroke="#f87171"/>')
    svg.append(f'  <text x="115" y="{limit_y - 10:.1f}" font-family="sans-serif" font-size="10" font-weight="700" fill="#b91c1c">⚠️ LIMITE MAX MOULINETTE (300 000)</text>')

    # Gridlines X (Steps 1 to 8)
    for s in range(1, 9):
        xp = x_px(s)
        svg.append(f'  <line x1="{xp:.1f}" y1="90" x2="{xp:.1f}" y2="380" stroke="#f1f5f9"/>')
        svg.append(f'  <text x="{xp:.1f}" y="402" font-family="sans-serif" font-size="11" font-weight="600" fill="#475569" text-anchor="middle">Step {s}</text>')

    # Axes
    svg.append('  <line x1="95" y1="380" x2="770" y2="380" stroke="#94a3b8" stroke-width="1.5"/>')
    svg.append('  <line x1="95" y1="90" x2="95" y2="380" stroke="#94a3b8" stroke-width="1.5"/>')
    svg.append('  <text x="432" y="425" font-family="sans-serif" font-size="12" font-weight="700" fill="#334155" text-anchor="middle">Itérations de l\'Agent SWE-bench</text>')
    svg.append('  <text x="25" y="235" font-family="sans-serif" font-size="12" font-weight="700" fill="#334155" text-anchor="middle" transform="rotate(-90 25 235)">Tokens d\'Entrée Cumulés</text>')

    # Data: Unbounded (Red line - quadratic explosion)
    red_pts = [(1, 18000), (2, 52000), (3, 108000), (4, 182000), (5, 268000), (6, 335000), (7, 406777)]
    red_str = " ".join(f"{x_px(s):.1f},{y_px(t):.1f}" for s, t in red_pts)
    svg.append(f'  <polyline points="{red_str}" fill="none" stroke="#ef4444" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>')

    # Data: Windowed (Green line - controlled linear)
    green_pts = [(1, 8990), (2, 24337), (3, 44120), (4, 68500), (5, 92100), (6, 114800), (7, 132400), (8, 140000)]
    green_str = " ".join(f"{x_px(s):.1f},{y_px(t):.1f}" for s, t in green_pts)
    svg.append(f'  <polyline points="{green_str}" fill="none" stroke="#10b981" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>')

    # Points on Red curve
    for s, t in red_pts:
        xp, yp = x_px(s), y_px(t)
        svg.append(f'  <circle cx="{xp:.1f}" cy="{yp:.1f}" r="5" fill="#ef4444" stroke="#ffffff" stroke-width="2"/>')
    # Final crash marker
    rx, ry = x_px(7), y_px(406777)
    svg.append(f'  <rect x="{rx - 75:.1f}" y="{ry - 30:.1f}" width="150" height="22" rx="4" fill="#ef4444"/>')
    svg.append(f'  <text x="{rx:.1f}" y="{ry - 15:.1f}" font-family="sans-serif" font-size="10" font-weight="700" fill="#ffffff" text-anchor="middle">❌ CRASH (406k &gt; 300k)</text>')

    # Points on Green curve
    for s, t in green_pts:
        xp, yp = x_px(s), y_px(t)
        svg.append(f'  <circle cx="{xp:.1f}" cy="{yp:.1f}" r="5" fill="#10b981" stroke="#ffffff" stroke-width="2"/>')
    # Final success marker
    gx, gy = x_px(8), y_px(140000)
    svg.append(f'  <rect x="{gx - 65:.1f}" y="{gy - 30:.1f}" width="145" height="22" rx="4" fill="#10b981"/>')
    svg.append(f'  <text x="{gx + 7:.1f}" y="{gy - 15:.1f}" font-family="sans-serif" font-size="10" font-weight="700" fill="#ffffff" text-anchor="middle">✅ SUCCÈS (140k &lt; 300k)</text>')

    # Legend at bottom
    svg.append('  <g transform="translate(130, 452)">')
    # Red legend item
    svg.append('    <line x1="0" y1="5" x2="25" y2="5" stroke="#ef4444" stroke-width="3.5"/>')
    svg.append('    <circle cx="12.5" cy="5" r="4" fill="#ef4444"/>')
    svg.append('    <text x="35" y="9" font-family="sans-serif" font-size="11" font-weight="600" fill="#334155">Sans Fenêtrage (Sortie brute pytest -&gt; Dépassement 300k)</text>')

    # Green legend item
    svg.append('    <line x1="360" y1="5" x2="385" y2="5" stroke="#10b981" stroke-width="3.5"/>')
    svg.append('    <circle cx="372.5" cy="5" r="4" fill="#10b981"/>')
    svg.append('    <text x="395" y="9" font-family="sans-serif" font-size="11" font-weight="700" fill="#047857">Avec Fenêtrage Agent Smith (40 tête / 60 fin -&gt; 92.5% succès)</text>')
    svg.append('  </g>')

    svg.append('</svg>')
    output_path.write_text("\n".join(svg), encoding="utf-8")
    print(f"✅ Generated {output_path.name}")


def main() -> None:
    """Generate all benchmark assets."""
    generate_pareto_svg(ASSETS_DIR / "pareto_frontier.svg")
    generate_performance_bars_svg(ASSETS_DIR / "model_performance.svg")
    generate_intermediary_metrics_svg(ASSETS_DIR / "intermediary_metrics.svg")
    generate_token_curve_svg(ASSETS_DIR / "token_curve.svg")


if __name__ == "__main__":
    main()
