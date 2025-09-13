# Armature Bone Name Mapper

Blenderアーマチュアのボーン名を別のアーマチュアに合わせて一括リネームするアドオンです。異なる命名規則のアーマチュア間でボーン名を統一したい場合に便利です。

## 主な機能
- 自動マッピング: 完全一致 / 正規化マッチ / 部分一致
- 階層ビュー: 親子構造をインデント表示 (Source Hierarchy)
- 折りたたみ: ツリーを展開 / 収納して整理
- 検索フィルタ: ソース名 / ターゲット名の両方で絞り込み
- ソート: Source / Target / 階層 / 階層(シンプル)
- 一括適用: マッピング結果でリネーム実行
## インストール
1. Blender を起動
2. Edit > Preferences > Add-ons
3. Install... から `Armature Bone Name Mapper.py` を選択
4. チェックを入れて有効化
5. 3D Viewport の N パネル「Bone Mapper」タブに表示されます
## 使い方
1. Source Armature と Target Armature を指定
2. Generate Mapping を押す
3. 一覧で自動マッピング結果を確認（未マッチは赤背景）
4. 必要なら手動修正
5. Apply Mapping でソースのボーンをリネーム

## ソートモード
- Source Name: ソース名アルファベット順
- Target Name: ターゲット名アルファベット順
- Source Hierarchy: 階層 + インデント + 折りたたみ
- Hierarchy (Simple): 階層順のみ

## UI 要素
| 要素 | 説明 |
|------|------|
| Source Armature | リネーム対象 |
| Target Armature | 参照（命名基準） |
| Generate Mapping | マッピング生成 / 再生成 |
| Apply Mapping | ソースへリネーム適用 |
| Search | 名前フィルタ（部分一致/両列） |
| Sort by | 並び替えモード |
| List (赤背景) | 未マッチ行 |
| ▶ / ▼ (Hierarchy) | 子階層の折りたたみ |


## マッピング手順（内部ロジック）
優先順位:
1. 完全一致 (名前そのまま一致)
2. 正規化一致 (normalize_bone_name による変換キー)
3. 部分一致 (正規化名を含む最短候補)
4. 見つからなければ空欄

## 正規化ルール概要
`normalize_bone_name()` で以下を実行:
- 小文字化
- 接頭辞除去: `character\d+_`, `mixamo:`, `armature_`
- 接尾辞除去: `_end`, `_const*`, `_twist*` 等
- 左右抽出: Left / Right / .L / .R / _l / _r / -l / -r → `_l` / `_r` （末尾または先頭語のみ）
- 指名統一: thumb/index/middle/ring/pinky(+数字) → `finger_<name><num>_l/r`
- 区切り統一: 空白 / '.' / '-' → `_` 連結アンダースコア圧縮
- 部位マップ `part_mapping` による同義語変換
  - 例: thigh → upperleg, shin/calf → lowerleg, forearm → lowerarm
- 追加ヒューリスティック:
  - `(upper|up).*leg` → upperleg
  - `(lower).*leg` → lowerleg
  - `(upper|up).*arm` → upperarm
  - `(lower|fore).*arm` → lowerarm
  - 語尾 upleg / leg / arm の再解釈

### 変更しやすい部分
`part_mapping` に行を追加すると簡単に正規化語彙を拡張できます。
```python
part_mapping = {
    "spine1": "spine",
    "spine2": "chest",
}
```

## トラブルシュート
| 症状 | 対処 |
|------|------|
| マッピングが空 | Source / Target が Armature 型か確認 |
| 期待と違うペア | 該当行の target_name を手動修正 |
| 階層が崩れる | Generate Mapping を再実行 |
| 一部が未マッチ | part_mapping に同義語を追加検討 |

## 拡張案（カスタマイズ）
| やりたいこと | 手段 |
|---------------|------|
| 新しい同義語追加 | `part_mapping` を編集 |
| 指以外の特殊命名 | normalize_bone_name 中に条件追加 |
| 別の並び替え基準 | Enum にモード追加 + filter_items 拡張 |
| CSV 入出力 | 新オペレーターを追加し mappings を走査 |

## パフォーマンス
- 正規化: O(n)（正規表現数は限定）
- 階層列挙: Pre-order + アルファソート
- 大量ボーン（>1000）でも軽量運用を想定

## 対応環境
- Blender 3.0+ 以降
- Windows / macOS / Linux


## ライセンス / 問い合わせ
用途に合わせて自由に改変可能です。バグ報告や要望は Issues へ。

---

改善提案歓迎。
