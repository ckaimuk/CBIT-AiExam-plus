# 数据库部署优化指南

## 🎯 优化内容

本次优化统一了数据库路径配置，解决了"路径不一致"和权限问题。

### ✅ 已完成的优化

1. **统一数据库路径**：所有环境统一使用 `/data/app.db`
2. **简化权限管理**：完全开放权限，避免复杂的用户权限设置
3. **数据持久化**：数据库独立于代码目录，安全可靠
4. **最小代码改动**：保持核心业务逻辑不变

## 🚀 部署步骤

### 1. 准备宿主机目录
```bash
# 创建数据目录
sudo mkdir -p /srv/yourapp/data

# 一次性权限设置（完全开放）
sudo chmod -R 777 /srv/yourapp/data
```

### 2. 部署应用
```bash
# 使用 docker-compose 部署
docker-compose up -d

# 或使用宝塔面板配置
docker-compose -f docker-compose.bt.yml up -d
```

### 3. 数据迁移（如有需要）
```bash
# 从旧路径迁移数据库
cp /path/to/old/exam.db /srv/yourapp/data/app.db

# 确保权限
chmod 777 /srv/yourapp/data/app.db
```

## 📁 目录结构

```
/srv/yourapp/
└── data/
    └── app.db          # SQLite 数据库文件
```

## 🔧 配置说明

### 环境变量
- `DATABASE_URL=sqlite:////data/app.db` （容器内路径）
- 宿主机挂载：`/srv/yourapp/data:/data`

### 自动路径检测
应用会自动检测运行环境：
- **容器环境**：使用 `/data/app.db`
- **开发环境**：使用 `instance/exam.db`

## 💾 备份与恢复

### 备份
```bash
cp /srv/yourapp/data/app.db /backup/location/app_backup_$(date +%Y%m%d_%H%M%S).db
```

### 恢复
```bash
cp /backup/location/app_backup_YYYYMMDD_HHMMSS.db /srv/yourapp/data/app.db
chmod 777 /srv/yourapp/data/app.db
```

## ✨ 优势

- ✅ **路径一致性**：彻底解决路径不一致问题
- ✅ **权限简化**：一次性权限设置，无需复杂管理
- ✅ **数据安全**：数据库独立于代码，容器重建不丢失
- ✅ **迁移简单**：只需复制一个文件
- ✅ **运维友好**：符合生产环境最佳实践

## 📝 注意事项

1. 确保 `/srv/yourapp/data` 目录存在且权限正确
2. 首次部署会自动创建数据库文件
3. 数据迁移时注意备份原数据
4. 定期备份数据库文件
