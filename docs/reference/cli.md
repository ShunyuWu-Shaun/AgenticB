# CLI 命令参考

入口：`easyshift-maas`

## Agentic
- `easyshift-maas parse-points --fields <json> [--points <json>] [--yaml <file>]`
- `easyshift-maas generate-draft --metadata <json> --fields <json> [--parser-result <json>] [--requirement ...]`
- `easyshift-maas run-agentic --metadata <json> --fields <json> [--points <json>] [--max-iterations 3] [--requirement ...]`

## 校验与评分
- `easyshift-maas validate-draft --draft <json>`
- `easyshift-maas quality-check (--template <json> | --draft <json>) [--samples <json>]`

## 点位与上下文
- `easyshift-maas load-catalog --yaml <file> --mode standard|legacy`
- `easyshift-maas build-context --catalog <json> --profiles <json> [--field <name>] [--missing-policy error|drop|zero]`

## 仿真
- `easyshift-maas simulate --template <json> --context <json>`
