# 🚀 服务器升级指南 - 筛选功能修复

本指南用于部署服务器的快速升级，修复题目筛选功能和优化数据库配置。

## 🎯 本次升级内容

### 🛠️ 主要修复
- ✅ **数据库路径标准化**: 统一使用 `/data/app.db`
- ✅ **题目筛选功能修复**: 前端筛选器与数据库标签完全匹配
- ✅ **权限简化**: 完全开放权限，避免复杂管理
- ✅ **数据持久化**: 数据独立于代码目录

### 🐛 解决的问题
- 筛选器无法正常筛选题目
- 数据库路径不一致导致的各种问题
- 容器重建时数据丢失风险

## 🚀 快速升级 (推荐)

### 方法一：使用专用升级脚本

```bash
# 1. 进入项目目录
cd /path/to/your/cbit-autoexam

# 2. 拉取最新代码 (或手动上传)
git pull origin main

# 3. 运行专用升级脚本
./upgrade_fix.sh
```

### 方法二：使用通用升级脚本

```bash
# 进入项目目录
cd /path/to/your/cbit-autoexam

# 运行通用升级脚本 (已包含修复功能)
./upgrade.sh
```

## 📋 手动升级步骤

如果自动脚本遇到问题，可以手动执行以下步骤：

### 1. 备份数据
```bash
# 备份现有数据库
cp instance/exam.db instance/exam_backup_$(date +%Y%m%d_%H%M%S).db

# 如果存在容器数据库也要备份
sudo cp /srv/yourapp/data/app.db /srv/yourapp/data/app_backup_$(date +%Y%m%d_%H%M%S).db
```

### 2. 停止服务
```bash
# 使用 docker-compose.yml
docker-compose down

# 或使用 docker-compose.bt.yml (宝塔环境)
docker-compose -f docker-compose.bt.yml down
```

### 3. 更新代码
```bash
git pull origin main
# 或手动上传修复后的文件
```

### 4. 准备新的数据库目录
```bash
# 创建新的数据目录
sudo mkdir -p /srv/yourapp/data
sudo chmod -R 777 /srv/yourapp/data

# 迁移数据库到新路径 (如果需要)
sudo cp instance/exam.db /srv/yourapp/data/app.db
sudo chmod 777 /srv/yourapp/data/app.db
```

### 5. 运行数据库修复
```bash
# 执行筛选标签修复
python3 database/fix_filter_tags.py

# 其他数据库迁移 (如果之前没执行过)
python3 database/migrate_quantity_control.py
python3 database/normalize_tags.py
```

### 6. 重启服务
```bash
# 重新构建镜像
docker-compose build --no-cache

# 启动服务
docker-compose up -d --force-recreate
```

## 🔍 验证升级结果

### 1. 检查服务状态
```bash
# 查看容器状态
docker ps

# 查看服务日志
docker logs cbit-autoexam
```

### 2. 测试访问
- 🌐 主页: http://localhost:8080
- 📋 题库管理: http://localhost:8080/question_management.html
- 🛠️ 管理后台: http://localhost:8080/admin/dashboard

### 3. 验证筛选功能
1. 访问题库管理页面
2. 测试学科筛选：数学、计算机科学、统计学、工程学
3. 测试难度筛选：高中水平、本科基础、本科高级、研究生水平
4. 测试题型筛选：选择题、简答题、编程题
5. 测试组合筛选功能

### 4. 检查数据库
```bash
# 检查数据库位置和权限
ls -la /srv/yourapp/data/

# 验证数据库内容
sqlite3 /srv/yourapp/data/app.db "SELECT COUNT(*) FROM questions;"

# 检查标签分布
sqlite3 /srv/yourapp/data/app.db "SELECT subject, COUNT(*) FROM questions GROUP BY subject;"
```

## 📂 新的目录结构

升级后的数据库和文件结构：

```
/srv/yourapp/
└── data/
    ├── app.db                    # 主数据库文件
    ├── app_backup_YYYYMMDD.db   # 自动备份文件
    └── ...

项目目录/
├── frontend/
│   └── question_management.html  # 修复的筛选页面
├── backend/
│   └── app.py                   # 优化的数据库配置
├── database/
│   └── fix_filter_tags.py      # 筛选修复脚本
├── docker/
│   └── Dockerfile               # 优化的容器配置
├── upgrade_fix.sh               # 专用升级脚本
└── upgrade.sh                   # 通用升级脚本
```

## 🛠️ 故障排除

### 常见问题

#### 1. 筛选功能仍然不工作
```bash
# 重新运行修复脚本
python3 database/fix_filter_tags.py

# 检查数据库标签
sqlite3 /srv/yourapp/data/app.db "SELECT DISTINCT difficulty FROM questions;"
```

#### 2. 数据库连接失败
```bash
# 检查数据库文件权限
ls -la /srv/yourapp/data/app.db

# 修复权限
sudo chmod 777 /srv/yourapp/data/app.db
```

#### 3. 容器启动失败
```bash
# 查看详细日志
docker logs cbit-autoexam

# 重新构建镜像
docker-compose build --no-cache
docker-compose up -d --force-recreate
```

#### 4. 数据库文件不存在
```bash
# 检查备份文件
ls -la instance/exam_backup_*
ls -la /srv/yourapp/data/app_backup_*

# 从备份恢复
cp instance/exam_backup_YYYYMMDD_HHMMSS.db /srv/yourapp/data/app.db
```

### 回滚方案

如果升级遇到问题，可以回滚到之前版本：

```bash
# 1. 停止服务
docker-compose down

# 2. 恢复数据库
cp instance/exam_backup_YYYYMMDD_HHMMSS.db instance/exam.db

# 3. 回滚代码 (如果是git仓库)
git checkout HEAD~1

# 4. 重启服务
docker-compose up -d
```

## 📞 技术支持

如果遇到问题，请提供以下信息：

1. 错误信息和日志
2. 系统环境 (操作系统、Docker版本)
3. 升级前的系统状态
4. 执行的具体步骤

## ✅ 升级成功标志

升级成功后，您应该看到：

- ✅ 容器正常运行 (`docker ps` 显示 cbit-autoexam)
- ✅ 网页可以正常访问
- ✅ 题库管理页面的筛选功能正常工作
- ✅ 数据库位于 `/srv/yourapp/data/app.db`
- ✅ 所有题目数据保持完整

🎉 **恭喜！您的CBIT智能考试系统已成功升级，筛选功能现在可以正常使用了！**
