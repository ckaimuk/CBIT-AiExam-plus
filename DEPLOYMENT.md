# 服务器部署指南

## 数据库路径问题解决方案

本项目已修复数据库路径在服务器环境下的问题。现在支持以下部署方式：

### 1. 使用部署脚本（推荐）

在服务器上使用 `deploy.py` 启动应用：

```bash
python deploy.py
```

此脚本会：
- 自动设置生产环境变量
- 在当前工作目录创建 `instance` 文件夹
- 自动初始化数据库
- 以生产模式启动应用

### 2. 使用环境变量

在服务器上设置环境变量后使用 `run.py`：

```bash
export FLASK_ENV=production
export DEPLOYMENT=server
export SECRET_KEY=your-production-secret-key
export FLASK_DEBUG=False
python run.py
```

### 3. 使用 .env 文件

在项目根目录创建 `.env` 文件：

```env
FLASK_ENV=production
DEPLOYMENT=server
SECRET_KEY=your-production-secret-key
FLASK_DEBUG=False
DATABASE_URL=sqlite:///instance/exam.db
```

然后运行：
```bash
python run.py
```

## 数据库文件位置

### 开发环境
- 路径：项目根目录/instance/exam.db
- 例如：`/Users/username/project/instance/exam.db`

### 生产环境
- 路径：当前工作目录/instance/exam.db
- 例如：`/home/username/project/instance/exam.db`

## 故障排除

### 问题1：`unable to open database file`

**解决方案：**
1. 确保 `instance` 目录存在且有写权限
2. 检查数据库文件路径是否正确
3. 使用绝对路径设置 `DATABASE_URL`

```bash
export DATABASE_URL="sqlite:////absolute/path/to/your/project/instance/exam.db"
```

### 问题2：数据库文件存在但无法访问

**解决方案：**
1. 检查文件权限：
```bash
chmod 644 instance/exam.db
chmod 755 instance/
```

2. 检查用户权限：
```bash
chown your-user:your-group instance/exam.db
```

### 问题3：数据丢失

如果你已经有数据库文件，确保：
1. 将现有的 `exam.db` 文件复制到正确的 `instance` 目录
2. 设置正确的文件权限
3. 使用绝对路径指定数据库位置

## 部署检查清单

- [ ] 项目代码已推送到服务器
- [ ] Python依赖已安装 (`pip install -r requirements.txt`)
- [ ] 数据库文件已复制到正确位置
- [ ] 环境变量已正确设置
- [ ] 8080端口未被占用
- [ ] 文件权限正确设置

## 快速部署命令

```bash
# 1. 进入项目目录
cd /path/to/your/project

# 2. 安装依赖
pip install -r requirements.txt

# 3. 复制数据库文件（如果存在）
cp /path/to/existing/exam.db instance/

# 4. 设置权限
chmod 755 instance/
chmod 644 instance/exam.db

# 5. 启动应用
python deploy.py
```
