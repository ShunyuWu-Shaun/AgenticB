# CLI 命令参考

二进制入口：`easyshift-maas`

## 模板与草案
- `easyshift-maas sample-template --variant energy|quality`
- `easyshift-maas list-base-templates`
- `easyshift-maas generate-draft --metadata <json> --fields <json> [--requirement ...]`
- `easyshift-maas validate-draft --draft <json>`
- `easyshift-maas quality-check (--template <json> | --draft <json>) [--samples <json>]`

## 点位与上下文
- `easyshift-maas load-catalog --yaml <file> --mode standard|legacy`
- `easyshift-maas build-context --catalog <json> --profiles <json> [--field <name>] [--missing-policy error|drop|zero]`

## 仿真
- `easyshift-maas simulate --template <json> --context <json>`
