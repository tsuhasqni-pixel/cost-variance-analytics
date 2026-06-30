# 原価差異 統計検証ツール

**ライブ版**: https://tsuhasqni-pixel.github.io/cost-variance-analytics/

[internal-accounting](https://github.com/tsuhasqni-pixel/internal-accounting) で蓄積した複数期間分の標準原価・実績データを JSON エクスポートで読み込み、各差異項目について**統計的に有意な乖離**かどうかを検証するツール。

## 機能

- **記述統計** — 各「製品 × 差異種別」シリーズの mean / median / SD / min / max
- **1サンプル t 検定** — H0: 差異の平均 = 0（標準どおり）に対する p 値・95% CI
- **Z-score** — 個別期間の差異が平均±SD からどれだけ離れているか
- **Pareto / ABC 分析** — 不利差異の寄与上位
- **管理図（I-MR）** — 中心線 / UCL / LCL ±2.66×MR̄、out-of-control 点をハイライト
- **トレンド** — 期間順差異の単回帰（傾き・p 値）
- **CVP 感度** — 不利差異 1% 増で営業利益にどれだけ響くかの単純試算

## 使い方

### ライブ（GitHub Pages）
1. internal-accounting で 4 期以上の実績を入力
2. internal-accounting の画面右上「JSONエクスポート」
3. https://tsuhasqni-pixel.github.io/cost-variance-analytics/ で「JSONインポート」 → 各分析へ
4. データはブラウザの localStorage に保存

### ローカル Flask
```bash
./start.command          # macOS — :7863 で起動、ブラウザ自動起動
```
依存: `flask`, `jinja2`, `numpy`, `scipy`

### CLI
```bash
python analyze.py /path/to/export.json --out /tmp/report.html
open /tmp/report.html
```
単一の自己完結 HTML を生成。

## 差異公式の真実

差異計算式は **[internal-accounting/core/variance.py](https://github.com/tsuhasqni-pixel/internal-accounting/blob/main/core/variance.py)** をベンダリング（コピー）して使用。両者の式が乖離しないよう、**式を直すときは internal-accounting 側を先に修正し、本リポジトリ `core/variance_calc.py` にコピーする** 運用とする。

## テスト

```bash
.venv/bin/python -m pytest tests/ -v
```

例題: 4 期分の材料価格差異 +100, +120, −50, +200 → 平均 92.5, SD ≈ 104.6, t ≈ 1.77（p ≈ 0.18, 有意でない）
