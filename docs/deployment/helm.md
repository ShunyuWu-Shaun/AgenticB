# 部署：Helm

Chart 路径：`charts/reflexflow-maas/`

## 关键 values
- `image.repository`
- `image.tag`
- `resources`
- `secrets.redisConn*`
- `secrets.mysqlConn*`

## 典型命令
```bash
helm upgrade --install reflexflow charts/reflexflow-maas \
  --set image.repository=<your-repo>/reflexflow-maas \
  --set image.tag=0.3.0 \
  --set secrets.redisConnSecretName=reflexflow-secrets \
  --set secrets.redisConnSecretKey=redis_conn \
  --set secrets.mysqlConnSecretName=reflexflow-secrets \
  --set secrets.mysqlConnSecretKey=mysql_conn
```

## 建议
- 连接字符串放 K8s Secret。
- 生产环境配合 Ingress/TLS。
