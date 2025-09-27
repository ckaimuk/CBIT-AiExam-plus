# 🚀 CBIT AutoExam 服务器升级指南

## ✨ 新版本功能

- **🎯 精确数量控制** - 为每个学科、难度、题型组合指定题目生成数量
- **🏷️ 统一标签体系** - 全面规范化题目标签，确保筛选准确性
- **🎨 全新UI设计** - 精确数量控制功能拥有独立模态窗口
- **🌐 完整多语言支持** - 所有新功能文本均已添加中英文翻译

## 🚀 一键升级（推荐）

在宝塔服务器SSH中执行：

```bash
cd /www/wwwroot/cbit-autoexam && git pull origin main && ./upgrade.sh
```

## 📋 升级过程

脚本将自动完成：

1. **环境检查** - 验证Docker、Git等必要工具
2. **创建备份** - 备份整个项目和数据库到 `/www/backup/`
3. **停止服务** - 强制清理Docker容器冲突
4. **更新代码** - 自动解决Git权限问题并拉取最新代码
5. **数据库迁移** - 添加新功能所需的数据库字段
6. **重启服务** - 强制重新创建容器避免冲突
7. **验证结果** - 检查服务状态

## 🎯 升级后测试

1. 访问 `http://你的服务器IP:8080`
2. 登录管理后台：`admin` / `imbagogo`
3. 进入"考试配置管理"测试精确数量控制功能
4. 验证题目筛选是否按新标签体系工作

## 🛡️ 安全保障

- **自动备份** - 每次升级前完整备份
- **一键回滚** - 如有问题可快速恢复
- **强制清理** - 自动解决Docker容器冲突
- **权限修复** - 自动处理Git安全问题

## 🆘 常见问题

**Git权限错误：**
```bash
git config --global --add safe.directory /www/wwwroot/cbit-autoexam
```

**Docker容器冲突：**
```bash
docker stop $(docker ps -q --filter "name=cbit")
docker rm -f $(docker ps -aq --filter "name=cbit")
```

**快速回滚：**
```bash
cd /www/wwwroot/cbit-autoexam
docker-compose down
rm -rf * .* 2>/dev/null || true
cp -r /www/backup/cbit-autoexam-backup-最新时间戳/* .
docker-compose up -d
```

---

**升级完成后即可使用全新的精确数量控制功能！** 🎉