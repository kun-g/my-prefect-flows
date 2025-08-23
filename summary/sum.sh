#!/bin/bash

# https://github.com/orgs/LambdaTheory/discussions/13

# 设置正确的编码环境
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# 使用变量存储文件路径
_FILE="./inbox/《SEO外链建设实战手册》    Web.Cafe.md"
# _FILE="./inbox/0 资源，做出 3 个日 UV 过十万、7-8 个日 UV 过万的网站，分享我获得无限网站流量的秘籍.md"
_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
_FILE_NAME=$(basename "$_FILE")
_OUTPUT="./output/${_FILE_NAME}_${_TIMESTAMP}.md"

# 检查文件是否存在
if [[ ! -f "$_FILE" ]]; then
    echo "错误：文件不存在: $_FILE"
    exit 1
fi

# 构建提示信息
_Prompt1="对文件 '$_FILE' 内容按，分析文章的类型，和内容主题。"

_Prompt2="对文件 '$_FILE' 内容按以下流程进行分析，并输出到 '$_OUTPUT' 文件中：
1. 进行基本性质判断
2. 基于基本总结策略和类型总结策略进行总结

## 基本性质
类型特征包括（同一属性的多个值用,分割）：
- 类型
- 领域
- 来源
  - 来源
  - 链接(有链接的话)
- 作者
  - 相关介绍
- 引用资料:
  - [文内描述](链接)：文内的介绍、引用的原因

## 基本总结策略
- 涉及到代码、模板的，进行原文引用
- 对于引用的链接和资料的整理，要尽可能的完整，不要遗漏

## 类型总结策略
### 教程/理论
### 教程/实操
侧重总结操作流程，让后续的使用者可以照着操作

### 方法论

### 其他

## 领域
### 营销/数字营销/SEO优化
### 其它

"

# 执行 q chat 命令
# q chat --trust-all-tools "$_Prompt"
q chat --no-interactive --trust-all-tools "$_Prompt1"
