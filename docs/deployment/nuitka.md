# 部署：Nuitka 可执行文件

## 适用场景
- 需要在受限环境分发二进制。
- 不方便直接安装 Python 依赖。

## 构建
```bash
pip install '.[build]'
./scripts/build_nuitka.sh
```

## 输出
- `dist/easyshift-maas`
- `dist/easyshift-maas-api`

## 注意
- 构建时间与平台相关。
- 建议在目标平台构建目标平台二进制。
