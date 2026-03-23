## 变更说明 / Description

> 简要描述这个 PR 做了什么 / Briefly describe what this PR does

### 变更类型 / Type of Change

- [ ] 🐛 Bug 修复 / Bug fix
- [ ] ✨ 新功能 / New feature
- [ ] 🧩 新 Skill 包 / New Skill pack
- [ ] 📟 新芯片支持 / New chip support
- [ ] 📄 文档改善 / Documentation improvement
- [ ] ♻️ 重构 / Refactor
- [ ] ⚡ 性能优化 / Performance improvement
- [ ] 🔧 CI / 配置变更 / CI or config change

---

## 关联 Issue / Related Issue

> 如修复了某个 Issue，请填写 / If this fixes an Issue, link it here

Closes #

---

## 测试方法 / How to Test

> 描述如何验证这个 PR 的改动 / Describe how to verify the changes

```bash
# 例如 / e.g.
gary doctor
gary do "PA0 LED blink 500ms" --chip STM32F103C8T6
```

**测试环境 / Test Environment:**
- OS:
- Python:
- 芯片 / Chip（如涉及硬件 / if hardware-related）:
- AI 后端 / AI Backend:

---

## 提交前检查 / Pre-merge Checklist

- [ ] 代码通过 `black` 格式化，`flake8` 无报错
- [ ] 新功能 / 新工具已在对应模块注册（如 `stm32_extra_tools.py`）
- [ ] 不破坏三种烧录模式（SWD / UART ISP / 无硬件）的行为一致性
- [ ] 如涉及 Skill，`skill.json` 中 `author` 字段已填写
- [ ] 文档已同步更新（如有必要）
- [ ] CHANGELOG.md 已更新（如有必要）
