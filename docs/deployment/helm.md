# 部署：Helm

Chart 路径：`charts/easyshift-maas/`

## 关键 values
- `image.repository`
- `image.tag`
- `resources`
- `secrets.redisConn*`
- `secrets.mysqlConn*`

## 典型命令
```bash
helm upgrade --install easyshift charts/easyshift-maas \
  --set image.repository=<your-repo>/easyshift-maas \
  --set image.tag=0.2.0 \
  --set secrets.redisConnSecretName=easyshift-secrets \
  --set secrets.redisConnSecretKey=redis_conn \
  --set secrets.mysqlConnSecretName=easyshift-secrets \
  --set secrets.mysqlConnSecretKey=mysql_conn
```

## 建议
- 连接字符串放 K8s Secret。
- 生产环境配合 Ingress/TLS。
