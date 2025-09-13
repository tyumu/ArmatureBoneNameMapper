bl_info = {
    "name": "Armature Bone Name Mapper",
    "author": "meguire",
    "version": (0, 3),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Bone Mapper",
    "description": "Rename bones of one armature to match another (with search & sort)",
    "category": "Rigging",
}

import bpy
import re

def normalize_bone_name(name: str) -> str:
    n = name.lower()

    # 接頭辞・接尾辞削除
    n = re.sub(r"(character\d+_|mixamo:|armature_)", "", n)
    n = re.sub(r"(_end|_const.*|_twist.*)$", "", n)

    # 左右識別子を先に抽出
    side = ""
    if re.search(r"(left|_l$|\.l$|-l$)", n):
        side = "_l"
    elif re.search(r"(right|_r$|\.r$|-r$)", n):
        side = "_r"

    # 指の正規化（早期リターン）
    if re.search(r"thumb\d*", n):
        num = re.search(r"thumb(\d*)", n).group(1) if re.search(r"thumb(\d+)", n) else ""
        return f"finger_thumb{num}{side}"
    if re.search(r"index\d*", n):
        num = re.search(r"index(\d*)", n).group(1) if re.search(r"index(\d+)", n) else ""
        return f"finger_index{num}{side}"
    if re.search(r"middle\d*", n):
        num = re.search(r"middle(\d*)", n).group(1) if re.search(r"middle(\d+)", n) else ""
        return f"finger_middle{num}{side}"
    if re.search(r"ring\d*", n):
        num = re.search(r"ring(\d*)", n).group(1) if re.search(r"ring(\d+)", n) else ""
        return f"finger_ring{num}{side}"
    if re.search(r"pinky\d*", n):
        num = re.search(r"pinky(\d*)", n).group(1) if re.search(r"pinky(\d+)", n) else ""
        return f"finger_pinky{num}{side}"

    # 左右識別子を削除（内部の _l / _r を壊さない: 先頭の left/right と末尾の区切り付きサフィックスのみ）
    # 先頭の left/right
    n = re.sub(r"^(left|right)", "", n)
    # 末尾の .l/.r / _l/_r / -l/-r を一括除去
    n = re.sub(r"([._-][lr])$", "", n)

    # 区切り文字統一
    n = re.sub(r"[ .\-]", "_", n)
    n = re.sub(r"_+", "_", n).strip("_")

    # 部位名の正規化マップ（完全一致）
    part_mapping = {
        # 脚部
        "upleg": "upperleg",
        "up_leg": "upperleg",
        "upper_leg": "upperleg",
        "upperleg": "upperleg",
        "thigh": "upperleg",
        "leg": "lowerleg",
        "lower_leg": "lowerleg",
        "lowerleg": "lowerleg",
        "calf": "lowerleg",
        "shin": "lowerleg",
        # 腕部
        "uparm": "upperarm",
        "up_arm": "upperarm",
        "upper_arm": "upperarm",
        "upperarm": "upperarm",
        "arm": "upperarm",
        "forearm": "lowerarm",
        "fore_arm": "lowerarm",
        "lower_arm": "lowerarm",
        "lowerarm": "lowerarm",
        # その他
        "pelvis": "hip",
        "hips": "hip",
        "hip": "hip",
        "shoulder": "shoulder",
        "wrist": "hand",
        "hand": "hand",
        "eye": "eye",
        "headtop": "headtop",
        "toe_base": "toes",
        "toe": "toes",
        "toes": "toes",
    }

    original_n = n  # ヒューリスティック前の保持

    if n in part_mapping:
        n = part_mapping[n]
    else:
        # ここからヒューリスティック（接尾語や補助語が付いたケース対応）
        base = n
        # 数字/補助語を除去（roll, twist, helper 等）
        base = re.sub(r"(roll|twist|helper|aux|assist|end)$", "", base)
        base = re.sub(r"\d+$", "", base)
        # 再度トリム
        base = base.strip('_')

        # 上下肢判定（含有ベース）
        if re.search(r"(upper|up).*leg", base):
            n = "upperleg"
        elif re.search(r"(lower).*leg", base):
            n = "lowerleg"
        elif re.search(r"(upper|up).*arm", base):
            n = "upperarm"
        elif re.search(r"(lower|fore).*arm", base):
            n = "lowerarm"
        elif base.endswith("upleg"):
            n = "upperleg"
        elif base.endswith("leg") and original_n != "leg":
            # 単独 leg 以外で leg 終了（例: shinleg など想定）
            n = "lowerleg"
        elif base.endswith("arm") and original_n != "arm":
            n = "upperarm"

    # toes_end の特例処理
    if "toe" in n and "end" in original_n:
        return f"toes_end{side}"

    return n + side


def get_bones_in_hierarchy(bones):
    """Return bone names in parent-child (preorder) hierarchy order."""
    result = []
    visited = set()

    def add_bone_and_children(bone):
        if bone.name in visited:
            return
        visited.add(bone.name)
        result.append(bone.name)
        
        # 子ボーンを名前順でソートしてから再帰的に追加
        children = sorted(bone.children, key=lambda x: x.name)
        for child in children:
            add_bone_and_children(child)

    # ルートボーン（親がないボーン）を名前順でソートしてから処理
    root_bones = sorted([b for b in bones if b.parent is None], key=lambda x: x.name)
    
    # 各ルートボーンとその子孫を順番に処理
    for root in root_bones:
        add_bone_and_children(root)
    
    # 処理されていないボーンがあれば追加
    all_bone_names = {b.name for b in bones}
    unprocessed = all_bone_names - visited
    if unprocessed:
        # 処理されていないボーンを名前順で最後に追加
        unprocessed_bones = sorted([b for b in bones if b.name in unprocessed], key=lambda x: x.name)
        for bone in unprocessed_bones:
            if bone.name not in visited:
                add_bone_and_children(bone)

    return result


# マッピング1行分
class BoneMappingItem(bpy.types.PropertyGroup):
    source_name: bpy.props.StringProperty(name="Source")
    target_name: bpy.props.StringProperty(name="Target")


# 折りたたみ状態保存用
class BoneFoldItem(bpy.types.PropertyGroup):
    bone_name: bpy.props.StringProperty()
    expanded: bpy.props.BoolProperty(default=True)


class BoneMapperProperties(bpy.types.PropertyGroup):
    source: bpy.props.PointerProperty(name="Source Armature", type=bpy.types.Object)
    target: bpy.props.PointerProperty(name="Target Armature", type=bpy.types.Object)
    mappings: bpy.props.CollectionProperty(type=BoneMappingItem)
    active_index: bpy.props.IntProperty()
    folds: bpy.props.CollectionProperty(type=BoneFoldItem)
    filter_string: bpy.props.StringProperty(name="Filter", default="")
    
    def update_sort_mode(self, context):
        # Sort mode が変更されたら マッピングを再生成
        props = context.scene.bone_mapper
        if len(props.mappings) > 0:
            bpy.ops.armature.generate_mapping()
        # UI も強制更新
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    
    sort_mode: bpy.props.EnumProperty(
        name="Sort by",
        items=[
            ('SOURCE', "Source Name", ""),
            ('TARGET', "Target Name", ""),
            ('SOURCE_HIER', "Source Hierarchy", ""),
            ('SOURCE_HIER_SIMPLE', "Hierarchy (Simple)", ""),
        ],
        default='SOURCE_HIER',
        update=update_sort_mode,
    )


# マッピング生成
class ARMATURE_OT_generate_mapping(bpy.types.Operator):
    bl_idname = "armature.generate_mapping"
    bl_label = "Generate Mapping (Stepwise)"

    def execute(self, context):
        props = context.scene.bone_mapper
        props.mappings.clear()
        props.folds.clear()

        if not props.source or not props.target:
            self.report({'WARNING'}, "Source and Target must be set")
            return {'CANCELLED'}

        src_bones = props.source.data.bones
        tgt_bones = props.target.data.bones

        tgt_names = [b.name for b in tgt_bones]
        tgt_norm = {normalize_bone_name(b.name): b.name for b in tgt_bones}

        # 階層順序を取得してマッピングを作成
        if props.sort_mode in ['SOURCE_HIER', 'SOURCE_HIER_SIMPLE']:
            # 階層順序でボーンを処理
            hierarchy_order = get_bones_in_hierarchy(src_bones)
            bone_order = hierarchy_order
        else:
            # 通常順序
            bone_order = [b.name for b in src_bones]

        for bone_name in bone_order:
            bone = src_bones.get(bone_name)
            if not bone:
                continue
                
            item = props.mappings.add()
            item.source_name = bone.name

            # 1. 完全一致
            if bone.name in tgt_names:
                item.target_name = bone.name
                continue

            # 2. 正規化一致
            norm = normalize_bone_name(bone.name)
            if norm in tgt_norm:
                item.target_name = tgt_norm[norm]
                continue

            # 3. 部分一致補助
            matches = [t for t in tgt_names if norm in normalize_bone_name(t)]
            if matches:
                matches.sort(key=lambda x: len(x))
                item.target_name = matches[0]
                continue

            # 4. 見つからなければ空欄
            item.target_name = ""

        # 折りたたみ状態を初期化（全て展開）
        for bone in src_bones:
            fold_item = props.folds.add()
            fold_item.bone_name = bone.name
            fold_item.expanded = True

        # ソースとターゲットのボーン数の違いを報告
        matched_count = sum(1 for item in props.mappings if item.target_name)
        unmatched_count = len(props.mappings) - matched_count
        
        self.report({'INFO'}, f"Generated {len(props.mappings)} mappings: {matched_count} matched, {unmatched_count} unmatched")
        return {'FINISHED'}



# リネーム実行
class ARMATURE_OT_apply_mapping(bpy.types.Operator):
    bl_idname = "armature.apply_mapping"
    bl_label = "Apply Mapping"

    def execute(self, context):
        props = context.scene.bone_mapper
        if not props.source:
            self.report({'WARNING'}, "Source Armature not set")
            return {'CANCELLED'}

        for item in props.mappings:
            if item.target_name:
                bone = props.source.data.bones.get(item.source_name)
                if bone:
                    bone.name = item.target_name

        self.report({'INFO'}, "Bone renaming applied")
        return {'FINISHED'}


# 折りたたみトグル
class ARMATURE_OT_toggle_fold(bpy.types.Operator):
    bl_idname = "armature.toggle_fold"
    bl_label = "Toggle Fold"

    bone_name: bpy.props.StringProperty()

    def execute(self, context):
        props = context.scene.bone_mapper
        
        # まず、折りたたみボタンが押されたアイテムを選択する
        for i, item in enumerate(props.mappings):
            if item.source_name == self.bone_name:
                props.active_index = i
                break
        
        # 現在のアクティブなアイテムのインデックスを保存
        current_active_index = props.active_index
        current_active_bone = None
        if 0 <= current_active_index < len(props.mappings):
            current_active_bone = props.mappings[current_active_index].source_name
        
        # 折りたたみ状態を変更
        for f in props.folds:
            if f.bone_name == self.bone_name:
                old_state = f.expanded
                f.expanded = not f.expanded
                
                # UIを強制更新
                context.area.tag_redraw()
                
                # 折りたたみ後、現在表示されているアイテムの中で適切な位置を探す
                if current_active_bone:
                    # 現在アクティブだったボーンが表示されているか確認
                    new_index = self.find_visible_bone_index(props, current_active_bone, context)
                    if new_index >= 0:
                        props.active_index = new_index
                    else:
                        # 表示されていない場合、折りたたんだボーンまたはその親を選択
                        fallback_index = self.find_fallback_bone_index(props, self.bone_name, context)
                        if fallback_index >= 0:
                            props.active_index = fallback_index
                
                self.report({'INFO'}, f"Toggled {self.bone_name}: {old_state} -> {f.expanded}")
                return {'FINISHED'}
        
        # folds に見つからない場合の処理
        self.report({'WARNING'}, f"Fold not found for bone: {self.bone_name}")
        return {'CANCELLED'}
    
    def find_visible_bone_index(self, props, bone_name, context):
        """指定されたボーンが表示されている場合、そのインデックスを返す"""
        if not props.source or not hasattr(props.source, 'data'):
            return -1
        
        bone_map = {b.name: b for b in props.source.data.bones}
        bone = bone_map.get(bone_name)
        if not bone:
            return -1
        
        # 親を辿って、折りたたまれた祖先がないかチェック
        parent = bone.parent
        while parent:
            fold = next((f for f in props.folds if f.bone_name == parent.name), None)
            if fold and not fold.expanded:
                return -1  # 祖先が折りたたまれているので非表示
            parent = parent.parent
        
        # 表示されている場合、mappings内でのインデックスを探す
        for i, item in enumerate(props.mappings):
            if item.source_name == bone_name:
                return i
        
        return -1
    
    def find_fallback_bone_index(self, props, bone_name, context):
        """フォールバック用：折りたたんだボーンの近くで適切なインデックスを返す"""
        if not props.source or not hasattr(props.source, 'data'):
            return 0
        
        # まず、折りたたんだボーン自体のインデックスを探す
        folded_bone_index = -1
        for i, item in enumerate(props.mappings):
            if item.source_name == bone_name:
                folded_bone_index = i
                break
        
        if folded_bone_index >= 0:
            return folded_bone_index
        
        # 折りたたんだボーンが見つからない場合、そのボーンの親を探す
        bone_map = {b.name: b for b in props.source.data.bones}
        bone = bone_map.get(bone_name)
        if bone and bone.parent:
            parent_name = bone.parent.name
            for i, item in enumerate(props.mappings):
                if item.source_name == parent_name:
                    return i
        
        # それも見つからない場合は最初のアイテム、または現在のアクティブアイテムの近くを維持
        current_active = props.active_index
        if 0 <= current_active < len(props.mappings):
            # 現在の位置から前後5つ以内で表示されているボーンを探す
            search_range = 5
            for offset in range(search_range):
                for direction in [-1, 1]:  # 前後両方向を検索
                    test_index = current_active + (direction * offset)
                    if 0 <= test_index < len(props.mappings):
                        test_bone_name = props.mappings[test_index].source_name
                        if self.find_visible_bone_index(props, test_bone_name, context) >= 0:
                            return test_index
        
        # 最後の手段：最初の表示可能なアイテム
        for i, item in enumerate(props.mappings):
            if self.find_visible_bone_index(props, item.source_name, context) >= 0:
                return i
        
        return 0 if len(props.mappings) > 0 else -1


# 表リスト
class BONE_UL_mapping_list(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        props = context.scene.bone_mapper
        row = layout.row(align=True)
        
        # Source Hierarchy モードの時だけインデント表示と折りたたみボタン（Simpleモードは除く）
        if props.sort_mode == 'SOURCE_HIER' and props.source and hasattr(props.source, 'data') and hasattr(props.source.data, 'bones'):
            bone = props.source.data.bones.get(item.source_name)
            if bone:
                # 深さを計算
                depth = 0
                parent = bone.parent
                while parent:
                    depth += 1
                    parent = parent.parent
                
                # インデント（深さ分だけ空白ラベル）
                for _ in range(depth):
                    row.label(text="", icon='BLANK1')
                
                # 子を持つボーンの場合は折りたたみボタンを表示
                if len(bone.children) > 0:
                    fold = next((f for f in props.folds if f.bone_name == bone.name), None)
                    if fold:
                        fold_icon = 'TRIA_DOWN' if fold.expanded else 'TRIA_RIGHT'
                    else:
                        # foldsに無い場合はデフォルトで展開状態
                        fold_icon = 'TRIA_DOWN'
                    op = row.operator("armature.toggle_fold", text="", icon=fold_icon)
                    op.bone_name = bone.name
                else:
                    # 子がないボーンは空白
                    row.label(text="", icon='BLANK1')
        
        row.label(text=item.source_name)
        
        # ターゲット名が空の場合は背景色を変更して目立たせる
        if item.target_name:
            row.prop(item, "target_name", text="")
        else:
            # 未マッチの場合は警告色で表示
            sub_row = row.row(align=True)
            sub_row.alert = True  # 赤い背景で強調
            sub_row.prop(item, "target_name", text="")

    # フィルタ処理（検索＆ソート）
    def filter_items(self, context, data, propname):
        props = context.scene.bone_mapper
        items = getattr(data, propname)
        helper_funcs = bpy.types.UI_UL_list

        # 初期化
        flt_flags = []
        flt_neworder = []

        # 検索フィルタ
        filter_str = props.filter_string.lower().strip()
        if filter_str:
            for item in items:
                if (
                    filter_str in item.source_name.lower()
                    or filter_str in item.target_name.lower()
                ):
                    flt_flags.append(self.bitflag_filter_item)
                else:
                    flt_flags.append(0)
        else:
            flt_flags = [self.bitflag_filter_item] * len(items)

        # ソート - SOURCE_HIER の場合はデータ生成時点で並び替え済みなのでそのまま使用
        if props.sort_mode == 'SOURCE':
            flt_neworder = sorted(range(len(items)), key=lambda i: items[i].source_name.lower())
        elif props.sort_mode == 'TARGET':
            flt_neworder = sorted(range(len(items)), key=lambda i: items[i].target_name.lower())
        else:  # SOURCE_HIER or その他
            # マッピング生成時点で既に正しい順序になっているので、そのまま使用
            flt_neworder = list(range(len(items)))
        
        # 折りたたみ処理：祖先が折りたたまれているアイテムを非表示
        if props.sort_mode == 'SOURCE_HIER' and props.source and hasattr(props.source, 'data') and hasattr(props.source.data, 'bones'):
            bone_map = {b.name: b for b in props.source.data.bones}
            for i, item in enumerate(items):
                bone = bone_map.get(item.source_name)
                if bone:
                    # 親を辿って、折りたたまれた祖先がないかチェック
                    parent = bone.parent
                    while parent:
                        fold = next((f for f in props.folds if f.bone_name == parent.name), None)
                        if fold and not fold.expanded:
                            # 祖先が折りたたまれているので非表示
                            flt_flags[i] = 0
                            break
                        parent = parent.parent

        return flt_flags, flt_neworder


# パネル
class ARMATURE_PT_bone_mapper(bpy.types.Panel):
    bl_label = "Bone Mapper"
    bl_idname = "ARMATURE_PT_bone_mapper"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Bone Mapper'

    def draw(self, context):
        layout = self.layout
        props = context.scene.bone_mapper

        layout.prop(props, "source")
        layout.prop(props, "target")

        row = layout.row()
        row.operator("armature.generate_mapping", text="Generate Mapping")
        row.operator("armature.apply_mapping", text="Apply Mapping")

        row2 = layout.row(align=True)
        row2.prop(props, "filter_string", text="Search")
        row2.prop(props, "sort_mode", text="")
        layout.template_list(
            "BONE_UL_mapping_list",
            "",
            props,
            "mappings",
            props,
            "active_index",
            rows=12,
        )


classes = (
    BoneMappingItem,
    BoneFoldItem,
    BoneMapperProperties,
    ARMATURE_OT_generate_mapping,
    ARMATURE_OT_apply_mapping,
    ARMATURE_OT_toggle_fold,
    BONE_UL_mapping_list,
    ARMATURE_PT_bone_mapper,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bone_mapper = bpy.props.PointerProperty(type=BoneMapperProperties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.bone_mapper


if __name__ == "__main__":
    register()
