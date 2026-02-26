# CLI 命令参考

入口：`reflexflow-maas`

## Agentic
- `reflexflow-maas parse-points --fields <json> [--points <json>] [--yaml <file>]`
- `reflexflow-maas generate-draft --metadata <json> --fields <json> [--parser-result <json>] [--requirement ...]`
- `reflexflow-maas run-agentic --metadata <json> --fields <json> [--points <json>] [--max-iterations 3] [--requirement ...]`

## 校验与评分
- `reflexflow-maas validate-draft --draft <json>`
- `reflexflow-maas quality-check (--template <json> | --draft <json>) [--samples <json>]`

## 点位与上下文
- `reflexflow-maas load-catalog --yaml <file> --mode standard|legacy`
- `reflexflow-maas build-context --catalog <json> --profiles <json> [--field <name>] [--missing-policy error|drop|zero]`

## 仿真
- `reflexflow-maas simulate --template <json> --context <json>`
