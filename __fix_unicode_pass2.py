from pathlib import Path
replacements = {
    ''.join(chr(c) for c in [0x05f4, 0x032c]): '状态',
    ''.join(chr(c) for c in [0x03b4, 0x05aa]): '未知',
    ''.join(chr(c) for c in [0x056a, 0x04aa]): '暂无',
    ''.join(chr(c) for c in [0x03f5, 0x0373]): '系统',
    ''.join(chr(c) for c in [0x01f3, 0x026b]): '浅色',
    ''.join(chr(c) for c in [0x016d, 0x026b]): '暖色',
}
for p in Path('frontend/src').rglob('*.vue'):
    text = p.read_text(encoding='utf-8')
    new = text
    for old, new_text in replacements.items():
        new = new.replace(old, new_text)
    if p.as_posix().endswith('CharacterPanel.vue'):
        new = new.replace('检测到重名人物,仍可继续保存。', '检测到重名人物，仍可继续保存。')
    if p.as_posix().endswith('RightWorkspacePanel.vue'):
        new = new.replace("defineEmits(['update:modelValue', 'save-dirty', 'discard-dirty', 'width-change'])", "defineEmits(['update:modelValue', 'update:model-value', 'save-dirty', 'discard-dirty', 'width-change'])")
    if new != text:
        p.write_text(new, encoding='utf-8')
        print(p)
