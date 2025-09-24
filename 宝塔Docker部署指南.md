# 🚀 CBIT AutoExam 宝塔Docker部署指南

## 📋 准备工作

### 1. 宝塔面板要求
- 宝塔面板版本：7.0.0 或更高版本
- 已安装Docker管理器插件
- 服务器内存：至少2GB
- 服务器存储：至少10GB可用空间

### 2. 检查Docker环境
在宝塔面板中：
1. 进入 **软件商店** → **Docker管理器**
2. 如未安装，请先安装Docker管理器
3. 确保Docker服务正常运行

## 🔧 部署方法

### 方法一：使用宝塔Docker管理器（推荐）

#### 步骤1：上传项目文件
1. 在宝塔面板 **文件管理** 中创建目录：`/www/wwwroot/cbit-autoexam/`
2. 将项目文件上传到该目录，或使用Git克隆：
```bash
cd /www/wwwroot/
git clone https://github.com/reneverland/CBIT-AiExam-plus.git cbit-autoexam
cd cbit-autoexam
```

#### 步骤2：构建Docker镜像
1. 进入 **Docker管理器** → **镜像管理**
2. 点击 **构建镜像**
3. 填写以下信息：
   - **镜像名称**: `cbit-autoexam`
   - **版本标签**: `latest`
   - **Dockerfile路径**: `/www/wwwroot/cbit-autoexam/docker/Dockerfile`
   - **构建上下文**: `/www/wwwroot/cbit-autoexam/`

#### 步骤3：创建容器
1. 进入 **Docker管理器** → **容器管理**
2. 点击 **创建容器**
3. 填写以下配置：

**基础配置：**
- **容器名称**: `cbit-autoexam`
- **镜像**: `cbit-autoexam:latest`
- **端口映射**: `8080:8080`

**环境变量：**
```
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///instance/exam.db
```

**目录映射：**
```
/www/wwwroot/cbit-autoexam/instance:/app/instance
/www/wwwroot/cbit-autoexam/static/uploads:/app/static/uploads
```

**重启策略**: `always`

#### 步骤4：启动容器
1. 在容器列表中找到 `cbit-autoexam`
2. 点击 **启动**
3. 查看日志确认启动成功

### 方法二：使用Docker命令行

#### 在宝塔终端中执行：

```bash
# 进入项目目录
cd /www/wwwroot/cbit-autoexam

# 构建镜像
docker build -f docker/Dockerfile -t cbit-autoexam:latest .

# 运行容器
docker run -d \
  --name cbit-autoexam \
  --restart unless-stopped \
  -p 8080:8080 \
  -e FLASK_ENV=production \
  -e SECRET_KEY=your-secret-key-here \
  -e DATABASE_URL=sqlite:///instance/exam.db \
  -v /www/wwwroot/cbit-autoexam/instance:/app/instance \
  -v /www/wwwroot/cbit-autoexam/static/uploads:/app/static/uploads \
  cbit-autoexam:latest
```

## 🌐 配置反向代理

### 1. 创建站点
1. 在宝塔面板 **网站** 中点击 **添加站点**
2. 填写域名（如：`exam.yourdomain.com`）
3. 不需要创建数据库和FTP

### 2. 配置反向代理
1. 进入站点设置 → **反向代理**
2. 添加反向代理：
   - **代理名称**: `CBIT AutoExam`
   - **目标URL**: `http://127.0.0.1:8080`
   - **发送域名**: `$host`
   - **内容替换**: 留空

### 3. 配置SSL（可选）
1. 在站点设置中进入 **SSL**
2. 申请Let's Encrypt免费证书
3. 开启强制HTTPS

## 🛠️ 维护操作

### 查看容器状态
```bash
# 查看运行状态
docker ps | grep cbit-autoexam

# 查看日志
docker logs cbit-autoexam

# 查看详细信息
docker inspect cbit-autoexam
```

### 更新应用
```bash
# 停止容器
docker stop cbit-autoexam
docker rm cbit-autoexam

# 拉取最新代码
cd /www/wwwroot/cbit-autoexam
git pull origin main

# 重新构建和运行
docker build -f docker/Dockerfile -t cbit-autoexam:latest .
docker run -d \
  --name cbit-autoexam \
  --restart unless-stopped \
  -p 8080:8080 \
  -e FLASK_ENV=production \
  -e SECRET_KEY=your-secret-key-here \
  -e DATABASE_URL=sqlite:///instance/exam.db \
  -v /www/wwwroot/cbit-autoexam/instance:/app/instance \
  -v /www/wwwroot/cbit-autoexam/static/uploads:/app/static/uploads \
  cbit-autoexam:latest
```

### 备份数据
```bash
# 备份数据库
cp /www/wwwroot/cbit-autoexam/instance/exam.db /www/backup/exam.db.$(date +%Y%m%d_%H%M%S)

# 备份上传文件
tar -czf /www/backup/uploads_$(date +%Y%m%d_%H%M%S).tar.gz /www/wwwroot/cbit-autoexam/static/uploads/
```

## 🚨 故障排除

### 常见问题

1. **SQLite数据库权限错误**
```
错误：sqlite3.OperationalError) unable to open database file
```

**解决方案：**
```bash
# 方法1：快速修复（最推荐）
cd /www/wwwroot/cbit-autoexam
git pull origin main
chmod +x quick_fix.sh
./quick_fix.sh

# 方法2：使用权限修复脚本
cd /www/wwwroot/cbit-autoexam
git pull origin main
chmod +x fix_database_permissions.sh
./fix_database_permissions.sh

# 方法3：手动修复
# 停止容器
docker stop cbit-autoexam && docker rm cbit-autoexam

# 修复权限
chown -R www:www /www/wwwroot/cbit-autoexam/instance/
chmod 755 /www/wwwroot/cbit-autoexam/instance/
chmod 664 /www/wwwroot/cbit-autoexam/instance/exam.db

# 初始化数据库（如果需要）
cd /www/wwwroot/cbit-autoexam
PYTHONPATH=".:backend" python3 database/init_db.py

# 重新启动（使用用户映射）
USER_ID=$(id -u www)
GROUP_ID=$(id -g www)
docker run -d \
  --name cbit-autoexam \
  --restart unless-stopped \
  -p 8080:8080 \
  -e FLASK_ENV=production \
  -e SECRET_KEY=your-secret-key \
  -e DATABASE_URL=sqlite:///instance/exam.db \
  -u "$USER_ID:$GROUP_ID" \
  -v /www/wwwroot/cbit-autoexam/instance:/app/instance:rw \
  -v /www/wwwroot/cbit-autoexam/static/uploads:/app/static/uploads:rw \
  cbit-autoexam:latest
```

2. **容器启动失败**
```bash
# 查看详细错误日志
docker logs cbit-autoexam --tail 50

# 检查端口占用
netstat -tlnp | grep 8080

# 检查Docker镜像
docker images | grep cbit-autoexam
```

3. **无法访问应用**
- 检查防火墙是否开放8080端口
- 检查反向代理配置是否正确
- 确认容器正在运行：`docker ps | grep cbit`

4. **文件上传失败**
```bash
# 修复上传目录权限
chown -R www:www /www/wwwroot/cbit-autoexam/static/uploads/
chmod -R 755 /www/wwwroot/cbit-autoexam/static/uploads/
```

4. **内存不足**
- 确保服务器有足够内存（建议4GB+）
- 可以调整Docker容器内存限制

### 性能优化

1. **启用宝塔缓存**
- 在反向代理中启用静态文件缓存
- 设置适当的缓存时间

2. **配置日志轮转**
```bash
# 限制Docker日志大小
docker run ... --log-opt max-size=10m --log-opt max-file=3 ...
```

## 📊 监控和告警

### 1. 宝塔监控
1. 进入 **监控** → **容器监控**
2. 添加cbit-autoexam容器监控
3. 设置告警规则（CPU、内存、磁盘使用率）

### 2. 健康检查
```bash
# 创建健康检查脚本
cat > /www/server/cron/cbit_health_check.sh << 'EOF'
#!/bin/bash
CONTAINER_NAME="cbit-autoexam"
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo "容器 $CONTAINER_NAME 未运行，正在重启..."
    docker start $CONTAINER_NAME
    # 发送告警通知（可选）
    curl -X POST "your-webhook-url" -d "CBIT AutoExam容器异常重启"
fi
EOF

chmod +x /www/server/cron/cbit_health_check.sh

# 添加到宝塔计划任务（每5分钟执行一次）
# 在宝塔面板 -> 计划任务 中添加Shell脚本任务
```

## 🔐 安全建议

1. **修改默认密码**
   - 部署后立即登录管理后台修改admin密码
   
2. **定期更新**
   - 定期拉取最新代码更新
   - 关注安全补丁

3. **防火墙配置**
   - 只开放必要端口（80、443、8080）
   - 考虑使用宝塔的IP白名单功能

4. **SSL证书**
   - 强烈建议启用HTTPS
   - 定期检查证书有效期

## 📞 技术支持

如遇到问题，请：
1. 检查容器日志：`docker logs cbit-autoexam`
2. 查看系统资源使用情况
3. 参考项目文档：https://github.com/reneverland/CBIT-AiExam-plus

---

**🎉 部署完成后访问地址：**
- 直接访问：`http://your-server-ip:8080`
- 域名访问：`https://your-domain.com`
- 管理后台：`/admin/dashboard`
- 默认账号：`admin / imbagogo`
