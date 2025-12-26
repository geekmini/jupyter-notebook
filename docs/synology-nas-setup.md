# 群晖 NAS 本地化部署方案

在 DS923+ 上搭建 Airflow + Gitea + MinIO 的完整开发/生产环境。

## 目录

- [硬件配置](#硬件配置)
- [架构概述](#架构概述)
- [内存升级](#内存升级)
- [Docker Compose 配置](#docker-compose-配置)
- [域名配置](#域名配置)
- [部署步骤](#部署步骤)
- [CI/CD 工作流](#cicd-工作流)
- [运维命令](#运维命令)

## 硬件配置

### DS923+ 规格

| 项目 | 配置                          |
| ---- | ----------------------------- |
| 型号 | DS923+                        |
| CPU  | AMD Ryzen R1600 (2核 2.6GHz)  |
| 内存 | 4GB DDR4 ECC (建议升级)       |
| 存储 | 10.9TB HDD + 2×931GB NVMe SSD |

### 存储规划

```
/volume1 (HDD)
├── docker/minio/data      # MinIO 数据（大文件）
└── backups/               # 备份

/volume2 (SSD)
├── docker/postgres/       # PostgreSQL 数据
├── docker/gitea/          # Gitea 数据
├── docker/airflow/        # Airflow DAGs & Logs
└── docker/traefik/        # Traefik 配置
```

## 架构概述

```
┌─────────────────────────────────────────────────────────┐
│                    Synology DS923+                       │
├─────────────────────────────────────────────────────────┤
│  Traefik (反向代理)        :80, :443                     │
│    ├── git.home      → Gitea           :3000            │
│    ├── airflow.home  → Airflow         :8080            │
│    ├── minio.home    → MinIO Console   :9001            │
│    └── app.home      → Frontend        :80              │
├─────────────────────────────────────────────────────────┤
│  Gitea (Git 服务)                                        │
│    └── Gitea Actions Runner (CI/CD)                     │
├─────────────────────────────────────────────────────────┤
│  Airflow (LocalExecutor)                                │
│    ├── Webserver                                        │
│    └── Scheduler                                        │
├─────────────────────────────────────────────────────────┤
│  MinIO (S3 兼容存储)                                     │
├─────────────────────────────────────────────────────────┤
│  PostgreSQL (共享数据库)                                 │
│    ├── gitea                                            │
│    └── airflow                                          │
└─────────────────────────────────────────────────────────┘
```

### 预估资源占用

| 服务         | 内存       | 说明                  |
| ------------ | ---------- | --------------------- |
| DSM 系统     | ~500MB     | 基础开销              |
| PostgreSQL   | ~200MB     | 共享数据库            |
| Gitea        | ~150MB     | Git 服务              |
| Gitea Runner | ~100MB     | CI 执行器 (空闲时)    |
| MinIO        | ~200MB     | S3 存储               |
| Airflow      | ~600MB     | Scheduler + Webserver |
| Traefik      | ~50MB      | 反向代理              |
| **总计**     | **~1.8GB** | 留余量给任务          |

## 内存升级

### 推荐配置

**最佳选择**: SK Hynix (海力士) 16GB DDR4 2666 ECC SODIMM × 2

| 规格   | 要求                          |
| ------ | ----------------------------- |
| 类型   | DDR4 ECC SODIMM (非 RECC/REG) |
| 频率   | 2666MHz                       |
| 容量   | 16GB × 2 = 32GB               |
| 参考价 | ¥400-500                      |

### 兼容型号

| 品牌     | 型号             | 备注     |
| -------- | ---------------- | -------- |
| SK Hynix | HMA82GS7DJR8N-VK | 推荐     |
| Samsung  | M474A2K43DB1-CVF | 推荐     |


### 安装步骤

1. 关机并断电
2. 拆下原装 4GB 内存
3. 插入 2 条 16GB 内存
4. 开机，DSM 自动识别 32GB

## Docker Compose 配置

### 目录结构

```bash
# 在 NAS 上创建目录
mkdir -p /volume2/docker/{postgres,gitea,airflow/dags,airflow/logs,traefik}
mkdir -p /volume1/docker/minio/data
```

### 环境变量 (.env)

```bash
# /volume2/docker/.env

# PostgreSQL
DB_PASSWORD=your_secure_password_here

# MinIO
MINIO_USER=admin
MINIO_PASSWORD=your_minio_password_here

# Gitea Runner
RUNNER_TOKEN=your_gitea_runner_token

# Airflow
AIRFLOW_ADMIN_PASSWORD=your_airflow_password
```

### docker-compose.yaml

```yaml
# /volume2/docker/docker-compose.yaml
version: "3.8"

services:
  # ============================================
  # 反向代理
  # ============================================
  traefik:
    image: traefik:v3.2
    container_name: traefik
    restart: unless-stopped
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
    ports:
      - "80:80"
      - "8080:8080"  # Traefik Dashboard
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    deploy:
      resources:
        limits:
          memory: 64M

  # ============================================
  # 数据库 (共享)
  # ============================================
  postgres:
    image: postgres:15-alpine
    container_name: postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - /volume2/docker/postgres:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    deploy:
      resources:
        limits:
          memory: 256M
    command: >
      postgres
      -c shared_buffers=64MB
      -c effective_cache_size=128MB
      -c maintenance_work_mem=32MB
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U admin"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ============================================
  # Git 服务
  # ============================================
  gitea:
    image: gitea/gitea:latest
    container_name: gitea
    restart: unless-stopped
    environment:
      - USER_UID=1000
      - USER_GID=1000
      - GITEA__database__DB_TYPE=postgres
      - GITEA__database__HOST=postgres:5432
      - GITEA__database__NAME=gitea
      - GITEA__database__USER=admin
      - GITEA__database__PASSWD=${DB_PASSWORD}
      - GITEA__server__ROOT_URL=http://git.home
      - GITEA__server__DOMAIN=git.home
    volumes:
      - /volume2/docker/gitea:/data
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.gitea.rule=Host(`git.home`)"
      - "traefik.http.routers.gitea.entrypoints=web"
      - "traefik.http.services.gitea.loadbalancer.server.port=3000"
    depends_on:
      postgres:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 200M

  # ============================================
  # Gitea Actions Runner
  # ============================================
  gitea-runner:
    image: gitea/act_runner:latest
    container_name: gitea-runner
    restart: unless-stopped
    environment:
      - GITEA_INSTANCE_URL=http://gitea:3000
      - GITEA_RUNNER_REGISTRATION_TOKEN=${RUNNER_TOKEN}
      - GITEA_RUNNER_NAME=nas-runner
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /volume2/docker/gitea-runner:/data
    depends_on:
      - gitea
    deploy:
      resources:
        limits:
          memory: 128M

  # ============================================
  # S3 兼容存储
  # ============================================
  minio:
    image: minio/minio
    container_name: minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    volumes:
      - /volume1/docker/minio/data:/data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.minio-console.rule=Host(`minio.home`)"
      - "traefik.http.routers.minio-console.entrypoints=web"
      - "traefik.http.services.minio-console.loadbalancer.server.port=9001"
      - "traefik.http.routers.minio-api.rule=Host(`s3.home`)"
      - "traefik.http.routers.minio-api.entrypoints=web"
      - "traefik.http.services.minio-api.loadbalancer.server.port=9000"
    deploy:
      resources:
        limits:
          memory: 256M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ============================================
  # Airflow (合并 Webserver + Scheduler)
  # ============================================
  airflow:
    image: apache/airflow:2.10.4-python3.11
    container_name: airflow
    restart: unless-stopped
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://admin:${DB_PASSWORD}@postgres/airflow
      AIRFLOW__CORE__LOAD_EXAMPLES: "false"
      AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: "true"
      AIRFLOW__WEBSERVER__WORKERS: 1
      AIRFLOW__WEBSERVER__EXPOSE_CONFIG: "true"
      AIRFLOW__SCHEDULER__MIN_FILE_PROCESS_INTERVAL: 60
      AIRFLOW__LOGGING__LOGGING_LEVEL: INFO
      # MinIO 连接
      AWS_ACCESS_KEY_ID: ${MINIO_USER}
      AWS_SECRET_ACCESS_KEY: ${MINIO_PASSWORD}
      AWS_ENDPOINT_URL: http://minio:9000
    volumes:
      - /volume2/docker/airflow/dags:/opt/airflow/dags
      - /volume2/docker/airflow/logs:/opt/airflow/logs
      - /volume2/docker/airflow/plugins:/opt/airflow/plugins
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.airflow.rule=Host(`airflow.home`)"
      - "traefik.http.routers.airflow.entrypoints=web"
      - "traefik.http.services.airflow.loadbalancer.server.port=8080"
    depends_on:
      postgres:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 768M
    command: >
      bash -c "
        airflow db migrate &&
        airflow users create \
          --username admin \
          --password ${AIRFLOW_ADMIN_PASSWORD:-admin} \
          --firstname Admin \
          --lastname User \
          --role Admin \
          --email admin@example.com || true &&
        airflow webserver &
        airflow scheduler
      "

# ============================================
# 网络
# ============================================
networks:
  default:
    name: nas-network
```

### 数据库初始化脚本 (init-db.sql)

```sql
-- /volume2/docker/init-db.sql
-- 创建 Gitea 和 Airflow 数据库

CREATE DATABASE gitea;
CREATE DATABASE airflow;

-- 授权
GRANT ALL PRIVILEGES ON DATABASE gitea TO admin;
GRANT ALL PRIVILEGES ON DATABASE airflow TO admin;
```

## 域名配置

### 方式一：修改本机 hosts (最简单)

```bash
# Mac/Linux: /etc/hosts
# Windows: C:\Windows\System32\drivers\etc\hosts

192.168.1.XXX  git.home airflow.home minio.home s3.home
```

将 `192.168.1.XXX` 替换为 NAS 的实际 IP。

### 方式二：路由器 DNS

在路由器管理界面添加静态 DNS 记录，所有设备自动生效。

### 方式三：群晖 DNS Server

1. 安装 DNS Server 套件
2. 创建 `home` 区域
3. 添加 A 记录指向 NAS IP

## 部署步骤

### 1. 准备工作

```bash
# SSH 登录到 NAS
ssh admin@192.168.1.XXX

# 创建目录结构
sudo mkdir -p /volume2/docker/{postgres,gitea,gitea-runner,airflow/dags,airflow/logs,airflow/plugins,traefik}
sudo mkdir -p /volume1/docker/minio/data

# 设置权限
sudo chown -R 1000:1000 /volume2/docker/gitea
sudo chown -R 50000:50000 /volume2/docker/airflow
```

### 2. 创建配置文件

```bash
cd /volume2/docker

# 创建 .env 文件
cat > .env << 'EOF'
DB_PASSWORD=change_me_postgres_password
MINIO_USER=admin
MINIO_PASSWORD=change_me_minio_password
RUNNER_TOKEN=your_gitea_runner_token
AIRFLOW_ADMIN_PASSWORD=change_me_airflow_password
EOF

# 创建数据库初始化脚本
cat > init-db.sql << 'EOF'
CREATE DATABASE gitea;
CREATE DATABASE airflow;
GRANT ALL PRIVILEGES ON DATABASE gitea TO admin;
GRANT ALL PRIVILEGES ON DATABASE airflow TO admin;
EOF
```

### 3. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 检查状态
docker-compose ps
```

### 4. 配置 Gitea Runner

```bash
# 1. 访问 http://git.home 完成 Gitea 初始化
# 2. 创建管理员账号
# 3. 进入 Site Administration > Actions > Runners
# 4. 点击 "Create new Runner" 获取 token
# 5. 更新 .env 中的 RUNNER_TOKEN
# 6. 重启 runner
docker-compose restart gitea-runner
```

### 5. 验证服务

| 服务              | 地址                | 默认账号          |
| ----------------- | ------------------- | ----------------- |
| Traefik Dashboard | http://NAS_IP:8080  | -                 |
| Gitea             | http://git.home     | (初始化时创建)    |
| Airflow           | http://airflow.home | admin / (见 .env) |
| MinIO Console     | http://minio.home   | admin / (见 .env) |

## CI/CD 工作流

### 示例：部署 DAGs 到 Airflow

在 Gitea 仓库中创建 `.gitea/workflows/deploy.yaml`:

```yaml
name: Deploy DAGs
on:
  push:
    branches: [main]
    paths:
      - 'dags/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Sync DAGs
        run: |
          # Runner 可以直接访问 NAS 文件系统
          rsync -avz --delete ./dags/ /volume2/docker/airflow/dags/

      - name: Verify
        run: |
          echo "DAGs deployed:"
          ls -la /volume2/docker/airflow/dags/
```

### 示例：构建并部署前端

```yaml
name: Build and Deploy Frontend
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install and Build
        run: |
          npm ci
          npm run build

      - name: Deploy
        run: |
          rsync -avz --delete ./dist/ /volume2/docker/frontend/
```

## 运维命令

### 服务管理

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启单个服务
docker-compose restart airflow

# 查看日志
docker-compose logs -f airflow
docker-compose logs -f --tail=100 gitea

# 进入容器
docker exec -it airflow bash
docker exec -it gitea bash
```

### 备份

```bash
#!/bin/bash
# /volume2/docker/backup.sh

BACKUP_DIR="/volume1/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 备份 PostgreSQL
docker exec postgres pg_dumpall -U admin > $BACKUP_DIR/postgres.sql

# 备份 Gitea
tar -czf $BACKUP_DIR/gitea.tar.gz -C /volume2/docker gitea

# 备份 Airflow DAGs
tar -czf $BACKUP_DIR/airflow-dags.tar.gz -C /volume2/docker/airflow dags

echo "Backup completed: $BACKUP_DIR"
```

### 监控资源

```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
df -h /volume1 /volume2

# 查看内存
free -h
```

### 更新镜像

```bash
# 拉取最新镜像
docker-compose pull

# 重建并重启
docker-compose up -d --build

# 清理旧镜像
docker image prune -f
```

## 故障排查

### Airflow 无法连接数据库

```bash
# 检查 PostgreSQL 状态
docker-compose logs postgres

# 测试连接
docker exec -it postgres psql -U admin -d airflow -c "SELECT 1"
```

### Gitea Runner 无法注册

```bash
# 检查 token 是否正确
docker-compose logs gitea-runner

# 重新获取 token 并更新 .env
docker-compose restart gitea-runner
```

### 内存不足

```bash
# 检查内存使用
docker stats --no-stream

# 临时停止不需要的服务
docker-compose stop gitea-runner
```

## 参考链接

- [Synology DS923+ 官方规格](https://www.synology.cn/zh-cn/products/DS923+)
- [DS923+ 内存兼容列表](https://nascompares.com/ram/synology-ds923-compatible-ram-upgrade/)
- [Gitea 官方文档](https://docs.gitea.com/)
- [Apache Airflow 文档](https://airflow.apache.org/docs/)
- [Traefik 文档](https://doc.traefik.io/traefik/)
